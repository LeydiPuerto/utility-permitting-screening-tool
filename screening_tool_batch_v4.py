# ================================================
# UTILITY ENVIRONMENTAL PERMITTING SCREENING TOOL
# Version 4.0 - Batch Processing Mode
# ================================================
# Author: Leydi Patricia Puerto Bohorquez
# Credentials: MS Environmental Management, USF
#              Certificate in Geospatial Information
#              Science, GsAL Lab USF
# Current Role: Permit Facilitator, PG&E
#               Northern California
#
# Purpose: Batch automated screening of multiple
# utility infrastructure project locations against
# federal and state environmental constraint layers.
#
# HOW TO USE:
# 1. Add your project locations to project_locations.csv
# 2. Update BASE path below to match your computer
# 3. Run this script in ArcGIS Pro Notebook
# 4. Reports and shapefiles generated automatically
#    for every project in the CSV
#
# Version History:
# v1.0 - Initial release: 5 constraint layers
# v2.0 - Added CAL FIRE Wildfire Hazard layer
# v3.0 - Full permit flagging, AGOL export ready
# v4.0 - Batch processing: screens multiple project
#         locations from CSV automatically
# ================================================

import arcpy
import os
import csv
import datetime

# ================================================
# CONFIGURATION
# Only change these paths to match your computer
# ================================================

BASE = r"C:\Users\PATRICIA\Documents\Work Paperwork\EB-2 NIW\Phyton_Arcpy"
GDB = os.path.join(BASE, "EnvironmentalConstraints.gdb")
INPUTS = os.path.join(BASE, "Inputs")
OUTPUTS = os.path.join(BASE, "Outputs")
PROJECTS_CSV = os.path.join(BASE, "project_locations.csv")

# ================================================
# ENVIRONMENTAL CONSTRAINT LAYERS
# With full permit flagging details
# ================================================

CONSTRAINTS = {
    "Wetlands": {
        "permit": "Section 404 Clean Water Act Permit",
        "agency": "U.S. Army Corps of Engineers (USACE) / EPA",
        "regulation": "33 U.S.C. 1344",
        "timeline": "Individual Permit: 6-18 months | Nationwide Permit: 45 days",
        "threshold": "Any discharge of dredge or fill material into waters of the U.S.",
        "mitigation": "Wetland mitigation banking or in-lieu fee program may be required"
    },
    "Floodplains": {
        "permit": "FEMA Floodplain Development Permit",
        "agency": "FEMA / Local Floodplain Administrator",
        "regulation": "44 CFR Part 60",
        "timeline": "30-60 days typically",
        "threshold": "Any development within Special Flood Hazard Area (SFHA)",
        "mitigation": "Flood elevation certificate and compensatory storage may be required"
    },
    "Streams": {
        "permit": "Section 401 Water Quality Certification",
        "agency": "California State Water Resources Control Board",
        "regulation": "33 U.S.C. 1341 / California Water Code Section 13160",
        "timeline": "60-180 days",
        "threshold": "Any federal permit that may result in discharge to waters",
        "mitigation": "Water quality monitoring and SWPPP required"
    },
    "CriticalHabitat": {
        "permit": "ESA Section 7 Formal Consultation",
        "agency": "U.S. Fish and Wildlife Service (USFWS) / NMFS",
        "regulation": "16 U.S.C. 1536",
        "timeline": "135 days for formal consultation",
        "threshold": "Federal nexus projects that may affect listed species or critical habitat",
        "mitigation": "Biological Opinion with reasonable and prudent alternatives may be required"
    },
    "ProtectedAreas": {
        "permit": "California Environmental Quality Act (CEQA) Review",
        "agency": "California Department of Fish and Wildlife (CDFW)",
        "regulation": "California Public Resources Code Section 21000 et seq.",
        "timeline": "6-24 months depending on project complexity",
        "threshold": "Projects with potential significant environmental effects",
        "mitigation": "Mitigation measures or alternative project designs may be required"
    },
    "WildfireHazard": {
        "permit": "CAL FIRE Building Standards and Fire Safe Regulations",
        "agency": "California Department of Forestry and Fire Protection (CAL FIRE)",
        "regulation": "California Public Resources Code Section 4290",
        "timeline": "30-90 days",
        "threshold": "Construction in State Responsibility Area Fire Hazard Severity Zones",
        "mitigation": "Fire-resistant construction standards and defensible space requirements"
    }
}

# ================================================
# HELPER FUNCTIONS
# ================================================

def create_project_point(project_id, lat, lon, name, utility):
    """
    Creates a point shapefile for a single project location.

    Parameters:
    project_id (str): Unique project identifier
    lat (float): Latitude in decimal degrees
    lon (float): Longitude in decimal degrees
    name (str): Project name
    utility (str): Utility company name

    Returns:
    str: Path to the created point shapefile
    """
    point_path = os.path.join(INPUTS, f"point_{project_id}.shp")
    sr = arcpy.SpatialReference(4326)

    arcpy.management.CreateFeatureclass(
        out_path=INPUTS,
        out_name=f"point_{project_id}.shp",
        geometry_type="POINT",
        spatial_reference=sr
    )
    arcpy.management.AddField(point_path, "ProjID", "TEXT", field_length=20)
    arcpy.management.AddField(point_path, "ProjName", "TEXT", field_length=100)
    arcpy.management.AddField(point_path, "Utility", "TEXT", field_length=50)

    with arcpy.da.InsertCursor(
        point_path, ["SHAPE@XY", "ProjID", "ProjName", "Utility"]
    ) as cursor:
        cursor.insertRow([(lon, lat), project_id, name[:100], utility[:50]])

    return point_path


def screen_project(project, run_date):
    """
    Runs the full environmental screening for one project.

    Parameters:
    project (dict): Project details from CSV row
    run_date (str): Formatted run date string

    Returns:
    dict: Screening results for this project
    """
    project_id = project["project_id"]
    project_name = project["project_name"]
    utility = project["utility"]
    lat = float(project["latitude"])
    lon = float(project["longitude"])
    buffer_ft = project["buffer_ft"] + " Feet"
    project_type = project["project_type"]
    notes = project["notes"]

    print(f"\n{'='*65}")
    print(f"SCREENING: {project_id} — {project_name}")
    print(f"{'='*65}")
    print(f"  Location:  {lat}N, {abs(lon)}W")
    print(f"  Buffer:    {buffer_ft}")
    print(f"  Type:      {project_type}")

    # Create project folder
    proj_output = os.path.join(OUTPUTS, project_id)
    if not os.path.exists(proj_output):
        os.makedirs(proj_output)

    # Create project point
    point_path = create_project_point(
        project_id, lat, lon, project_name, utility
    )

    # Create buffer
    buffer_output = os.path.join(proj_output, "project_buffer.shp")
    arcpy.analysis.Buffer(
        in_features=point_path,
        out_feature_class=buffer_output,
        buffer_distance_or_field=buffer_ft,
        dissolve_option="ALL"
    )

    screening_results = {}
    flagged_permits = []

    # Screen each constraint layer
    for layer, info in CONSTRAINTS.items():
        try:
            intersect_out = os.path.join(
                proj_output, f"intersect_{layer}.shp"
            )
            arcpy.analysis.Intersect(
                in_features=[buffer_output, layer],
                out_feature_class=intersect_out
            )
            count = int(
                arcpy.GetCount_management(intersect_out).getOutput(0)
            )

            extra_detail = ""
            if layer == "WildfireHazard" and count > 0:
                try:
                    with arcpy.da.SearchCursor(
                        intersect_out, ["FHSZ_Descr"]
                    ) as cursor:
                        classes = set(
                            row[0] for row in cursor if row[0]
                        )
                    extra_detail = f"Hazard Class: {', '.join(classes)}"
                except Exception:
                    pass

            if count > 0:
                status = "FLAGGED"
                flagged_permits.append(layer)
                print(f"  {layer}: FLAGGED — {info['permit']}")
                if extra_detail:
                    print(f"    {extra_detail}")
            else:
                status = "CLEAR"
                print(f"  {layer}: CLEAR")

            screening_results[layer] = {
                "status": status,
                "count": count,
                "info": info,
                "extra": extra_detail
            }

        except Exception as e:
            print(f"  {layer}: ERROR - {e}")
            screening_results[layer] = {
                "status": "ERROR",
                "count": 0,
                "info": info,
                "extra": ""
            }

    # Hydrological proximity analysis
    try:
        arcpy.analysis.Near(
            in_features=buffer_output,
            near_features="Streams",
            search_radius="1 Miles"
        )
        with arcpy.da.SearchCursor(
            buffer_output, ["NEAR_DIST"]
        ) as cursor:
            for row in cursor:
                dist = max(row[0], 0)

        if dist < 100:
            hydro_risk = "HIGH"
            hydro_action = "IMMEDIATE ACTION REQUIRED"
        elif dist < 300:
            hydro_risk = "MEDIUM"
            hydro_action = "ASSESSMENT RECOMMENDED"
        elif dist < 1000:
            hydro_risk = "LOW-MEDIUM"
            hydro_action = "STANDARD CONTROLS REQUIRED"
        else:
            hydro_risk = "LOW"
            hydro_action = "MONITOR"

        hydro_note = (
            f"Project is {dist:.1f} ft from nearest waterway. "
            f"{hydro_action}."
        )
        print(f"  Hydrology: {hydro_risk} — {hydro_action}")

    except Exception as e:
        hydro_risk = "UNDETERMINED"
        hydro_action = "MANUAL REVIEW REQUIRED"
        hydro_note = f"Analysis error: {e}"
        dist = -1

    # Create final combined AGOL layer
    label_map = {
        "Wetlands": "Wetlands - Sec 404 CWA",
        "Floodplains": "Floodplains - FEMA",
        "Streams": "Streams - Sec 401",
        "CriticalHabitat": "Critical Habitat - ESA Sec 7",
        "ProtectedAreas": "Protected Areas - CEQA/CDFW",
        "WildfireHazard": "Wildfire Hazard - CALFIRE PRC 4290"
    }

    study_area = os.path.join(proj_output, "study_area.shp")
    arcpy.analysis.Buffer(
        in_features=point_path,
        out_feature_class=study_area,
        buffer_distance_or_field="1 Mile",
        dissolve_option="ALL"
    )

    clipped_layers = []
    for layer in CONSTRAINTS.keys():
        clipped_out = os.path.join(proj_output, f"clip_{layer}.shp")
        try:
            arcpy.analysis.Clip(
                in_features=layer,
                clip_features=study_area,
                out_feature_class=clipped_out
            )
            count = int(
                arcpy.GetCount_management(clipped_out).getOutput(0)
            )
            if count > 0:
                for field, length in [
                    ("CONSTTYPE", 60), ("PERMIT", 100),
                    ("AGENCY", 100), ("STATUS", 20),
                    ("PROJ_ID", 20), ("PROJ_NAME", 100)
                ]:
                    arcpy.management.AddField(
                        clipped_out, field, "TEXT",
                        field_length=length
                    )

                s = (
                    "FLAGGED"
                    if screening_results[layer]["status"] == "FLAGGED"
                    else "CLEAR"
                )
                for field, val in [
                    ("CONSTTYPE", label_map.get(layer, layer)),
                    ("PERMIT", CONSTRAINTS[layer]["permit"]),
                    ("AGENCY", CONSTRAINTS[layer]["agency"]),
                    ("STATUS", s),
                    ("PROJ_ID", project_id),
                    ("PROJ_NAME", project_name[:100])
                ]:
                    arcpy.management.CalculateField(
                        clipped_out, field, f'"{val}"', "PYTHON3"
                    )
                clipped_layers.append(clipped_out)

        except Exception as e:
            pass

    final_layer = ""
    if clipped_layers:
        final_layer = os.path.join(
            proj_output, f"Final_Screening_{project_id}.shp"
        )
        arcpy.management.Merge(
            inputs=clipped_layers,
            output=final_layer
        )

    # Generate individual project report
    report_path = os.path.join(
        proj_output, f"Report_{project_id}.txt"
    )

    with open(report_path, "w") as f:
        f.write("=" * 65 + "\n")
        f.write("AUTOMATED ENVIRONMENTAL PERMITTING SCREENING REPORT\n")
        f.write("UTILITY INFRASTRUCTURE PROJECT — NORTHERN CALIFORNIA\n")
        f.write("VERSION 4.0 — BATCH PROCESSING\n")
        f.write("=" * 65 + "\n")
        f.write(f"Generated:    {run_date}\n")
        f.write(f"Tool:         ArcPy Environmental Screening Tool v4.0\n")
        f.write(f"Author:       Leydi Patricia Puerto Bohorquez\n")
        f.write(
            f"Credentials:  MS Environmental Management, USF\n"
            f"              Certificate Geospatial Information "
            f"Science, GsAL Lab USF\n"
        )
        f.write(f"Role:         Permit Facilitator, PG&E Northern California\n")
        f.write(f"\nPROJECT DETAILS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Project ID:   {project_id}\n")
        f.write(f"Project Name: {project_name}\n")
        f.write(f"Utility:      {utility}\n")
        f.write(f"Type:         {project_type}\n")
        f.write(f"Coordinates:  {lat}N, {abs(lon)}W\n")
        f.write(f"Buffer:       {buffer_ft}\n")
        f.write(f"Notes:        {notes}\n")
        f.write("=" * 65 + "\n\n")

        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Constraints Screened: {len(CONSTRAINTS)}\n")
        f.write(f"Permits Triggered:    {len(flagged_permits)}\n")
        f.write(
            f"Constraints Clear:    "
            f"{len(CONSTRAINTS) - len(flagged_permits)}\n"
        )
        f.write(f"Hydrological Risk:    {hydro_risk}\n")
        f.write(f"Required Action:      {hydro_action}\n\n")

        if flagged_permits:
            f.write("PERMITS TRIGGERED:\n")
            for p in flagged_permits:
                f.write(f"  - {CONSTRAINTS[p]['permit']}\n")
        else:
            f.write("NO PERMITS TRIGGERED WITHIN BUFFER\n")
        f.write("\n")

        f.write("DETAILED SCREENING RESULTS\n")
        f.write("-" * 40 + "\n")
        for layer, result in screening_results.items():
            info = result["info"]
            f.write(f"\n{'='*40}\n")
            f.write(f"LAYER: {layer}\n")
            f.write(f"Status:      {result['status']}\n")
            if result["status"] == "FLAGGED":
                f.write(f"Features:    {result['count']}\n")
                f.write(f"Permit:      {info['permit']}\n")
                f.write(f"Agency:      {info['agency']}\n")
                f.write(f"Regulation:  {info['regulation']}\n")
                f.write(f"Timeline:    {info['timeline']}\n")
                f.write(f"Trigger:     {info['threshold']}\n")
                f.write(f"Mitigation:  {info['mitigation']}\n")
                if result["extra"]:
                    f.write(f"Details:     {result['extra']}\n")
            else:
                f.write(
                    f"Finding:     No constraints detected "
                    f"within {buffer_ft} buffer\n"
                )

        f.write(f"\n{'='*40}\n")
        f.write("HYDROLOGICAL PROXIMITY ANALYSIS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Risk Level:  {hydro_risk}\n")
        f.write(f"Action:      {hydro_action}\n")
        f.write(f"Finding:     {hydro_note}\n")
        f.write("=" * 65 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 65 + "\n")

    return {
        "project_id": project_id,
        "project_name": project_name,
        "flagged_count": len(flagged_permits),
        "flagged_layers": flagged_permits,
        "hydro_risk": hydro_risk,
        "hydro_action": hydro_action,
        "report_path": report_path,
        "final_layer": final_layer
    }


# ================================================
# BATCH SUMMARY REPORT
# ================================================

def generate_batch_summary(all_results, run_date):
    """
    Generates a master summary report for all projects.

    Parameters:
    all_results (list): List of result dicts from screen_project()
    run_date (str): Formatted run date string
    """
    summary_path = os.path.join(OUTPUTS, "BATCH_SUMMARY_REPORT.txt")

    with open(summary_path, "w") as f:
        f.write("=" * 65 + "\n")
        f.write("BATCH ENVIRONMENTAL PERMITTING SCREENING\n")
        f.write("MASTER SUMMARY REPORT\n")
        f.write("=" * 65 + "\n")
        f.write(f"Generated:   {run_date}\n")
        f.write(f"Tool:        ArcPy Environmental Screening Tool v4.0\n")
        f.write(f"Author:      Leydi Patricia Puerto Bohorquez\n")
        f.write(f"Role:        Permit Facilitator, PG&E Northern California\n")
        f.write(f"Projects:    {len(all_results)}\n")
        f.write("=" * 65 + "\n\n")

        f.write("PORTFOLIO OVERVIEW\n")
        f.write("-" * 40 + "\n")

        total_flagged = sum(r["flagged_count"] for r in all_results)
        high_risk = sum(1 for r in all_results if r["hydro_risk"] == "HIGH")
        no_permits = sum(
            1 for r in all_results if r["flagged_count"] == 0
        )

        f.write(f"Total Projects Screened:    {len(all_results)}\n")
        f.write(f"Projects with Permits:      {len(all_results) - no_permits}\n")
        f.write(f"Projects Clear (No Permits): {no_permits}\n")
        f.write(f"High Hydrological Risk:     {high_risk}\n")
        f.write(f"Total Permit Triggers:      {total_flagged}\n\n")

        f.write("PROJECT BY PROJECT RESULTS\n")
        f.write("-" * 40 + "\n")

        for r in all_results:
            f.write(f"\n{r['project_id']}: {r['project_name']}\n")
            if r["flagged_count"] > 0:
                f.write(f"  Permits Triggered: {r['flagged_count']}\n")
                for layer in r["flagged_layers"]:
                    f.write(f"    - {CONSTRAINTS[layer]['permit']}\n")
            else:
                f.write(f"  Permits Triggered: NONE\n")
            f.write(
                f"  Hydrological Risk: {r['hydro_risk']} "
                f"— {r['hydro_action']}\n"
            )
            f.write(f"  Full Report: {r['report_path']}\n")

        f.write("\n" + "=" * 65 + "\n")
        f.write("END OF BATCH SUMMARY\n")
        f.write("=" * 65 + "\n")

    print(f"\n  Batch summary saved: {summary_path}")
    return summary_path


# ================================================
# MAIN BATCH RUNNER
# ================================================

def run_batch():
    """
    Main batch processing function.
    Reads project_locations.csv and screens every project.
    Generates individual reports and one master summary.

    TO ADD A NEW PROJECT:
    Simply add a new row to project_locations.csv and run again.
    No code changes needed.
    """

    arcpy.env.workspace = GDB
    arcpy.env.overwriteOutput = True
    run_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    print("=" * 65)
    print("BATCH ENVIRONMENTAL PERMITTING SCREENING — v4.0")
    print("=" * 65)
    print(f"Author:   Leydi Patricia Puerto Bohorquez")
    print(f"Role:     Permit Facilitator, PG&E Northern California")
    print(f"Run Date: {run_date}")
    print(f"CSV:      {PROJECTS_CSV}")

    # Read projects from CSV
    if not os.path.exists(PROJECTS_CSV):
        print(f"\nERROR: CSV not found at {PROJECTS_CSV}")
        print("Please create project_locations.csv with your project list.")
        return

    projects = []
    with open(PROJECTS_CSV, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            projects.append(row)

    print(f"Projects loaded: {len(projects)}")
    print("=" * 65)

    # Screen each project
    all_results = []
    for i, project in enumerate(projects):
        print(f"\nProject {i+1} of {len(projects)}")
        try:
            result = screen_project(project, run_date)
            all_results.append(result)
        except Exception as e:
            print(f"  ERROR screening {project['project_id']}: {e}")

    # Generate master summary
    print("\n" + "=" * 65)
    print("GENERATING BATCH SUMMARY REPORT...")
    summary_path = generate_batch_summary(all_results, run_date)

    # Final output
    print("\n" + "=" * 65)
    print("BATCH SCREENING COMPLETE")
    print("=" * 65)
    print(f"Projects screened: {len(all_results)}")
    print(f"Reports saved in:  {OUTPUTS}")
    print(f"Summary report:    {summary_path}")
    print("\nTO SCREEN NEW PROJECTS:")
    print("  1. Open project_locations.csv")
    print("  2. Add a new row with your project details")
    print("  3. Run this script again")
    print("  4. Reports generate automatically")
    print("=" * 65)


# ================================================
# RUN THE BATCH TOOL
# ================================================

if __name__ == "__main__":
    run_batch()
