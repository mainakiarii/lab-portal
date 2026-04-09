import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- SYSTEM CONFIG ---
DB_FILE = "lab_lims_final.db"
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

st.set_page_config(page_title="Official Lab Sample Portal", page_icon="🧪", layout="wide")

# --- LOGIN / LOGOUT LOGIC ---
if "auth" not in st.session_state:
    st.session_state["auth"] = False

def logout():
    st.session_state["auth"] = False
    st.rerun()

# --- LOGIN SCREEN ---
if not st.session_state["auth"]:
    st.title("🔐 Laboratory Information Management System")
    st.info("Authorized access only. Please enter the team security password.")
    
    with st.container():
        pwd = st.text_input("Security Password", type="password")
        if st.button("Unlock Portal"):
            if pwd == PORTAL_PASSWORD:
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

# --- AUTHORIZED PORTAL ---
else:
    init_db()
    
    # Sidebar Navigation & Logout
    st.sidebar.markdown(f"## 🧪 Lab LIMS v1.1")
    st.sidebar.success("Access Granted")
    
    menu = st.sidebar.radio("MAIN MENU", ["📊 Dashboard", "📥 Sample Reception", "🔍 Inventory Management"])
    
    st.sidebar.divider()
    if st.sidebar.button("🔌 Log Off / Lock Portal"):
        logout()

    # --- 1. DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📈 Lab Operations Overview")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples", conn)
        conn.close()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Samples", len(df))
        col2.metric("Active Projects", df['project'].nunique() if not df.empty else 0)
        col3.metric("Last Entry", df['date_received'].iloc[-1] if not df.empty else "N/A")

        if not df.empty:
            st.subheader("Sample Distribution by Freezer")
            st.bar_chart(df['location'].value_counts())
        else:
            st.info("No data available yet. Please register a sample in the Reception tab.")

    # --- 2. REGISTRATION ---
    elif menu == "📥 Sample Reception":
        st.header("📥 New Sample Entry")
        with st.form("reg_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            proj = c1.text_input("Study/Project (e.g. MAGIA)")
            sid = c1.text_input("Sample ID / Barcode")
            dt = c1.date_input("Reception Date", datetime.now())
            stype = c2.selectbox("Material Type", SAMPLE_TYPES)
            loc = c2.selectbox("Storage Target", FREEZERS)
            staff = c2.selectbox("Responsible Officer", PERSONNEL)
            if st.form_submit_button("Finalize Accession"):
                if proj and sid:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT INTO samples (date_received, project, sample_id, sample_type, location, staff) VALUES (?,?,?,?,?,?)",
                              (str(dt), proj, sid, stype, loc, staff))
                    conn.commit()
                    conn.close()
                    st.success(f"Sample {sid} registered successfully.")
                else: st.warning("Please fill required fields.")

    # --- 3. INVENTORY & EDIT ---
    else:
        st.header("🔍 Inventory & Chain of Custody")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples ORDER BY id DESC", conn)
        conn.close()

        search = st.text_input("Filter inventory by ID, Project, or Material...")
        if search:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

        st.dataframe(df, use_container_width=True)
        
        # Export Button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📂 Download Inventory (CSV)", csv, "lab_inventory.csv", "text/csv")

        st.divider()
        st.subheader("🔄 Relocate or Update Sample")
        target_id = st.selectbox("Select ID to Edit", ["-- Select ID --"] + df['sample_id'].tolist())
        
        if target_id != "-- Select ID --":
            row = df[df['sample_id'] == target_id].iloc[0]
            with st.form("edit_box"):
                nc1, nc2 = st.columns(2)
                n_loc = nc1.selectbox("New Location", FREEZERS, index=FREEZERS.index(row['location']))
                n_stype = nc2.selectbox("Update Type", SAMPLE_TYPES, index=SAMPLE_TYPES.index(row['sample_type']))
                if st.form_submit_button("Update Records"):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("UPDATE samples SET location=?, sample_type=? WHERE sample_id=?", (n_loc, n_stype, target_id))
                    conn.commit()
                    conn.close()
                    st.success(f"Records updated for {target_id}")
                    st.rerun()
