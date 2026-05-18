import streamlit as st
import sqlite3
import pandas as pd
import os
import json
import mimetypes
from datetime import datetime

from squad_os.core.guardrails import screen_input, SafetyLevel

# Configuration
DB_PATHS = ["shared_memory.db", "instance/shared_memory.db"]
WORKSPACE_DIR = "workspace"
PROJECTS_DIR = os.path.join(WORKSPACE_DIR, "projects")
ARCHIVES_DIR = os.path.join(WORKSPACE_DIR, "archives")

st.set_page_config(page_title="SquadOS: Project Command Center", layout="wide", page_icon="🛡️")

# Ensure workspace directories exist
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(ARCHIVES_DIR, exist_ok=True)

# --- Session State ---
if "selected_proj" not in st.session_state:
    st.session_state.selected_proj = None
if "is_active" not in st.session_state:
    st.session_state.is_active = True
if "submit_status" not in st.session_state:
    st.session_state.submit_status = None


# --- Database Helpers ---

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


# --- Interrupt Helpers (single definitions, no duplicates) ---

def _resolve_interrupt(interrupt_id: int, user_guidance: str, mission_status: str = "QUEUED") -> bool:
    """Centralized interrupt resolution. All interrupt types funnel through here."""
    path = get_active_db_path()
    if not path:
        return False
    conn = sqlite3.connect(path, timeout=10)
    try:
        conn.execute("PRAGMA busy_timeout=10000;")
        conn.execute(
            "UPDATE mission_interrupts SET user_guidance = ?, status = 'RESOLVED' WHERE id = ?",
            (user_guidance, interrupt_id),
        )
        conn.execute(
            "UPDATE missions SET status = ? WHERE id = ("
            "  SELECT mission_id FROM mission_interrupts WHERE id = ?"
            ")",
            (mission_status, interrupt_id),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Failed to resolve interrupt: {e}")
        conn.close()
        return False


def resume_interrupt(interrupt_id: int, user_guidance: str) -> bool:
    return _resolve_interrupt(interrupt_id, user_guidance)


def approve_tool_interrupt(interrupt_id: int, user_guidance: str) -> bool:
    return _resolve_interrupt(interrupt_id, user_guidance or "Approved")


def reject_tool_interrupt(interrupt_id: int, rejection_reason: str) -> bool:
    guidance = f"REJECTED: {rejection_reason}. Do not use this tool. Try an alternative approach."
    return _resolve_interrupt(interrupt_id, guidance)


def load_pending_interrupts():
    """Fetch all PENDING interrupts with mission goal."""
    path = get_active_db_path()
    if not path:
        return []
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            "SELECT mi.*, m.goal FROM mission_interrupts mi "
            "JOIN missions m ON mi.mission_id = m.id "
            "WHERE mi.status = 'PENDING' ORDER BY mi.id DESC"
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        conn.close()
        return []


# --- Mission Submission ---

def save_uploaded_files(uploaded_files):
    if not uploaded_files:
        return None

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

    temp_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    upload_dir = os.path.join(WORKSPACE_DIR, "uploads", f"pending_{temp_id}")
    os.makedirs(upload_dir, exist_ok=True)

    files_metadata = []
    for f in uploaded_files:
        filename = os.path.basename(f.name)
        name, ext = os.path.splitext(filename)
        target_path = os.path.join(upload_dir, filename)
        if os.path.exists(target_path):
            filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            target_path = os.path.join(upload_dir, filename)

        with open(target_path, "wb") as out:
            out.write(f.getbuffer())

        files_metadata.append({
            "name": filename,
            "type": f.type,
            "size_bytes": f.size,
            "temp_path": os.path.abspath(target_path),
        })

    return json.dumps(files_metadata)


def submit_new_mission(prompt, uploaded_files_json=None, max_tokens=0, max_turns=0, max_cost_usd=0.0):
    """Submit a new mission with safety screening.

    Returns:
        tuple: (success: bool, message: str)
    """
    safety = screen_input(prompt)
    if safety.is_blocked:
        reasons = "; ".join(v.description for v in safety.violations)
        return False, f"Mission blocked: {reasons}"

    for path in DB_PATHS:
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(missions)")
                columns = [c[1] for c in cursor.fetchall()]

                if "goal" in columns:
                    has_budget = all(c in columns for c in ("max_tokens", "max_turns", "max_cost_usd"))
                    if has_budget:
                        cursor.execute(
                            "INSERT INTO missions (goal, status, uploaded_files, max_tokens, max_turns, max_cost_usd) VALUES (?, ?, ?, ?, ?, ?)",
                            (prompt, "QUEUED", uploaded_files_json, max_tokens, max_turns, max_cost_usd),
                        )
                    elif "uploaded_files" in columns:
                        cursor.execute(
                            "INSERT INTO missions (goal, status, uploaded_files) VALUES (?, ?, ?)",
                            (prompt, "QUEUED", uploaded_files_json),
                        )
                    else:
                        cursor.execute("INSERT INTO missions (goal, status) VALUES (?, ?)", (prompt, "QUEUED"))
                elif "name" in columns and "description" in columns:
                    task_name = f"ChatTask_{datetime.now().strftime('%H%M%S')}"
                    cursor.execute(
                        "INSERT INTO missions (name, description, status) VALUES (?, ?, ?)",
                        (task_name, prompt, "QUEUED"),
                    )

                conn.commit()
                conn.close()
                if safety.level == SafetyLevel.SUSPICIOUS:
                    reasons = "; ".join(v.description for v in safety.violations)
                    return True, f"Mission queued (flagged: {reasons})"
                return True, "Mission queued"
            except Exception as e:
                return False, f"Failed to push to {path}: {e}"
    return False, "No database found"


# --- Fragment-based HITL Queue (avoids full script reruns) ---

@st.fragment(run_every=5000)
def render_hitl_queue():
    """Render the HITL queue as an isolated fragment that polls independently."""
    interrupts = load_pending_interrupts()
    if not interrupts:
        st.success("No pending interrupts. All agents are running autonomously.")
        return

    for interrupt in interrupts:
        goal = interrupt.get("goal", "Unknown mission")
        task_idx = interrupt.get("task_idx", "?")
        reason = interrupt.get("error_message", interrupt.get("interrupt_reason", "No reason provided"))
        interrupt_id = interrupt["id"]
        context_json = interrupt.get("context", "")

        is_tool_approval = "Tool approval required" in (interrupt.get("interrupt_reason", "") or "")
        is_budget_exhausted = "Budget Exhausted" in (interrupt.get("interrupt_reason", "") or "")

        if is_tool_approval:
            st.markdown("### 🔒 Tool Approval Request")
        elif is_budget_exhausted:
            st.markdown("### 💰 Budget Exhausted")
        else:
            st.markdown("### ⏸️ HITL Guidance Request")

        with st.expander(f"Mission #{interrupt['mission_id']}: {goal[:80]}... (Task {task_idx})", expanded=True):
            st.markdown(f"**Mission:** {goal}")
            st.markdown(f"**Paused at task:** {task_idx}")
            st.markdown(f"**Reason:** {reason}")

            if context_json:
                try:
                    snapshot = json.loads(context_json)
                    st.markdown(f"**Agent role:** {snapshot.get('agent_role', 'N/A')}")
                    st.markdown(f"**Current task:** {snapshot.get('current_task_description', 'N/A')}")
                    st.markdown(f"**Tokens used:** {snapshot.get('prompt_tokens', 0)} prompt / {snapshot.get('completion_tokens', 0)} completion")
                    if snapshot.get("quality_failure_count", 0) > 0:
                        st.warning(f"Quality failures: {snapshot['quality_failure_count']}")
                    if is_tool_approval and snapshot.get("error_message"):
                        st.markdown("**Proposed tool arguments:**")
                        st.code(snapshot["error_message"], language="json")
                    if snapshot.get("short_term_memory"):
                        with st.expander("📋 Execution context"):
                            st.code(snapshot["short_term_memory"][:2000])

                    # Budget display
                    max_tokens = snapshot.get("max_tokens", 0)
                    max_turns = snapshot.get("max_turns", 0)
                    max_cost = snapshot.get("max_cost_usd", 0.0)
                    if max_tokens > 0 or max_turns > 0 or max_cost > 0:
                        st.markdown("---")
                        st.markdown("**Budget:**")
                        total_tokens = snapshot.get("prompt_tokens", 0) + snapshot.get("completion_tokens", 0)
                        if max_tokens > 0:
                            pct = min(100, int(total_tokens / max_tokens * 100))
                            st.progress(pct / 100, text=f"Tokens: {total_tokens:,} / {max_tokens:,} ({pct}%)")
                        if max_turns > 0:
                            turns_used = snapshot.get("total_iteration_count", 0)
                            pct = min(100, int(turns_used / max_turns * 100))
                            st.progress(pct / 100, text=f"Turns: {turns_used} / {max_turns} ({pct}%)")
                        if max_cost > 0:
                            st.caption(f"Cost limit: ${max_cost:.4f}")
                except Exception:
                    st.caption("Snapshot parse error — raw context unavailable")

            if is_budget_exhausted:
                st.markdown("**Increase budget to resume:**")
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    top_up_tokens = st.number_input(
                        "Additional tokens (0 = no change)",
                        min_value=0, value=0, step=1000,
                        key=f"topup_tokens_{interrupt_id}",
                    )
                with col_t2:
                    top_up_turns = st.number_input(
                        "Additional turns (0 = no change)",
                        min_value=0, value=0, step=5,
                        key=f"topup_turns_{interrupt_id}",
                    )
                with col_t3:
                    top_up_cost = st.number_input(
                        "Additional cost USD (0 = no change)",
                        min_value=0.0, value=0.0, step=0.5,
                        key=f"topup_cost_{interrupt_id}",
                    )
                guidance_budget = st.text_area(
                    "Guidance note (optional):",
                    key=f"budget_guidance_{interrupt_id}",
                    placeholder="e.g., 'Try a more direct approach'",
                )
                if st.button("💰 Top Up & Resume", key=f"topup_{interrupt_id}"):
                    if top_up_tokens > 0 or top_up_turns > 0 or top_up_cost > 0:
                        from squad_os.database.session import top_up_mission_budget, update_interrupt_guidance
                        import asyncio
                        mission_id = interrupt["mission_id"]
                        async def do_top_up():
                            await top_up_mission_budget(
                                mission_id,
                                max_tokens=top_up_tokens if top_up_tokens > 0 else None,
                                max_turns=top_up_turns if top_up_turns > 0 else None,
                                max_cost_usd=top_up_cost if top_up_cost > 0 else None,
                            )
                            await update_interrupt_guidance(interrupt_id, guidance_budget.strip() or "Budget topped up")
                        asyncio.run(do_top_up())
                        st.success("Budget topped up. Mission queued for resume.")
                        st.rerun()
                    else:
                        st.warning("Increase at least one budget limit.")
            elif is_tool_approval:
                st.markdown("**Approve or reject this tool execution:**")
                col_approve, col_reject = st.columns(2)
                with col_approve:
                    guidance_approve = st.text_area(
                        "Approval note (optional):",
                        key=f"approve_note_{interrupt_id}",
                        placeholder="e.g., 'Proceed, but limit scope to...'",
                    )
                    if st.button("✅ Approve & Resume", key=f"approve_{interrupt_id}"):
                        if approve_tool_interrupt(interrupt_id, guidance_approve.strip() or "Approved"):
                            st.success("Tool approved. Mission queued for resume.")
                            st.rerun()
                        else:
                            st.error("Failed to approve.")
                with col_reject:
                    rejection_reason = st.text_area(
                        "Rejection reason:",
                        key=f"reject_reason_{interrupt_id}",
                        placeholder="e.g., 'Too risky, use read_file instead'",
                    )
                    if st.button("❌ Reject & Resume", key=f"reject_{interrupt_id}"):
                        if rejection_reason.strip():
                            if reject_tool_interrupt(interrupt_id, rejection_reason.strip()):
                                st.success("Tool rejected. Mission queued with feedback.")
                                st.rerun()
                            else:
                                st.error("Failed to reject.")
                        else:
                            st.warning("Please provide a rejection reason.")
            else:
                guidance = st.text_area(
                    "Your guidance:",
                    key=f"guidance_{interrupt_id}",
                    placeholder="e.g., 'Proceed with the current approach', or 'Change the search query to...'",
                )
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    if st.button("Submit & Resume", key=f"resume_{interrupt_id}"):
                        if guidance.strip():
                            if resume_interrupt(interrupt_id, guidance.strip()):
                                st.success(f"Interrupt #{interrupt_id} resolved. Mission queued for resume.")
                                st.rerun()
                            else:
                                st.error("Failed to submit guidance.")
                        else:
                            st.warning("Please enter guidance before submitting.")


# --- UI ---

st.title("🛡️ SquadOS: Project Command Center")

# Sidebar
st.sidebar.header("🕹️ Control Panel")

active_projects, archived_projects = list_projects()

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
    col_s2.metric("Total Tokens", f"{(stats[0] or 0) + (stats[1] or 0):,}")

selected_project = st.session_state.selected_proj
is_selected_active = st.session_state.is_active

if not selected_project:
    st.info("👋 Welcome to SquadOS. Dispatch a new mission below, or click a project on the left to view details.")

    main_tab, hitl_tab = st.tabs(["💬 Missions", "⏸️ HITL Queue"])

    with main_tab:
        st.subheader("Mission Control Chat")

        missions = load_missions()
        chat_container = st.container(height=500)

        with chat_container:
            if not missions.empty:
                for _, row in missions.iterrows():
                    prompt_text = row.get("goal") if pd.notna(row.get("goal")) else row.get("description", "Unknown Task")
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
                            st.error("❌ Mission failed. Please check terminal logs.")
                        elif status == "PAUSED":
                            st.warning("⏸️ Mission paused — awaiting human input in HITL Queue.")
                        else:
                            st.write(f"Status: {status}")
            else:
                st.write("No missions found. Send a message below to start!")

        with st.container():
            uploaded_files = st.file_uploader(
                "📎 Attach documents, images, videos, etc.",
                accept_multiple_files=True,
                label_visibility="collapsed",
            )

            with st.expander("⚙️ Budget Limits (optional)"):
                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    budget_tokens = st.number_input("Max tokens", min_value=0, value=0, step=5000, help="0 = unlimited")
                with col_b2:
                    budget_turns = st.number_input("Max turns", min_value=0, value=0, step=10, help="0 = unlimited")
                with col_b3:
                    budget_cost = st.number_input("Max cost (USD)", min_value=0.0, value=0.0, step=1.0, help="0 = unlimited")

            if prompt := st.chat_input("Ask SquadOS to do something... (e.g., 'Analyze this document for me')"):
                files_json = save_uploaded_files(uploaded_files)
                if files_json != "ERROR_SIZE":
                    success, message = submit_new_mission(prompt, files_json, max_tokens=budget_tokens, max_turns=budget_turns, max_cost_usd=budget_cost)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    with hitl_tab:
        st.subheader("Human-in-the-Loop Review Queue")
        st.write("Missions paused and awaiting your guidance or tool approval.")
        # Fragment-based polling — only this section reruns every 5s
        render_hitl_queue()

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
            img_exts = (".png", ".jpg", ".jpeg", ".webp")
            vid_exts = (".mp4", ".webm")

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

                        mime_type, _ = mimetypes.guess_type(v_path)
                        with open(v_path, "rb") as f:
                            st.download_button(
                                label=f"💾 Download {v_file}",
                                data=f,
                                file_name=v_file,
                                mime=mime_type or "application/octet-stream",
                                key=f"dl_{v_file}",
                                width="stretch",
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
                    st.code(json.dumps(entry.get("inputs"), indent=2), language="json")
                    st.write("**Output:**")
                    st.code(entry.get("output"))
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
            except Exception as e:
                st.error(f"Error parsing artifacts.json: {e}")
        else:
            st.write("Manifest will appear when the project is ready for commit.")
