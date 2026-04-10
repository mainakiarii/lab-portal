import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- SYSTEM CONFIG ---
DB_FILE = "strong_lab_portal_v1.db"
SAMPLE_TYPES = ["Serum", "Plasma", "Whole Blood", "Swabs", "Urine", "Other"]
FREEZERS = ["Freezer A (-20°C)", "Freezer B (-80°C)", "Fridge 1 (4°C)", "Bench Top", "Shipped/Out"]
VOL_UNITS = ["μL", "mL", "Vials", "Slides"]

def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# --- DATABASE LOGIC (STRENGTHENED) ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Added UNIQUE constraint to sample_id for data integrity
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date_received TEXT, 
                  project TEXT, 
                  sample_id TEXT UNIQUE, 
                  sample_type TEXT, 
                  volume REAL, 
                  unit TEXT, 
                  location TEXT, 
                  staff TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, full_name TEXT, role TEXT, status TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS reset_requests 
                 (username TEXT PRIMARY KEY, request_time TEXT, status TEXT)''')
    
    # NEW: Optimization Indexes for high-volume searching
    c.execute("CREATE INDEX IF NOT EXISTS idx_sample_id ON samples(sample_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_project ON samples(project)")
    
    # Master Admin: Gedieon
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

# --- LOGIN LOGIC ---
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
                    elif res: st.error("Account pending approval by Gedieon.")
                    else: st.error("Invalid credentials.")
            
            elif mode == "Request Access":
                n_name = st.text_input("Full Name")
                n_u = st.text_input("Username").lower().strip()
                n_p = st.text_input("Password", type="password")
                if st.button("Submit Request", use_container_width=True):
                    try:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("INSERT INTO users VALUES (?,?,?,?,?)", (n_u, hash_pass(n_p), n_name, "Staff", "Pending"))
                        conn.commit()
                        conn.close()
                        st.success("Request sent to Admin.")
                    except: st.error("Username already taken.")

# --- AUTHORIZED PORTAL ---
else:
    st.sidebar.title("Lab Portal v4.0 (Strong)")
    menu_options = ["📊 Dashboard", "📥 Reception", "🔍 Inventory"]
    if st.session_state["role"] == "Admin":
        menu_options.append("👥 Access Control")
    
    menu = st.sidebar.radio("Main Menu", menu_options)
    
    if st.sidebar.button("🔌 Sign Out"):
        st.session_state.update({"auth": False, "user": None})
        st.rerun()

    # --- RECEPTION (With Integrity Checks) ---
    if menu == "📥 Reception":
        st.header("Sample Accessioning")
        with st.form("reception_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                proj = st.text_input("Study/Project")
                sid = st.text_input("Sample ID")
                stype = st.selectbox("Sample Type", SAMPLE_TYPES)
            with col_b:
                vol = st.number_input("Volume", min_value=0.0, step=0.1)
                unit = st.selectbox("Unit", VOL_UNITS)
                loc = st.selectbox("Storage Location", FREEZERS)
            
            if st.form_submit_button("Record Sample"):
                if proj and sid:
                    try:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute('''INSERT INTO samples 
                                     (date_received, project, sample_id, sample_type, volume, unit, location, staff) 
                                     VALUES (?,?,?,?,?,?,?,?)''',
                                  (datetime.now().strftime("%Y-%m-%d"), proj, sid, stype, vol, unit, loc, st.session_state['full_name']))
                        conn.commit()
                        conn.close()
                        st.success(f"Sample {sid} recorded.")
                    except sqlite3.IntegrityError:
                        st.error(f"Error: Sample ID '{sid}' already exists in the system!")
                else: st.error("Required fields missing.")

    # --- INVENTORY (Server-Side Optimized) ---
    elif menu == "🔍 Inventory":
        st.header("Master Inventory")
        conn = sqlite3.connect(DB_FILE)
        
        # Search directly in SQL for speed
        search = st.text_input("Search by Sample ID or Project...")
        
        if search:
            query = "SELECT * FROM samples WHERE sample_id LIKE ? OR project LIKE ? ORDER BY id DESC LIMIT 200"
            df = pd.read_sql_query(query, conn, params=(f'%{search}%', f'%{search}%'))
        else:
            # Only load the last 100 to save memory
            df = pd.read_sql_query("SELECT * FROM samples ORDER BY id DESC LIMIT 100", conn)
        
        conn.close()
        st.dataframe(df, use_container_width=True)
        st.caption("Displaying limited results for performance. Use search for older records.")

    # --- DASHBOARD & ACCESS CONTROL (Optimized) ---
    elif menu == "📊 Dashboard":
        st.title(f"Welcome, {st.session_state['full_name']}")
        conn = sqlite3.connect(DB_FILE)
        count = pd.read_sql_query("SELECT COUNT(*) as total FROM samples", conn).iloc[0]['total']
        conn.close()
        st.metric("Total Samples in Database", f"{count:,}")

    elif menu == "👥 Access Control":
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
