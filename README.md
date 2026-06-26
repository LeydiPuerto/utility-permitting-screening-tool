# Utility Environmental Permitting Screening Tool

**Author:** Leydi Patricia Puerto Bohorquez  
**Credentials:** MS Environmental Management, University of San Francisco | Certificate in Geospatial Information Science, GsAL Lab USF  
**Current Role:** Permit Facilitator, Pacific Gas & Electric (PG&E), Northern California  

---

## Overview

An ArcPy-based automated GIS screening tool that evaluates utility infrastructure project locations against federal and state environmental constraint layers to support environmental compliance and permitting decisions for critical infrastructure in the United States.

This tool was developed to address a documented national challenge: environmental permitting delays that slow grid modernization, wildfire mitigation, and clean energy deployment across the United States. According to the U.S. Department of Energy, major transmission projects take an average of 10 years to complete, with permitting identified as a key contributing factor. This tool replaces manual, fragmented data cross-referencing with automated GIS-based environmental screening.

---

## What This Tool Does

Given a utility infrastructure project location, this tool automatically:

1. Creates a configurable buffer around the project area
2. Screens against five federal and state environmental constraint layers
3. Flags which environmental permits would be triggered
4. Runs a hydrological proximity analysis and assigns risk level
5. Generates a permitting screening report with permit types and agencies

---

## Environmental Constraint Layers Screened

| Layer | Data Source | Permit Triggered |
|---|---|---|
| Wetlands | USFWS National Wetlands Inventory (NWI) | Section 404 Clean Water Act |
| Floodplains | FEMA National Flood Hazard Layer | Floodplain Development Permit |
| Streams | USGS National Hydrography Dataset (NHD) | Section 401 Water Quality Certification |
| Critical Habitat | USFWS Critical Habitat Database | ESA Section 7 Consultation |
| Protected Areas | California Protected Areas Database (CAPAD) | State Environmental Review |

---

## Hydrological Screening

The tool calculates proximity to the nearest waterway and assigns a risk classification:

- **HIGH** — Project within 100 ft of waterway
- **MEDIUM** — Project within 300 ft of waterway
- **LOW-MEDIUM** — Project within 1000 ft of waterway
- **LOW** — Project beyond 1000 ft of waterway

---

## Tools and Requirements

- ArcGIS Pro 3.x
- Python 3.x (bundled with ArcGIS Pro)
- ArcPy library
- File Geodatabase with environmental constraint layers

---

## Data Sources

All datasets are publicly available at no cost:

- [USFWS National Wetlands Inventory](https://www.fws.gov/program/national-wetlands-inventory)
- [FEMA National Flood Hazard Layer](https://msc.fema.gov/portal/home)
- [USGS National Hydrography Dataset](https://www.usgs.gov/national-hydrography)
- [USFWS Critical Habitat](https://ecos.fws.gov/ecp/report/table/critical-habitat.html)
- [California Protected Areas Database](https://calands.datasettes.com)

---

## National Relevance

This tool directly supports national priorities in:
- **Grid modernization** — faster permitting for transmission infrastructure
- **Wildfire mitigation** — quicker environmental review in high-risk regions
- **Clean energy deployment** — reducing regulatory delays for renewable projects

---

## Status

Active development — Version 1.0 in progress
