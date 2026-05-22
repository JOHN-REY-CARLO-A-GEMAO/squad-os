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
            return (stats[0], stats[1], stats[2]) if stats else (0, 0, 0.0)
        except Exception:
            pass
    return (0, 0, 0.0)

def list_projects():
    # Use os.scandir() for O(N) traversal, replacing O(2N) listdir+isdir pattern
    with os.scandir(PROJECTS_DIR) as active_entries:
        active = sorted([entry.name for entry in active_entries if entry.is_dir()], reverse=True)
    with os.scandir(ARCHIVES_DIR) as archived_entries:
        archived = sorted([entry.name for entry in archived_entries if entry.is_dir()], reverse=True)
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

if st.session_state.get("mission_submitted"):
    st.toast("✅ Mission dispatched successfully!")
    st.session_state.mission_submitted = False

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
        if st.button(label, key=f"btn_act_{proj}", width="stretch", help=f"Open active project: {proj}"):
            st.session_state.selected_proj = proj
            st.session_state.is_active = True
            st.rerun()

    st.write("**Archived Projects**")
    if not archived_projects:
        st.write("No archived projects.")
    for proj in archived_projects:
        label = f"📍 {proj}" if proj == st.session_state.selected_proj else f"📦 {proj}"
        if st.button(label, key=f"btn_arc_{proj}", width="stretch", help=f"Open archived project: {proj}"):
            st.session_state.selected_proj = proj
            st.session_state.is_active = False
            st.rerun()

    if st.button("Reset View (Go to Chat)", width="stretch", shortcut="Esc", help="Return to the main chat interface"):
        st.session_state.selected_proj = None
        st.rerun()

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
        uploaded_files = st.file_uploader("📎 Attach documents, images, videos, etc.", accept_multiple_files=True, label_visibility="collapsed", help="Total upload limit: 500MB (200MB per file)")
        if prompt := st.chat_input("Ask SquadOS to do something... (e.g., 'Analyze this document for me')"):
            files_json = save_uploaded_files(uploaded_files)
            if files_json != "ERROR_SIZE":
                submit_new_mission(prompt, files_json)
                st.session_state.mission_submitted = True
                st.rerun()

else:
    # --- INDIVIDUAL PROJECT VIEW ---
    status = get_project_status(selected_project, is_selected_active)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header(f"Project: `{selected_project}`")
    with col2:
        if st.button("🔙 Back to Chat", shortcut="Esc", help="Return to the main chat interface"):
            st.session_state.selected_proj = None
            st.rerun()

    st.markdown(f"**Current Status:** {status}")

    project_root = os.path.join(PROJECTS_DIR if is_selected_active else ARCHIVES_DIR, selected_project)

    tab1, tab2, tab3, tab4 = st.tabs(["🖼️ Project Files", "📜 Live Logs", "🧠 Memory", "✅ Commit Review"])

    with tab1:
        st.subheader("All Project Files")
        EXTENSIONS_CODE = {'.py', '.js', '.ts', '.html', '.css', '.json', '.md', '.yaml', '.yml', '.toml', '.cfg', '.ini', '.sh', '.bat', '.ps1', '.sql', '.txt', '.env.example', '.gitignore'}
        EXTENSIONS_IMG = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.bmp'}
        EXTENSIONS_VID = {'.mp4', '.webm', '.avi', '.mov'}

        all_files = []
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for f in files:
                if f.startswith('.'):
                    continue
                rel = os.path.relpath(os.path.join(root, f), project_root)
                all_files.append(rel)

        if all_files:
            view_filter = st.radio("Filter", ["All", "Code", "Images", "Documents"], horizontal=True, label_visibility="collapsed")

            code_exts = EXTENSIONS_CODE
            img_exts = EXTENSIONS_IMG
            doc_exts = {'.md', '.txt', '.pdf'}

            grouped = {}
            for rel in all_files:
                ext = os.path.splitext(rel)[1].lower()
                if view_filter == "Code" and ext not in code_exts:
                    continue
                if view_filter == "Images" and ext not in img_exts:
                    continue
                if view_filter == "Documents" and ext not in doc_exts:
                    continue
                dirname = os.path.dirname(rel) or "."
                grouped.setdefault(dirname, []).append(rel)

            for dirname in sorted(grouped.keys()):
                with st.expander(f"📁 {dirname}/", expanded=(dirname == ".")):
                    for rel in sorted(grouped[dirname]):
                        fpath = os.path.join(project_root, rel)
                        ext = os.path.splitext(rel)[1].lower()
                        col_a, col_b = st.columns([4, 1])
                        with col_a:
                            if ext in img_exts:
                                try:
                                    st.image(fpath, use_container_width=True)
                                except Exception:
                                    st.write(f"🖼️ {rel}")
                            elif ext in code_exts:
                                try:
                                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                                        st.code(fh.read(), language="python" if ext == ".py" else None)
                                except Exception:
                                    st.write(f"📄 {rel}")
                            else:
                                st.write(f"📄 {rel}")
                        with col_b:
                            mime_type, _ = mimetypes.guess_type(fpath)
                            with open(fpath, "rb") as fh:
                                st.download_button("💾", data=fh, file_name=os.path.basename(rel), mime=mime_type or "application/octet-stream", key=f"dl1_{rel}", use_container_width=True)

            # Also show visuals as a dedicated section if they exist
            visuals_path = os.path.join(project_root, "visuals")
            if os.path.exists(visuals_path):
                img_vid_exts = EXTENSIONS_IMG | EXTENSIONS_VID
                with os.scandir(visuals_path) as entries:
                    visual_files = sorted([entry.name for entry in entries if entry.is_file() and entry.name.lower().endswith(tuple(img_vid_exts))], reverse=True)
                if visual_files:
                    st.markdown("---")
                    st.subheader("🖼️ Visuals")
                    cols = st.columns(2)
                    for idx, v_file in enumerate(visual_files):
                        v_path = os.path.join(visuals_path, v_file)
                        with cols[idx % 2]:
                            st.write(f"**{v_file}**")
                            if v_file.lower().endswith(tuple(EXTENSIONS_IMG)):
                                try:
                                    st.image(v_path, use_container_width=True)
                                except Exception:
                                    st.warning(f"Could not load image: {v_file}")
                            elif v_file.lower().endswith(tuple(EXTENSIONS_VID)):
                                st.video(v_path)
                            mime_type, _ = mimetypes.guess_type(v_path)
                            with open(v_path, "rb") as fh:
                                st.download_button("💾 Download", data=fh, file_name=v_file, mime=mime_type or "application/octet-stream", key=f"dl_vis_{v_file}", use_container_width=True)
        else:
            st.info("No files found in this project. 🗂️")

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
            st.info("No execution logs found. 📜")

        if logs:
            for entry in reversed(logs):
                ts = entry.get('timestamp')
                try:
                    ts = datetime.fromisoformat(ts).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass
                with st.expander(f"🛠️ {entry.get('tool')} @ {ts}", expanded=(entry == logs[-1])):
                    st.write("**Inputs:**")
                    st.code(json.dumps(entry.get('inputs'), indent=2), language="json")
                    st.write("**Output:**")
                    st.code(entry.get('output'))
        elif os.path.exists(log_jsonl) or os.path.exists(log_json):
            st.info("Log is empty. 📜")

    with tab3:
        st.subheader("Project Context & Learnings")
        st.caption("Architecture decisions, execution notes, and agent observations recorded during this mission.")
        memory_path = os.path.join(project_root, "project_memory.md")
        if os.path.exists(memory_path):
            with open(memory_path, "r") as f:
                st.markdown(f.read())
        else:
            st.info("No project memory found. 🧠")

    with tab4:
        st.subheader("Final Output — Committed Artifacts")
        st.caption("All files that were committed by the agent as the final deliverable.")

        all_out = []
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for f in files:
                if f.startswith('.'):
                    continue
                rel = os.path.relpath(os.path.join(root, f), project_root)
                all_out.append(rel)

        if not all_out:
            st.info("No committed artifacts found. 📋")
        else:
            st.success(f"**{len(all_out)} files** committed in this mission.")

            # Show README.md first as a default overview
            readme_files = [f for f in all_out if os.path.basename(f).lower() == 'readme.md']
            if readme_files:
                with st.expander("📖 README — Project Overview", expanded=True):
                    for rf in readme_files:
                        rpath = os.path.join(project_root, rf)
                        try:
                            with open(rpath, "r", encoding="utf-8", errors="ignore") as fh:
                                st.markdown(fh.read())
                        except Exception:
                            st.write(f"Could not read {rf}")

            # Everything else grouped by directory
            code_preview_exts = {'.py', '.js', '.ts', '.html', '.css', '.json', '.md', '.yaml', '.yml', '.toml', '.sh', '.sql', '.txt', '.gitignore'}
            grouped = {}
            for rel in all_out:
                dirname = os.path.dirname(rel) or "."
                grouped.setdefault(dirname, []).append(rel)

            # "Download All" button — create a zip in memory
            import io
            import zipfile
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(project_root):
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                    for f in files:
                        if f.startswith('.'):
                            continue
                        fpath = os.path.join(root, f)
                        rel = os.path.relpath(fpath, project_root)
                        zf.write(fpath, rel)
            zip_buf.seek(0)

            col_zip, _ = st.columns([1, 3])
            with col_zip:
                st.download_button(
                    "📦 Download All as ZIP",
                    data=zip_buf,
                    file_name=f"{os.path.basename(project_root)}.zip",
                    mime="application/zip",
                    use_container_width=True
                )

            st.markdown("---")
            for dirname in sorted(grouped.keys()):
                label = "📁 Root" if dirname == "." else f"📁 {dirname}/"
                with st.expander(label, expanded=(dirname == ".")):
                    for rel in sorted(grouped[dirname]):
                        fpath = os.path.join(project_root, rel)
                        ext = os.path.splitext(rel)[1].lower()
                        col_a, col_b = st.columns([4, 1])
                        with col_a:
                            if ext in code_preview_exts:
                                try:
                                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                                        st.code(fh.read(), language="python" if ext == ".py" else None)
                                except Exception:
                                    st.write(f"📄 {rel}")
                            else:
                                st.write(f"📄 {rel}")
                        with col_b:
                            mime_type, _ = mimetypes.guess_type(fpath)
                            with open(fpath, "rb") as fh:
                                st.download_button("💾", data=fh, file_name=os.path.basename(rel), mime=mime_type or "application/octet-stream", key=f"dl4_{rel}", use_container_width=True)