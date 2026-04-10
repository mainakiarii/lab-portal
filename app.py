import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- SYSTEM CONFIG ---
DB_FILE = "lab_lims_final_v4.db"
SAMPLE_TYPES = ["Serum", "Plasma", "Whole Blood", "Swabs", "Urine", "Other"]
FREEZERS = ["Freezer A (-20°C)", "Freezer B (-80°C)", "Fridge 1 (4°C)", "Bench Top", "Shipped/Out"]

def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date_received TEXT, project TEXT, 
                  sample_id TEXT, sample_type TEXT,
                  location TEXT, staff TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, full_name TEXT, role TEXT)''')
    # Admin check
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?)", ("admin", hash_pass("Gedieon2026"), "Gedieon Kiarii", "Admin"))
    conn.commit()
    conn.close()

st.set_page_config(page_title="Institutional Lab Portal", page_icon="🔬", layout="wide")

if "auth" not in st.session_state:
    st.session_state.update({"auth": False, "user": None, "role": None, "full_name": None})

# --- LOGIN / SIGN UP ---
if not st.session_state["auth"]:
    st.markdown("<h1 style='text-align: center;'>🔬 Institutional Laboratory Portal</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        mode = st.radio("System Access", ["Sign In", "Request Account"], horizontal=True)
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
            else:
                n_name = st.text_input("Full Name")
                n_u = st.text_input("Username")
                n_p = st.text_input("Password", type="password")
                if st.button("Create Account"):
                    try:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("INSERT INTO users VALUES (?,?,?,?)", (n_u, hash_pass(n_p), n_name, "Staff"))
                        conn.commit()
                        conn.close()
                        st.success("Account created! Please Sign In.")
                    except: st.error("Username taken.")

# --- AUTHORIZED PORTAL ---
else:
    init_db()
    st.sidebar.title("🧪 Lab LIMS v2.2")
    st.sidebar.write(f"Active: **{st.session_state['full_name']}**")
    
    tabs = ["📊 Dashboard", "📥 Reception", "🔍 Inventory", "⚙️ My Settings"]
    if st.session_state["role"] == "Admin":
        tabs.append("👥 Staff Management")
    
    menu = st.sidebar.radio("Navigation", tabs)
    
    if st.sidebar.button("🔌 Secure Logout", use_container_width=True):
        st.session_state.update({"auth": False, "user": None})
        st.rerun()

    # --- PASSWORD RESET (SELF-SERVICE) ---
    if menu == "⚙️ My Settings":
        st.header("Security Settings")
        st.subheader("Change Your Password")
        with st.form("reset_pwd"):
            old_p = st.text_input("Current Password", type="password")
            new_p = st.text_input("New Password", type="password")
            confirm_p = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE username=? AND password=?", (st.session_state['user'], hash_pass(old_p)))
                if not c.fetchone():
                    st.error("Current password incorrect.")
                elif new_p != confirm_p:
                    st.error("New passwords do not match.")
                else:
                    c.execute("UPDATE users SET password=? WHERE username=?", (hash_pass(new_p), st.session_state['user']))
                    conn.commit()
                    st.success("Password updated successfully!")
                conn.close()

    # --- STAFF MANAGEMENT (ADMIN MASTER RESET) ---
    elif menu == "👥 Staff Management":
        st.header("Staff Administration")
        conn = sqlite3.connect(DB_FILE)
        u_df = pd.read_sql_query("SELECT username, full_name, role FROM users", conn)
        st.table(u_df)
        
        st.subheader("Admin: Force Password Reset")
        target_user = st.selectbox("Select Staff Member", u_df['username'].tolist())
        forced_p = st.text_input("Set New Temporary Password", type="password")
        if st.button("Reset Staff Password"):
            c = conn.cursor()
            c.execute("UPDATE users SET password=? WHERE username=?", (hash_pass(forced_p), target_user))
            conn.commit()
            st.warning(f"Password for {target_user} has been reset by Admin.")
        conn.close()

    # --- OTHER TABS (DASHBOARD, RECEPTION, INVENTORY) ---
    elif menu == "🔍 Inventory":
        # (Inventory code as before...)
        pass
    
    elif menu == "📥 Reception":
        # (Reception code as before...)
        pass

    elif menu == "📊 Dashboard":
        st.title("Laboratory Status")
        # (Dashboard code as before...)
        pass
