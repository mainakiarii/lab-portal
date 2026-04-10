import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- SYSTEM CONFIG ---
DB_FILE = "sample_lab_v8.db"
SAMPLE_TYPES = ["Serum", "Plasma", "Whole Blood", "Swabs", "Urine", "Other"]
FREEZERS = ["Freezer A (-20°C)", "Freezer B (-80°C)", "Fridge 1 (4°C)", "Bench Top", "Shipped/Out"]
VOL_UNITS = ["μL", "mL", "Vials", "Slides"] # The new pull-down menu options

def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Updated table to include volume and units
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date_received TEXT, 
                  project TEXT, 
                  sample_id TEXT, 
                  sample_type TEXT, 
                  volume REAL, 
                  unit TEXT, 
                  location TEXT, 
                  staff TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, full_name TEXT, role TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reset_requests 
                 (username TEXT PRIMARY KEY, request_time TEXT, status TEXT)''')
    
    c.execute("SELECT * FROM users WHERE username='gedieon'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?,?)", 
                 ("gedieon", hash_pass("Gedieon2026"), "Gedieon Kiarii", "Admin", "Active"))
    conn.commit()
    conn.close()

init_db()

# --- UI SETUP ---
st.set_page_config(page_title="Sample Laboratory Portal", layout="wide")

if "auth" not in st.session_state:
    st.session_state.update({"auth": False, "user": None, "role": None, "full_name": None})

# --- LOGIN LOGIC (Same as before) ---
if not st.session_state["auth"]:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Sample Laboratory Portal</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        mode = st.radio("Portal Access", ["Sign In", "Request Access", "Forgot Password"], horizontal=True)
        with st.container(border=True):
            if mode == "Sign In":
                u = st.text_input("Username").lower().strip()
                p = st.text_input("Password", type="password")
                if st.button("Log In", use_container_width=True):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT full_name, role, status FROM users WHERE username=? AND password=?", (u, hash_pass(p)))
                    res = c.fetchone()
                    conn.close()
                    if res and res[2] == "Active":
                        st.session_state.update({"auth": True, "user": u, "full_name": res[0], "role": res[1]})
                        st.rerun()
                    elif res: st.error("Account pending approval.")
                    else: st.error("Invalid credentials.")
            # (Request Access and Forgot Password logic remains the same...)
            elif mode == "Request Access":
                n_name = st.text_input("Full Name")
                n_u = st.text_input("Username").lower().strip()
                n_p = st.text_input("Password", type="password")
                if st.button("Submit Request"):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO users VALUES (?,?,?,?,?)", (n_u, hash_pass(n_p), n_name, "Staff", "Pending"))
                        conn.commit()
                        st.success("Request sent to Gedieon.")
                    except: st.error("Username taken.")
                    conn.close()

# --- AUTHORIZED PORTAL ---
else:
    st.sidebar.title("Lab Portal v3.1")
    menu_options = ["📊 Dashboard", "📥 Reception", "🔍 Inventory"]
    if st.session_state["role"] == "Admin":
        menu_options.append("👥 Access Control")
    
    menu = st.sidebar.radio("Main Menu", menu_options)
    
    if st.sidebar.button("🔌 Sign Out"):
        st.session_state.update({"auth": False, "user": None})
        st.rerun()

    # --- UPDATED RECEPTION SECTION ---
    if menu == "📥 Reception":
        st.header("Sample Accessioning")
        with st.form("reception_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            
            with col_a:
                proj = st.text_input("Study/Project")
                sid = st.text_input("Sample ID")
                stype = st.selectbox("Sample Type", SAMPLE_TYPES)
            
            with col_b:
                # NEW VOLUME AND PULL-DOWN MENU
                vol = st.number_input("Volume", min_value=0.0, step=0.1)
                unit = st.selectbox("Unit", VOL_UNITS)
                loc = st.selectbox("Storage Location", FREEZERS)
            
            if st.form_submit_button("Record Sample"):
                if proj and sid:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute('''INSERT INTO samples 
                                 (date_received, project, sample_id, sample_type, volume, unit, location, staff) 
                                 VALUES (?,?,?,?,?,?,?,?)''',
                              (datetime.now().strftime("%Y-%m-%d"), proj, sid, stype, vol, unit, loc, st.session_state['full_name']))
                    conn.commit()
                    conn.close()
                    st.success(f"Sample {sid} ({vol} {unit}) recorded successfully.")
                else:
                    st.error("Study and Sample ID are required.")

    # --- INVENTORY VIEW ---
    elif menu == "🔍 Inventory":
        st.header("Master Inventory")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples ORDER BY id DESC", conn)
        conn.close()
        
        # Displaying with the new columns
        st.dataframe(df, use_container_width=True)

    # --- OTHER SECTIONS (DASHBOARD & ACCESS CONTROL) ---
    elif menu == "📊 Dashboard":
        st.title(f"Welcome, {st.session_state['full_name']}")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples", conn)
        conn.close()
        if not df.empty:
            st.metric("Total Samples", len(df))
            st.bar_chart(df['sample_type'].value_counts())

    elif menu == "👥 Access Control":
        # (Same Admin logic as before)
        st.header("Admin Control")
        conn = sqlite3.connect(DB_FILE)
        pending = pd.read_sql_query("SELECT username, full_name FROM users WHERE status='Pending'", conn)
        if not pending.empty:
            st.table(pending)
            u_to_app = st.selectbox("Approve User", pending['username'].tolist())
            if st.button("Grant Access"):
                c = conn.cursor()
                c.execute("UPDATE users SET status='Active' WHERE username=?", (u_to_app,))
                conn.commit()
                st.rerun()
        else: st.info("No pending requests.")
        conn.close()
