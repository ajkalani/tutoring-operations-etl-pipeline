# Multi-Semester Higher Education Tutoring ETL & Data Quality Pipeline

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-150458.svg)](https://pandas.pydata.org/)
[![NumPy](https://img.shields.io/badge/NumPy-1.24%2B-013243.svg)](https://numpy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview
This repository contains a production-grade Python ETL pipeline designed to ingest, clean, anonymize, and audit multi-semester tutoring logs from Excel workbooks. 

In university academic support operations, logging data across multiple semesters often leads to schema inconsistencies, human keying errors in session durations, and privacy compliance risks.
This pipeline automates data standardization, enforces FERPA compliance through student anonymization, and executes automated time-discrepancy audits for payroll and operational reporting.

---

## Key Capabilities:
* Automated Multi-Tab Ingestion: Concatenates dynamic workbook sheets while preserving temporal context (Semester, Year, Month, Day, Day of Week).
* Data Governance & FERPA Compliance: Deterministically factorizes student identity strings into uniform identifiers (`Student_001`, `Student_002`), removing PII before public export or analytics ingestion.
* Payroll & Duration Auditing: Calculates actual session durations from raw timestamp ranges, flags 12-hour clock wraparounds, and isolates variance ($\ge 15$ minutes) between logged payroll hours and scheduled time slots.
* Defensive Reporting: Generates a dynamic CLI audit report tracking row retention rates, unparseable entries, and total data anomalies.

---

## Pipeline Architecture

Raw Multi-Sheet Workbook (.xlsx)
1. Dynamic Ingestion ------> Concatenate all semester tabs via pd.concat()
2. Row Filtering ----------> Strip nulls & non-session entries ('Reading Day Review')
3. Feature Extraction -----> Parse dates & derive temporal features (Year, Month, Day, Weekday)
4. Identity Anonymization -> Factorize student PII -> Student_XXX (FERPA Compliance)
5. Duration Auditing ------> Standardize Start/End times, handle 12-hr wraparound, flag $\ge 15$ min diffs
6. Target Export ----------> Output clean schema to CSV & print CLI Data Quality Audit Report
