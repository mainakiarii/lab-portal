import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- SYSTEM CONFIG ---
DB_FILE = "lab_lims_v5_final.db"
SAMPLE_TYPES = ["Serum", "Plasma", "Whole Blood", "Swabs", "Urine", "Other"]
FREEZERS = ["Freezer A (-20°C)", "Freezer B (-80°C)", "Fridge 1 (4°C)", "Bench Top", "Shipped/Out"]

def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def init_db():# --- DATABASE LOGIC ---
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 1. Create Samples Table
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date_received TEXT, project TEXT, 
                  sample_id TEXT, sample_type TEXT, location TEXT, staff TEXT)''')
    
    # 2. Create Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, full_name TEXT, role TEXT)''')
    
    # 3. Create Reset Requests Table (This is the one causing the error)
    c.execute('''CREATE TABLE IF NOT EXISTS reset_requests 
                 (username TEXT PRIMARY KEY, request_time TEXT, status TEXT)''')
    
    # 4. Ensure Admin exists
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?)", ("admin", hash_pass("Gedieon2026"), "Gedieon Kiarii", "Admin"))
    
    conn.commit()
    conn.close()

# CRITICAL: Run this immediately so tables exist before any user clicks anything
    init_db()
    conn = sqlite3.connect
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date_received TEXT, project TEXT, 
                  sample_id TEXT, sample_type TEXT, location TEXT, staff TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, full_name TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reset_requests 
                 (username TEXT PRIMARY KEY, request_time TEXT, status TEXT)''')
    
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?)", ("admin", hash_pass("Gedieon2026"), "Gedieon Kiarii", "Admin"))
    conn.commit()
    conn.close()

st.set_page_config(page_title="Institutional Lab Portal", page_icon="🔬", layout="wide")

if "auth" not in st.session_state:
    st.session_state.update({"auth": False, "user": None, "role": None, "full_name": None})

# --- LOGIN / SIGN UP / FORGOT PWD ---
if not st.session_state["auth"]:
    st.markdown("<h1 style='text-align: center;'>🔬 Institutional Laboratory Portal</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        mode = st.radio("System Access", ["Sign In", "Request Account", "Forgot Password"], horizontal=True)
        with st.container(border=True):
            if mode == "Sign In":
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.button("Access Portal", use_container_width=True):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT full_name, role FROM users WHERE username=? AND password=?", (u, hash_pass(p)))
                    res = c.fetchone()
                    conn.close()
                    if res:
                        st.session_state.update({"auth": True, "user": u, "full_name": res[0], "role": res[1]})
                        st.rerun()
                    else: st.error("Invalid credentials.")
            elif mode == "Request Account":
                n_name = st.text_input("Full Name")
                n_u = st.text_input("Desired Username")
                n_p = st.text_input("Set Password", type="password")
                if st.button("Register Account"):
                    try:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("INSERT INTO users VALUES (?,?,?,?)", (n_u, hash_pass(n_p), n_name, "Staff"))
                        conn.commit()
                        conn.close()
                        st.success("Account created! Please Sign In.")
                    except: st.error("Username exists.")
            elif mode == "Forgot Password":
                f_u = st.text_input("Enter your Username")
                if st.button("Submit Reset Request"):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username=?", (f_u,))
                    if c.fetchone():
                        c.execute("INSERT OR REPLACE INTO reset_requests VALUES (?,?,?)", (f_u, datetime.now().strftime("%Y-%m-%d %H:%M"), "Pending"))
                        conn.commit()
                        st.success("Request sent to Admin.")
                    else: st.error("User not found.")
                    conn.close()
else:
    init_db()
    st.sidebar.title("🧪 Lab LIMS v2.5")
    st.sidebar.write(f"User: **{st.session_state['full_name']}**")
    menu = st.sidebar.radio("Menu", ["📊 Dashboard", "📥 Reception", "🔍 Inventory", "👥 Staff Management"])
    if st.sidebar.button("🔌 Logout"):
        st.session_state.update({"auth": False, "user": None})
        st.rerun()

    if menu == "📊 Dashboard":
        st.title("Laboratory Dashboard")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples", conn)
        conn.close()
        c1, c2, c3 = st.columns(3)
        c1.metric("Samples", len(df))
        c2.metric("Projects", df['project'].nunique() if not df.empty else 0)
        c3.metric("Status", "Online")
        if not df.empty: st.bar_chart(df['location'].value_counts())

    elif menu == "📥 Reception":
        st.header("New Sample Entry")
        with st.form("reg"):
            c1, c2 = st.columns(2)
            proj = c1.text_input("Project Name")
            sid = c1.text_input("Sample ID")
            stype = c2.selectbox("Type", SAMPLE_TYPES)
            loc = c2.selectbox("Storage", FREEZERS)
            if st.form_submit_button("Log Entry"):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("INSERT INTO samples (date_received, project, sample_id, sample_type, location, staff) VALUES (?,?,?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d"), proj, sid, stype, loc, st.session_state['full_name']))
                conn.commit()
                st.success("Logged!")

    elif menu == "🔍 Inventory":
        st.header("Inventory Management")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples ORDER BY id DESC", conn)
        conn.close()
        search = st.text_input("Search...")
        if search:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
        st.dataframe(df, use_container_width=True)
        
        st.subheader("Move Sample")
        target = st.selectbox("ID to move", ["-- Select --"] + df['sample_id'].tolist())
        if target != "-- Select --":
            with st.form("move"):
                new_l = st.selectbox("New Location", FREEZERS)
                if st.form_submit_button("Update Location"):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("UPDATE samples SET location=?, staff=? WHERE sample_id=?", (new_l, st.session_state['full_name'], target))
                    conn.commit()
                    st.success("Moved!")
                    st.rerun()

    elif menu == "👥 Staff Management":
        if st.session_state["role"] == "Admin":
            st.header("Staff Administration")
            conn = sqlite3.connect(DB_FILE)
            req_df = pd.read_sql_query("SELECT * FROM reset_requests WHERE status='Pending'", conn)
            if not req_df.empty:
                st.warning("Pending Password Resets")
                st.table(req_df)
                t_user = st.selectbox("Reset User", req_df['username'].tolist())
                t_pass = st.text_input("New Temp Password", type="password")
                if st.button("Reset Now"):
                    c = conn.cursor()
                    c.execute("UPDATE users SET password=? WHERE username=?", (hash_pass(t_pass), t_user))
                    c.execute("UPDATE reset_requests SET status='Done' WHERE username=?", (t_user,))
                    conn.commit()
                    st.success("Done!")
            else: st.info("No reset requests.")
            conn.close()
        else: st.error("Admin access required.")
