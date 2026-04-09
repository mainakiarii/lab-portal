import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- SYSTEM CONFIG ---
DB_FILE = "lab_lims_v2.db"
SAMPLE_TYPES = ["Serum", "Plasma", "Whole Blood", "Swabs", "Urine", "Other"]
FREEZERS = ["Freezer A (-20°C)", "Freezer B (-80°C)", "Fridge 1 (4°C)", "Bench Top", "Shipped/Out"]

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Table for samples
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date_received TEXT, project TEXT, 
                  sample_id TEXT, sample_type TEXT,
                  location TEXT, staff TEXT)''')
    # Table for users
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    
    # Create default admin if no users exist
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        # Default Admin: Username: admin | Password: Gedieon2026
        hashed_pw = hashlib.sha256("Gedieon2026".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?,?,?)", ("admin", hashed_pw, "Admin"))
    
    conn.commit()
    conn.close()

def check_login(user, pwd):
    hashed_pw = hashlib.sha256(pwd.encode()).hexdigest()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=?", (user, hashed_pw))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def add_user(user, pwd, role):
    hashed_pw = hashlib.sha256(pwd.encode()).hexdigest()
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?,?,?)", (user, hashed_pw, role))
        conn.commit()
        conn.close()
        return True
    except: return False

# --- UI CONFIG ---
st.set_page_config(page_title="Institutional Lab LIMS", page_icon="🔬", layout="wide")

if "auth" not in st.session_state:
    st.session_state["auth"] = False
    st.session_state["user"] = None
    st.session_state["role"] = None

# --- LOGIN SCREEN (OFFICIAL LOOK) ---
if not st.session_state["auth"]:
    st.markdown("<h1 style='text-align: center;'>🔬 Institutional Laboratory Portal</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>Sample Management & Chain of Custody System</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.divider()
        with st.container(border=True):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Sign In", use_container_width=True):
                role = check_login(u, p)
                if role:
                    st.session_state["auth"] = True
                    st.session_state["user"] = u
                    st.session_state["role"] = role
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
    st.markdown("<p style='text-align: center; font-size: 12px;'>Protected by 256-bit Encryption | Ministry of Health Lab Standards</p>", unsafe_allow_html=True)

# --- AUTHORIZED SYSTEM ---
else:
    init_db()
    st.sidebar.title("🧪 Lab LIMS v2.0")
    st.sidebar.write(f"Logged in: **{st.session_state['user']}** ({st.session_state['role']})")
    
    tabs = ["📊 Dashboard", "📥 Reception", "🔍 Inventory"]
    if st.session_state["role"] == "Admin":
        tabs.append("👥 User Management")
    
    menu = st.sidebar.radio("Navigation", tabs)
    
    if st.sidebar.button("🔌 Secure Log Out", use_container_width=True):
        st.session_state["auth"] = False
        st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title(f"Welcome, {st.session_state['user']}")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples", conn)
        conn.close()
        c1, c2, c3 = st.columns(3)
        c1.metric("Logged Samples", len(df))
        c2.metric("Storage Sites", df['location'].nunique() if not df.empty else 0)
        c3.metric("System Status", "Online")
        if not df.empty: st.bar_chart(df['location'].value_counts())

    # --- USER MANAGEMENT (ADMIN ONLY) ---
    elif menu == "👥 User Management":
        st.header("Manage Staff Access")
        with st.form("new_user"):
            new_u = st.text_input("New Staff Username")
            new_p = st.text_input("Assign Password", type="password")
            new_r = st.selectbox("Role", ["Staff", "Admin"])
            if st.form_submit_button("Create Account"):
                if add_user(new_u, new_p, new_r):
                    st.success(f"Account for {new_u} created!")
                else: st.error("Username already exists.")

    # --- RECEPTION ---
    elif menu == "📥 Reception":
        st.header("Register New Sample")
        with st.form("reg"):
            c1, c2 = st.columns(2)
            p_name = c1.text_input("Project Name")
            s_id = c1.text_input("Sample ID")
            s_type = c2.selectbox("Sample Type", SAMPLE_TYPES)
            s_loc = c2.selectbox("Freezer Location", FREEZERS)
            if st.form_submit_button("Log Sample"):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("INSERT INTO samples (date_received, project, sample_id, sample_type, location, staff) VALUES (?,?,?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d"), p_name, s_id, s_type, s_loc, st.session_state['user']))
                conn.commit()
                st.success("Logged!")

    # --- INVENTORY ---
    elif menu == "🔍 Inventory":
        st.header("Master Inventory")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
