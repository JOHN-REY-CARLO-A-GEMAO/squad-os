# Squad OS Mobile Remote Companion App: Product Design & Migration Blueprint

## 1. Product Vision: The AI Remote Controller

The mobile application for Squad OS is evolving from a dashboard-oriented replication of the desktop interface into a high-speed, simplified **Remote Companion and AI Controller**.

Rather than serving as an administrative panel with heavy metrics, complex DAG editors, and file browsers, the mobile application adopts a philosophy inspired by **Claude Mobile** and **ChatGPT Mobile**. It acts as the fastest way to interact with Squad OS when away from the computer.

```
       +--------------------------------------------+
       |             SQUAD OS ECOSYSTEM             |
       +--------------------------------------------+
                     /                      \
                    /                        \
       +--------------------+        +--------------------+
       |  Desktop Dashboard |        | Mobile Companion   |
       |  (Heavy Admin,     |        | (Chat, Quick HITL, |
       |   DAG Editors,     |        |  Real-time Alerts) |
       |   Task Explorer)   |        +--------------------+
       +--------------------+                  |
                 ^                             |
                 |                             |
                 v                             v
       +--------------------------------------------+
       |           Squad OS Backend API             |
       |     (FastAPI, WebSocket, SQLite DB)        |
       +--------------------------------------------+
```

### Core Tenets
* **Mobile-First Conversational UX:** Interaction begins and ends with conversation. The default app state is a conversational input bar ready for requests.
* **One-Handed Interactivity:** Destructive or high-consequence human-in-the-loop (HITL) actions are optimized for quick, single-thumb tapping (e.g., Approve / Reject / View Details).
* **Glanceable Status:** Heavy logs, terminal outputs, and complex DAGs are kept on desktop. Mobile surfaces only key milestones, progress bars, and critical state indicators.
* **Seamless Notification Deep-Linking:** Real-time push notifications map to direct application deep-links, minimizing friction from lock screen to system action.

---

## 2. UX Philosophy: Conversation vs. Administration

We reject "dashboard thinking" for the mobile application. The app avoids exposing raw database tables, complete session logs, or system hardware metrics. It focuses entirely on execution, feedback loops, and human-in-the-loop approvals.

| UX Dimension | Desktop/Web Dashboard (Admin Panel) | Mobile Remote Companion (Companion UX) |
| :--- | :--- | :--- |
| **Primary Interaction** | Complex form fields, tab switching, drag-and-drop workflow builders, full text editor. | Instant Chat input, simple follow-up messages, single-tap buttons. |
| **Data Granularity** | Full task streams, direct console logs, full JSON payloads, raw SQLite table queries. | Hand-curated execution milestones, progress percentages, active mission summaries. |
| **HITL Focus** | Granular inspection of code diffs, custom parameter tuning, full workspace file tree inspection. | Slack-style interactive approval cards, fast approval/rejection with optional quick-guidance templates. |
| **Visual Styling** | Multi-column layouts, heavy tabular views, Graphviz/SVG rendering of workflows. | Vertical single-column timeline, compact active cards with status indicators (⌛, ⚡, ✅, ❌, 💬). |

---

## 3. Primary Navigation & Screen Architecture

The Flutter mobile application will restructure its primary navigation from dashboard tabs to a clean, mobile-first 5-tab system.

```
+-------------------------------------------------------------+
|                                                             |
|                       SQUAD OS MOBILE                       |
|                                                             |
|  +--------+   +----------+   +--------+   +----+   +-----+  |
|  |  Chat  |   | Activity |   |  HITL  |   |Alert|   | Set |  |
|  |  [01]  |   |   [02]   |   |  [03]  |   |[04] |   | [05]|  |
|  +--------+   +----------+   +--------+   +----+   +-----+  |
|                                                             |
+-------------------------------------------------------------+
```

### 1. Chat Screen (Primary/Home)
* **The Heart of the App:** Displays the open conversation. Immediately accepts prompts such as *"Write a python script to parse logs"* or *"Check if our server is up"*.
* **Active Mission Overlay:** If a mission is running, a compact progress card floats near the top of the chat view or sits pinned as an active banner, providing instant visual feedback.
* **Multi-Session Quick Switcher:** Uses a clean horizontal pill system (`st.pills` equivalent in Flutter) to let users toggle between different active or historical mission threads without leaving the screen.

### 2. Activity Feed
* **Glanceable Timeline:** A lightweight vertical timeline detailing system milestones (e.g., "✓ Flutter App Compiled", "✓ Testing Suite Passed", "⚠ Deployment Failed").
* **Filter Controls:** Allows toggling between "All Missions", "Running", and "My Contributions".
* **No Raw Logs:** Selecting an item expands a clean summarization card. Clicking "Inspect Technical Logs" displays a modal pointing the user to their desktop workspace, keeping mobile uncluttered.

### 3. HITL (Human-In-The-Loop)
* **Approval Inbox:** A dedicated queue of pending approvals.
* **Slack-style Interactive Cards:** Each card displays:
  1. The target operation (e.g., *"Delete 483 obsolete workspace files?"*).
  2. Concise contextual prompt.
  3. Action buttons: **Approve (Green, primary)**, **Reject (Red)**, **Provide Guidance (Text Input)**.
* **Thumb-Optimized Layout:** Key action buttons are placed in the bottom-third of the screen for comfortable one-handed use.

### 4. Notifications (Alerts Hub)
* **System Event Feed:** High-priority notices (e.g., *"Mission #91 Completed"*, *"Worker Offline"*).
* **Unread Badging:** Prominent notification badges on the app icon and the navigation bar.
* **Interactive Taps:** Tapping an alert immediately opens the specific context (e.g., tapping an "Approval Required" notification brings the user directly to the relevant HITL approval card).

### 5. Settings & Toolbox
* **Profile & Identity:** Server credentials, JWT authentication tokens, server profiles (local, staging, cloud).
* **Diagnostics:** Connection status, WebSocket ping latency, and raw backend health tests.
* **Ecosystem Store (Secondary):** System/Store administration and package installation move here as a secondary sub-menu. Users can view installed packages and browse available workflows, but execution details are simplified.

---

## 4. Screen Mockups & Visual Flow

### Home & Chat Screen
```
+---------------------------------------------------+
|  [=] Squad OS                           (Profile) |
+---------------------------------------------------+
|  Good evening, Operator.                          |
|  Squad Status: ⚡ Running 2 missions               |
+---------------------------------------------------+
|  ACTIVE MISSION                                   |
|  [⚡] Mission #91: Refactor Authentication        |
|  Progress: [██████░░] 75% | Coder Agent Active    |
+---------------------------------------------------+
|                                                   |
|  🤖 Squad OS Assistant:                           |
|     Planner has successfully structured task #1.   |
|     Coder is now implementing JWT verification.   |
|                                                   |
|  💬 User:                                         |
|     Make sure we use secure environment secrets.  |
|                                                   |
|  🤖 Squad OS Assistant:                           |
|     Understood. Forwarded to Coder.               |
|                                                   |
+---------------------------------------------------+
|  [📎] Ask Squad OS to do something...        [>]  |
+---------------------------------------------------+
|   [Chat]    Activity     HITL     Alerts    Specs |
+---------------------------------------------------+
```

### HITL Decision Screen
```
+---------------------------------------------------+
|  Human-In-The-Loop Approvals                  [2] |
+---------------------------------------------------+
|  CARD 1 OF 2                                      |
|  Mission: #91 Refactor Authentication             |
|  Agent: CoderAgent                                |
|                                                   |
|  ⚠️ ACTION REQUIRED:                              |
|  "The team wants to delete 48 obsolete security  |
|   configuration files from the workspace."        |
|                                                   |
|  [ Approve Deletion (Green) ]                     |
|                                                   |
|  [ Reject / Request Adjustments (Red) ]           |
|                                                   |
|  +---------------------------------------------+  |
|  | Optional feedback (e.g. Keep config.json)   |  |
|  +---------------------------------------------+  |
+---------------------------------------------------+
|    Chat     Activity    [HITL]    Alerts    Specs |
+---------------------------------------------------+
```

---

## 5. API Evolution: Mission-Centric vs. Conversation-First

Currently, the Squad OS API operates under a **Mission-Centric Model** where clients explicitly construct workflows or dispatch concrete missions via `/missions/dispatch`.

To achieve a true "Claude Mobile" or "ChatGPT Mobile" experience, we recommend transitioning to a **Conversation-First API Model** supported by a **Hybrid Gateway**.

```
              CONVERSATION-FIRST API ARCHITECTURE

                   +------------------------+
                   |  Mobile Client (Chat)  |
                   +------------------------+
                               |
                               | POST /api/v1/chat
                               v
                   +------------------------+
                   |  Conversational Router |
                   |  (LLM Classifier /     |
                   |   Decision Layer)      |
                   +------------------------+
                              / \
                             /   \
          If simple query   /     \  If action / task-oriented
                           v       v
            +----------------+   +----------------------------+
            | Direct Answer  |   | Spawn/Modify Mission       |
            | (Fast path,    |   | (Queue Worker,             |
            |  no agent DAG) |   |  Stream Progress over WS)  |
            +----------------+   +----------------------------+
```

### Comparison Matrix

| Dimension | Mission-Centric API (Current) | Conversation-First API (Recommended) |
| :--- | :--- | :--- |
| **Primary Entry Point** | `POST /missions/dispatch` | `POST /chat` (Gateway Route) |
| **Client Responsibility** | Client must determine if a request needs a complex agent crew or is a simple request, forcing a structured mission. | Client sends raw text; the backend parses the intent and handles routing dynamically. |
| **Speed / Latency** | High overhead. Every text message creates a mission and spawns/spins up an agent workspace, taking 10s of seconds. | Ultra-low latency for direct requests (e.g., "What was the result of the last run?" -> parsed in <1s from database). |
| **User Experience** | Feels like an orchestration management panel (Airflow/Jenkins). | Feels like an interactive, intelligent companion (ChatGPT/Claude). |

### Recommendation: The Hybrid Gateway Model
We recommend introducing a conversational unified route (`POST /api/v1/chat`).
* When a message is posted, an ultra-fast LLM classifier layer (or direct heuristic/intent matcher) categorizes the request:
  * **Direct Queries (Database & Memory Checks):** Served immediately using the read-only DB paths (e.g., *"Is the landing page finished?"* or *"What is the status of mission #91?"*). Returns a clean JSON markdown response in < 1 second.
  * **Execution Requests (Complex Actions):** Backend dynamically triggers `add_to_queue(goal)` under the hood and returns a structure notifying the client that Mission #X has been dispatched, immediately opening a WebSocket stream.

This gives the user the best of both worlds: **instant chat-bot replies** for questions, and **robust, async agent team execution** for complex work.

---

## 6. Recommended Backend API Endpoint Specifications

To enable the Flutter application to function efficiently, the Squad OS backend API should extend its existing REST layout (`squad_os/api/main.py`) with the following lightweight, mobile-optimized endpoints.

### 1. Unified Conversational Gateway
* **Endpoint:** `POST /api/v1/chat`
* **Purpose:** Unified text entry point for the mobile client. Routes automatically between direct query and mission dispatching.
* **Payload:**
```json
{
  "message": "Write a secure auth middleware, and tell me if our tests pass.",
  "session_id": 91,
  "uploaded_files_json": null
}
```
* **Response (Mission Spawning):**
```json
{
  "routing_decision": "SPAWN_MISSION",
  "response_message": "Understood. I am spinning up a security-focused developer team for Mission #91.",
  "mission_id": 91,
  "status": "QUEUED"
}
```
* **Response (Direct Answer):**
```json
{
  "routing_decision": "DIRECT_ANSWER",
  "response_message": "Mission #90 was completed successfully at 5:12 PM. All 18 tests are green.",
  "mission_id": 90,
  "status": "COMPLETED"
}
```

### 2. Mobile-Optimized Mission Status Summary
* **Endpoint:** `GET /api/v1/missions/{id}/summary`
* **Purpose:** Mobile clients do not need to parse complete task inputs, outputs, errors, and agent configs. This returns a tiny, aggregated state packet.
* **Response:**
```json
{
  "mission_id": 91,
  "goal": "Refactor authentication layer",
  "status": "IN_PROGRESS",
  "progress_percent": 75,
  "started_at": "2026-07-26T14:30:00Z",
  "active_agent": "CoderAgent",
  "task_summary": {
    "completed": 3,
    "total": 4,
    "current_description": "Implementing JWT verification logic"
  },
  "awaiting_approval": false
}
```

### 3. Unified Activity Timeline (Activity Feed)
* **Endpoint:** `GET /api/v1/activity`
* **Purpose:** Returns a lightweight, milestone-oriented feed of system-wide historical events.
* **Query Parameters:** `limit` (default: 20), `offset` (default: 0).
* **Response:**
```json
{
  "timeline": [
    {
      "timestamp": "2026-07-26T14:52:10Z",
      "event_type": "MISSION_COMPLETED",
      "mission_id": 90,
      "title": "Android app generated",
      "description": "Planner, Researcher, and Coder successfully built and compiled the landing page app."
    },
    {
      "timestamp": "2026-07-26T14:48:00Z",
      "event_type": "TASK_VERIFICATION_SUCCESS",
      "mission_id": 90,
      "title": "Tests passed",
      "description": "Verifier completed verification suite on checkout branch."
    },
    {
      "timestamp": "2026-07-26T14:12:05Z",
      "event_type": "DEPLOYMENT_FAILED",
      "mission_id": 89,
      "title": "Deployment failed",
      "description": "Execution interrupted: Port 8080 already in use on staging target."
    }
  ]
}
```

### 4. Compact Notification Feed
* **Endpoint:** `GET /api/v1/notifications`
* **Purpose:** Fetch a lightweight list of recent notifications for the Alerts tab (or poll-based fallback if push fails).
* **Response:**
```json
{
  "unread_count": 1,
  "notifications": [
    {
      "id": "notif_44920",
      "title": "Approval Required",
      "body": "Mission #91 is paused awaiting your confirmation.",
      "timestamp": "2026-07-26T14:55:00Z",
      "read": false,
      "deep_link": "squados://approvals/91"
    }
  ]
}
```

---

## 7. WebSocket & Event Coordinator Strategy

The companion app depends heavily on low-latency, real-time updates. The mobile app will integrate with the backend's existing WebSocket system using a mobile-adapted messaging pattern.

### Event Propagation Model
Rather than streaming detailed agent trace logs (which clog cellular bandwidth and slow down client processing), the server's WebSocket coordinator will filter and wrap notifications using lightweight channel subscriptions.

```
       [Worker / Manager]
               |
               v (New Log / Task State Changed)
     [WebSocket EventCoordinator]
               |
               +--------------------------------------+
               | Filter out verbose raw stdout/stderr  |
               +--------------------------------------+
               |
               v (Simplified JSON Payload)
       [Mobile WebSocket Client]
```

### Simplified Event Payloads

* **`MISSION_PROGRESS` Event:**
```json
{
  "event": "mission_progress",
  "data": {
    "mission_id": 91,
    "status": "IN_PROGRESS",
    "progress_percent": 50,
    "active_agent": "CoderAgent",
    "status_message": "Writing JWT validation routines..."
  }
}
```

* **`APPROVAL_REQUESTED` Event:**
```json
{
  "event": "approval_requested",
  "data": {
    "mission_id": 91,
    "task_id": 1024,
    "approval_id": 412,
    "message": "Authorize deployment of auth middleware to staging environment?"
  }
}
```

### Reconnection and State Recovery Policy
Mobile devices regularly lose connectivity, change IP addresses, or switch between Cellular and Wi-Fi networks.
1. **Heartbeat Pings:** The client sends a lightweight `{"ping": true}` packet every 15 seconds to keep the socket alive.
2. **Exponential Backoff Reconnection:** If disconnected, the Flutter app attempts reconnection at intervals of 1s, 2s, 4s, 8s, up to a maximum of 30s.
3. **Implicit Reconciliation:** Upon reconnection, the client queries `GET /api/v1/missions/active` and `GET /api/v1/notifications` to fetch any state updates missed during the offline period, ensuring the local app state aligns perfectly with the backend database.

---

## 8. Push Notification & Deep-Linking Strategy

Push notifications represent a critical communication channel for the mobile app, allowing the system to alert users instantly even when the app is closed.

```
+--------------------------------------------------------------+
| [🛡️ SquadOS]  Mission #91                                    |
| Coder requires your approval to modify staging.              |
|                                                              |
| [ Approve ]     [ Reject ]     [ Tap to View ]               |
+--------------------------------------------------------------+
```

### Push Architecture
1. **Token Registration:** Upon login, the Flutter app registers its unique Firebase Cloud Messaging (FCM) or Apple Push Notification service (APNs) token via `POST /api/v1/devices/register`.
2. **Trigger Points:** The backend triggers a push alert on:
   * **Mission Interrupts:** When an agent pauses execution waiting for feedback.
   * **Mission Completion / Failures:** When a long-running execution reaches terminal states.
   * **System Offline Warnings:** If the agent worker goes offline during an active run.
3. **Dynamic Actions:** Integrating **FCM Notification Actions** allows the OS to display button options (e.g., "Approve", "Reject") directly on the system lock screen, eliminating the need to launch the app for quick, standard responses.

### Deep-Linking Registry
Tapping a push notification triggers custom URL deep-linking within GoRouter on the mobile device.

| Alert Category | Target Deep Link URL Scheme | Destination App Route |
| :--- | :--- | :--- |
| **Approval Requested** | `squados://approvals/{mission_id}?task={id}` | Navigates directly to the single-card HITL review screen. |
| **Mission Finished** | `squados://chat/{mission_id}` | Opens the relevant chat session history thread. |
| **Worker Down Alert** | `squados://settings/diagnostics` | Opens connection diagnostics for quick recovery. |

---

## 9. Migration & Implementation Roadmap

Converting the mobile app from a complex dashboard clone to a high-speed AI remote companion follows a phased, zero-breaking-change rollout.

```
  PHASE 1 (Backend REST & WS)     PHASE 2 (Flutter Core UI)      PHASE 3 (Deep-links & Push)
  [=========================>]   [========================>]    [===========================>]
  - Deploy /chat endpoint        - Build primary 5-tab Nav      - Set up APNs/FCM channels
  - Add /missions/summary        - Build Conversation view      - Add squados:// URL schemes
  - Keep Streamlit untouched     - Integrate status overlays    - Final verification tests
```

### Phase 1: API and Backend Preparation (No Breaking Changes)
* **Goal:** Extend `squad_os/api/main.py` and `squad_os/database/session.py` with mobile-optimized routes.
* **Tasks:**
  * Add `/api/v1/chat` conversational router.
  * Implement lightweight `/api/v1/missions/{id}/summary` to drastically reduce DB processing during polling.
  * Ensure all SQLite write functions are atomic to avoid concurrency errors during parallel updates.
* **Streamlit Safety:** No existing frontend code is modified, preserving the desktop experience.

### Phase 2: Mobile Navigation Restructuring (Flutter UI)
* **Goal:** Implement the new tab-based navigation shell.
* **Tasks:**
  * Replace the dashboard screens in GoRouter with the new 5-tab layout (Chat, Activity, HITL, Alerts, Settings).
  * Build the primary Chat interface with a streamlined horizontal session selector. Pointers to historical lists are nested inside settings.
  * Implement the Floating Progress Overlay on the Home screen.

### Phase 3: One-Handed HITL & Activity Feed
* **Goal:** Implement clean approval cards and milestone-based activity streams.
* **Tasks:**
  * Implement Slack-style card renderers in Flutter for the HITL tab.
  * Build a simple visual milestone list for Activity, stripping out heavy task DAGs and logs.
  * Connect buttons to existing `/approvals` or `update_interrupt_guidance` backend endpoints.

### Phase 4: Push Notifications, WebSockets, and Deep-Linking
* **Goal:** Hook up the real-time push notification network.
* **Tasks:**
  * Connect FCM / APNs payload triggers to the backend database lifecycle.
  * Set up deep-link handlers inside GoRouter to navigate directly on tap.
  * Enable cellular-optimized WebSocket subscription parameters.

---

## 10. Long-Term Future Vision

With this companion app architecture in place, Squad OS becomes an incredibly responsive, highly accessible mobile coordinator:

1. **Voice-to-Command Actions:** Natural voice integration (using Whisper or native device transcription) will allow operators to say *"Deploy a backup server"* while walking. The app converts the voice input to text, posts it to `/api/v1/chat`, and returns the spawned mission details.
2. **Context-Aware Recommendations:** If a mission fails or requires approval, the assistant will pre-generate 2-3 likely response options (e.g., *"Retry with SQLite"*, *"Change port to 3000"*), giving operators one-tap recovery alternatives while on the go.
3. **Cross-Device Handovers:** Operators can initiate a mission on their phone during a commute, monitor its progress live, and seamlessly open their laptop to find the complete visual DAG and file tree ready on their primary desktop dashboard.
