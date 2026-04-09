import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- SYSTEM CONFIG ---
DB_FILE = "lab_lims_v3.db"
SAMPLE_TYPES = ["Serum", "Plasma", "Whole Blood", "Swabs", "Urine", "Other"]
FREEZERS = ["Freezer A (-20°C)", "Freezer B (-80°C)", "Fridge 1 (4°C)", "Bench Top", "Shipped/Out"]

# --- DATABASE LOGIC ---
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
    # Default Admin Check
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        hashed_pw = hashlib.sha256("Gedieon2026".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?,?,?,?)", ("admin", hashed_pw, "Gedieon Kiarii", "Admin"))
    conn.commit()
    conn.close()

def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# --- UI CONFIG ---
st.set_page_config(page_title="Institutional Lab Portal", page_icon="🔬", layout="wide")

if "auth" not in st.session_state:
    st.session_state.update({"auth": False, "user": None, "role": None, "full_name": None})

# --- LOGIN & SIGN UP PAGE ---
if not st.session_state["auth"]:
    st.markdown("<h1 style='text-align: center; color: #0E1117;'>🔬 Institutional Laboratory Portal</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #555;'>Ministry of Health / Research Division</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.divider()
        mode = st.radio("System Access", ["Sign In", "Request Account (Sign Up)"], horizontal=True)
        
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
                        st.error("Invalid credentials.")
            
            else:
                new_name = st.text_input("Full Name (e.g. Sophia Wanjiku)")
                new_u = st.text_input("Desired Username")
                new_p = st.text_input("Set Password", type="password")
                confirm_p = st.text_input("Confirm Password", type="password")
                if st.button("Create Account", use_container_width=True):
                    if new_p != confirm_p:
                        st.error("Passwords do not match.")
                    elif len(new_p) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        try:
                            conn = sqlite3.connect(DB_FILE)
                            c = conn.cursor()
                            c.execute("INSERT INTO users VALUES (?,?,?,?)", (new_u, hash_pass(new_p), new_name, "Staff"))
                            conn.commit()
                            conn.close()
                            st.success("Account created! You can now Sign In.")
                        except:
                            st.error("Username already exists.")

# --- AUTHORIZED SYSTEM ---
else:
    init_
