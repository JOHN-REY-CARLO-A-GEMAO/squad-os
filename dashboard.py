import streamlit as st
import sqlite3
import pandas as pd
import os
import json
import mimetypes
import asyncio
import tempfile
import pathlib
import urllib.request
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from squad_os.database.session import save_persona, get_all_personas, delete_persona


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

def ensure_personas_table():
    for path in DB_PATHS:
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(path)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_personas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT UNIQUE NOT NULL,
                        goal TEXT NOT NULL,
                        backstory TEXT NOT NULL,
                        tools TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                conn.close()
            except Exception:
                pass

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



def submit_followup(mission_id: int, message: str):
    """Send a follow-up message to an existing mission. Queues it for the worker."""
    for path in DB_PATHS:
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                # Get current conversation history
                cursor.execute("SELECT conversation_history FROM missions WHERE id = ?", (mission_id,))
                row = cursor.fetchone()
                history = json.loads(row[0] or "[]") if row else []
                history.append({
                    "role": "user",
                    "content": message,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
                # Set status to FOLLOWUP so the worker picks it up
                cursor.execute(
                    "UPDATE missions SET conversation_history = ?, status = 'FOLLOWUP' WHERE id = ?",
                    (json.dumps(history), mission_id)
                )
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                st.error(f"Failed to submit follow-up: {e}")
                return False
    return False

# Optimization: Cache global stats to reduce DB load during 5s auto-refreshes.
# Reduces database aggregation overhead from O(N) every 5s to once per minute.
@st.cache_data(ttl=60)
def load_global_stats():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(prompt_tokens), SUM(completion_tokens), SUM(cost_usd) FROM tasks")
            stats = cursor.fetchone()
            conn.close()
            # Explicitly return standard Python types (tuple) to ensure @st.cache_data serialization works.
            return (stats[0] or 0, stats[1] or 0, stats[2] or 0.0) if stats else (0, 0, 0.0)
        except Exception:
            pass
    return (0, 0, 0.0)

REGISTRY_URL = "https://raw.githubusercontent.com/JOHN-REY-CARLO-A-GEMAO/squad-os/main/packages.json"


@st.cache_data(ttl=3600)
def fetch_registry_packages() -> list:
    """Read validated package registry — local packages.json primary, remote fallback."""
    try:
        with open("packages.json", encoding="utf-8") as f:
            return json.load(f).get("packages", [])
    except Exception:
        pass
    try:
        req = urllib.request.Request(REGISTRY_URL, headers={"User-Agent": "SquadOS-Dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8")).get("packages", [])
    except Exception as e:
        print(f"[Dashboard] Registry fetch failed: {e}")
        return []


def load_store_catalog():
    """Query store_packages joined with install status, merged with remote registry entries."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.version, p.author, p.description, p.tags,
                   p.install_count, p.source_url,
                   COALESCE(i.status, 'NOT_INSTALLED') as install_status,
                   i.version as installed_version
            FROM store_packages p
            LEFT JOIN installed_packages i ON p.id = i.package_id AND i.status = 'ACTIVE'
            ORDER BY p.install_count DESC, p.name ASC
        """)
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        local_packages = {r["id"]: dict(zip(cols, r)) for r in rows}

        # Merge community registry packages
        remote_packages = fetch_registry_packages()
        for rp in remote_packages:
            pid = rp["id"]
            if pid not in local_packages:
                local_packages[pid] = {
                    "id": pid,
                    "name": rp.get("name", pid),
                    "version": "0.0.0",
                    "author": "",
                    "description": rp.get("description", ""),
                    "tags": "[]",
                    "install_count": 0,
                    "source_url": rp.get("source_url", ""),
                    "install_status": "REMOTE",
                    "installed_version": None,
                }

        result = sorted(local_packages.values(), key=lambda x: (-x["install_count"], x["name"]))
        conn.close()
        return result
    except Exception:
        return []

def install_remote_package(pkg):
    """Download a .sqad from a remote URL and install it."""
    import urllib.request
    import tempfile

    url = pkg.get("source_url", "")
    if not url:
        st.error(f"No source URL for '{pkg['id']}'")
        return

    try:
        os.makedirs("workspace/packages/uploads", exist_ok=True)
        dest = os.path.join("workspace", "packages", "uploads", f"{pkg['id']}.sqad")
        with st.spinner(f"Downloading {pkg['name']}..."):
            urllib.request.urlretrieve(url, dest)
        pkg_obj = AgentPackageLoader.load_sqad(dest)
        if pkg_obj:
            asyncio.run(AgentPackageLoader.install_package(pkg_obj))
            st.success(f"✅ {pkg['name']} installed from registry!")
        else:
            st.error("Failed to validate package.")
    except Exception as e:
        st.error(f"Failed to install from registry: {e}")


def install_registry_package(pkg: dict) -> bool:
    """Download remote squad.yaml, compile to .sqad, and install into SQLite."""
    repo_url = pkg["source_url"].rstrip("/")
    raw_base = repo_url.replace("github.com", "raw.githubusercontent.com")
    manifest_path = pkg.get("manifest_path", "main/squad.yaml").lstrip("/")
    manifest_url = f"{raw_base}/{manifest_path}"

    try:
        req = urllib.request.Request(manifest_url, headers={"User-Agent": "SquadOS-Dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            yaml_content = resp.read()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_yaml = pathlib.Path(tmpdir) / "squad.yaml"
            temp_yaml.write_bytes(yaml_content)

            sqad_path = AgentPackageLoader.build_sqad_from_yaml(str(temp_yaml))

            pkg_obj = AgentPackageLoader.load_sqad(sqad_path)
            if not pkg_obj:
                st.error("Validation failed: downloaded manifest contains layout errors.")
                return False

            asyncio.run(AgentPackageLoader.install_package(pkg_obj))
            return True

    except Exception as e:
        st.error(f"Installation pipeline error: {e}")
        return False


def deploy_store_workflow(package_id: str, custom_goal: str = ""):
    """Queue a mission from a stored workflow."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT workflow FROM store_workflows WHERE package_id = ?", (package_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        workflow_str = row[0]
        workflow = json.loads(workflow_str)
        goal = custom_goal or workflow.get("description") or f"Workflow: {package_id}"
        cursor.execute(
            "INSERT INTO missions (goal, status, workflow_json) VALUES (?, 'QUEUED', ?)",
            (goal, workflow_str)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def list_installed_packages():
    """List active installed packages with their workflow info."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.package_id, i.version, i.install_path, i.installed_at,
                   p.name, p.description, w.workflow
            FROM installed_packages i
            JOIN store_packages p ON i.package_id = p.id
            LEFT JOIN store_workflows w ON w.package_id = i.package_id
            WHERE i.status = 'ACTIVE'
            ORDER BY i.installed_at DESC
        """)
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []

def list_toolbox_packages():
    """List .sqad files in the packages directory (for sideloading display)."""
    packages_dir = os.path.join(WORKSPACE_DIR, "packages")
    if not os.path.isdir(packages_dir):
        return []
    return sorted([
        d for d in os.listdir(packages_dir)
        if os.path.isdir(os.path.join(packages_dir, d))
    ], reverse=True)

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

def format_project_label(project_id):
    """Transforms a project ID like '20241027_123456_my_project' into '12:34:56 - My Project'."""
    parts = project_id.split("_")
    if len(parts) >= 3 and len(parts[0]) == 8 and len(parts[1]) == 6:
        # It follows the 20240101_120000_slug pattern
        time_part = parts[1]
        formatted_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
        slug_part = " ".join(parts[2:]).title()
        return f"{formatted_time} - {slug_part}"
    return project_id.replace("_", " ").title()

def format_log_timestamp(ts_str):
    """Converts ISO timestamp strings to HH:MM:SS format for cleaner logs."""
    if not ts_str:
        return ""
    try:
        # Handle cases with 'Z' or other ISO variations
        dt = datetime.fromisoformat(str(ts_str).replace('Z', '+00:00'))
        return dt.strftime('%H:%M:%S')
    except Exception:
        return str(ts_str)
# --- UI ---

st.title("🛡️ SquadOS: Project Command Center")

if st.session_state.get("mission_submitted"):
    st.toast("✅ Mission dispatched successfully!")
    st.session_state.mission_submitted = False

if st.session_state.get("persona_deleted"):
    st.toast("🗑️ Persona deleted successfully!")
    st.session_state.persona_deleted = False

if st.session_state.get("persona_created"):
    st.toast("💾 Persona saved successfully!")
    st.session_state.persona_created = False

if st.session_state.get("package_uninstalled"):
    st.toast("📦 Package uninstalled successfully!")
    st.session_state.package_uninstalled = False

if st.session_state.get("workflow_deployed"):
    st.toast("🚀 Workflow deployed successfully!")
    st.session_state.workflow_deployed = False

# Session state for mission chat sessions
if "selected_session_id" not in st.session_state:
    st.session_state.selected_session_id = None

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
        proj_status = get_project_status(proj, True)
        icon = "🟢" if proj_status == "Exploring" else "👀"
        if proj == st.session_state.selected_proj: icon = "📍"

        readable_name = format_project_label(proj)
        label = f"{icon} {readable_name}"

        if st.button(label, key=f"btn_act_{proj}", use_container_width=True, help=f"Open active project ({proj_status}): {proj}"):
            st.session_state.selected_proj = proj
            st.session_state.is_active = True
            st.rerun()

    st.write("**Archived Projects**")
    if not archived_projects:
        st.write("No archived projects.")
    for proj in archived_projects:
        icon = "📍" if proj == st.session_state.selected_proj else "📦"
        readable_name = format_project_label(proj)
        label = f"{icon} {readable_name}"
        if st.button(label, key=f"btn_arc_{proj}", use_container_width=True, help=f"Open archived project: {proj}"):
            st.session_state.selected_proj = proj
            st.session_state.is_active = False
            st.rerun()

    if st.button("Reset View (Go to Chat)", use_container_width=True, shortcut="Esc", help="Return to the main chat interface"):
        st.session_state.selected_proj = None
        st.rerun()

    # Global Stats
    stats = load_global_stats()
    st.markdown("---")
    st.subheader("📊 Global Performance")
    col_s1, col_s2 = st.columns(2)
    col_s1.metric(
        "Total Cost",
        f"${stats[2] if stats[2] else 0.0:.4f}",
        help="The aggregate USD cost of all LLM requests across all missions."
    )
    col_s2.metric(
        "Total Tokens",
        f"{ (stats[0] or 0) + (stats[1] or 0) :,}",
        help="The combined count of prompt and completion tokens processed."
    )

selected_project = st.session_state.selected_proj
is_selected_active = st.session_state.is_active

if not selected_project:
    st.info("👋 Welcome to SquadOS. Dispatch a new mission below, or click a project on the left to view details.")

    main_tab1, main_tab2, main_tab3 = st.tabs(["💬 Mission Control", "🏗️ Agent Factory", "💾 Agent Store"])

    @st.fragment
    def _render_chat():
        missions_df = load_missions()
        selected_id = st.session_state.selected_session_id

        # --- Session Selector ---
        if not missions_df.empty:
            mission_options = []
            mission_labels = {}
            for _, row in missions_df.iterrows():
                mid = row["id"]
                status = row.get("status", "UNKNOWN")
                goal_short = (str(row.get("goal", ""))[:28] + "..") if len(str(row.get("goal", ""))) > 30 else str(row.get("goal", ""))
                icons = {"QUEUED": "⏳", "IN_PROGRESS": "⚡", "COMPLETED": "✅", "FAILED": "❌", "FOLLOWUP": "💬"}
                icon = icons.get(status, "❓")
                label = f"{icon} #{mid} {goal_short}"
                mission_options.append(mid)
                mission_labels[mid] = label

            selected_pill = st.pills(
                "Select Mission Session",
                options=mission_options,
                format_func=lambda x: mission_labels.get(x),
                selection_mode="single",
                label_visibility="collapsed",
                default=st.session_state.selected_session_id
            )

            if selected_pill != st.session_state.selected_session_id:
                st.session_state.selected_session_id = selected_pill
                st.rerun()
        else:
            st.info("No missions yet. Send a message below to start!")

        st.divider()

        # --- Chat Area ---
        chat_container = st.container(height=480)

        with chat_container:
            if selected_id is not None:
                mission_row = missions_df[missions_df["id"] == selected_id]
                if mission_row.empty:
                    st.write("Mission not found.")
                else:
                    row = mission_row.iloc[0]
                    prompt_text = str(row.get("goal", ""))
                    status = row.get("status", "UNKNOWN").upper()

                    with st.chat_message("user"):
                        st.write(prompt_text)
                        uploaded_files_json = row.get("uploaded_files")
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

                    with st.chat_message("assistant", avatar="🤖"):
                        if status == "QUEUED":
                            st.info("⏳ Queued and waiting for the SquadOS worker to pick this up...")
                        elif status == "IN_PROGRESS":
                            st.warning("⚡ The team is currently executing this mission in the background.")
                        elif status == "COMPLETED":
                            st.success("✅ Mission accomplished! Check the Branch Explorer for results.")
                        elif status == "FAILED":
                            st.error("❌ Mission failed. You can send a follow-up below to retry with adjustments.")
                        elif status == "FOLLOWUP":
                            st.warning("💬 Follow-up queued — worker will process it shortly.")
                        else:
                            st.write(f"Status: {status}")

                    conv_history = json.loads(row.get("conversation_history") or "[]")
                    for msg in conv_history:
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        if role == "user":
                            with st.chat_message("user"):
                                st.write(content)
                        elif role == "system":
                            with st.chat_message("assistant", avatar="⚙️"):
                                st.caption(content)
                        elif role == "assistant":
                            with st.chat_message("assistant", avatar="🤖"):
                                st.write(content)
            else:
                if not missions_df.empty:
                    for _, row in missions_df.iterrows():
                        prompt_text = str(row.get("goal", ""))
                        status = row.get("status", "UNKNOWN").upper()

                        with st.chat_message("user"):
                            st.write(prompt_text)
                            uploaded_files_json = row.get("uploaded_files")
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

                        with st.chat_message("assistant", avatar="🤖"):
                            if status == "QUEUED":
                                st.info("⏳ Queued and waiting...")
                            elif status == "IN_PROGRESS":
                                st.warning("⚡ Executing...")
                            elif status == "COMPLETED":
                                st.success("✅ Done.")
                            elif status == "FAILED":
                                st.error("❌ Failed.")
                            elif status == "FOLLOWUP":
                                st.info("💬 Follow-up queued.")
                            else:
                                st.write(f"Status: {status}")
                else:
                    st.write("No missions found. Send a message below to start!")

        # --- Input Area ---
        with st.container():
            if "upload_key" not in st.session_state:
                st.session_state.upload_key = 0

            uploaded_files = st.file_uploader("📎 Attach documents, images, videos, etc.", accept_multiple_files=True, label_visibility="collapsed", help="Total upload limit: 500MB (200MB per file)", key=f"mission_file_uploader_{st.session_state.upload_key}")

            if selected_id is not None:
                mission_row = missions_df[missions_df["id"] == selected_id]
                is_active = False
                if not mission_row.empty:
                    s = mission_row.iloc[0].get("status", "").upper()
                    is_active = s in ("IN_PROGRESS", "QUEUED", "FOLLOWUP")

                if is_active:
                    st.info(f"⏳ Mission #{selected_id} is in progress. Wait for it to complete before sending a follow-up.")
                else:
                    if prompt := st.chat_input(f"Follow-up for Mission #{selected_id}... (e.g., 'Retry with a different approach')"):
                        submit_followup(selected_id, prompt)
                        st.session_state.mission_submitted = True
                        st.session_state.upload_key += 1
                        st.rerun()
            else:
                if prompt := st.chat_input("Ask SquadOS to do something... (e.g., 'Analyze this document for me')"):
                    files_json = save_uploaded_files(uploaded_files)
                    if files_json != "ERROR_SIZE":
                        submit_new_mission(prompt, files_json)
                        st.session_state.mission_submitted = True
                        st.session_state.upload_key += 1
                        st.rerun()
    with main_tab1:
        _render_chat()

    with main_tab2:
        st.subheader("🏗️ Agent Factory")
        st.caption("Design and deploy specialized agent personas for your squad.")

        col_a, col_b = st.columns([1, 2])

        with col_a:
            st.write("**Active Personas**")
            ensure_personas_table()
            personas = asyncio.run(get_all_personas())
            if not personas:
                st.info("No custom personas defined.")
            else:
                for p in personas:
                    with st.expander(f"👤 {p['role']}"):
                        st.write(f"**Goal:** {p['goal']}")
                        st.write(f"**Tools:** {', '.join(json.loads(p['tools']))}")
                        with st.popover("🗑️ Delete", use_container_width=True, help=f"Delete the '{p['role']}' persona"):
                            st.warning("Are you sure? This cannot be undone.")
                            if st.button(f"Confirm Delete", key=f"conf_del_{p['role']}", type="primary", use_container_width=True):
                                asyncio.run(delete_persona(p['role']))
                                st.session_state.persona_deleted = True
                                st.rerun()

        with col_b:
            st.write("**Assemble New Agent**")
            with st.form("new_agent_form"):
                new_role = st.text_input("Role Name", placeholder="e.g. Senior Security Auditor")
                new_goal = st.text_area("Primary Goal", placeholder="Identify vulnerabilities in the provided codebase.")
                new_backstory = st.text_area("Backstory", placeholder="An elite white-hat hacker with 20 years of experience...")

                all_tools = [
                    "web_search", "write_file", "read_file", "terminal", "python_runner",
                    "dashboard_approval", "memory_search", "set_shared_value", "get_shared_value",
                    "delegate_task", "desktop_control", "ui_inspector", "commit_project",
                    "browser_control", "vision_analysis", "video_processing", "telegram_send",
                    "telegram_receive", "discord_send", "discord_receive", "email_send",
                    "email_receive", "marketplace_search", "install_skill", "get_tool_info",
                    "schedule_mission", "list_schedules", "cancel_schedule", "self_heal",
                    "health_check", "rich_approval", "notify_human", "hitl_interrupt"
                ]
                selected_tools = st.multiselect("Assign Tools", all_tools)
                
                submit_agent = st.form_submit_button("💾 Save Persona", help="Register this new agent persona to the database")
                if submit_agent:
                    if new_role and new_goal and new_backstory:
                        asyncio.run(save_persona(new_role, new_goal, new_backstory, selected_tools))
                        st.session_state.persona_created = True
                        st.rerun()
                    else:
                        st.error("Please fill in all fields.")

    with main_tab3:
        from squad_os.store.loader import AgentPackageLoader
        st.subheader("💾 Agent Store")
        st.caption("Browse, install, and run .sqad workflow packages.")

        store_tab1, store_tab2, store_tab3 = st.tabs(["📦 Browse", "✅ Installed", "📤 Upload .sqad"])

        with store_tab1:
            catalog = load_store_catalog()

            # ── Local / installed packages ──────────────────────
            if catalog:
                col_search, _ = st.columns([2, 1])
                with col_search:
                    search_term = st.text_input("🔍 Search packages", placeholder="name or tag...", label_visibility="collapsed")
                for pkg in catalog:
                    if search_term:
                        q = search_term.lower()
                        if q not in pkg["name"].lower() and q not in (pkg.get("description") or "").lower():
                            continue
                    tags = json.loads(pkg["tags"]) if pkg["tags"] else []
                    tag_str = ", ".join(tags[:4]) if tags else ""
                    is_installed = pkg["install_status"] == "ACTIVE"
                    with st.container():
                        cols = st.columns([3, 1, 1])
                        with cols[0]:
                            st.write(f"**{pkg['name']}** v{pkg['version']}")
                            st.caption(f"by {pkg['author'] or 'unknown'} · {pkg['install_count'] or 0} installs")
                            if tag_str:
                                st.caption(f"🏷️ {tag_str}")
                            if pkg.get("description"):
                                st.write(pkg["description"])
                        with cols[1]:
                            install_status = pkg.get("install_status", "NOT_INSTALLED")
                            if install_status == "ACTIVE":
                                st.success("✅ Installed")
                            elif install_status == "REMOTE":
                                if st.button(f"⬇️ Get from Registry", key=f"remote_{pkg['id']}", use_container_width=True):
                                    install_remote_package(pkg)
                                    st.rerun()
                            else:
                                sqad_path = pkg.get("source_url", "")
                                if sqad_path and sqad_path.startswith("http"):
                                    st.caption("📡 Remote")
                                elif sqad_path and os.path.exists(sqad_path):
                                    if st.button(f"⬇️ Install", key=f"install_{pkg['id']}", use_container_width=True):
                                        asyncio.run(AgentPackageLoader.install_package(
                                            AgentPackageLoader.load_sqad(sqad_path)
                                        ))
                                        st.rerun()
                                else:
                                    st.caption("No source")
                        with cols[2]:
                            if is_installed:
                                with st.popover("🗑️", use_container_width=True, help=f"Uninstall {pkg['name']}"):
                                    st.warning(f"Uninstall {pkg['name']}?")
                                    if st.button("Confirm", key=f"conf_un_{pkg['id']}", type="primary", use_container_width=True):
                                        asyncio.run(AgentPackageLoader.uninstall_package(pkg["id"]))
                                        st.session_state.package_uninstalled = True
                                        st.rerun()
                        st.divider()
            else:
                st.info("No local packages found. Upload a .sqad package or explore the community registry below.")

            # ── Community registry cards ─────────────────────────
            registry_pkgs = fetch_registry_packages()
            if registry_pkgs:
                st.markdown("---")
                st.subheader("🌐 Community Registry")
                st.caption("Validated by CI — contribute yours via a PR to packages.json")

                for i in range(0, len(registry_pkgs), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j < len(registry_pkgs):
                            pkg = registry_pkgs[i + j]
                            with cols[j].container(border=True):
                                st.markdown(f"**{pkg['name']}**")
                                if pkg.get("source_url"):
                                    st.caption(f"🔗 [Source]({pkg['source_url']})")
                                if pkg.get("description"):
                                    st.write(pkg["description"])
                                if st.button(
                                    "⬇️ Install Workflow",
                                    key=f"ci_install_{i+j}",
                                    use_container_width=True,
                                ):
                                    with st.spinner(f"Ingesting {pkg['name']}..."):
                                        ok = install_registry_package(pkg)
                                        if ok:
                                            st.toast(f"✅ {pkg['name']} installed!")
                                            st.rerun()
            elif not catalog:
                st.info("No community packages found. Be the first to submit one!")

        with store_tab2:
            installed = list_installed_packages()
            if not installed:
                st.info("No packages installed yet. Browse or upload one above.")
            for ip in installed:
                with st.expander(f"📦 **{ip['name']}** v{ip['version']}", expanded=True):
                    st.write(f"**Description:** {ip.get('description', 'N/A')}")
                    st.caption(f"Path: `{ip['install_path']}` · Installed: {ip['installed_at']}")
                    if ip.get("workflow"):
                        wf = json.loads(ip["workflow"])
                        wf_name = wf.get("name", "Default workflow")
                        st.write(f"**Workflow:** {wf_name}")
                        st.code(json.dumps(wf, indent=2), language="json", line_numbers=True)
                        if st.button(f"🚀 Deploy '{wf_name}' as Mission", key=f"deploy_{ip['package_id']}", use_container_width=True, help=f"Execute the {wf_name} workflow as a new mission"):
                            success = deploy_store_workflow(ip["package_id"])
                            if success:
                                st.session_state.workflow_deployed = True
                                st.rerun()
                            else:
                                st.error("Failed to deploy workflow.")
                    else:
                        st.write("No workflow in this package (tools-only package).")

        with store_tab3:
            st.write("Upload a `.sqad` package file to sideload it into the Agent Store.")
            uploaded_sqad = st.file_uploader("Choose a .sqad file", type=["sqad"], label_visibility="collapsed")
            if uploaded_sqad:
                save_dir = os.path.join(WORKSPACE_DIR, "packages", "uploads")
                os.makedirs(save_dir, exist_ok=True)
                dest_path = os.path.join(save_dir, uploaded_sqad.name)
                with open(dest_path, "wb") as f:
                    f.write(uploaded_sqad.getbuffer())
                st.success(f"Saved to `{dest_path}`")

                pkg = AgentPackageLoader.load_sqad(dest_path)
                if pkg:
                    st.write(f"**Package:** {pkg.name} v{pkg.version}")
                    st.write(f"**Author:** {pkg.manifest.get('author', 'unknown')}")
                    st.write(f"**Workflow:** {'Yes' if pkg.workflow else 'No'}")
                    st.write(f"**Custom tools:** {len(pkg.custom_tools)}")
                    st.write(f"**Custom agents:** {len(pkg.custom_agents)}")
                    st.write(f"**Dependencies:** {len(pkg.dependencies)}")

                    validation = AgentPackageLoader.validate_package(pkg)
                    if validation:
                        st.success("Package validation passed.")
                    else:
                        for e in validation.errors:
                            st.error(f"❌ {e}")
                    for w in validation.warnings:
                        st.warning(f"⚠️ {w}")

                    if st.button("💾 Install this package", use_container_width=True, type="primary"):
                        success = asyncio.run(AgentPackageLoader.install_package(pkg))
                        if success:
                            st.success(f"Package '{pkg.name}' installed!")
                            st.rerun()
                        else:
                            st.error("Installation failed.")
                else:
                    st.error("Failed to parse .sqad package. Check that it contains a valid manifest.json.")

else:
    # --- INDIVIDUAL PROJECT VIEW ---
    status = get_project_status(selected_project, is_selected_active)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        readable_project_name = format_project_label(selected_project)
        st.header(f"Project: `{readable_project_name}`")
        st.caption(f"ID: {selected_project}")
    with col2:
        if st.button("🔙 Back to Chat", use_container_width=True, help="Return to the main chat interface"):
            st.session_state.selected_proj = None
            st.rerun()

    st.markdown(f"**Current Status:** {status}")

    project_root = os.path.join(PROJECTS_DIR if is_selected_active else ARCHIVES_DIR, selected_project)

    tab1, tab2, tab3, tab4 = st.tabs(["🛠️ Live Workspace", "📜 Live Logs", "🧠 Memory", "✅ Commit Review"])

    with tab1:
        st.subheader("🛠️ Live Coder Workspace")
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
            view_filter = st.segmented_control(
                "Filter Files",
                options=["All", "Code", "Images", "Documents"],
                default="All",
                label_visibility="collapsed"
            )

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

                        # Get file stats for "Live Coder" feel
                        stats = os.stat(fpath)
                        mtime = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        size_kb = stats.st_size / 1024

                        col_a, col_b = st.columns([4, 1])
                        with col_a:
                            st.caption(f"Last modified: {mtime} | Size: {size_kb:.1f} KB")
                            if ext in img_exts:
                                try:
                                    st.image(fpath, use_container_width=True)
                                except Exception:
                                    st.write(f"🖼️ {rel}")
                            elif ext in code_exts:
                                try:
                                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                                        st.code(fh.read(), language=ext.lstrip('.'), line_numbers=True)
                                except Exception:
                                    st.write(f"📄 {rel}")
                            else:
                                st.write(f"📄 {rel}")
                        with col_b:
                            mime_type, _ = mimetypes.guess_type(fpath)
                            with open(fpath, "rb") as fh:
                                st.download_button("💾", data=fh, file_name=os.path.basename(rel), mime=mime_type or "application/octet-stream", key=f"dl1_{rel}", use_container_width=True, help="Download file")

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
                                st.download_button("💾 Download", data=fh, file_name=v_file, mime=mime_type or "application/octet-stream", key=f"dl_vis_{v_file}", use_container_width=True, help=f"Download visual artifact: {v_file}")
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
                ts_display = format_log_timestamp(entry.get('timestamp'))
                with st.expander(f"🛠️ {entry.get('tool')} @ {ts_display}", expanded=(entry == logs[-1])):
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
                    use_container_width=True,
                    help="Download all committed project files as a ZIP archive"
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
                                st.download_button("💾", data=fh, file_name=os.path.basename(rel), mime=mime_type or "application/octet-stream", key=f"dl4_{rel}", use_container_width=True, help="Download file")