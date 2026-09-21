# ================================================
# UTILITY ENVIRONMENTAL PERMITTING SCREENING TOOL
# Version 3.0
# ================================================
# Author: Leydi Patricia Puerto Bohorquez
# Credentials: MS Environmental Management, USF
#              Certificate in Geospatial Information
#              Science, GsAL Lab USF
# Current Role: Permit Facilitator, PG&E
#               Northern California
#
# Purpose: Automated ArcPy-based GIS screening tool
# that evaluates utility infrastructure project
# locations against federal and state environmental
# constraint layers to support permitting decisions
# for critical infrastructure in the United States.
#
# This tool replaces manual, fragmented data
# cross-referencing with automated GIS-based
# environmental screening, directly supporting
# faster permitting for grid modernization,
# wildfire mitigation, and clean energy deployment.
#
# Version History:
# v1.0 - Initial release: 5 constraint layers
# v2.0 - Added CAL FIRE Wildfire Hazard layer
# v3.0 - Full permit flagging, AGOL export ready,
#         comprehensive report with regulation
#         citations, timelines, and mitigation
# ================================================

import arcpy
import os
import datetime

# ================================================
# CONFIGURATION — Update these paths before running
# ================================================

BASE = r"C:\Users\PATRICIA\Documents\Work Paperwork\EB-2 NIW\Phyton_Arcpy"
GDB = os.path.join(BASE, "EnvironmentalConstraints.gdb")
INPUTS = os.path.join(BASE, "Inputs")
OUTPUTS = os.path.join(BASE, "Outputs")
PROJECT_POINT = os.path.join(INPUTS, "project_point.shp")
BUFFER_DISTANCE = "500 Feet"

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
        "threshold": "Any federal permit or license that may result in discharge to waters",
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
# RECOMMENDED FUTURE DATASETS
# ================================================

FUTURE_DATASETS = [
    "California Coastal Zone Boundary (Coastal Act jurisdiction)",
    "Migratory Bird Treaty Act (MBTA) Bird Conservation Regions",
    "California Groundwater Sustainability Agency (SGMA) Basins",
    "Native American Tribal Consultation Areas (NHPA Section 106)",
    "California Air Resources Board (CARB) Air Quality Basins",
    "USFWS National Bald Eagle Management Guidelines Zones",
    "USACE Regulatory Jurisdictional Determination Areas",
    "California Dept of Conservation Farmland Mapping (FMMP)",
    "State Historic Preservation Office (SHPO) Cultural Resources",
    "FEMA National Flood Insurance Program (NFIP) Policy Data"
]

# ================================================
# LAYER VISIBILITY MANAGER
# ================================================

def manage_layer_visibility(keep_visible_names):
    """
    Manages ArcGIS Pro map layer visibility.
    Shows only specified layers, hides all others.
    Works automatically as new layers are added.

    Parameters:
    keep_visible_names (list): Layer names to keep visible
    """
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        map_obj = aprx.activeMap or aprx.listMaps()[0]

        for lyr in map_obj.listLayers():
            if (not lyr.isGroupLayer and
                not lyr.isBasemapLayer and
                    lyr.supports("VISIBLE")):
                if any(k in lyr.name for k in keep_visible_names):
                    lyr.visible = True
                else:
                    lyr.visible = False

        aprx.save()
        print(f"  Map updated — visible: {', '.join(keep_visible_names)}")

    except Exception as e:
        print(f"  Map visibility update skipped: {e}")


def show_screening_result(layer_name):
    """
    Shows a specific screening result layer during the loop.
    Always keeps project point and buffer visible for context.

    Parameters:
    layer_name (str): Name of the intersect result layer to show
    """
    always_visible = ["project_point", "project_buffer"]
    manage_layer_visibility(always_visible + [layer_name])


def cycle_through_layers(layer_list):
    """
    Loops through constraint layers showing each one at a time.
    Useful for reviewing each dataset individually.

    Parameters:
    layer_list (list): List of layer names to cycle through
    """
    print("Cycling through constraint layers...")
    for i, layer_name in enumerate(layer_list):
        manage_layer_visibility(["project_point", layer_name])
        print(f"  Step {i+1}/{len(layer_list)}: {layer_name}")
    print("Cycle complete.")


# ================================================
# MAIN SCREENING FUNCTION
# ================================================

def run_screening():
    """
    Main function that runs the full environmental
    permitting screening workflow.
    """

    arcpy.env.workspace = GDB
    arcpy.env.overwriteOutput = True
    run_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    print("=" * 65)
    print("UTILITY ENVIRONMENTAL PERMITTING SCREENING TOOL v3.0")
    print("=" * 65)
    print(f"Author:   Leydi Patricia Puerto Bohorquez")
    print(f"Role:     Permit Facilitator, PG&E Northern California")
    print(f"Project:  Potrero to Marina Transmission Corridor")
    print(f"Utility:  Pacific Gas and Electric (PG&E)")
    print(f"Location: San Francisco, California")
    print(f"Run Date: {run_date}")
    print("=" * 65)

    # Validate inputs
    if not arcpy.Exists(PROJECT_POINT):
        print(f"ERROR: Project point not found: {PROJECT_POINT}")
        return

    if not os.path.exists(OUTPUTS):
        os.makedirs(OUTPUTS)

    screening_results = {}
    flagged_permits = []

    # ---- STEP 1: Project Buffer ----
    print("\nSTEP 1: Creating project buffer...")
    buffer_output = os.path.join(OUTPUTS, "project_buffer.shp")
    arcpy.analysis.Buffer(
        in_features=PROJECT_POINT,
        out_feature_class=buffer_output,
        buffer_distance_or_field=BUFFER_DISTANCE,
        dissolve_option="ALL"
    )
    print(f"  Buffer created: {BUFFER_DISTANCE} radius")

    # Show buffer on map
    manage_layer_visibility(["project_point", "project_buffer"])

    # ---- STEP 2: Screen All Constraints ----
    print("\nSTEP 2: Screening environmental constraints...")
    print("-" * 65)

    for layer, info in CONSTRAINTS.items():
        try:
            intersect_out = os.path.join(OUTPUTS, f"intersect_{layer}.shp")
            arcpy.analysis.Intersect(
                in_features=[buffer_output, layer],
                out_feature_class=intersect_out
            )
            count = int(
                arcpy.GetCount_management(intersect_out).getOutput(0)
            )

            extra_detail = ""

            # Get wildfire hazard class
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

            # Get wetland types
            if layer == "Wetlands" and count > 0:
                try:
                    with arcpy.da.SearchCursor(
                        intersect_out, ["WETLAND_TY"]
                    ) as cursor:
                        types = set(
                            row[0] for row in cursor if row[0]
                        )
                    extra_detail = f"Types: {', '.join(list(types)[:3])}"
                except Exception:
                    pass

            if count > 0:
                status = "FLAGGED"
                flagged_permits.append(layer)
                print(f"\n  *** {layer}: FLAGGED ***")
                if extra_detail:
                    print(f"      {extra_detail}")
                print(f"      Features:   {count}")
                print(f"      Permit:     {info['permit']}")
                print(f"      Agency:     {info['agency']}")
                print(f"      Regulation: {info['regulation']}")
                print(f"      Timeline:   {info['timeline']}")
            else:
                status = "CLEAR"
                print(f"\n  {layer}: CLEAR")

            screening_results[layer] = {
                "status": status,
                "count": count,
                "info": info,
                "extra": extra_detail
            }

            # Show each intersect result as it is processed
            show_screening_result(f"intersect_{layer}")

        except Exception as e:
            print(f"\n  {layer}: ERROR - {e}")
            screening_results[layer] = {
                "status": "ERROR",
                "count": 0,
                "info": info,
                "extra": ""
            }

    # ---- STEP 3: Hydrological Proximity ----
    print("\nSTEP 3: Hydrological proximity analysis...")
    print("-" * 65)

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
            hydro_note = (
                f"Project is {dist:.1f} ft from nearest waterway. "
                f"Section 404/401 permits highly likely. "
                f"Hydrological impact assessment required."
            )
        elif dist < 300:
            hydro_risk = "MEDIUM"
            hydro_action = "ASSESSMENT RECOMMENDED"
            hydro_note = (
                f"Project is {dist:.1f} ft from nearest waterway. "
                f"Hydrological assessment recommended."
            )
        elif dist < 1000:
            hydro_risk = "LOW-MEDIUM"
            hydro_action = "STANDARD CONTROLS REQUIRED"
            hydro_note = (
                f"Project is {dist:.1f} ft from nearest waterway. "
                f"Standard stormwater controls likely sufficient."
            )
        else:
            hydro_risk = "LOW"
            hydro_action = "MONITOR"
            hydro_note = (
                f"Project is {dist:.1f} ft from nearest waterway. "
                f"No immediate hydrological concern identified."
            )

        print(f"  Risk Level: {hydro_risk} — {hydro_action}")
        print(f"  Finding:    {hydro_note}")

    except Exception as e:
        hydro_risk = "UNDETERMINED"
        hydro_action = "MANUAL REVIEW REQUIRED"
        hydro_note = f"Analysis error: {e}"
        dist = -1
        print(f"  Error: {e}")

    # ---- STEP 4: Final Combined Layer for AGOL ----
    print("\nSTEP 4: Creating final layer for ArcGIS Online...")
    print("-" * 65)

    study_area = os.path.join(OUTPUTS, "study_area_1mile.shp")
    arcpy.analysis.Buffer(
        in_features=PROJECT_POINT,
        out_feature_class=study_area,
        buffer_distance_or_field="1 Mile",
        dissolve_option="ALL"
    )

    label_map = {
        "Wetlands": "Wetlands - Sec 404 CWA",
        "Floodplains": "Floodplains - FEMA",
        "Streams": "Streams - Sec 401",
        "CriticalHabitat": "Critical Habitat - ESA Sec 7",
        "ProtectedAreas": "Protected Areas - CEQA/CDFW",
        "WildfireHazard": "Wildfire Hazard - CALFIRE PRC 4290"
    }

    clipped_layers = []
    for layer in CONSTRAINTS.keys():
        clipped_out = os.path.join(OUTPUTS, f"clip_{layer}.shp")
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
                    ("CONSTTYPE", 60),
                    ("PERMIT", 100),
                    ("AGENCY", 100),
                    ("STATUS", 20)
                ]:
                    arcpy.management.AddField(
                        clipped_out, field, "TEXT",
                        field_length=length
                    )

                label = label_map.get(layer, layer)
                permit = CONSTRAINTS[layer]["permit"]
                agency = CONSTRAINTS[layer]["agency"]
                status = (
                    "FLAGGED"
                    if screening_results[layer]["status"] == "FLAGGED"
                    else "CLEAR"
                )

                arcpy.management.CalculateField(
                    clipped_out, "CONSTTYPE", f'"{label}"', "PYTHON3"
                )
                arcpy.management.CalculateField(
                    clipped_out, "PERMIT", f'"{permit}"', "PYTHON3"
                )
                arcpy.management.CalculateField(
                    clipped_out, "AGENCY", f'"{agency}"', "PYTHON3"
                )
                arcpy.management.CalculateField(
                    clipped_out, "STATUS", f'"{status}"', "PYTHON3"
                )
                clipped_layers.append(clipped_out)
                print(f"  {layer}: {count} features labeled")

        except Exception as e:
            print(f"  {layer}: Error - {e}")

    final_layer = ""
    if clipped_layers:
        final_layer = os.path.join(
            OUTPUTS, "Final_Environmental_Screening_v3.shp"
        )
        arcpy.management.Merge(
            inputs=clipped_layers,
            output=final_layer
        )
        total = arcpy.GetCount_management(final_layer).getOutput(0)
        print(f"\n  Final layer: {total} features")
        print(f"  Fields: CONSTTYPE, PERMIT, AGENCY, STATUS")
        print(f"  Saved: {final_layer}")
        print(f"  Ready for ArcGIS Online upload!")

        # Add to map and show only final layer
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            map_obj = aprx.activeMap or aprx.listMaps()[0]
            map_obj.addDataFromPath(final_layer)
            aprx.save()
        except Exception:
            pass

        manage_layer_visibility(
            ["project_point", "project_buffer",
             "Final_Environmental_Screening_v3"]
        )

    # ---- STEP 5: Generate Report ----
    print("\nSTEP 5: Generating comprehensive report...")

    report_path = os.path.join(
        OUTPUTS, "Permitting_Screening_Report_v3.txt"
    )

    with open(report_path, "w") as f:
        f.write("=" * 65 + "\n")
        f.write("AUTOMATED ENVIRONMENTAL PERMITTING SCREENING REPORT\n")
        f.write("UTILITY INFRASTRUCTURE PROJECT — NORTHERN CALIFORNIA\n")
        f.write("VERSION 3.0\n")
        f.write("=" * 65 + "\n")
        f.write(f"Generated:   {run_date}\n")
        f.write(f"Tool:        ArcPy Environmental Screening Tool v3.0\n")
        f.write(f"Author:      Leydi Patricia Puerto Bohorquez\n")
        f.write(
            f"Credentials: MS Environmental Management, USF\n"
            f"             Certificate Geospatial Information "
            f"Science, GsAL Lab USF\n"
        )
        f.write(f"Role:        Permit Facilitator, PG&E Northern California\n")
        f.write(f"Project:     Potrero to Marina Transmission Corridor\n")
        f.write(f"Utility:     Pacific Gas and Electric (PG&E)\n")
        f.write(f"Location:    San Francisco, California\n")
        f.write(f"Coordinates: 37.75683N, 122.38635W\n")
        f.write(f"Buffer:      {BUFFER_DISTANCE}\n")
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
                    f"within {BUFFER_DISTANCE} buffer\n"
                )

        f.write(f"\n{'='*40}\n")
        f.write("HYDROLOGICAL PROXIMITY ANALYSIS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Risk Level:  {hydro_risk}\n")
        f.write(f"Action:      {hydro_action}\n")
        f.write(f"Finding:     {hydro_note}\n\n")

        f.write("METHODOLOGY\n")
        f.write("-" * 40 + "\n")
        f.write(
            "This tool uses ArcPy spatial analysis to automatically\n"
            "screen utility infrastructure project locations against\n"
            "federal and state environmental constraint layers.\n"
            "It replaces manual, fragmented data cross-referencing\n"
            "with automated GIS-based environmental impact screening,\n"
            "directly supporting faster and more reliable permitting\n"
            "for U.S. utility infrastructure.\n\n"
        )
        f.write("DATA SOURCES:\n")
        sources = [
            ("USFWS National Wetlands Inventory (NWI)", "891,106"),
            ("FEMA National Flood Hazard Layer", "3,854,000"),
            ("USGS National Hydrography Dataset (NHD)", "484,774"),
            ("USFWS Critical Habitat Database", "803"),
            ("California Protected Areas Database (CAPAD)", "162,773"),
            ("CAL FIRE Fire Hazard Severity Zones (FHSZLRA25)", "9,752"),
        ]
        for i, (src, count) in enumerate(sources, 1):
            f.write(f"  {i}. {src} — {count} features\n")
        f.write(f"  Total Features Processed: 5,403,208\n\n")

        f.write("RECOMMENDED FUTURE DATASETS:\n")
        for i, dataset in enumerate(FUTURE_DATASETS, 1):
            f.write(f"  {i}. {dataset}\n")

        if final_layer:
            f.write("\nAGOL EXPORT:\n")
            f.write(f"  Layer: {final_layer}\n")
            f.write(f"  Fields: CONSTTYPE, PERMIT, AGENCY, STATUS\n")

        f.write("\n" + "=" * 65 + "\n")
        f.write("END OF REPORT — v3.0\n")
        f.write("=" * 65 + "\n")

    print(f"  Report saved: {report_path}")

    # ---- FINAL SUMMARY ----
    print("\n" + "=" * 65)
    print("SCREENING COMPLETE — v3.0")
    print("=" * 65)
    print(f"Constraints screened:  {len(CONSTRAINTS)}")
    print(f"Permits triggered:     {len(flagged_permits)}")
    if flagged_permits:
        print(f"Flagged layers:        {', '.join(flagged_permits)}")
    else:
        print("  No permits triggered within buffer")
    print(f"Hydrological risk:     {hydro_risk} — {hydro_action}")
    if final_layer:
        print(f"AGOL layer ready:      Final_Environmental_Screening_v3.shp")
    print(f"Report:                Permitting_Screening_Report_v3.txt")
    print("\nNEXT: Upload Final_Environmental_Screening_v3.shp to AGOL")
    print("=" * 65)


# ================================================
# RUN THE TOOL
# ================================================

if __name__ == "__main__":
    run_screening()
