import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

# Mapping dict for fuzzy column detection
COLUMN_MAPPING = {
    "patient_id": ["patient id", "patient_id", "patientid", "id", "pid"],
    "patient_name": ["patient name", "patient_name", "name", "patientname", "full name", "fullname"],
    "age": ["age", "patient age", "patient_age"],
    "gender": ["gender", "sex", "patient gender", "patient_gender"],
    "blood_type": ["blood type", "blood_type", "bloodtype", "blood"],
    "medical_condition": ["medical condition", "medical_condition", "condition", "disease", "diagnosis", "illness"],
    "admission_date": ["admission date", "admission_date", "date of admission", "date_of_admission", "admitted", "admissiondate"],
    "discharge_date": ["discharge date", "discharge_date", "date of discharge", "date_of_discharge", "discharged", "dischargedate"],
    "billing_amount": ["billing amount", "billing_amount", "billing", "amount", "cost", "billingamount", "charge"],
    "hospital_department": ["hospital department", "hospital_department", "department", "dept", "ward", "hospitaldepartment"],
    "admission_type": ["admission type", "admission_type", "type of admission", "type_of_admission", "admissiontype"],
    "test_results": ["test results", "test_results", "test result", "test_result", "results", "testresults"]
}

def map_columns(df):
    """Maps df columns to canonical names using fuzzy matching."""
    mapped_cols = {}
    lower_cols = {col.lower().strip().replace("_", " ").replace("  ", " "): col for col in df.columns}
    
    for canonical, variations in COLUMN_MAPPING.items():
        found = False
        for var in variations:
            # Check for direct variations
            if var in lower_cols:
                mapped_cols[lower_cols[var]] = canonical
                found = True
                break
        if not found:
            # Check for substring match if not found directly
            for raw_col_lower, raw_col_orig in lower_cols.items():
                if any(var in raw_col_lower for var in variations):
                    mapped_cols[raw_col_orig] = canonical
                    break
                    
    # Rename matching columns and drop others or keep them
    df_renamed = df.rename(columns=mapped_cols)
    # Ensure canonical columns exist (use NaN if missing)
    for col in COLUMN_MAPPING.keys():
        if col not in df_renamed.columns:
            df_renamed[col] = np.nan
            
    return df_renamed[list(COLUMN_MAPPING.keys())]

def clean_numeric(val):
    """Cleans currency, commas, and negative formats."""
    if pd.isna(val) or val == "":
        return np.nan
    val_str = str(val).strip().replace("$", "").replace(",", "")
    if not val_str:
        return np.nan
    # Handle parentheses for negatives e.g. (100) -> -100
    if val_str.startswith("(") and val_str.endswith(")"):
        val_str = "-" + val_str[1:-1]
    try:
        return float(val_str)
    except ValueError:
        return np.nan

def parse_date(val):
    """Parses date using multiple common formats, returning YYYY-MM-DD string."""
    if pd.isna(val) or val == "":
        return None
    val_str = str(val).strip()
    
    # Common formats to try
    formats = [
        "%Y-%m-%d", "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y", "%m/%d/%Y %H:%M", "%m/%d/%y",
        "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    # Fallback to pandas to_datetime if it can parse it
    try:
        dt = pd.to_datetime(val_str)
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    except:
        pass
        
    return None

def run_data_quality_checks(df, db_path="src/healthcare.db"):
    """
    Runs 9 data quality rules against the uploaded dataframe.
    Returns:
        issues: dict with check results
        row_issues_mask: boolean series indicating if row has any critical/warning issues
        health_score: float (percentage of fully valid rows)
    """
    issues = {
        "orphan_patients": [],      # Critical
        "orphan_departments": [],   # Critical
        "future_admissions": [],    # Warning
        "invalid_stay_duration": [],# Critical
        "negative_billing": [],     # Warning
        "null_values": [],          # Warning
        "age_sanity": [],           # Warning
        "excessive_stay": [],       # Info
        "extreme_billing": []       # Info
    }
    
    n_rows = len(df)
    if n_rows == 0:
        return issues, pd.Series(dtype=bool), 1.0
        
    # Get historical billing average and std deviation for outlier check
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT AVG(billing_amount), AVG(billing_amount * billing_amount) FROM fact_admissions")
        res = cursor.fetchone()
        avg_bill = res[0] if res[0] else 5000.0
        # Compute std dev
        variance = res[1] - (avg_bill * avg_bill) if res[1] else 0
        std_bill = np.sqrt(max(0, variance)) if variance > 0 else 2000.0
    except:
        avg_bill = 5000.0
        std_bill = 2000.0
    conn.close()

    # Pre-calculate dates for checks
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    # We will build a mask of rows with errors (Critical or Warning severity)
    # Info severity does not penalize the health score.
    row_failed_health = pd.Series(False, index=df.index)
    
    for idx, row in df.iterrows():
        # Load values
        pid = row["patient_id"]
        name = row["patient_name"]
        age = row["age"]
        gender = row["gender"]
        cond = row["medical_condition"]
        adm_date_str = row["admission_date"]
        dis_date_str = row["discharge_date"]
        billing = row["billing_amount"]
        dept = row["hospital_department"]
        
        row_num = idx + 1 # 1-indexed for reporting
        row_has_crit_or_warn = False
        
        # 1. Orphan Patients (Patient ID present but no Name/Age, and patient doesn't exist in dim_patients)
        if pd.isna(pid) or str(pid).strip() == "":
            issues["orphan_patients"].append({"row": row_num, "msg": "Patient ID is missing."})
            row_has_crit_or_warn = True
        elif pd.isna(name) or str(name).strip() == "":
            # Check if patient exists in dim_patients
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM dim_patients WHERE patient_id = ?", (str(pid),))
            exists = c.fetchone()[0] > 0
            conn.close()
            if not exists:
                issues["orphan_patients"].append({"row": row_num, "patient_id": pid, "msg": f"Patient ID '{pid}' has no name and does not exist in the system."})
                row_has_crit_or_warn = True
                
        # 2. Orphan Departments (Department name is missing or empty)
        if pd.isna(dept) or str(dept).strip() == "":
            issues["orphan_departments"].append({"row": row_num, "msg": "Hospital Department is missing."})
            row_has_crit_or_warn = True
            
        # 3. Future Admissions (Admission date is in the future)
        if adm_date_str:
            if adm_date_str > today_str:
                issues["future_admissions"].append({"row": row_num, "date": adm_date_str, "msg": f"Admission date '{adm_date_str}' is in the future."})
                row_has_crit_or_warn = True
        else:
            issues["null_values"].append({"row": row_num, "column": "admission_date", "msg": "Admission date is missing."})
            row_has_crit_or_warn = True
            
        # 4. Invalid Stay Duration (Discharge before Admission)
        if adm_date_str and dis_date_str:
            if dis_date_str < adm_date_str:
                issues["invalid_stay_duration"].append({"row": row_num, "adm": adm_date_str, "dis": dis_date_str, "msg": f"Discharge date '{dis_date_str}' is before admission date '{adm_date_str}'."})
                row_has_crit_or_warn = True
                
        # 5. Negative Billing Amount (Billing amount <= 0)
        if pd.notna(billing):
            if billing <= 0:
                issues["negative_billing"].append({"row": row_num, "amount": billing, "msg": f"Billing amount ${billing:.2f} is zero or negative."})
                row_has_crit_or_warn = True
        else:
            issues["null_values"].append({"row": row_num, "column": "billing_amount", "msg": "Billing amount is missing."})
            row_has_crit_or_warn = True
            
        # 6. Null Values Check
        null_cols = []
        for col in ["gender", "medical_condition"]:
            if pd.isna(row[col]) or str(row[col]).strip() == "":
                null_cols.append(col)
        if null_cols:
            issues["null_values"].append({"row": row_num, "columns": null_cols, "msg": f"Missing critical details in columns: {', '.join(null_cols)}"})
            row_has_crit_or_warn = True
            
        # 7. Age Sanity Check
        if pd.notna(age):
            try:
                age_int = int(age)
                if age_int < 0 or age_int > 115:
                    issues["age_sanity"].append({"row": row_num, "age": age_int, "msg": f"Unrealistic patient age: {age_int}."})
                    row_has_crit_or_warn = True
            except ValueError:
                issues["age_sanity"].append({"row": row_num, "age": age, "msg": "Invalid age representation."})
                row_has_crit_or_warn = True
        else:
            issues["null_values"].append({"row": row_num, "column": "age", "msg": "Patient age is missing."})
            row_has_crit_or_warn = True
            
        # 8. Excessive Length of Stay (> 90 days) - Severity: Info
        if adm_date_str and dis_date_str:
            adm_dt = datetime.strptime(adm_date_str, "%Y-%m-%d")
            dis_dt = datetime.strptime(dis_date_str, "%Y-%m-%d")
            length = (dis_dt - adm_dt).days
            if length > 90:
                issues["excessive_stay"].append({"row": row_num, "days": length, "msg": f"Long hospital stay of {length} days."})
                # Not critical/warning, so doesn't fail health check
                
        # 9. Extreme Billing Outliers (> 3 standard deviations or > $100K) - Severity: Info
        if pd.notna(billing) and billing > 0:
            threshold = avg_bill + 3 * std_bill
            if billing > max(100000.0, threshold):
                issues["extreme_billing"].append({"row": row_num, "amount": billing, "msg": f"Outlier billing amount: ${billing:.2f}."})
                # Not critical/warning, so doesn't fail health check
                
        if row_has_crit_or_warn:
            row_failed_health.iloc[idx] = True
            
    # Calculate health score: percentage of rows passing critical/warning rules
    failed_count = row_failed_health.sum()
    health_score = 1.0 - (failed_count / n_rows) if n_rows > 0 else 1.0
    
    return issues, row_failed_health, health_score

def merge_batch_to_db(df, db_path="src/healthcare.db"):
    """Inserts dimensions and facts from the processed dataframe into the SQLite DB."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    try:
        # Start Transaction
        cursor.execute("BEGIN TRANSACTION;")
        
        # 1. Dim Patients
        # Drop duplicates where patient_id matches but keep the latest values if any
        patients = df[["patient_id", "patient_name", "age", "gender", "blood_type"]].dropna(subset=["patient_id", "patient_name"])
        patients = patients.drop_duplicates(subset=["patient_id"])
        
        for _, row in patients.iterrows():
            cursor.execute("""
            INSERT OR REPLACE INTO dim_patients (patient_id, patient_name, age, gender, blood_type)
            VALUES (?, ?, ?, ?, ?)
            """, (
                row["patient_id"], 
                row["patient_name"], 
                int(row["age"]) if pd.notna(row["age"]) else None, 
                row["gender"], 
                row["blood_type"]
            ))
            
        # 2. Dim Departments
        departments = df["hospital_department"].dropna().unique()
        for dept in departments:
            cursor.execute("INSERT OR IGNORE INTO dim_departments (department_name) VALUES (?)", (dept,))
            
        # 3. Dim Conditions
        conditions = df["medical_condition"].dropna().unique()
        for cond in conditions:
            cursor.execute("INSERT OR IGNORE INTO dim_conditions (condition_name) VALUES (?)", (cond,))
            
        # Commit dimensions changes so we can lookup new IDs
        conn.commit()
        
        # Fetch lookup dicts
        cursor.execute("SELECT department_id, department_name FROM dim_departments")
        dept_lookup = {name: id for id, name in cursor.fetchall()}
        
        cursor.execute("SELECT condition_id, condition_name FROM dim_conditions")
        cond_lookup = {name: id for id, name in cursor.fetchall()}
        
        # Restart facts transaction
        cursor.execute("BEGIN TRANSACTION;")
        
        # 4. Fact Admissions
        admissions = []
        for _, row in df.iterrows():
            dept_id = dept_lookup.get(row["hospital_department"])
            cond_id = cond_lookup.get(row["medical_condition"])
            
            admissions.append((
                row["patient_id"],
                row["admission_date"],
                row["discharge_date"] if pd.notna(row["discharge_date"]) else None,
                dept_id,
                cond_id,
                row["billing_amount"],
                row["admission_type"],
                row["test_results"]
            ))
            
        cursor.executemany("""
        INSERT INTO fact_admissions (
            patient_id, admission_date, discharge_date, department_id, condition_id, billing_amount, admission_type, test_result
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, admissions)
        
        cursor.execute("COMMIT;")
        conn.close()
        return True, len(df)
        
    except Exception as e:
        cursor.execute("ROLLBACK;")
        conn.close()
        print(f"Error merging batch: {e}")
        return False, str(e)

def process_file_upload(filepath, filename, db_path="src/healthcare.db"):
    """
    Coordinates the entire ingestion pipeline:
    1. Reads Excel or CSV.
    2. Maps columns to standard names.
    3. Cleans types (numeric, dates).
    4. Runs the 9 data quality validation checks.
    5. Determines batch status (Accepted, Needs Review, Rejected).
    6. Logs the batch result in ingestion_log.
    7. Merges data to DB if status is Accepted or Needs Review.
    """
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Read file
    try:
        if filename.endswith(".csv"):
            df_raw = pd.read_csv(filepath)
        elif filename.endswith((".xls", ".xlsx")):
            df_raw = pd.read_excel(filepath)
        else:
            return {
                "success": False,
                "msg": "Unsupported file format. Please upload a CSV or Excel file.",
                "status": "Rejected"
            }
    except Exception as e:
        return {
            "success": False,
            "msg": f"Failed to read file: {e}",
            "status": "Rejected"
        }
        
    n_rows = len(df_raw)
    if n_rows == 0:
        return {
            "success": False,
            "msg": "The uploaded file is empty.",
            "status": "Rejected"
        }
        
    # 2. Map Columns
    df_mapped = map_columns(df_raw)
    
    # 3. Clean fields
    df_clean = df_mapped.copy()
    df_clean["billing_amount"] = df_mapped["billing_amount"].apply(clean_numeric)
    df_clean["admission_date"] = df_mapped["admission_date"].apply(parse_date)
    df_clean["discharge_date"] = df_mapped["discharge_date"].apply(parse_date)
    
    # Clean up strings
    for str_col in ["patient_id", "patient_name", "gender", "blood_type", "medical_condition", "hospital_department", "admission_type", "test_results"]:
        df_clean[str_col] = df_clean[str_col].apply(lambda x: str(x).strip() if pd.notna(x) else np.nan)
        
    # 4. Data Quality Validation Gate
    issues, row_issues_mask, health_score = run_data_quality_checks(df_clean, db_path)
    
    # 5. Determine Verdict
    # Health Score criteria
    if health_score >= 0.8:
        status = "Accepted"
    elif health_score >= 0.5:
        status = "Needs Review"
    else:
        status = "Rejected"
        
    # Write details to DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    accepted_rows = 0
    rejected_rows = 0
    merge_success = False
    
    # Save issues summary as JSON
    issues_summary = {k: v for k, v in issues.items() if len(v) > 0}
    issues_json_str = json.dumps(issues_summary)
    
    if status in ["Accepted", "Needs Review"]:
        # Merge valid/accepted data into the db
        # Note: Even in 'Needs Review', we attempt to merge the entire batch, but flag the batch as warning
        merge_success, merge_info = merge_batch_to_db(df_clean, db_path)
        if merge_success:
            accepted_rows = n_rows
        else:
            status = "Rejected"
            issues_json_str = json.dumps({"db_error": [f"Database write failure: {merge_info}"]})
            rejected_rows = n_rows
    else:
        # Rejected batches are not merged
        rejected_rows = n_rows
        merge_success = False
        
    # Log the ingestion batch
    cursor.execute("""
    INSERT INTO ingestion_log (submitted_at, filename, row_count, status, health_score, issues_json, accepted_rows, rejected_rows)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (submitted_at, filename, n_rows, status, health_score, issues_json_str, accepted_rows, rejected_rows))
    
    conn.commit()
    conn.close()
    
    return {
        "success": merge_success or status == "Needs Review",
        "status": status,
        "health_score": health_score,
        "row_count": n_rows,
        "accepted_rows": accepted_rows,
        "rejected_rows": rejected_rows,
        "issues": issues_summary
    }

if __name__ == "__main__":
    # Test file upload with dirty file
    print("Testing data ingestion with dirty CSV...")
    import sys
    db_path = "src/healthcare.db"
    dirty_csv = "healthcare_data_dirty.csv"
    
    if os.path.exists(dirty_csv):
        result = process_file_upload(dirty_csv, "healthcare_data_dirty.csv", db_path)
        print(f"Status: {result['status']}")
        print(f"Health Score: {result['health_score'] * 100:.1f}%")
        print(f"Issues Found: {list(result['issues'].keys())}")
    else:
        print("Dirty test CSV not found.")
