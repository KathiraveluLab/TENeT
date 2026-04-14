# Data Quality Findings & Project Update: TENeT

## Overview
I have successfully implemented the first phase of the **TENeT (Telehealth Effectiveness and Necessity Tracker for +Alaska)** data pipeline and map visualization. This update includes a Python-based ingestion script that pulls facility data from **healthsites.io** and a React map interface using **react-leaflet**.

## Key Data Quality Findings
After querying and normalizing the healthsites.io data for the Alaska region, I observed several significant characteristics:

### 1. Western Alaska Coverage Gap
The most critical finding is the **sparse data density in remote Western Alaska**. While major urban centers like Anchorage, Fairbanks, and Juneau are well-represented, many remote villages and tribal clinics in the Western and Northern regions are missing from the public healthsites.io dataset. This confirms our initial hypothesis: public crowdsourced data alone is insufficient to map the true healthcare landscape of rural Alaska.

### 2. Attribution Inconsistency
The facility types (amenities) vary significantly in the source data, ranging from `hospital` and `clinic` to generic `doctor` tags. Normalization logic was required to group these into a consistent taxonomy for the Healthcare Desert Index (HDI).

### 3. Coordinate Accuracy
Most facility centroids align well with OSM data, but some rural entries lack high-resolution coordinates, which may impact the precision of the HDI calculation at the village level.

## Next Steps
To address the coverage gap, the next phase of development will focus on integrating:
- **FCC National Broadband Map** data to overlay internet feasibility.
- **ANTHC (Alaska Native Tribal Health Consortium)** records to fill the tribal clinic data gap.
- Refinement of the **HDI formula** to account for travel distance to the nearest mapped facility.

## PR Link
[LINK_TO_PULL_REQUEST_HERE]

---
*This post is part of the ongoing development for the TENeT project. Feedback on the HDI scoring methodology is welcomed in this discussion thread.*
