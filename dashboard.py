import streamlit as st
import sqlite3
import pandas as pd
import os
import json
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Configuration
DB_PATHS = ["shared_memory.db", "instance/shared_memory.db"]
WORKSPACE_DIR = "workspace"
PROJECTS_DIR = os.path.join(WORKSPACE_DIR, "projects")
ARCHIVES_DIR = os.path.join(WORKSPACE_DIR, "archives")

st.set_page_config(page_title="SquadOS: Project Command Center", layout="wide", page_icon="🛡️")

# Auto-refresh every 5 seconds
st_autorefresh(interval=5000, key="datarefresh")

# Ensure workspace directories exist
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(ARCHIVES_DIR, exist_ok=True)

def get_active_db_path():
    for path in DB_PATHS:
        if os.path.exists(path):
            return path
    return None

def get_db_connection():
    path = get_active_db_path()
    if path:
        try:
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception:
            pass
    return None

def load_missions():
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql_query("SELECT * FROM missions ORDER BY id ASC", conn)
            conn.close()
            return df
        except Exception:
            pass
    return pd.DataFrame()

def submit_new_mission(prompt):
    """Smart inserter that handles both older and newer database schemas."""
    for path in DB_PATHS:
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(missions)")
                columns = [c[1] for c in cursor.fetchall()]
                
                if 'goal' in columns:
                    cursor.execute("INSERT INTO missions (goal, status) VALUES (?, ?)", (prompt, "QUEUED"))
                elif 'name' in columns and 'description' in columns:
                    # Create a unique name based on timestamp
                    task_name = f"ChatTask_{datetime.now().strftime('%H%M%S')}"
                    cursor.execute("INSERT INTO missions (name, description, status) VALUES (?, ?, ?)", (task_name, prompt, "QUEUED"))
                
                conn.commit()
                conn.close()
            except Exception as e:
                st.error(f"Failed to push to {path}: {e}")

def load_global_stats():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(prompt_tokens), SUM(completion_tokens), SUM(cost_usd) FROM tasks")
            stats = cursor.fetchone()
            conn.close()
            return stats
        except Exception:
            pass
    return (0, 0, 0.0)

def list_projects():
    active = sorted([d for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))], reverse=True)
    archived = sorted([d for d in os.listdir(ARCHIVES_DIR) if os.path.isdir(os.path.join(ARCHIVES_DIR, d))], reverse=True)
    return active, archived

def get_project_status(project_id, is_active):
    if not is_active:
        return "Archived"
    project_path = os.path.join(PROJECTS_DIR, project_id)
    if os.path.exists(os.path.join(project_path, "STATUS_AWAITING_COMMIT")):
        return "Awaiting Commit"
    return "Exploring"

# --- UI ---

st.title("🛡️ SquadOS: Project Command Center")

# Sidebar
st.sidebar.header("🕹️ Control Panel")

active_projects, archived_projects = list_projects()

if 'selected_proj' not in st.session_state:
    st.session_state.selected_proj = None
if 'is_active' not in st.session_state:
    st.session_state.is_active = True

with st.sidebar:
    st.subheader("📂 Branch Explorer")

    st.write("**Active Projects**")
    if not active_projects:
        st.write("No active projects.")
    for proj in active_projects:
        if st.button(f"🚀 {proj}", key=f"btn_act_{proj}"):
            st.session_state.selected_proj = proj
            st.session_state.is_active = True

    st.write("**Archived Projects**")
    if not archived_projects:
        st.write("No archived projects.")
    for proj in archived_projects:
        if st.button(f"📦 {proj}", key=f"btn_arc_{proj}"):
            st.session_state.selected_proj = proj
            st.session_state.is_active = False

    if st.button("Reset View (Go to Chat)"):
        st.session_state.selected_proj = None

    # Global Stats
    stats = load_global_stats()
    st.markdown("---")
    st.subheader("📊 Global Performance")
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Total Cost", f"${stats[2] if stats[2] else 0.0:.4f}")
    col_s2.metric("Total Tokens", f"{ (stats[0] or 0) + (stats[1] or 0) :,}")

selected_project = st.session_state.selected_proj
is_selected_active = st.session_state.is_active

if not selected_project:
    st.info("👋 Welcome to SquadOS. Dispatch a new mission below, or click a project on the left to view details.")

    # --- CHAT GPT LIKE INTERFACE ---
    st.subheader("💬 Mission Control Chat")
    
    # Display Chat History (Past Missions)
    missions = load_missions()
    chat_container = st.container(height=500)
    
    with chat_container:
        if not missions.empty:
            for _, row in missions.iterrows():
                # Extract the prompt text based on schema
                prompt_text = row.get('goal') if pd.notna(row.get('goal')) else row.get('description', 'Unknown Task')
                status = row.get('status', 'UNKNOWN').upper()
                
                # User Bubble
                with st.chat_message("user"):
                    st.write(prompt_text)
                
                # Agent Bubble
                with st.chat_message("assistant", avatar="🤖"):
                    if status == "QUEUED":
                        st.info("⏳ Queued and waiting for the SquadOS worker to pick this up...")
                    elif status == "IN_PROGRESS":
                        st.warning("⚡ The team is currently executing this mission in the background.")
                    elif status == "COMPLETED":
                        st.success("✅ Mission accomplished! Check the Branch Explorer for results.")
                    elif status == "FAILED":
                        st.error("❌ Mission failed. Please check terminal logs.")
                    else:
                        st.write(f"Status: {status}")
        else:
            st.write("No missions found. Send a message below to start!")

    # Chat Input Box
    if prompt := st.chat_input("Ask SquadOS to do something... (e.g., 'Go to wikipedia and take a screenshot of AI')"):
        submit_new_mission(prompt)
        st.rerun()

else:
    # --- INDIVIDUAL PROJECT VIEW ---
    status = get_project_status(selected_project, is_selected_active)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header(f"Project: `{selected_project}`")
    with col2:
        if st.button("🔙 Back to Chat"):
            st.session_state.selected_proj = None
            st.rerun()

    st.markdown(f"**Current Status:** {status}")

    project_root = os.path.join(PROJECTS_DIR if is_selected_active else ARCHIVES_DIR, selected_project)

    tab1, tab2, tab3, tab4 = st.tabs(["🖼️ Gallery", "📜 Live Logs", "🧠 Memory", "✅ Commit Review"])

    with tab1:
        st.subheader("Visual Artifacts")
        visuals_path = os.path.join(project_root, "visuals")
        if os.path.exists(visuals_path):
            files = os.listdir(visuals_path)
            img_exts = ('.png', '.jpg', '.jpeg', '.webp')
            vid_exts = ('.mp4', '.webm')

            visual_files = sorted([f for f in files if f.lower().endswith(img_exts + vid_exts)], reverse=True)
            if visual_files:
                cols = st.columns(2)
                for idx, v_file in enumerate(visual_files):
                    v_path = os.path.join(visuals_path, v_file)
                    with cols[idx % 2]:
                        st.write(f"**{v_file}**")
                        if v_file.lower().endswith(img_exts):
                            st.image(v_path, use_container_width=True)
                        elif v_file.lower().endswith(vid_exts):
                            st.video(v_path)
            else:
                st.write("No visual artifacts found.")
        else:
            st.error("Visuals directory missing.")

    with tab2:
        st.subheader("Real-time Tool Execution")
        log_path = os.path.join(project_root, "session_log.json")
        if os.path.exists(log_path):
            try:
                with open(log_path, "r") as f:
                    logs = json.load(f)

                if logs:
                    for entry in reversed(logs):
                        with st.expander(f"🛠️ {entry.get('tool')} @ {entry.get('timestamp')}", expanded=(entry == logs[-1])):
                            st.write("**Inputs:**")
                            st.code(json.dumps(entry.get('inputs'), indent=2), language="json")
                            st.write("**Output:**")
                            st.text(entry.get('output'))
                else:
                    st.write("Log is empty.")
            except Exception as e:
                st.error(f"Error reading logs: {e}")
        else:
            st.write("No `session_log.json` found.")

    with tab3:
        st.subheader("Project Context & Learnings")
        memory_path = os.path.join(project_root, "project_memory.md")
        if os.path.exists(memory_path):
            with open(memory_path, "r") as f:
                st.markdown(f.read())
        else:
            st.write("No `project_memory.md` found.")

    with tab4:
        st.subheader("Pending Commit Reviewer")
        manifest_path = os.path.join(project_root, "artifacts.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                st.info("The agent has nominated these artifacts as 'Final Outputs'.")
                # Manifest rendering logic...
            except Exception as e:
                st.error(f"Error parsing artifacts.json: {e}")
        else:
            st.write("Manifest will appear when the project is ready for commit.")