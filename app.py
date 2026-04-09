import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Database logic
DB_FILE = "samples.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS samples 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date_received TEXT, project TEXT, 
                  sample_id TEXT, location TEXT, staff TEXT)''')
    conn.commit()
    conn.close()

# Portal Interface
st.set_page_config(page_title="Lab Portal", layout="wide")

if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    st.title("🔒 Lab Portal Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "LabTeam2026": # Your password
            st.session_state["auth"] = True
            st.rerun()
else:
    init_db()
    st.title("🧪 Sample Reception Portal")
    menu = st.sidebar.radio("Menu", ["Add Sample", "Locate Sample"])

    if menu == "Add Sample":
        with st.form("add_form"):
            project = st.text_input("Project Name")
            s_id = st.text_input("Sample ID")
            loc = st.text_input("Storage Location")
            staff = st.text_input("Staff Name")
            if st.form_submit_button("Save Sample"):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("INSERT INTO samples (date_received, project, sample_id, location, staff) VALUES (?,?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d %H:%M"), project, s_id, loc, staff))
                conn.commit()
                st.success(f"Sample {s_id} stored in {loc}")

    else:
        search = st.text_input("Search Project or ID")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM samples", conn)
        if search:
            df = df[df['project'].str.contains(search, case=False) | df['sample_id'].str.contains(search, case=False)]
        st.dataframe(df, use_container_width=True)
