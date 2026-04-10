import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- SYSTEM CONFIG ---
DB_FILE = "lab_lims_final_v5.db"
SAMPLE_TYPES = ["Serum", "Plasma", "Whole Blood", "Swabs", "Urine", "Other"]
FREEZERS = ["Freezer A (-20°C)", "Freezer B (-80°C)", "Fridge 1 (4°C)", "Bench Top", "Shipped/Out"]

def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date_received TEXT, project TEXT, 
                  sample_id TEXT, sample_type TEXT, location TEXT, staff TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, full_name TEXT, role TEXT)''')
    # Table to track forgot password requests
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
                    else:
                        st.error("Invalid credentials. If you forgot your password, click 'Forgot Password' above.")
            
            elif mode == "Request Account":
                n_name = st.text_input("Full Name")
                n_u = st.text_input("Desired Username")
                n_p = st.text_input("Set Password", type="password")
                if st.button("Register Staff Account"):
                    try:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("INSERT INTO users VALUES (?,?,?,?)", (n_u, hash_pass(n_p), n_name, "Staff"))
                        conn.commit()
                        conn.close()
                        st.success("Account created! You can now Sign In.")
                    except: st.error("Username already exists.")

            elif mode == "Forgot Password":
                st.subheader("Password Reset Request")
                st.write("Enter your username. The Admin will reset your password to a temporary one.")
                f_u = st.text_input("Your Username")
                if st.button("Submit Reset Request"):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username=?", (f_u,))
                    if c.fetchone():
                        c.execute("INSERT OR REPLACE INTO reset_requests VALUES (?,?,?)", 
                                  (f_u, datetime.now().strftime("%Y-%m-%d %H:%M"), "Pending"))
                        conn.commit()
                        st.success("Request sent to Admin. Please contact Gedieon to receive your new temporary password.")
                    else:
                        st.error("Username not found in system.")
                    conn.close()

# --- AUTHORIZED PORTAL ---
else:
    init_db()
    st.sidebar.title("🧪 Lab LIMS v2.5")
    st.sidebar.write(f"Officer: **{st.session_state['full_name']}**")
    
    tabs = ["📊 Dashboard", "📥 Reception", "🔍 Inventory"]
    if st.session_state["role"] == "Admin":
        tabs.append("👥 Staff & Security")
    
    menu = st.sidebar.radio("Navigation", tabs)
    
    if st.sidebar.button("🔌 Secure Logout", use_container_width=True):
        st.session_state.update({"auth": False, "user": None})
        st.rerun()

    # --- STAFF & SECURITY (ADMIN RESET PANEL) ---
    if menu == "👥 Staff & Security":
        st.header("Security Administration")
        
        # Section 1: Reset Requests
        st.subheader("⚠️ Pending Password Reset Requests")
        conn = sqlite3.connect(DB_FILE)
        req_df = pd.read_sql_query("SELECT * FROM reset_requests WHERE status='Pending'", conn)
        
        if not req_df.empty:
            st.table(req_df)
            target = st.selectbox("Action: Select User to Reset", req_df['username'].tolist())
            new_temp = st.text_input("New Temporary Password", type="password")
            if st.button("Approve & Reset Password"):
                c = conn.cursor()
                c.execute("UPDATE users SET password=? WHERE username=?", (hash_pass(new_temp), target))
                c.execute("UPDATE reset_requests SET status='Completed' WHERE username=?", (target,))
                conn.commit()
                st.success(f"Password for {target} has been updated. Notify the staff member.")
        else:
            st.info("No pending reset requests.")
        
        st.divider()
        # Section 2: User List
        st.subheader("All Registered Personnel")
        u_df = pd.read_sql_query("SELECT username, full_name, role FROM users", conn)
        st.dataframe(u_df, use_container_width=True)
        conn.close()

    # --- REMAINING TABS (INVENTORY, RECEPTION, DASHBOARD) ---
    elif menu == "🔍 Inventory":
        # (
