import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURATION ---
DB_FILE = "samples_pro.db"
PORTAL_PASSWORD = "LabTeam2026"

# Define your Laboratory Dropdowns here
SAMPLE_TYPES = ["Serum", "Plasma", "Whole Blood", "Swabs", "Urine", "Tissue", "Other"]
FREEZERS = ["Freezer A (-20°C)", "Freezer B (-80°C)", "Fridge 1 (4°C)", "Liquid Nitrogen Tank"]
PERSONNEL = ["Gedieon Kiarii", "Sophia", "James", "Laurene"]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date_received TEXT, 
                  project TEXT, 
                  sample_id TEXT, 
                  sample_type TEXT,
                  location TEXT, 
                  staff TEXT)''')
    conn.commit()
    conn.close()

st.set_page_config(page_title="Lab LIMS Portal", layout="wide")

if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    st.title("🧪 Lab LIMS Access")
    pwd = st.text_input("Enter Team Password", type="password")
    if st.button("Login"):
        if pwd == PORTAL_PASSWORD:
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("Access Denied")
else:
    init_db()
    st.sidebar.title("LIMS Navigation")
    menu = st.sidebar.radio("Go to:", ["📥 Receive Samples", "🔍 Inventory Search"])

    if menu == "📥 Receive Samples":
        st.header("Sample Accessioning")
        with st.form("sample_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                project = st.text_input("Project Name (e.g., MAGIA Study)")
                s_id = st.text_input("Sample ID / Barcode")
                # Calendar Input
                d_received = st.date_input("Date Received", datetime.now())
            
            with col2:
                # Dropdown Menus
                s_type = st.selectbox("Sample Type", SAMPLE_TYPES)
                loc = st.selectbox("Storage Location", FREEZERS)
                staff = st.selectbox("Personnel Receiving", PERSONNEL)
            
            if st.form_submit_button("Log Sample to Database"):
                if project and s_id:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT INTO samples (date_received, project, sample_id, sample_type, location, staff) VALUES (?,?,?,?,?,?)",
                              (str(d_received), project, s_id, s_type, loc, staff))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Success: Sample {s_id} ({s_type}) registered in {loc}")
                else:
                    st.error("Please fill in the Project and Sample ID.")

    else:
        st.header("Laboratory Inventory")
        search = st.text_input("Quick Search (Project, ID, or Type)")
        
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples ORDER BY id DESC", conn)
        conn.close()

        if search:
            # Filter the table based on search
            df = df[df.stack().str.contains(search, case=False).groupby(level=0).any()]

        st.dataframe(df, use_container_width=True)
        
        # Add a download button for Excel/CSV reports
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📂 Export Inventory to CSV", csv, "lab_inventory.csv", "text/csv")
       
