# ================================================
# UTILITY ENVIRONMENTAL PERMITTING SCREENING TOOL
# ArcGIS Pro Python Toolbox (.pyt)
# ================================================
# Author: Leydi Patricia Puerto Bohorquez
# Credentials: MS Environmental Management, USF
#              Certificate in Geospatial Information
#              Science, GsAL Lab USF
# Current Role: Permit Facilitator, PG&E
#               Northern California
#
# PURPOSE:
# This Python Toolbox (.pyt) exposes the automated
# environmental permitting screening tool as a
# native ArcGIS Pro geoprocessing tool with a
# user interface. No coding required to run.
#
# HOW TO USE:
# 1. Copy this file to your project folder
# 2. In ArcGIS Pro open the Catalog pane
# 3. Navigate to this .pyt file
# 4. Double click to open the toolbox
# 5. Fill in the parameters and click Run
#
# TOOLS IN THIS TOOLBOX:
# 1. Single Project Screening - screen one location
# 2. Batch Project Screening  - screen CSV of locations
# ================================================

import arcpy
import os
import csv
import datetime


class Toolbox(object):
    """
    Utility Environmental Permitting Screening Toolbox.
    Provides automated GIS-based environmental screening
    for utility infrastructure projects.
    """

    def __init__(self):
        self.label = "Utility Environmental Permitting Screening"
        self.alias = "UtilityPermitScreening"
        self.description = (
            "Automated environmental permitting screening tool "
            "for utility infrastructure projects. Screens project "
            "locations against federal and state environmental "
            "constraint layers and generates permitting reports. "
            "Author: Leydi Patricia Puerto Bohorquez, "
            "Permit Facilitator, PG&E Northern California."
        )
        # List of tool classes in this toolbox
        self.tools = [SingleProjectScreening, BatchProjectScreening]


# ================================================
# SHARED CONSTRAINT DEFINITIONS
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
        "threshold": "Federal nexus projects that may affect listed species",
        "mitigation": "Biological Opinion may be required"
    },
    "ProtectedAreas": {
        "permit": "California Environmental Quality Act (CEQA) Review",
        "agency": "California Department of Fish and Wildlife (CDFW)",
        "regulation": "California Public Resources Code Section 21000",
        "timeline": "6-24 months depending on project complexity",
        "threshold": "Projects with potential significant environmental effects",
        "mitigation": "Mitigation measures or alternative designs may be required"
    },
    "WildfireHazard": {
        "permit": "CAL FIRE Building Standards and Fire Safe Regulations",
        "agency": "California Department of Forestry and Fire Protection",
        "regulation": "California Public Resources Code Section 4290",
        "timeline": "30-90 days",
        "threshold": "Construction in State Responsibility Area Fire Hazard Zones",
        "mitigation": "Fire-resistant construction and defensible space required"
    }
}


def run_screening_core(
    project_id, project_name, utility, point_path,
    buffer_distance, gdb, output_folder, run_date, messages
):
    """
    Core screening logic shared by both tools.
    Screens one project location against all constraint layers.

    Parameters:
    project_id (str): Unique project identifier
    project_name (str): Full project name
    utility (str): Utility company name
    point_path (str): Path to project point feature class
    buffer_distance (str): Buffer distance with units e.g. '500 Feet'
    gdb (str): Path to environmental constraints geodatabase
    output_folder (str): Folder to save outputs
    run_date (str): Formatted run date string
    messages: ArcPy messages object for toolbox logging

    Returns:
    dict: Screening results
    """
    arcpy.env.workspace = gdb
    arcpy.env.overwriteOutput = True

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    messages.addMessage(f"Screening: {project_id} — {project_name}")
    messages.addMessage(f"Buffer: {buffer_distance}")

    # Create buffer
    buffer_output = os.path.join(output_folder, "project_buffer.shp")
    arcpy.analysis.Buffer(
        in_features=point_path,
        out_feature_class=buffer_output,
        buffer_distance_or_field=buffer_distance,
        dissolve_option="ALL"
    )
    messages.addMessage("Buffer created")

    screening_results = {}
    flagged_permits = []

    # Screen each constraint layer
    for layer, info in CONSTRAINTS.items():
        try:
            intersect_out = os.path.join(
                output_folder, f"intersect_{layer}.shp"
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
                messages.addMessage(
                    f"  {layer}: FLAGGED — {info['permit']}"
                )
                if extra_detail:
                    messages.addMessage(f"    {extra_detail}")
            else:
                status = "CLEAR"
                messages.addMessage(f"  {layer}: CLEAR")

            screening_results[layer] = {
                "status": status,
                "count": count,
                "info": info,
                "extra": extra_detail
            }

        except Exception as e:
            messages.addWarningMessage(f"  {layer}: ERROR - {e}")
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
        messages.addMessage(
            f"  Hydrology: {hydro_risk} — {hydro_action}"
        )

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

    study_area = os.path.join(output_folder, "study_area.shp")
    arcpy.analysis.Buffer(
        in_features=point_path,
        out_feature_class=study_area,
        buffer_distance_or_field="1 Mile",
        dissolve_option="ALL"
    )

    clipped_layers = []
    for layer in CONSTRAINTS.keys():
        clipped_out = os.path.join(
            output_folder, f"clip_{layer}.shp"
        )
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
                        clipped_out, field,
                        f'"{val}"', "PYTHON3"
                    )
                clipped_layers.append(clipped_out)
        except Exception:
            pass

    final_layer = ""
    if clipped_layers:
        final_layer = os.path.join(
            output_folder,
            f"Final_Screening_{project_id}.shp"
        )
        arcpy.management.Merge(
            inputs=clipped_layers,
            output=final_layer
        )
        messages.addMessage(
            f"Final AGOL layer: {final_layer}"
        )

    # Generate report
    report_path = os.path.join(
        output_folder, f"Report_{project_id}.txt"
    )

    with open(report_path, "w") as f:
        f.write("=" * 65 + "\n")
        f.write("AUTOMATED ENVIRONMENTAL PERMITTING SCREENING REPORT\n")
        f.write("UTILITY INFRASTRUCTURE PROJECT — NORTHERN CALIFORNIA\n")
        f.write("=" * 65 + "\n")
        f.write(f"Generated:    {run_date}\n")
        f.write(f"Tool:         ArcPy Screening Toolbox v4.0\n")
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
        f.write(f"Buffer:       {buffer_distance}\n")
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
                    f"within {buffer_distance} buffer\n"
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

    messages.addMessage(f"Report saved: {report_path}")

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
# TOOL 1: SINGLE PROJECT SCREENING
# ================================================

class SingleProjectScreening(object):
    """
    Screens a single utility infrastructure project
    location against all environmental constraint layers.
    Fill in the form and click Run — no coding needed.
    """

    def __init__(self):
        self.label = "Single Project Screening"
        self.description = (
            "Screen one utility infrastructure project location "
            "against federal and state environmental constraint "
            "layers. Generates a permitting report and AGOL-ready "
            "combined constraint layer."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define tool parameters shown in the user interface."""

        # Parameter 0 - Project ID
        param_id = arcpy.Parameter(
            displayName="Project ID",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_id.value = "PGE-001"

        # Parameter 1 - Project Name
        param_name = arcpy.Parameter(
            displayName="Project Name",
            name="project_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_name.value = "My Utility Project"

        # Parameter 2 - Utility Company
        param_utility = arcpy.Parameter(
            displayName="Utility Company",
            name="utility",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_utility.value = "Pacific Gas and Electric (PG&E)"

        # Parameter 3 - Project Point Location
        param_point = arcpy.Parameter(
            displayName="Project Location (Point Feature)",
            name="project_point",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param_point.filter.list = ["Point"]

        # Parameter 4 - Buffer Distance
        param_buffer = arcpy.Parameter(
            displayName="Buffer Distance",
            name="buffer_distance",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input"
        )
        param_buffer.value = "500 Feet"

        # Parameter 5 - Environmental Constraints Geodatabase
        param_gdb = arcpy.Parameter(
            displayName="Environmental Constraints Geodatabase",
            name="gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )
        param_gdb.filter.list = ["Local Database"]

        # Parameter 6 - Output Folder
        param_output = arcpy.Parameter(
            displayName="Output Folder",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )

        # Parameter 7 - Output Report (derived)
        param_report = arcpy.Parameter(
            displayName="Output Report",
            name="output_report",
            datatype="DETextfile",
            parameterType="Derived",
            direction="Output"
        )

        return [
            param_id, param_name, param_utility,
            param_point, param_buffer, param_gdb,
            param_output, param_report
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        """Run the single project screening."""

        project_id = parameters[0].valueAsText
        project_name = parameters[1].valueAsText
        utility = parameters[2].valueAsText
        point_path = parameters[3].valueAsText
        buffer_distance = parameters[4].valueAsText
        gdb = parameters[5].valueAsText
        output_folder = os.path.join(
            parameters[6].valueAsText, project_id
        )
        run_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        messages.addMessage("=" * 60)
        messages.addMessage(
            "UTILITY ENVIRONMENTAL PERMITTING SCREENING TOOL"
        )
        messages.addMessage(f"Project: {project_id} — {project_name}")
        messages.addMessage(f"Run Date: {run_date}")
        messages.addMessage("=" * 60)

        result = run_screening_core(
            project_id, project_name, utility,
            point_path, buffer_distance,
            gdb, output_folder, run_date, messages
        )

        messages.addMessage("\n" + "=" * 60)
        messages.addMessage("SCREENING COMPLETE")
        messages.addMessage(
            f"Permits triggered: {result['flagged_count']}"
        )
        messages.addMessage(
            f"Hydrological risk: {result['hydro_risk']} "
            f"— {result['hydro_action']}"
        )
        messages.addMessage(f"Report: {result['report_path']}")
        messages.addMessage("=" * 60)

        parameters[7].value = result["report_path"]


# ================================================
# TOOL 2: BATCH PROJECT SCREENING
# ================================================

class BatchProjectScreening(object):
    """
    Screens multiple utility infrastructure project
    locations from a CSV file automatically.
    Add new projects to the CSV and run again.
    No coding required.
    """

    def __init__(self):
        self.label = "Batch Project Screening"
        self.description = (
            "Screen multiple utility infrastructure project "
            "locations from a CSV file. Generates individual "
            "reports for each project plus a master summary. "
            "To add new projects simply add rows to the CSV "
            "and run again."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define tool parameters shown in the user interface."""

        # Parameter 0 - Projects CSV File
        param_csv = arcpy.Parameter(
            displayName="Project Locations CSV File",
            name="projects_csv",
            datatype="DEFile",
            parameterType="Required",
            direction="Input"
        )
        param_csv.filter.list = ["csv"]

        # Parameter 1 - Environmental Constraints Geodatabase
        param_gdb = arcpy.Parameter(
            displayName="Environmental Constraints Geodatabase",
            name="gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )
        param_gdb.filter.list = ["Local Database"]

        # Parameter 2 - Output Folder
        param_output = arcpy.Parameter(
            displayName="Output Folder",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )

        # Parameter 3 - Spatial Reference
        param_sr = arcpy.Parameter(
            displayName="Spatial Reference for Project Points",
            name="spatial_reference",
            datatype="GPSpatialReference",
            parameterType="Optional",
            direction="Input"
        )
        param_sr.value = arcpy.SpatialReference(4326).exportToString()

        # Parameter 4 - Output Summary Report (derived)
        param_summary = arcpy.Parameter(
            displayName="Batch Summary Report",
            name="summary_report",
            datatype="DETextfile",
            parameterType="Derived",
            direction="Output"
        )

        return [
            param_csv, param_gdb,
            param_output, param_sr, param_summary
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        """Run the batch project screening."""

        projects_csv = parameters[0].valueAsText
        gdb = parameters[1].valueAsText
        output_base = parameters[2].valueAsText
        sr_string = parameters[3].valueAsText
        run_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        # Parse spatial reference
        try:
            sr = arcpy.SpatialReference()
            sr.loadFromString(sr_string)
        except Exception:
            sr = arcpy.SpatialReference(4326)

        messages.addMessage("=" * 60)
        messages.addMessage(
            "BATCH ENVIRONMENTAL PERMITTING SCREENING v4.0"
        )
        messages.addMessage(
            "Author: Leydi Patricia Puerto Bohorquez"
        )
        messages.addMessage(
            "Role: Permit Facilitator, PG&E Northern California"
        )
        messages.addMessage(f"Run Date: {run_date}")
        messages.addMessage(f"CSV: {projects_csv}")
        messages.addMessage("=" * 60)

        # Read CSV
        projects = []
        with open(projects_csv, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                projects.append(row)

        messages.addMessage(f"Projects loaded: {len(projects)}")

        all_results = []

        for i, project in enumerate(projects):
            project_id = project["project_id"]
            project_name = project["project_name"]
            utility = project["utility"]
            lat = float(project["latitude"])
            lon = float(project["longitude"])
            buffer_ft = project["buffer_ft"] + " Feet"

            messages.addMessage(
                f"\nProject {i+1} of {len(projects)}: {project_id}"
            )

            # Create point shapefile for this project
            output_folder = os.path.join(output_base, project_id)
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            point_path = os.path.join(
                output_folder, f"point_{project_id}.shp"
            )

            arcpy.management.CreateFeatureclass(
                out_path=output_folder,
                out_name=f"point_{project_id}.shp",
                geometry_type="POINT",
                spatial_reference=sr
            )
            arcpy.management.AddField(
                point_path, "ProjID", "TEXT", field_length=20
            )
            arcpy.management.AddField(
                point_path, "ProjName", "TEXT", field_length=100
            )

            with arcpy.da.InsertCursor(
                point_path,
                ["SHAPE@XY", "ProjID", "ProjName"]
            ) as cursor:
                cursor.insertRow([
                    (lon, lat),
                    project_id,
                    project_name[:100]
                ])

            try:
                result = run_screening_core(
                    project_id, project_name, utility,
                    point_path, buffer_ft,
                    gdb, output_folder, run_date, messages
                )
                all_results.append(result)
            except Exception as e:
                messages.addWarningMessage(
                    f"Error screening {project_id}: {e}"
                )

        # Generate batch summary report
        summary_path = os.path.join(
            output_base, "BATCH_SUMMARY_REPORT.txt"
        )

        with open(summary_path, "w") as f:
            f.write("=" * 65 + "\n")
            f.write("BATCH ENVIRONMENTAL PERMITTING SCREENING\n")
            f.write("MASTER SUMMARY REPORT\n")
            f.write("=" * 65 + "\n")
            f.write(f"Generated:   {run_date}\n")
            f.write(
                f"Tool:        ArcPy Screening Toolbox v4.0\n"
            )
            f.write(
                f"Author:      Leydi Patricia Puerto Bohorquez\n"
            )
            f.write(
                f"Role:        Permit Facilitator, "
                f"PG&E Northern California\n"
            )
            f.write(f"Projects:    {len(all_results)}\n")
            f.write("=" * 65 + "\n\n")

            f.write("PORTFOLIO OVERVIEW\n")
            f.write("-" * 40 + "\n")
            total_flagged = sum(
                r["flagged_count"] for r in all_results
            )
            high_risk = sum(
                1 for r in all_results
                if r["hydro_risk"] == "HIGH"
            )
            no_permits = sum(
                1 for r in all_results
                if r["flagged_count"] == 0
            )
            f.write(
                f"Total Projects Screened:     {len(all_results)}\n"
            )
            f.write(
                f"Projects with Permits:       "
                f"{len(all_results) - no_permits}\n"
            )
            f.write(
                f"Projects Clear:              {no_permits}\n"
            )
            f.write(
                f"High Hydrological Risk:      {high_risk}\n"
            )
            f.write(
                f"Total Permit Triggers:       {total_flagged}\n\n"
            )

            f.write("PROJECT BY PROJECT RESULTS\n")
            f.write("-" * 40 + "\n")
            for r in all_results:
                f.write(
                    f"\n{r['project_id']}: {r['project_name']}\n"
                )
                if r["flagged_count"] > 0:
                    f.write(
                        f"  Permits Triggered: {r['flagged_count']}\n"
                    )
                    for layer in r["flagged_layers"]:
                        f.write(
                            f"    - {CONSTRAINTS[layer]['permit']}\n"
                        )
                else:
                    f.write(f"  Permits Triggered: NONE\n")
                f.write(
                    f"  Hydrological Risk: {r['hydro_risk']} "
                    f"— {r['hydro_action']}\n"
                )
                f.write(f"  Report: {r['report_path']}\n")

            f.write("\n" + "=" * 65 + "\n")
            f.write("TO SCREEN NEW PROJECTS:\n")
            f.write("  1. Open project_locations.csv\n")
            f.write("  2. Add a new row with project details\n")
            f.write("  3. Run this tool again\n")
            f.write("  4. Reports generate automatically\n")
            f.write("=" * 65 + "\n")
            f.write("END OF BATCH SUMMARY\n")
            f.write("=" * 65 + "\n")

        messages.addMessage(f"Batch summary: {summary_path}")
        messages.addMessage("\n" + "=" * 60)
        messages.addMessage("BATCH SCREENING COMPLETE")
        messages.addMessage(f"Projects screened: {len(all_results)}")
        messages.addMessage(f"Reports in: {output_base}")
        messages.addMessage("=" * 60)

        parameters[4].value = summary_path
