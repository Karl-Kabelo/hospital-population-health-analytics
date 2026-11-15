# Hospital Population Health & Clinical Operations Analytics Platform

An end-to-end healthcare analytics engineering and business intelligence portfolio project built on realistic synthetic electronic health records from [Synthea](https://github.com/synthetichealth/synthea) ([MITRE Corporation](https://synthea.mitre.org/downloads)). This platform demonstrates reproducible Python ETL pipelines, automated clinical data quality governance, dimensional star-schema modeling in SQLite/PostgreSQL, advanced analytical SQL (CTEs, window functions, cohort stratification), and a 4-page Power BI operational dashboard accompanied by an executive management report.

> **Synthetic Data Disclaimer:** All patient records, demographics, diagnoses, encounters, and financial claims in this repository are **100% synthetic** outputs generated according to the [Synthea CSV File Data Dictionary](https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary). Never cite these numbers as real-world clinical or epidemiological statistics.

## 1. Business Questions Answered
1. **Which patient groups use hospital services most frequently?** Seniors aged `65+` represent 22.2% of the cohort (111 patients) but generate **31.03% of all visits** (520 encounters; **4.68 visits/patient**), while multimorbid patients with `3+ chronic conditions` (117 patients) average **4.53 visits/patient**.
2. **What are the most common diagnoses?** Chronic cardiometabolic conditions lead cohort prevalence: **Essential hypertension** (`SNOMED 59621000`, **32.0%** of patients), **Obesity BMI 30+** (`162864005`, **25.0%**), **Prediabetes** (`15777000`, **21.8%**), and **Type 2 diabetes mellitus** (`44054006`, **21.4%**). Among acute diagnoses, **Pneumonia** (`233604007`) ranks #1 (**15.8%** patient prevalence).
3. **Which organisations have the highest admission and encounter volumes?** **Massachusetts General Regional Hospital (Boston)** leads with **478 encounters (28.52% share)** and the highest emergency visit rate (**14.02%**), followed by **Cambridge Health Alliance (374 visits, 22.32%)** and **Worcester Memorial Medical Center (317 visits, 18.91%)**.
4. **How do length of stay (LOS) and readmission rates vary?** Overall mean encounter duration is **18.25 hours** (`0.76 days`), stratified sharply between **inpatient admissions** (**144.69 hours / 6.03 days**, $18,209.16 mean claim cost), **emergency visits** (**8.58 hours**, $1,896.86), and **ambulatory visits** (**0.97 hours**, $321.25). Across 189 inpatient stays, the **30-day inpatient readmission rate is 18.52%** (35 readmissions), peaking at *Springfield Community Valley Hospital* (**27.59%**) and *Mass General Regional* (**23.40%**).
5. **Which patient groups need targeted outpatient follow-up?** The **59 super-utilizer patients** (`6+ encounters`, 11.80% of the cohort) generate **24.82% of all hospital visits (416 encounters)**, and seniors (`65+`) rely on the emergency department for **16.15% of their visits**.

## 2. Repository Architecture

```text
hospital-population-health-analytics/
│
├── data/
│   ├── raw/                        # 8 Synthea CSV exports (patients, encounters, conditions, etc.)
│   ├── processed/                  # Cleaned CSVs, Star Schema CSVs, and hospital_analytics.db
│   └── README.md                   # Complete Data Dictionary & Entity-Relationship Diagram
│
├── notebooks/
│   ├── 01_data_understanding.ipynb       # Schema inspection & PK/FK relationship audit
│   ├── 02_data_quality_assessment.ipynb  # Pre/post cleaning verification (DQ-01 to DQ-09)
│   └── 03_population_health_analysis.ipynb # KPI analysis & cohort visual exploration
│
├── scripts/
│   ├── extract_data.py             # Reproducible Synthea CSV generator & extractor
│   ├── clean_data.py               # Automated data cleaning & data_quality_report.csv builder
│   ├── transform_data.py           # Dimensional star-schema builder (LOS & 30d readmission flags)
│   └── load_database.py            # SQLite database loader with FK enforcement & indexing
│
├── sql/
│   ├── schema.sql                  # Relational DDL (4 dimensions, 4 fact tables, 8 indexes)
│   ├── data_quality_checks.sql     # 8 automated SQL post-load verification assertions
│   ├── healthcare_kpis.sql         # Executive KPI scorecard, MoM growth, chronic prevalence
│   └── analytical_queries.sql      # 12 core clinical operations & population health SQL queries
│
├── powerbi/
│   ├── hospital_analytics.pbix     # Power BI model package + DAX measures specification
│   └── dashboard_screenshots/      # 4 rendered 16:9 Power BI dashboard page views (PNG)
│
├── reports/
│   ├── data_quality_report.csv     # Structured audit of all 9 data quality checks
│   └── management_report.pdf       # 5-page executive management report with charts & tables
│
├── tests/
│   └── test_data_pipeline.py       # 7 automated unit & integration tests (unittest/pytest)
│
├── requirements.txt
├── README.md
└── .gitignore
```

## 3. Healthcare KPI Definitions & Operational Guardrails

| KPI Name | SQL / DAX Formula | Result | Operational Scope & Analytical Guardrail |
| :--- | :--- | ---: | :--- |
| **Total Unique Patients** | `COUNT(DISTINCT patient_id)` in `dim_patient` | `500` | Validated deduplicated cohort across the 2024–2025 observation window. |
| **Total Encounters** | `COUNT(encounter_id)` in `fact_encounter` | `1,676` | Measures clinical service volume, **not** physical hospital bed capacity. |
| **Avg Encounters / Patient** | `Total Encounters / Total Unique Patients` | `3.35` | Overall utilization intensity (median `3.0`, IQR `2.0–4.0`). |
| **Overall Avg LOS** | `AVG(los_hours)` across all encounter classes | `18.25 hrs` | Includes short outpatient/wellness visits (`<1 hr`) and multi-day inpatient stays. |
| **Inpatient Avg LOS** | `AVG(los_days) WHERE is_inpatient = 1` | `6.03 days` | True acute hospital stay duration (`144.69 hours` across 189 stays). |
| **Emergency Encounter Rate** | `SUM(is_emergency) / COUNT(encounter_id)` | `12.53%` | Share of all visits occurring in the Emergency Department (`210 / 1,676`). |
| **Repeat Patient Rate** | `Patients with >= 2 visits / Total Unique Patients` | `82.80%` | Measured across the full 24-month observation period (`414 / 500` patients). |
| **30-Day Readmission Rate** | `Inpatient stays followed by inpatient stay <= 30d / Total Inpatient Stays` | `18.52%` | Standard acute care quality indicator (`35 / 189` inpatient admissions). |

## 4. Quickstart & Reproducibility Instructions

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the end-to-end ETL pipeline
python3 scripts/extract_data.py
python3 scripts/clean_data.py
python3 scripts/transform_data.py
python3 scripts/load_database.py

# 3. Run the automated test suite (7/7 tests pass)
python3 -m unittest discover -s tests -v
```

## 5. Portfolio Completion Checklist (12 / 12 Completed — 100%)
- [x] Download or generate the [Synthea](https://github.com/synthetichealth/synthea) dataset (`data/raw/*.csv`)
- [x] Document the dataset and [CSV File Data Dictionary](https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary) (`data/README.md`)
- [x] Complete Python data cleaning (`scripts/clean_data.py`, `scripts/transform_data.py`)
- [x] Create the data quality report (`reports/data_quality_report.csv`)
- [x] Build the relational database (`sql/schema.sql`, `data/processed/hospital_analytics.db`)
- [x] Complete the 12 SQL analytical questions (`sql/analytical_queries.sql`)
- [x] Calculate and document healthcare KPIs (`sql/healthcare_kpis.sql`)
- [x] Build all four Power BI pages (`powerbi/hospital_analytics.pbix` & `powerbi/dashboard_screenshots/`)
- [x] Write the management report (`reports/management_report.pdf`)
- [x] Add automated tests (`tests/test_data_pipeline.py`)
- [x] Document limitations and synthetic data provenance (`README.md`, `reports/management_report.pdf`)
- [x] Package the repository for GitHub (`hospital-population-health-analytics.zip`)
