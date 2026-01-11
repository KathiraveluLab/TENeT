# Data Sources & Methodology

## Overview

TENeT combines multiple public data sources to provide comprehensive telehealth infrastructure analysis for Alaska communities. This document details our data sources, processing methods, and quality considerations.

---

## 📊 Primary Data Sources

### 1. Healthcare Facilities

**Source:** OpenStreetMap (OSM)  
**License:** Open Database License (ODbL)  
**URL:** https://www.openstreetmap.org

**Data Coverage:**
- Hospitals, clinics, and pharmacies across Alaska
- Geocoded locations (latitude/longitude)
- Facility type classification
- Emergency service availability

**Quality Indicators:**
- ✅ **High Confidence:** Facilities with complete metadata, recent updates
- ⚠️ **Medium Confidence:** Basic information, older data
- ❌ **Low Confidence:** Incomplete records, unverified locations

**Known Limitations:**
- Rural areas may have incomplete coverage
- Small clinics may not be mapped
- Seasonal facility closures not tracked

---

### 2. Broadband Coverage

**Source:** FCC National Broadband Map  
**URL:** https://broadbandmap.fcc.gov  
**License:** Public Domain

**Metrics Tracked:**
- Download/upload speeds (Mbps)
- Coverage percentage by census block
- Primary technology type (fiber, cable, satellite, DSL)
- Provider availability

**Quality Indicators:**
- ✅ **High:** Multiple providers, terrestrial connections
- ⚠️ **Medium:** Single provider, or mixed terrestrial/satellite
- ❌ **Low:** Satellite-only, or no reported data

**Data Gaps:**
- Satellite-dependent communities (Starlink not fully represented)
- Speed tests may not reflect real-world performance
- Coverage maps don't account for affordability

---

### 3. Transportation Access

**Source:** Alaska Department of Transportation & Public Facilities (DOT&PF)  
**URL:** http://dot.alaska.gov

**Categories:**
- ✈️ **Air:** Airport presence and type (jet, prop, bush plane only)
- 🚢 **Water:** Harbor/port facilities, seasonal ferry service
- 🚗 **Road:** Highway system connectivity
- 🧊 **Ice Roads:** Winter-only access routes

**Seasonal Considerations:**
- **Summer:** Water routes open, ice roads closed
- **Winter:** Ice roads accessible, rivers frozen, some harbors closed
- **Year-Round:** Conservative baseline assuming worst-case access

**Access Tier Classification:**
- **Tier 1 (Well-connected):** Road + airport, or population >10,000
- **Tier 2 (Moderate):** Airport + harbor, or road access to smaller hubs
- **Tier 3 (Remote):** Air-only access, very isolated

---

## 🔬 Data Processing Methodology

### Community Record Creation

Each community in TENeT is built from:

1. **Base Data Collection**
   - Geographic coordinates (USGS, OSM)
   - Population estimates (US Census Bureau)
   - Administrative region (Alaska Native Regional Corporations, Boroughs)

2. **Healthcare Analysis**
   - Distance calculations to nearest facility (Haversine formula)
   - Facility density per 1000 population
   - Specialist availability assessment

3. **Connectivity Assessment**
   - Broadband availability mapping
   - Speed tier classification (FCC standards)
   - Technology type analysis

4. **Access Scoring**
   - Transport mode availability
   - Season-adjusted difficulty multipliers
   - Isolation factor calculation

### Quality Assurance

**Data Completeness Score:** Each community has a `data_completeness` metric (0.0-1.0) calculated as:

```
completeness = (fields_with_high_confidence + 0.5 * fields_with_medium_confidence) / total_fields
```

**Confidence Levels:**
- 🟢 **HIGH:** Multiple corroborating sources, recent data, verified accuracy
- 🟡 **MEDIUM:** Single source, older data, or partial verification
- 🔴 **LOW:** Inferred data, very old, or unverified
- ⚫ **MISSING:** No data available

---

## 📈 Healthcare Necessity Scoring

TENeT calculates a **Healthcare Necessity Score (0-100)** for each community:

### Scoring Components

1. **Distance to Nearest Facility (0-40 points)**
   - <10km: 5 points
   - 10-50km: 15 points
   - 50-100km: 25 points
   - 100-200km: 35 points
   - >200km: 40 points

2. **Local Facility Availability (0-30 points)**
   - 0 facilities: 30 points
   - 1 facility: 20 points
   - 2 facilities: 10 points
   - 3+ facilities: 5 points

3. **Population Pressure (0-15 points)**
   - <500: 15 points (high need per capita)
   - 500-1000: 12 points
   - 1000-3000: 8 points
   - 3000-10000: 5 points
   - >10000: 0 points (urban, more resources)

4. **Season Adjustment (0-15 points)**
   - Based on access tier and selected season
   - Tier 3 communities in winter get maximum points
   - Tier 1 communities get minimal seasonal impact

### Score Interpretation

- **0-30 (LOW):** Good healthcare access, telehealth supplementary
- **31-50 (MODERATE):** Some challenges, telehealth beneficial
- **51-70 (HIGH):** Significant healthcare desert, telehealth recommended
- **71-100 (CRITICAL):** Severe healthcare desert, telehealth essential

---

## 🔄 Data Update Cycle

**Current Status:** Prototype with sample data

**Production Roadmap:**

- **Healthcare Facilities:** Quarterly updates from OSM
- **Broadband Data:** Semi-annual from FCC releases
- **Transportation:** Annual from Alaska DOT
- **Population:** Annual from US Census estimates

**User Contributions:**
- Future versions may allow community members to report data gaps
- Crowdsourced verification of facility status
- Speed test integration for real-world connectivity data

---

## ⚖️ Ethical Considerations

### Data Privacy
- No personally identifiable information (PII) collected
- Aggregate community-level data only
- No tracking of individual healthcare needs

### Equity & Representation
- All Alaska communities treated equally in analysis
- No algorithmic bias in necessity scoring
- Transparent methodology for all calculations

### Limitations Disclosure
- Sample data represents prototype only
- Real-world conditions may vary significantly
- Professional medical assessment always recommended

---

## 📚 References

1. FCC National Broadband Map: https://broadbandmap.fcc.gov
2. OpenStreetMap: https://www.openstreetmap.org
3. Alaska DOT&PF: http://dot.alaska.gov
4. US Census Bureau Alaska: https://www.census.gov/quickfacts/AK
5. Haversine Formula: https://en.wikipedia.org/wiki/Haversine_formula

---

## 📧 Contact & Feedback

For questions about data sources or methodology:
- GitHub Issues: [Your Repository]
- Email: [Your Contact]
- Documentation: See ARCHITECTURE.md for technical details

---

**Last Updated:** January 11, 2026  
**Data Version:** 0.2.0 (Enhanced Prototype)  
**Next Review:** Q2 2026
