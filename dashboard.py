import streamlit as st
import sqlite3
import pandas as pd
import os
import json
import mimetypes
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

def save_uploaded_files(uploaded_files):
    if not uploaded_files:
        return None

    # 200MB per file, 500MB total cap
    MAX_FILE_SIZE = 200 * 1024 * 1024
    MAX_TOTAL_SIZE = 500 * 1024 * 1024

    total_size = sum(f.size for f in uploaded_files)
    if total_size > MAX_TOTAL_SIZE:
        st.error(f"Total upload size exceeds 500MB limit (Current: {total_size / (1024*1024):.1f}MB)")
        return "ERROR_SIZE"

    for f in uploaded_files:
        if f.size > MAX_FILE_SIZE:
            st.error(f"File '{f.name}' exceeds 200MB limit.")
            return "ERROR_SIZE"

    # Create a temporary directory for these uploads
    temp_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    upload_dir = os.path.join(WORKSPACE_DIR, "uploads", f"pending_{temp_id}")
    os.makedirs(upload_dir, exist_ok=True)

    files_metadata = []
    for f in uploaded_files:
        filename = os.path.basename(f.name)
        name, ext = os.path.splitext(filename)

        target_path = os.path.join(upload_dir, filename)
        # Handle duplicate filenames in the same upload batch (unlikely but possible)
        if os.path.exists(target_path):
             filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
             target_path = os.path.join(upload_dir, filename)

        with open(target_path, "wb") as out:
            out.write(f.getbuffer())

        files_metadata.append({
            "name": filename,
            "type": f.type,
            "size_bytes": f.size,
            "temp_path": os.path.abspath(target_path)
        })

    return json.dumps(files_metadata)

def submit_new_mission(prompt, uploaded_files_json=None):
    """Smart inserter that handles both older and newer database schemas."""
    for path in DB_PATHS:
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(missions)")
                columns = [c[1] for c in cursor.fetchall()]
                
                if 'goal' in columns:
                    if 'uploaded_files' in columns:
                        cursor.execute("INSERT INTO missions (goal, status, uploaded_files) VALUES (?, ?, ?)", (prompt, "QUEUED", uploaded_files_json))
                    else:
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
    # Optimized using os.scandir to reduce system calls from O(2N) to O(N)
    with os.scandir(PROJECTS_DIR) as entries:
        active = sorted([e.name for e in entries if e.is_dir()], reverse=True)
    with os.scandir(ARCHIVES_DIR) as entries:
        archived = sorted([e.name for e in entries if e.is_dir()], reverse=True)
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
        label = f"📍 {proj}" if proj == st.session_state.selected_proj else f"🚀 {proj}"
        if st.button(label, key=f"btn_act_{proj}", width="stretch"):
            st.session_state.selected_proj = proj
            st.session_state.is_active = True
            st.rerun()

    st.write("**Archived Projects**")
    if not archived_projects:
        st.write("No archived projects.")
    for proj in archived_projects:
        label = f"📍 {proj}" if proj == st.session_state.selected_proj else f"📦 {proj}"
        if st.button(label, key=f"btn_arc_{proj}", width="stretch"):
            st.session_state.selected_proj = proj
            st.session_state.is_active = False
            st.rerun()

    if st.button("Reset View (Go to Chat)", width="stretch"):
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

                    # Show uploaded files if any
                    uploaded_files_json = row.get('uploaded_files')
                    if uploaded_files_json:
                        try:
                            files = json.loads(uploaded_files_json)
                            if files:
                                st.markdown("---")
                                st.markdown(f"📎 **Attached Files ({len(files)}):**")
                                for f in files:
                                    st.caption(f"📄 {f['name']} ({f['size_bytes']//1024} KB)")
                        except Exception:
                            pass
                
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
    with st.container():
        uploaded_files = st.file_uploader("📎 Attach documents, images, videos, etc.", accept_multiple_files=True, label_visibility="collapsed")
        if prompt := st.chat_input("Ask SquadOS to do something... (e.g., 'Analyze this document for me')"):
            files_json = save_uploaded_files(uploaded_files)
            if files_json != "ERROR_SIZE":
                submit_new_mission(prompt, files_json)
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
                            try:
                                st.image(v_path, use_container_width=True)
                            except Exception:
                                st.warning(f"Could not load image: {v_file}")
                        elif v_file.lower().endswith(vid_exts):
                            st.video(v_path)

                        # Add a download button for accessibility/usability
                        mime_type, _ = mimetypes.guess_type(v_path)
                        with open(v_path, "rb") as f:
                            st.download_button(
                                label=f"💾 Download {v_file}",
                                data=f,
                                file_name=v_file,
                                mime=mime_type or "application/octet-stream",
                                key=f"dl_{v_file}",
                                width="stretch"
                            )
            else:
                st.write("No visual artifacts found.")
        else:
            st.error("Visuals directory missing.")

    with tab2:
        st.subheader("Real-time Tool Execution")
        log_jsonl = os.path.join(project_root, "session_log.jsonl")
        log_json = os.path.join(project_root, "session_log.json")

        logs = []
        if os.path.exists(log_jsonl):
            try:
                with open(log_jsonl, "r") as f:
                    for line in f:
                        if line.strip():
                            logs.append(json.loads(line))
            except Exception as e:
                st.error(f"Error reading .jsonl log: {e}")
        elif os.path.exists(log_json):
            # Backward compatibility for old .json format
            try:
                with open(log_json, "r") as f:
                    logs = json.load(f)
            except Exception as e:
                st.error(f"Error reading .json log: {e}")
        else:
            st.write("No `session_log.jsonl` or `session_log.json` found.")

        if logs:
            for entry in reversed(logs):
                with st.expander(f"🛠️ {entry.get('tool')} @ {entry.get('timestamp')}", expanded=(entry == logs[-1])):
                    st.write("**Inputs:**")
                    st.code(json.dumps(entry.get('inputs'), indent=2), language="json")
                    st.write("**Output:**")
                    st.code(entry.get('output'))
        elif os.path.exists(log_jsonl) or os.path.exists(log_json):
            st.write("Log is empty.")

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