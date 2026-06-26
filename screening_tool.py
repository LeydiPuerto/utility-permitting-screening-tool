# ================================================
# UTILITY ENVIRONMENTAL PERMITTING SCREENING TOOL
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
# ================================================

import arcpy
import os
import datetime

# ================================================
# CONFIGURATION — Update these paths before running
# ================================================

PROJECT_LOCATION = r"C:\NIW_Project\Inputs\project_point.shp"
GDB = r"C:\NIW_Project\EnvironmentalConstraints.gdb"
OUTPUT_FOLDER = r"C:\NIW_Project\Outputs"
BUFFER_DISTANCE = "500 Feet"

# ================================================
# ENVIRONMENTAL CONSTRAINT LAYERS
# All layers must be loaded into your geodatabase
# ================================================

CONSTRAINT_LAYERS = {
    "Wetlands": {
        "layer": "Wetlands",
        "permit": "Section 404 Clean Water Act Permit",
        "agency": "U.S. Army Corps of Engineers / EPA"
    },
    "Floodplains": {
        "layer": "Floodplains",
        "permit": "FEMA Floodplain Development Permit",
        "agency": "FEMA / Local Floodplain Administrator"
    },
    "Streams": {
        "layer": "Streams",
        "permit": "Section 401 Water Quality Certification",
        "agency": "California State Water Resources Control Board"
    },
    "CriticalHabitat": {
        "layer": "CriticalHabitat",
        "permit": "ESA Section 7 Consultation",
        "agency": "U.S. Fish and Wildlife Service / NMFS"
    },
    "ProtectedAreas": {
        "layer": "ProtectedAreas",
        "permit": "State Environmental Review Required",
        "agency": "California Department of Fish and Wildlife"
    }
}

# ================================================
# MAIN SCREENING FUNCTION
# ================================================

def run_screening():

    # Set workspace and environment
    arcpy.env.workspace = GDB
    arcpy.env.overwriteOutput = True

    print("=" * 55)
    print("UTILITY ENVIRONMENTAL PERMITTING SCREENING TOOL")
    print(f"Run Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    # Validate inputs
    if not arcpy.Exists(PROJECT_LOCATION):
        print(f"ERROR: Project location not found: {PROJECT_LOCATION}")
        return

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Created output folder: {OUTPUT_FOLDER}")

    screening_results = {}

    # ---- STEP 1: Create project buffer ----
    print("\nStep 1: Creating project area buffer...")
    project_buffer = os.path.join(OUTPUT_FOLDER, "project_buffer.shp")

    arcpy.analysis.Buffer(
        in_features=PROJECT_LOCATION,
        out_feature_class=project_buffer,
        buffer_distance_or_field=BUFFER_DISTANCE,
        line_side="FULL",
        line_end_type="ROUND",
        dissolve_option="ALL"
    )
    print(f"Buffer created: {BUFFER_DISTANCE} around project location")

    # ---- STEP 2: Screen environmental constraints ----
    print("\nStep 2: Running environmental constraint screening...")

    for name, info in CONSTRAINT_LAYERS.items():
        intersect_output = os.path.join(
            OUTPUT_FOLDER, f"intersect_{name}.shp"
        )

        try:
            arcpy.analysis.Intersect(
                in_features=[project_buffer, info["layer"]],
                out_feature_class=intersect_output,
                join_attributes="ALL"
            )

            count = int(
                arcpy.GetCount_management(intersect_output).getOutput(0)
            )

            if count > 0:
                screening_results[name] = {
                    "status": "FLAGGED",
                    "permit": info["permit"],
                    "agency": info["agency"],
                    "features": count
                }
                print(f"  {name}: FLAGGED ({count} overlapping features)")
            else:
                screening_results[name] = {
                    "status": "CLEAR",
                    "permit": info["permit"],
                    "agency": info["agency"],
                    "features": 0
                }
                print(f"  {name}: CLEAR")

        except arcpy.ExecuteError:
            print(f"  {name}: ERROR - {arcpy.GetLastMessage()}")
            screening_results[name] = {
                "status": "ERROR",
                "permit": info["permit"],
                "agency": info["agency"],
                "features": 0
            }

    # ---- STEP 3: Hydrological proximity analysis ----
    print("\nStep 3: Running hydrological proximity analysis...")

    try:
        arcpy.analysis.Near(
            in_features=project_buffer,
            near_features="Streams",
            search_radius="1 Miles",
            location="NO_LOCATION",
            angle="NO_ANGLE",
            method="PLANAR"
        )

        distance_ft = None
        with arcpy.da.SearchCursor(
            project_buffer, ["NEAR_DIST"]
        ) as cursor:
            for row in cursor:
                distance_ft = row[0]

        if distance_ft is not None and distance_ft >= 0:
            if distance_ft < 100:
                hydro_risk = "HIGH"
                hydro_detail = (
                    f"Project is {distance_ft:.1f} ft from nearest "
                    f"waterway. Section 404/401 permits highly likely. "
                    f"Hydrological impact assessment required."
                )
            elif distance_ft < 300:
                hydro_risk = "MEDIUM"
                hydro_detail = (
                    f"Project is {distance_ft:.1f} ft from nearest "
                    f"waterway. Hydrological assessment recommended. "
                    f"Monitor for stormwater and erosion impacts."
                )
            elif distance_ft < 1000:
                hydro_risk = "LOW-MEDIUM"
                hydro_detail = (
                    f"Project is {distance_ft:.1f} ft from nearest "
                    f"waterway. Standard stormwater controls "
                    f"likely sufficient."
                )
            else:
                hydro_risk = "LOW"
                hydro_detail = (
                    f"Project is {distance_ft:.1f} ft from nearest "
                    f"waterway. No immediate hydrological concern "
                    f"identified."
                )
        else:
            hydro_risk = "UNDETERMINED"
            hydro_detail = (
                "No stream features found within 1 mile search radius."
            )

        print(f"  Hydrological Risk: {hydro_risk}")
        print(f"  Detail: {hydro_detail}")

    except arcpy.ExecuteError:
        hydro_risk = "ERROR"
        hydro_detail = f"Analysis error: {arcpy.GetLastMessage()}"
        distance_ft = None
        print(f"  Hydrological analysis error: {arcpy.GetLastMessage()}")

    screening_results["Hydrological_Proximity"] = {
        "status": hydro_risk,
        "detail": hydro_detail,
        "distance_ft": distance_ft
    }

    # ---- STEP 4: Generate permitting screening report ----
    print("\nStep 4: Generating permitting screening report...")

    flagged_count = sum(
        1 for k, r in screening_results.items()
        if k != "Hydrological_Proximity" and r.get("status") == "FLAGGED"
    )

    report_path = os.path.join(
        OUTPUT_FOLDER, "Permitting_Screening_Report.txt"
    )

    with open(report_path, "w") as report:
        report.write("=" * 60 + "\n")
        report.write("UTILITY INFRASTRUCTURE\n")
        report.write("AUTOMATED ENVIRONMENTAL PERMITTING SCREENING REPORT\n")
        report.write("=" * 60 + "\n")
        report.write(
            f"Generated: "
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        )
        report.write("Tool: ArcPy Environmental Screening Tool v1.0\n")
        report.write(
            "Author: Leydi Patricia Puerto Bohorquez\n"
        )
        report.write(
            "Study Area: Northern California Utility Corridor\n"
        )
        report.write(f"Buffer Applied: {BUFFER_DISTANCE}\n")
        report.write("=" * 60 + "\n\n")

        report.write("EXECUTIVE SUMMARY\n")
        report.write("-" * 40 + "\n")
        report.write(f"Constraints Screened: {len(CONSTRAINT_LAYERS)}\n")
        report.write(f"Constraints Flagged: {flagged_count}\n")
        hydro = screening_results["Hydrological_Proximity"]
        report.write(
            f"Hydrological Risk Level: {hydro['status']}\n\n"
        )

        report.write("ENVIRONMENTAL CONSTRAINT SCREENING RESULTS\n")
        report.write("-" * 40 + "\n")

        for name, result in screening_results.items():
            if name == "Hydrological_Proximity":
                continue
            report.write(f"\n{name}:\n")
            report.write(f"  Status: {result['status']}\n")
            if result["status"] == "FLAGGED":
                report.write(
                    f"  Permit Required: {result['permit']}\n"
                )
                report.write(
                    f"  Reviewing Agency: {result['agency']}\n"
                )
                report.write(
                    f"  Overlapping Features: {result['features']}\n"
                )
            else:
                report.write(
                    "  No constraints detected in project buffer\n"
                )

        report.write("\nHYDROLOGICAL PROXIMITY ANALYSIS\n")
        report.write("-" * 40 + "\n")
        report.write(f"  Risk Level: {hydro['status']}\n")
        report.write(f"  Detail: {hydro['detail']}\n\n")

        report.write("METHODOLOGY\n")
        report.write("-" * 40 + "\n")
        report.write(
            "This tool uses ArcPy spatial analysis to automatically\n"
            "screen utility infrastructure project locations against\n"
            "federal and state environmental constraint layers.\n"
            "It replaces manual data cross-referencing with automated\n"
            "GIS-based screening, reducing review time and improving\n"
            "consistency in environmental permitting workflows for\n"
            "U.S. utility infrastructure projects.\n\n"
        )
        report.write("Data Sources:\n")
        report.write("  - USFWS National Wetlands Inventory (NWI)\n")
        report.write("  - FEMA National Flood Hazard Layer\n")
        report.write("  - USGS National Hydrography Dataset (NHD)\n")
        report.write("  - USFWS Critical Habitat Database\n")
        report.write(
            "  - California Protected Areas Database (CAPAD)\n"
        )
        report.write("=" * 60 + "\n")
        report.write("END OF REPORT\n")
        report.write("=" * 60 + "\n")

    print(f"Report saved: {report_path}")
    print("\nScreening complete.")
    print(f"Constraints flagged: {flagged_count} of {len(CONSTRAINT_LAYERS)}")
    print(f"Hydrological risk: {hydro_risk}")
    print(f"Full report: {report_path}")

# ================================================
# RUN THE TOOL
# ================================================

if __name__ == "__main__":
    run_screening()
