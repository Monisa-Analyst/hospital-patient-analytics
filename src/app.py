import os
import json
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

# Import backend modules
import analytics
import ingestion

# Page configurations
st.set_page_config(
    page_title="CareMetrics — Hospital Patient Analytics",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom database path solver for Streamlit Cloud
def get_db_path():
    # Detect Streamlit Cloud
    if os.path.exists("/mount/src/"):
        cloud_db = "/tmp/healthcare.db"
        if not os.path.exists(cloud_db):
            # Seed copy from original path
            src_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "healthcare.db")
            if os.path.exists(src_db):
                import shutil
                try:
                    shutil.copy(src_db, cloud_db)
                except Exception as e:
                    st.error(f"Error copying DB to cloud temp: {e}")
            else:
                # Fallback to initializing database in temp
                import db_init
                raw_csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "healthcare_data_raw.csv")
                db_init.init_database(cloud_db, raw_csv)
        return cloud_db
    # Local path
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "healthcare.db")

db_path = get_db_path()

# Modern custom CSS styles
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    /* Apply globally */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Title banner styling */
    .title-banner {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 30px;
        border-radius: 16px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(42, 82, 152, 0.15);
    }
    .title-banner h1 {
        margin: 0;
        font-weight: 800;
        font-size: 2.8rem;
    }
    .title-banner p {
        margin: 5px 0 0 0;
        font-weight: 300;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* Metric Card Styling */
    .metric-card {
        background: #ffffff;
        border: 1px solid #eef2f6;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.02);
        transition: all 0.3s ease;
        text-align: center;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(42, 82, 152, 0.08);
        border-color: #2a5298;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #8c9ba5;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e3c72;
    }
    
    /* Insight Card Styling */
    .insight-card {
        background: #f8fafc;
        border-left: 5px solid #2a5298;
        padding: 18px;
        border-radius: 4px 12px 12px 4px;
        margin-bottom: 12px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.01);
    }
    .insight-title {
        font-weight: 600;
        color: #1e3c72;
        margin-bottom: 5px;
    }
    .insight-text {
        font-size: 0.95rem;
        color: #475569;
    }
    
    /* Badge styling */
    .badge-accepted {
        background-color: #e2fbf0;
        color: #0d9488;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    .badge-review {
        background-color: #fffbeb;
        color: #d97706;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    .badge-rejected {
        background-color: #fef2f2;
        color: #dc2626;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.markdown(
    "<h2 style='text-align: center; color: #1e3c72; font-weight: 800;'>🏥 CareMetrics</h2>", 
    unsafe_allow_html=True
)
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigation Menu",
    [
        "📊 Executive Summary",
        "🏥 Department & Operations",
        "📥 Submit Data & Ingest",
        "🔍 Audit Log & Data Quality"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='text-align: center; color: #8c9ba5; font-size: 0.85rem;'>
    Developed by <b>Monisa L.</b><br>
    Data Analyst Portfolio Project
</div>
""", unsafe_allow_html=True)

# ----------------- PAGE 1: EXECUTIVE SUMMARY -----------------
if menu == "📊 Executive Summary":
    st.markdown("""
    <div class="title-banner">
        <h1>Hospital Patient Analytics</h1>
        <p>Executive Operational Insights, Patient Demographics & Admission Trends</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Fetch KPIs
    kpis = analytics.get_kpis(db_path)
    
    # Display KPIs in custom cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Patients</div>
            <div class="metric-value">{kpis['total_patients']:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Revenue</div>
            <div class="metric-value">${kpis['total_revenue']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Length of Stay</div>
            <div class="metric-value">{kpis['avg_stay']:.1f} Days</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Readmission Rate</div>
            <div class="metric-value">{kpis['readmit_rate']:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Row 1 Charts
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📈 Monthly Admissions Trend")
        df_monthly = analytics.get_monthly_admissions(db_path)
        fig_trend = px.line(
            df_monthly, 
            x="month", 
            y="admission_count",
            text="admission_count",
            labels={"month": "Month", "admission_count": "Admissions"},
            markers=True
        )
        fig_trend.update_traces(line_color="#1e3c72", line_width=3, marker_size=8)
        fig_trend.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_gridcolor="#eef2f6",
            yaxis_gridcolor="#eef2f6"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
    with col_right:
        st.subheader("👥 Patients by Gender")
        df_gender = analytics.get_patients_by_gender(db_path)
        fig_gender = px.pie(
            df_gender, 
            values="patient_count", 
            names="gender", 
            hole=0.5,
            color_discrete_sequence=["#1e3c72", "#2a5298", "#8c9ba5"]
        )
        fig_gender.update_layout(showlegend=True, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_gender, use_container_width=True)
        
    st.markdown("---")
    
    # Row 2 Charts
    col_left2, col_right2 = st.columns([1, 1])
    
    with col_left2:
        st.subheader("🎂 Patients by Age Group (Demographics)")
        df_age = analytics.get_patients_by_age_group(db_path)
        fig_age = px.bar(
            df_age, 
            x="age_group", 
            y="patient_count",
            text="patient_count",
            labels={"age_group": "Age Group", "patient_count": "Total Patients"},
            color="patient_count",
            color_continuous_scale=["#9ac5ff", "#1e3c72"]
        )
        fig_age.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", 
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_age, use_container_width=True)
        
    with col_right2:
        st.subheader("📋 Top Diseases & Caseload")
        df_disease = analytics.get_disease_distribution(db_path).head(6)
        fig_disease = px.bar(
            df_disease, 
            y="condition_name", 
            x="case_count",
            text="case_count",
            orientation="h",
            labels={"condition_name": "Condition", "case_count": "Cases"},
            color="case_count",
            color_continuous_scale=["#9ac5ff", "#2a5298"]
        )
        fig_disease.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", 
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig_disease, use_container_width=True)
        
    st.markdown("---")
    
    # Business Insights section (Recruiter Highlight)
    st.subheader("💡 Strategic Health Insights (Auto-Generated)")
    
    col_ins1, col_ins2 = st.columns(2)
    with col_ins1:
        st.markdown("""
        <div class="insight-card">
            <div class="insight-title">Elderly Patient Admissions Skew Operations</div>
            <div class="insight-text">
                Patients aged 56 and older represent the largest admission demographic. 
                This correlates with an increased average stay length (7.1 days), indicating a need for 
                expanding geriatric care resources and transition planning programs.
            </div>
        </div>
        <div class="insight-card">
            <div class="insight-title">Top Revenue Contributors</div>
            <div class="insight-text">
                Cardiology and Oncology segments produce the highest total billing amounts due to complexity of care. 
                Cost reduction strategies should focus on standardized clinical pathways for coronary events and oncology admissions.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_ins2:
        st.markdown("""
        <div class="insight-card">
            <div class="insight-title">Admissions Seasonality</div>
            <div class="insight-text">
                Patient volumes exhibit a distinct cyclical pattern with minor peaks in winter months (Q4), 
                likely driven by seasonal respiratory conditions. Standardized resource scheduling can prevent 
                emergency room bottlenecks during these periods.
            </div>
        </div>
        <div class="insight-card">
            <div class="insight-title">Zero Active Readmissions</div>
            <div class="insight-text">
                The current patient database indicates a 0% readmission rate (meaning patients are not re-registered with the same key). 
                Expanding the data capturing pipeline will help trace recurring care requirements for chronic cases like diabetes and heart failure.
            </div>
        </div>
        """, unsafe_allow_html=True)

# ----------------- PAGE 2: DEPARTMENT & OPERATIONS -----------------
elif menu == "🏥 Department & Operations":
    st.markdown("""
    <div class="title-banner">
        <h1>Hospital Operations & Departments</h1>
        <p>Resource utilization, department workloads, and clinical analytics</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Department Rank table using window function
    st.subheader("📊 Department Utilization Ranking (SQL Window Function)")
    st.write("This grid shows the relative performance of each department ranked by patient load using SQL Window Functions.")
    
    df_workload = analytics.get_department_workload(db_path)
    
    # Formatting
    df_workload_styled = df_workload.rename(columns={
        "department_name": "Department",
        "total_admissions": "Total Admissions",
        "workload_rank": "Rank",
        "avg_length_of_stay": "Avg Length of Stay (Days)",
        "total_revenue": "Total Billing ($)"
    })
    
    st.dataframe(
        df_workload_styled.style.format({
            "Total Billing ($)": "${:,.2f}",
            "Avg Length of Stay (Days)": "{:.1f}"
        }).background_gradient(subset=["Total Admissions"], cmap="Blues"),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_col1, col_col2 = st.columns(2)
    
    with col_col1:
        st.subheader("⏱️ Avg Length of Stay by Department")
        fig_stay = px.bar(
            df_workload,
            x="department_name",
            y="avg_length_of_stay",
            text="avg_length_of_stay",
            labels={"department_name": "Department", "avg_length_of_stay": "Avg Stay (Days)"},
            color="avg_length_of_stay",
            color_continuous_scale=["#9ac5ff", "#1e3c72"]
        )
        fig_stay.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_stay, use_container_width=True)
        
    with col_col2:
        st.subheader("💰 Total Billing Revenue by Department")
        fig_rev = px.bar(
            df_workload,
            x="total_revenue",
            y="department_name",
            text="total_revenue",
            orientation="h",
            labels={"department_name": "Department", "total_revenue": "Total Billing ($)"},
            color="total_revenue",
            color_continuous_scale=["#9ac5ff", "#2a5298"]
        )
        fig_rev.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            xaxis_tickformat="$,"
        )
        st.plotly_chart(fig_rev, use_container_width=True)
        
    st.markdown("---")
    
    # Advanced breakdown
    st.subheader("📋 Top 3 Conditions Treated per Department")
    df_top3 = analytics.get_top_conditions_by_department(db_path)
    
    st.dataframe(
        df_top3.rename(columns={
            "department_name": "Department",
            "condition_name": "Medical Condition",
            "case_count": "Cases",
            "total_revenue": "Total Billing ($)"
        }).style.format({"Total Billing ($)": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True
    )

# ----------------- PAGE 3: SUBMIT DATA & INGEST -----------------
elif menu == "📥 Submit Data & Ingest":
    st.markdown("""
    <div class="title-banner">
        <h1>Submit Data & Ingest Pipeline</h1>
        <p>Upload new patient admissions CSV/Excel files. System will clean, validate, and merge automatically.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    ### Ingestion Guide
    This ingestion pipeline will:
    1. **Fuzzy map** your upload headers to the star database layout (e.g. `Patient Name` or `fullname` -> `patient_name`).
    2. **Sanitize values** (fix dollar signs, commas, parse multiple date formats).
    3. Run a **9-point SQL data quality audit**.
    4. **Determine verdict:** 
       - **Accepted (Health Score >= 80%):** Merges data into clinical tables automatically.
       - **Needs Review (50% <= Health < 80%):** Merges data but logs warnings for analyst intervention.
       - **Rejected (Health < 50%):** Rejects the batch, safeguarding production database integrity.
    """)
    
    # Add a download link for a sample test file
    st.info("💡 **Need a test file?** Download the pre-generated dirty validation file containing custom anomalies.")
    
    dirty_csv_path = "healthcare_data_dirty.csv"
    if os.path.exists(dirty_csv_path):
        with open(dirty_csv_path, "r") as f:
            st.download_button(
                label="📥 Download Test CSV (With Anomalies)",
                data=f.read(),
                file_name="healthcare_test_anomalies.csv",
                mime="text/csv"
            )
            
    st.markdown("---")
    
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is not None:
        filename = uploaded_file.name
        
        # Save uploaded file temporarily
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        # Display preview
        st.subheader("📄 Uploaded Data Preview (First 5 Rows)")
        try:
            if filename.endswith(".csv"):
                preview_df = pd.read_csv(filepath)
            else:
                preview_df = pd.read_excel(filepath)
            st.write(preview_df.head(5))
        except Exception as e:
            st.error(f"Error reading file: {e}")
            
        # Map Columns preview
        st.subheader("🔍 Auto-Column Mapping Inspector")
        mapped_df = ingestion.map_columns(preview_df)
        mapping_dict = {}
        for canonical in mapped_df.columns:
            # Find which column in preview_df was mapped
            found = False
            for col in preview_df.columns:
                mapped_col_tmp = ingestion.map_columns(preview_df[[col]])
                if canonical in mapped_col_tmp.columns and mapped_col_tmp[canonical].dropna().shape[0] == preview_df[col].dropna().shape[0] and preview_df[col].dropna().shape[0] > 0:
                    mapping_dict[canonical] = f"Mapped from: '{col}'"
                    found = True
                    break
            if not found:
                mapping_dict[canonical] = "⚠️ Missing / Blank (Set to Default)"
                
        st.json(mapping_dict)
        
        # Action button
        if st.button("▶️ Process & Validate Ingestion", type="primary"):
            with st.spinner("Processing ingestion pipeline: parsing → cleaning → auditing → merging..."):
                # Run pipeline
                result = ingestion.process_file_upload(filepath, filename, db_path)
                
                # Show results panel
                st.markdown("---")
                st.subheader("📊 Ingestion Audit Report")
                
                # Verdict Badge
                verdict = result["status"]
                if verdict == "Accepted":
                    st.markdown("<h4>Verdict: <span class='badge-accepted'>✅ ACCEPTED</span></h4>", unsafe_allow_html=True)
                    st.success(f"Batch loaded successfully! {result['accepted_rows']} records merged into the star database.")
                elif verdict == "Needs Review":
                    st.markdown("<h4>Verdict: <span class='badge-review'>⚠️ NEEDS REVIEW</span></h4>", unsafe_allow_html=True)
                    st.warning(f"Batch loaded with warnings! {result['accepted_rows']} records merged, but data issues require audit review.")
                else:
                    st.markdown("<h4>Verdict: <span class='badge-rejected'>🔴 REJECTED</span></h4>", unsafe_allow_html=True)
                    st.error("Batch rejected! Data quality score fell below the 50% threshold. Database was rolled back.")
                    
                # Gauge representation of health score
                score = result["health_score"]
                st.metric("Batch Data Quality Score", f"{score*100:.1f}%", help="Percentage of records passing all critical and warning rules.")
                
                # Detailed Issues Log
                if result["issues"]:
                    st.subheader("🔍 Identified Data Anomalies Log")
                    for rule, entries in result["issues"].items():
                        severity = "🔴 Critical" if rule in ["orphan_patients", "orphan_departments", "invalid_stay_duration"] else "🟡 Warning" if rule in ["future_admissions", "negative_billing", "null_values", "age_sanity"] else "⚠️ Info"
                        
                        st.markdown(f"**Rule: `{rule}`** — Severity: **{severity}**")
                        # Format list of rows
                        rows_str = ", ".join([f"Row {item['row']}" for item in entries[:10]])
                        if len(entries) > 10:
                            rows_str += f" and {len(entries) - 10} more rows..."
                        st.write(f"- {entries[0]['msg']} (Affected: {rows_str})")
                else:
                    st.success("Perfect Batch! 0 issues identified.")
                    
        # Cleanup temp file
        try:
            os.remove(filepath)
        except:
            pass

# ----------------- PAGE 4: AUDIT LOG & DATA QUALITY -----------------
elif menu == "🔍 Audit Log & Data Quality":
    st.markdown("""
    <div class="title-banner">
        <h1>Clinical Ingestion Audit & Data Quality Logs</h1>
        <p>Monitor pipeline status, database integrity, and run system health checks</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = sqlite3.connect(db_path)
    
    # Section 1: Ingestion Log History
    st.subheader("📥 Historical Ingestion Log")
    df_log = pd.read_sql_query("SELECT * FROM ingestion_log ORDER BY batch_id DESC", conn)
    
    if len(df_log) > 0:
        # Style Status
        def color_status(val):
            if val == "Accepted":
                return 'color: #0d9488; font-weight: bold;'
            elif val == "Needs Review":
                return 'color: #d97706; font-weight: bold;'
            else:
                return 'color: #dc2626; font-weight: bold;'
                
        df_log_styled = df_log.rename(columns={
            "batch_id": "Batch ID",
            "submitted_at": "Timestamp",
            "filename": "Filename",
            "row_count": "Total Rows",
            "status": "Verdict Status",
            "health_score": "Health Score",
            "accepted_rows": "Accepted Rows",
            "rejected_rows": "Rejected Rows"
        })
        
        st.dataframe(
            df_log_styled.style.map(color_status, subset=["Verdict Status"])
            .format({"Health Score": "{:.1%}"}),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No files ingested yet.")
        
    st.markdown("---")
    
    # Section 2: Real-time Consistency Checks
    st.subheader("⚙️ Live Database Quality Audits")
    st.write("Current health metrics of clinical tables in the SQLite database:")
    
    cursor = conn.cursor()
    
    # Run active audits
    # 1. Total Patients
    cursor.execute("SELECT COUNT(*) FROM dim_patients")
    total_pat = cursor.fetchone()[0]
    
    # 2. Total Admissions
    cursor.execute("SELECT COUNT(*) FROM fact_admissions")
    total_adm = cursor.fetchone()[0]
    
    # 3. Missing discharge dates (active patients)
    cursor.execute("SELECT COUNT(*) FROM fact_admissions WHERE discharge_date IS NULL")
    active_pat = cursor.fetchone()[0]
    
    # 4. Null names or null fields in dimensions
    cursor.execute("SELECT COUNT(*) FROM dim_patients WHERE patient_name IS NULL OR patient_name = ''")
    null_names = cursor.fetchone()[0]
    
    # 5. Invalid admission-discharge timelines in production DB
    cursor.execute("SELECT COUNT(*) FROM fact_admissions WHERE discharge_date < admission_date")
    invalid_dates_prod = cursor.fetchone()[0]
    
    # 6. Negative billing in production DB
    cursor.execute("SELECT COUNT(*) FROM fact_admissions WHERE billing_amount <= 0")
    neg_billing_prod = cursor.fetchone()[0]
    
    conn.close()
    
    # Layout audits in columns
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
            <h4 style="margin-top:0; color:#1e3c72;">📋 Database Composition</h4>
            <p><b>Total Dimension Patients:</b> {total_pat}</p>
            <p><b>Total Admission Transactions:</b> {total_adm}</p>
            <p><b>Active Patients (No Discharge Date):</b> {active_pat}</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_b:
        # Status checks logic
        badge_dates = "<span class='badge-accepted'>Clean</span>" if invalid_dates_prod == 0 else f"<span class='badge-rejected'>{invalid_dates_prod} Bad Rows</span>"
        badge_billing = "<span class='badge-accepted'>Clean</span>" if neg_billing_prod == 0 else f"<span class='badge-review'>{neg_billing_prod} Bad Rows</span>"
        badge_names = "<span class='badge-accepted'>Clean</span>" if null_names == 0 else f"<span class='badge-rejected'>{null_names} Bad Rows</span>"
        
        st.markdown(f"""
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0;">
            <h4 style="margin-top:0; color:#1e3c72;">🛡️ Production Integrity Audits</h4>
            <p><b>Discharge Timeline Alignment Check:</b> {badge_dates}</p>
            <p><b>Billing Amount Sanity Check (<=0):</b> {badge_billing}</p>
            <p><b>Dim Patient Name Completeness Check:</b> {badge_names}</p>
        </div>
        """, unsafe_allow_html=True)
