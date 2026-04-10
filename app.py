import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- SYSTEM CONFIG ---
DB_FILE = "sample_lab_v7.db"
SAMPLE_TYPES = ["Serum", "Plasma", "Whole Blood", "Swabs", "Urine", "Other"]
FREEZERS = ["Freezer A (-20°C)", "Freezer B (-80°C)", "Fridge 1 (4°C)", "Bench Top", "Shipped/Out"]

def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date_received TEXT, project TEXT, 
                  sample_id TEXT, sample_type TEXT, location TEXT, staff TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, full_name TEXT, role TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reset_requests 
                 (username TEXT PRIMARY KEY, request_time TEXT, status TEXT)''')
    
    # MASTER ADMIN: Gedieon
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

# --- LOGIN / SIGN UP / FORGOT PWD ---
if not st.session_state["auth"]:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Sample Laboratory Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748B;'>Secure Sample Management System</p>", unsafe_allow_html=True)
    
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
                    if res:
                        if res[2] == "Active":
                            st.session_state.update({"auth": True, "user": u, "full_name": res[0], "role": res[1]})
                            st.rerun()
                        else:
                            st.error("Account pending approval. Please contact Gedieon.")
                    else: st.error("Invalid credentials.")
            
            elif mode == "Request Access":
                n_name = st.text_input("Full Name")
                n_u = st.text_input("Username (Choice)").lower().strip()
                n_p = st.text_input("Password (Choice)", type="password")
                if st.button("Submit Request", use_container_width=True):
                    try:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        # Default status is 'Pending' - only Gedieon can make them 'Active'
                        c.execute("INSERT INTO users VALUES (?,?,?,?,?)", (n_u, hash_pass(n_p), n_name, "Staff", "Pending"))
                        conn.commit()
                        conn.close()
                        st.success("Access request submitted to Gedieon.")
                    except: st.error("Username already taken.")

            elif mode == "Forgot Password":
                f_u = st.text_input("Enter your Username").lower().strip()
                if st.button("Request Reset", use_container_width=True):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT OR REPLACE INTO reset_requests VALUES (?,?,?)", 
                             (f_u, datetime.now().strftime("%Y-%m-%d %H:%M"), "Pending"))
                    conn.commit()
                    st.success("Request sent to Gedieon.")
                    conn.close()

# --- AUTHORIZED PORTAL ---
else:
    st.sidebar.title("Lab Portal v3.0")
    st.sidebar.write(f"Logged in: **{st.session_state['full_name']}**")
    
    menu_options = ["📊 Dashboard", "📥 Reception", "🔍 Inventory"]
    if st.session_state["role"] == "Admin":
        menu_options.append("👥 Access Control")
    
    menu = st.sidebar.radio("Main Menu", menu_options)
    
    if st.sidebar.button("🔌 Sign Out", use_container_width=True):
        st.session_state.update({"auth": False, "user": None})
        st.rerun()

    # --- ACCESS CONTROL (FOR GEDIEON ONLY) ---
    if menu == "👥 Access Control":
        st.header("Admin Control Panel")
        conn = sqlite3.connect(DB_FILE)
        
        # 1. Approve New Users
        st.subheader("Pending Access Requests")
        pending_df = pd.read_sql_query("SELECT username, full_name, status FROM users WHERE status='Pending'", conn)
        if not pending_df.empty:
            st.table(pending_df)
            user_to_act = st.selectbox("Select User to Approve", pending_df['username'].tolist())
            if st.button("Grant Access"):
                c = conn.cursor()
                c.execute("UPDATE users SET status='Active' WHERE username=?", (user_to_act,))
                conn.commit()
                st.success(f"Access granted to {user_to_act}")
                st.rerun()
        else: st.info("No pending access requests.")

        # 2. Reset Password Requests
        st.divider()
        st.subheader("Reset Requests")
        res_df = pd.read_sql_query("SELECT * FROM reset_requests WHERE status='Pending'", conn)
        if not res_df.empty:
            st.table(res_df)
            r_user = st.selectbox("Select User to Reset", res_df['username'].tolist())
            r_pass = st.text_input("Temporary Password", type="password")
            if st.button("Finish Reset"):
                c = conn.cursor()
                c.execute("UPDATE users SET password=? WHERE username=?", (hash_pass(r_pass), r_user))
                c.execute("UPDATE reset_requests SET status='Done' WHERE username=?", (r_user,))
                conn.commit()
                st.success("Password Updated.")
        
        conn.close()

    # --- OTHER SECTIONS (INVENTORY, RECEPTION, DASHBOARD) ---
    elif menu == "🔍 Inventory":
        st.header("Master Inventory")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples ORDER BY id DESC", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)

    elif menu == "📥 Reception":
        st.header("Sample Accessioning")
        with st.form("reg"):
            c1, c2 = st.columns(2)
            proj = c1.text_input("Study/Project")
            sid = c1.text_input("Sample ID")
            stype = c2.selectbox("Type", SAMPLE_TYPES)
            loc = c2.selectbox("Storage", FREEZERS)
            if st.form_submit_button("Record Sample"):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("INSERT INTO samples (date_received, project, sample_id, sample_type, location, staff) VALUES (?,?,?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d"), proj, sid, stype, loc, st.session_state['full_name']))
                conn.commit()
                conn.close()
                st.success("Sample recorded.")

    elif menu == "📊 Dashboard":
        st.title(f"Hello, {st.session_state['full_name']}")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples", conn)
        conn.close()
        st.metric("Total Samples Registered", len(df))
        if not df.empty: st.bar_chart(df['location'].value_counts())
