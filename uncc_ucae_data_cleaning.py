from pathlib import Path
import pandas as pd
import numpy as np

def clean_tutoring_data(
    file_path: str | Path, output_dir: str | Path | None = None
) -> pd.DataFrame:
    """Ingests, cleans, anonymizes, and audits tutoring hours log data across all workbook sheets.

    This ETL pipeline processes multi-tab Excel workbooks containing tutoring session logs.
    It standardizes date/time formatting, calculates duration metrics to audit logged hours,
    anonymizes student names for FERPA compliance, and outputs clean data builds along with
    a data quality report.

    Args:
        file_path (str | Path): Path to the source Excel file (.xlsx) containing 
            semester tutoring session logs.
        output_dir (str | Path | None, optional): Directory path where cleaned CSV 
            files will be saved. If None, file export is skipped. Defaults to None.

    Returns:
        pd.DataFrame: A structured, cleaned DataFrame containing standardized session 
            dates, subject codes, parsed start/end times, calculated session hours, 
            discrepancy flags, and anonymized student IDs.

    Raises:
        FileNotFoundError: If `file_path` does not exist.
        ValueError: If required columns (`keep_columns`) are missing from the workbook.
    """
    file_path = Path(file_path)

    # columns to keep (non-administrative columns)
    keep_columns = [
        "Date",
        "Subject",
        "Scheduled Time",
        "Hours",
        "Student",
        "Attendance (Y/N)",
    ]

    # multi-sheet ingestion
    sheets_dict = pd.read_excel(file_path, sheet_name = None, usecols = keep_columns)
    master_df = pd.concat(sheets_dict.values(), keys = sheets_dict.keys(), names = ["Semester", "Original_Index"])
    master_df = master_df.reset_index(level = "Semester").reset_index(drop = True)
    initial_rows = len(master_df)

    # drop rows missing critical student or attendance values
    null_student_att_mask = master_df[["Student", "Attendance (Y/N)"]].isna().any(axis=1)
    dropped_nulls_count = null_student_att_mask.sum()
    master_df = master_df[~null_student_att_mask].copy()

    # filter out administrative/non-session rows
    student_clean = master_df["Student"].astype(str).str.strip()
    reading_day_mask = student_clean.str.lower() == "reading day review"
    dropped_reading_days_count = reading_day_mask.sum()
    master_df = master_df[~reading_day_mask].copy()

    # normalize attendance to true/false
    att_clean = master_df["Attendance (Y/N)"].astype(str).str.strip().str.upper()
    master_df["Attended"] = att_clean.isin(["Y", "YES", "P", "PRESENT", "1"])

    # parse dates and extract year, month, day, and day of week
    dates = pd.to_datetime(master_df["Date"], errors="coerce")
    unparseable_dates_count = dates.isna().sum()

    master_df["Year"] = dates.dt.year
    master_df["Month"] = dates.dt.month
    master_df["Day"] = dates.dt.day
    master_df["Day_of_Week"] = dates.dt.day_name()

    # numeric standardization for subjects and hours
    master_df["Subject"] = master_df["Subject"].astype(str).str.strip().str.upper()
    hours_numeric = pd.to_numeric(master_df["Hours"], errors="coerce")
    unparseable_hours_count = hours_numeric.isna().sum()
    master_df["Hours"] = hours_numeric

    # scheduled time parsing & duration audit
    if "Scheduled Time" in master_df.columns:
        times = master_df["Scheduled Time"].astype(str).str.split(r"\s*[\-–]\s*", n=1, expand=True)
        master_df["Start Time"] = times[0].str.strip()
        master_df["End Time"] = times[1].str.strip() if times.shape[1] > 1 else None

    # parse timestamps and compute session duration
    start_dt = pd.to_datetime(master_df["Start Time"], errors="coerce")
    end_dt = pd.to_datetime(master_df["End Time"], errors="coerce")

    # compute duration in decimal hours
    duration_hours = (end_dt - start_dt).dt.total_seconds() / 3600.0

    # adjust for 12-hour clock wraparound
    duration_hours = np.where(duration_hours < 0, duration_hours + 12.0, duration_hours)
    master_df["Calculated_Hours"] = np.round(duration_hours, 2)

    # discrepancy flagging logic (>= 15 minute variance or unparseable time string)
    hour_diff = np.round(np.abs(master_df["Hours"] - master_df["Calculated_Hours"]), 4)
    master_df["Hours_Discrepancy"] = (hour_diff >= 0.25) | (master_df["Hours"].notna() & master_df["Calculated_Hours"].isna())
    discrepancy_count = master_df["Hours_Discrepancy"].sum()

    # student anonymization
    student_ids, unique_students = pd.factorize(master_df["Student"].astype(str).str.strip().str.title())
    master_df["Student_ID"] = [f"Student_{i+1:03d}" for i in student_ids]

    # final column selection & reordering
    ordered_columns = [
        "Semester",
        "Year",
        "Month",
        "Day",
        "Day_of_Week",
        "Subject",
        "Start Time",
        "End Time",
        "Hours",
        "Calculated_Hours",
        "Hours_Discrepancy",
        "Student_ID",
        "Attended",
    ]
    final_cols = [col for col in ordered_columns if col in master_df.columns]
    master_df = master_df[final_cols].reset_index(drop=True)

    # DATA AUDIT REPORT
    final_rows = len(master_df)
    print("=" * 60)
    print("              ETL DATA QUALITY AUDIT REPORT              ")
    print("=" * 60)
    print(f"Total Raw Records Ingested:        {initial_rows:>6}")
    print(f"Dropped (Null Student/Attendance): {dropped_nulls_count:>6}")
    print(f"Dropped ('Reading Day Review'):    {dropped_reading_days_count:>6}")
    print("-" * 60)
    print(f"Final Cleaned Record Count:        {final_rows:>6} ({(final_rows/initial_rows)*100:.1f}% retained)")
    print("=" * 60)
    print("DATA CONVERSION WARNINGS & DISCREPANCIES:")
    print(f" - Unparseable Dates Coerced to NaN: {unparseable_dates_count:>5}")
    print(f" - Unparseable Hours Coerced to NaN: {unparseable_hours_count:>5}")
    print(f" - Logged vs. Scheduled Mismatches:  {discrepancy_count:>5} ({(discrepancy_count/final_rows)*100:.1f}% of clean records)")
    print(f" - Unique Anonymous Students Tracked:{len(unique_students):>5}")
    print("=" * 60)

    # optional file export
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        master_df.to_csv(output_path / "cleaned_tutoring_hours.csv", index=False)
        print(f"\n[INFO] Successfully exported cleaned dataset to {output_path}")

    return master_df

if __name__ == "__main__":
    # relative paths for repository portability
    BASE_DIR = Path(__file__).resolve().parent
    INPUT_FILE = BASE_DIR / "data" / "raw" / "mock_tutoring_hours.xlsx"
    OUTPUT_FOLDER = BASE_DIR / "data" / "processed"

    # local paths if outside repository
    if not INPUT_FILE.exists():
        INPUT_FILE = "D:/Tutoring/UNCC UCAE Tutoring Hours.xlsx"
        OUTPUT_FOLDER = "D:/PythonScripts/Cleaned_Data"

    cleaned_df = clean_tutoring_data(
        file_path = INPUT_FILE, output_dir = OUTPUT_FOLDER
    )

# DATA AUDIT REPORT RESULT
# ============================================================
#               ETL DATA QUALITY AUDIT REPORT              
# ============================================================
# Total Raw Records Ingested:           460
# Dropped (Null Student/Attendance):     17
# Dropped ('Reading Day Review'):         1
# ------------------------------------------------------------
# Final Cleaned Record Count:           442 (96.1% retained)
# ============================================================
# DATA CONVERSION WARNINGS & DISCREPANCIES:
#  - Unparseable Dates Coerced to NaN:     0
#  - Unparseable Hours Coerced to NaN:     0
#  - Logged vs. Scheduled Mismatches:    101 (22.9% of clean records)
#  - Unique Anonymous Students Tracked:  216
# ============================================================