import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURATION ---
DB_FILE = "lab_lims_master.db"
PORTAL_PASSWORD = "LabTeam2026"
SAMPLE_TYPES = ["Serum", "Plasma", "Whole Blood", "Swabs", "Urine", "Other"]
FREEZERS = ["Freezer A (-20°C)", "Freezer B (-80°C)", "Fridge 1 (4°C)", "Bench Top", "Shipped/Out"]
PERSONNEL = ["Gedieon Kiarii", "Sophia", "James", "Laurene"]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date_received TEXT, project TEXT, 
                  sample_id TEXT, sample_type TEXT,
                  location TEXT, staff TEXT)''')
    conn.commit()
    conn.close()

st.set_page_config(page_title="Advanced Lab LIMS", layout="wide")

if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    st.title("🧪 Lab LIMS Portal")
    pwd = st.text_input("Enter Team Password", type="password")
    if st.button("Login"):
        if pwd == PORTAL_PASSWORD:
            st.session_state["auth"] = True
            st.rerun()
        else: st.error("Access Denied")
else:
    init_db()
    st.sidebar.title("LIMS Operations")
    menu = st.sidebar.radio("Navigation", ["📥 Register New", "🔍 Inventory & Edit"])

    # --- 1. REGISTRATION PAGE ---
    if menu == "📥 Register New":
        st.header("New Sample Accessioning")
        with st.form("reg_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                proj = st.text_input("Project Name")
                sid = st.text_input("Sample ID")
                dt = st.date_input("Date Received", datetime.now())
            with col2:
                stype = st.selectbox("Type", SAMPLE_TYPES)
                loc = st.selectbox("Location", FREEZERS)
                staff = st.selectbox("Personnel", PERSONNEL)
            
            if st.form_submit_button("Save to Database"):
                if proj and sid:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT INTO samples (date_received, project, sample_id, sample_type, location, staff) VALUES (?,?,?,?,?,?)",
                              (str(dt), proj, sid, stype, loc, staff))
                    conn.commit()
                    conn.close()
                    st.success(f"Sample {sid} logged.")
                    st.rerun()

    # --- 2. INVENTORY & EDIT PAGE ---
    else:
        st.header("Laboratory Inventory Management")
        
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples ORDER BY id DESC", conn)
        conn.close()

        # Search Bar
        search = st.text_input("Search (ID, Project, or Type)")
        if search:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

        st.subheader("Current Stock")
        st.dataframe(df, use_container_width=True)

        st.divider()
        
        # EDIT SECTION
        st.subheader("🔄 Update/Move a Sample")
        sample_to_edit = st.selectbox("Select Sample ID to Update", ["None"] + df['sample_id'].tolist())
        
        if sample_to_edit != "None":
            # Fetch specific row data
            row_data = df[df['sample_id'] == sample_to_edit].iloc[0]
            
            with st.expander(f"Edit details for {sample_to_edit}", expanded=True):
                with st.form("edit_form"):
                    e_col1, e_col2 = st.columns(2)
                    new_proj = e_col1.text_input("Project Name", value=row_data['project'])
                    new_stype = e_col2.selectbox("Sample Type", SAMPLE_TYPES, index=SAMPLE_TYPES.index(row_data['sample_type']))
                    new_loc = e_col1.selectbox("New Location (Move to)", FREEZERS, index=FREEZERS.index(row_data['location']))
                    new_staff = e_col2.selectbox("Updated By", PERSONNEL, index=PERSONNEL.index(row_data['staff']))
                    
                    if st.form_submit_button("Confirm Update/Move"):
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute('''UPDATE samples SET project=?, sample_type=?, location=?, staff=? 
                                     WHERE sample_id=?''', (new_proj, new_stype, new_loc, new_staff, sample_to_edit))
                        conn.commit()
                        conn.close()
                        st.success(f"Updated: {sample_to_edit} has been moved to {new_loc}")
                        st.rerun()
