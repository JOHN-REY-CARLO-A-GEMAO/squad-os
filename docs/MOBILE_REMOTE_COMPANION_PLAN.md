# Squad OS Mobile Remote Companion App: Product Design & Migration Blueprint

## 1. Product Vision: The AI Remote Companion (Claude Mobile for SquadOS)

The mobile companion for Squad OS is evolving from a dashboard-oriented replication of the desktop interface into a high-speed, conversation-first **Remote Companion and AI Controller**.

Rather than serving as an administrative panel with heavy metrics, complex DAG editors, and file browsers, the mobile application adopts a philosophy inspired directly by **Claude Mobile** and **ChatGPT Mobile**. It acts as the fastest, most natural way to interact with Squad OS when away from the computer.

```
       +--------------------------------------------+
       |             SQUAD OS ECOSYSTEM             |
       +--------------------------------------------+
                     /                      \
                    /                        \
       +--------------------+        +--------------------+
       |  Desktop Dashboard |        | Mobile Companion   |
       |  (Control Center,  |        | (AI Companion:     |
       |   DAG Editors,     |        |  Conversation,     |
       |   Technical Logs)  |        |  Quick Approvals)  |
       +--------------------+        +--------------------+
                 ^                             |
                 |                             |
                 v                             v
       +--------------------------------------------+
       |           Squad OS Backend API             |
       |     (FastAPI, WebSocket, SQLite DB)        |
       +--------------------------------------------+
```

### Core Product Philosophy
* **Desktop is the Control Center:** Desktop is where users inspect DAGs, browse full terminal logs, debug complex failures, configure workflows, and perform system-wide administration.
* **Mobile is the AI Companion:** Mobile is where users chat with Squad OS, launch work, monitor live execution streams, approve single-thumb requests, and receive real-time updates. The phone should never feel like Jenkins; it should feel like you are texting your AI team.
* **Conversation-First Orchestration:** All interaction begins and ends inside a unified chat. Execution progress, notifications, milestones, and approvals are streamed directly inside the chat timeline as lightweight conversation events.
* **One-Handed Interactivity:** Human-in-the-loop (HITL) actions, alerts, and decisions are optimized for quick, single-thumb, Slack/Discord-style interactions.

---

## 2. Information Hierarchy

To support a conversation-first model, we invert the traditional mission-centric hierarchy. Instead of treating missions as the top-level container, we group them dynamically under persistent conversations.

```
Workspace
    └── Conversation
            └── Messages
                    └── Mission
                            ├── Agents
                            └── Tasks
```

### The Architectural Objects:
1. **Workspace:** Represents a project or logical boundary (e.g., *"Mobile App"* or *"E-commerce Backend"*), similar to a Claude Project.
2. **Conversation:** A persistent chat history that maintains long-term execution context. Multiple missions are spawned, updated, and completed directly inside the same conversation timeline.
3. **Messages:** Standard conversation items (User Prompts and Assistant Responses).
4. **Mission:** Spawned automatically by the assistant to handle execution requests. The user never leaves the chat; the mission runs and displays progress inline.
5. **Agents & Tasks:** Under-the-hood worker states represented as glanceable, expandable summaries within the conversation.

#### Conversation Example:
```
Workspace: Mobile App

[Conversation Timeline]

You:
"Build the user login screen."

Assistant:
"Understood! Spawning a developer team to build the login view."
[Mission #21 Started: Build Login Screen]
[Progress: Coder working... ⚡]

...

You:
"Now add OTP verification."

Assistant:
"Adding OTP code verification to the existing login module."
[Mission #22 Started: Add OTP Module]
[Progress: Completed ✅]

...

You:
"Fix the configuration crash."

Assistant:
"Debugging config crash."
[Mission #23 Started: Repair Crash]
[Progress: Running... ⚡]
```

---

## 3. Primary Navigation & Screen Architecture

The mobile application relies on a clean, simplified **3-Tab Navigation System**. Standalone screens for activities, tasks, and notifications are removed completely; activity and notifications live naturally inside the conversations themselves.

```
+-----------------------------------------------------+
|                                                     |
|                   SQUAD OS MOBILE                   |
|                                                     |
|        +----------+   +-------------+   +--------+  |
|        |   Chat   |   |  Approvals  |   | Settings| |
|        |   [01]   |   |     [02]    |   |  [03]  |  |
|        +----------+   +-------------+   +--------+  |
|                                                     |
+-----------------------------------------------------+
```

### 1. Chat Screen (Primary/Home)
* **The Heart of the App:** Displays the open conversation. Immediately accepts prompts and allows switching between multiple workspace threads.
* **Inline Mission Streams:** If a mission is running, a compact status card streams live updates right within the chat history.
* **Conversation Switching:** Exposes a clean workspace-to-conversation list hierarchy via a slide-out drawer, a bottom sheet, or a simple drop-down switcher.

### 2. Approvals Screen (HITL Queue)
* **Approval Inbox:** A dedicated queue of pending approvals, designed specifically for easy, one-handed thumb interaction.
* **Slack-Style interactive Cards:** Each card displays only the critical context (e.g., *"Delete 48 obsolete security configuration files from workspace?"*) and simple **Approve** / **Reject** buttons along with an optional guidance text field.

### 3. Settings Screen (Toolbox)
* **Secondary Operations Hub:** Keeps primary screens completely uncluttered by holding:
  * Server Profiles & Connection Status (local, staging, cloud)
  * Diagnostics & Health Tests (WebSocket latency, connection uptime)
  * System/Store Administration (Installed Packages list and the Ecosystem Store)
  * Appearance & Notification preferences

---

## 4. UI/UX Mockups & Visual Flow

### Home & Chat Screen
The chat screen represents active collaboration. Notice how mission execution and progress are blended seamlessly as events inside the chat timeline:

```
+---------------------------------------------------+
|  [=] Mobile App Backend Workspace       (Profile) |
+---------------------------------------------------+
|                                                   |
|  💬 You                                            |
|     Refactor authentication to use secure JWT.    |
|                                                   |
|  🤖 Assistant                                     |
|     Got it. I'll spin up our security experts.    |
|                                                   |
|  -----------------------------------------------  |
|  [⚡] Mission #91: Refactor Authentication        |
|  Progress: [██████░░] 75% | Coder working         |
|                                                   |
|  Planner    ✓ Goal understood                     |
|  Researcher ✓ Security patterns analyzed          |
|  Coder      ⚡ Implementing jwt_verify()           |
|  Tester     ○ Waiting                             |
|  -----------------------------------------------  |
|                                                   |
|  💬 You                                            |
|     Use Riverpod instead of Provider.             |
|                                                   |
|  🤖 Assistant                                     |
|     Understood. Forwarding directive to Coder.    |
|                                                   |
+---------------------------------------------------+
|  [+] Message...                              [>]  |
+---------------------------------------------------+
|     [Chat]            Approvals          Settings |
+---------------------------------------------------+
```

### Workspace & Conversation Switcher (Drawer/Slide-out)
Users can slide open the drawer to change workspaces and jump directly to active conversation threads:

```
+---------------------------------------------------+
|  [x] Workspaces                                   |
+---------------------------------------------------+
|                                                   |
|  📁 MOBILE APP                                    |
|     • JWT Auth Migration (Active ⚡)              |
|     • Landing Page Checkout                       |
|     • Bugfix: Core Router Crash                   |
|                                                   |
|  📁 SHOPPING CART SERVICE                         |
|     • Stripe Integration                          |
|     • Inventory Sync Cron                         |
|                                                   |
+---------------------------------------------------+
```

### HITL Decision Card (Approvals Tab)
The approvals screen focuses on fast, single-thumb interactive confirmation cards. It's designed to make complex actions very clear and easily actionable:

```
+---------------------------------------------------+
|  Approvals Inbox                              [1] |
+---------------------------------------------------+
|  CARD 1 OF 1                                      |
|  Mission: #91 Refactor Authentication             |
|                                                   |
|  ⚠️ ACTION REQUIRED                               |
|  "The team wants to delete 48 obsolete security  |
|   configuration files from the workspace."        |
|                                                   |
|  +---------------------------------------------+  |
|  | [ Approve Deletion (Green / Primary) ]      |  |
|  +---------------------------------------------+  |
|  | [ Reject / Request Adjustments (Red) ]      |  |
|  +---------------------------------------------+  |
|                                                   |
|  +---------------------------------------------+  |
|  | Optional guidance (e.g. Keep config.json)   |  |
|  +---------------------------------------------+  |
+---------------------------------------------------+
|      Chat           [Approvals]          Settings |
+---------------------------------------------------+
```

### Attachments Drawer
Pressing the `+` button in the chat screen opens an overlays menu for fast, contextual attachments:

```
+---------------------------------------------------+
|  Select Attachment                                |
+---------------------------------------------------+
|  [📷 Camera]      [🖼️ Gallery]     [📁 Files]     |
|  [📋 Clipboard]   [🎤 Voice]       [📸 Photo]     |
+---------------------------------------------------+
```

---

## 5. Backend Architecture & Conversational Gateway

The Squad OS backend is already **80-90% complete**. We do not rewrite or replace any of the existing backend systems:
* Event Bus & Command Bus
* Mission dispatch workflows
* SQLite schema and database records
* WebSockets and multi-server coordinator
* Replay buffers & JWT verification

Instead, we add a thin conversational gateway layer to manage persistent sessions.

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
                   |  (LLM/Heuristic/Rule)  |
                   +------------------------+
                              / \
                             /   \
          If simple query   /     \  If execution / action
                           v       v
            +----------------+   +----------------------------+
            | Direct Answer  |   | Spawn/Modify Mission       |
            | (Fast path,    |   | (Queue Worker,             |
            |  no agent DAG) |   |  Stream Progress over WS)  |
            +----------------+   +----------------------------+
```

### Unified Conversational Gateway
Mobile clients interact primarily with the new `POST /api/v1/chat` endpoint.
* **Intent Classification:** The backend conversational router analyzes the incoming prompt (using an LLM classifier, direct rules, or heuristics).
* **Direct Queries:** If the user is asking a system or status question (e.g., *"Did our tests pass?"*), the backend replies directly with a static markdown message from database indexes in <1s.
* **Execution Requests:** If the user issues an active instruction (e.g., *"Deploy the staging server"*), the gateway automatically dispatches a mission, initializes the agent crew, and establishes the WebSocket stream.

---

## 6. Mobile API Specifications

The mobile client interacts with Squad OS using the following tailored REST endpoints.

### 1. Unified Chat Gateway
* **Endpoint:** `POST /api/v1/chat`
* **Payload:**
```json
{
  "message": "Write a secure auth middleware, and check if tests pass.",
  "conversation_id": 14,
  "uploaded_files_json": null
}
```
* **Response (Mission Spawned):**
```json
{
  "routing_decision": "SPAWN_MISSION",
  "response_message": "Understood. I am starting Mission #91 to refactor the auth middleware.",
  "mission_id": 91,
  "status": "QUEUED"
}
```

### 2. Conversation Listing
* **Endpoint:** `GET /api/v1/conversations`
* **Response:**
```json
{
  "conversations": [
    {
      "id": 14,
      "workspace": "Mobile App",
      "title": "Auth Middleware Refactor",
      "last_message_at": "2026-07-26T14:55:00Z"
    }
  ]
}
```

### 3. Get Conversation Details
* **Endpoint:** `GET /api/v1/conversations/{id}`
* **Response:**
```json
{
  "id": 14,
  "workspace": "Mobile App",
  "messages": [
    {
      "role": "user",
      "content": "Write a secure auth middleware.",
      "timestamp": "2026-07-26T14:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Understood. Spawning Mission #91.",
      "timestamp": "2026-07-26T14:30:02Z",
      "mission_id": 91
    }
  ]
}
```

### 4. Send Message to Conversation
* **Endpoint:** `POST /api/v1/conversations/{id}/messages`
* **Payload:**
```json
{
  "role": "user",
  "content": "Make sure we use secure environment secrets."
}
```

### 5. Get Mission Summary
* **Endpoint:** `GET /api/v1/missions/{id}/summary`
* **Purpose:** Mobile clients fetch a small, highly optimized status packet containing current agent milestones, rather than processing verbose terminal stdout/stderr logs.
* **Response:**
```json
{
  "mission_id": 91,
  "goal": "Refactor authentication",
  "status": "IN_PROGRESS",
  "progress_percent": 75,
  "active_agent": "CoderAgent",
  "task_summary": {
    "completed": 2,
    "total": 4,
    "current_description": "Implementing jwt_verify() verification"
  },
  "awaiting_approval": false
}
```

### 6. Pending Approvals Queue
* **Endpoint:** `GET /api/v1/approvals`
* **Response:**
```json
{
  "pending_approvals": [
    {
      "id": 412,
      "mission_id": 91,
      "message": "The team wants to delete 48 obsolete security configuration files from the workspace.",
      "created_at": "2026-07-26T14:52:00Z"
    }
  ]
}
```

### 7. Device Push Token Registration
* **Endpoint:** `POST /api/v1/devices/register`
* **Payload:**
```json
{
  "token": "fcm_or_apns_device_token_string",
  "platform": "ios"
}
```

---

## 7. WebSocket Event Streams & Progress Delivery

Real-time streaming is handled via WebSockets, optimized specifically to save mobile cellular bandwidth.

Rather than sending massive logs, the WebSocket server filters out developer console traces and pushes only structured progression updates:

### Live Status Stream Event
```json
{
  "event": "mission_progress",
  "data": {
    "mission_id": 91,
    "status": "IN_PROGRESS",
    "progress_percent": 75,
    "active_agent": "CoderAgent",
    "status_message": "Implementing jwt_verify() verification..."
  }
}
```

### Interrupt / Approval Required Stream Event
```json
{
  "event": "approval_requested",
  "data": {
    "mission_id": 91,
    "task_id": 1024,
    "approval_id": 412,
    "message": "The team wants to delete 48 obsolete security configuration files."
  }
}
```

---

## 8. Voice Interaction Design

To keep voice interaction seamless, the client introduces an intuitive record-to-send option directly inside the chat interface rather than a separate app state.

```
🎤 Hold microphone icon
↓
UI displays: "Listening... Release to send."
↓
Release icon to compile transcription and dispatch
```

* **Backend Processing:** Audio inputs are transmitted as lightweight payloads to the server, where they are transcribed (using OpenAI Whisper or a local equivalent) and processed directly as standard conversational text inside `/api/v1/chat`.
* **Simple Integration:** Voice is treated strictly as an alternative input format. No complex voice modes or audio playbacks are expected on the mobile companion.

---

## 9. Push Notifications & Deep-Linking

When the application is closed or in the background, Squad OS pushes real-time system state changes via Firebase Cloud Messaging (FCM) or Apple Push Notifications (APNs).

* **Trigger Events:** Alerts are sent immediately for **Approval Required**, **Mission Completed/Failed**, and **System Offline** notices.
* **Deep-Link Redirection:** Tapping on a notification immediately resolves a custom deep link mapping back to the relevant conversation:

| Push Event | Deep Link Target | Destination Route |
| :--- | :--- | :--- |
| Approval Needed | `squados://approvals/{mission_id}?id={approval_id}` | Opens the direct, single-card HITL screen. |
| Mission Finished | `squados://conversations/{id}` | Opens the specific conversation history chat. |
| Worker Disconnected | `squados://settings/diagnostics` | Opens settings diagnostics view. |

---

## 10. Migration & Implementation Roadmap

Converting the mobile app from a complex dashboard clone to a high-speed AI remote companion follows a phased, zero-breaking-change rollout.

### Phase 1: Conversation Backend
* **Goal:** Extend SquadOS API and database models to support conversations.
* **Deliverables:**
  * Define SQLite database schema adjustments for Workspaces and Conversations.
  * Implement the `/api/v1/chat` unified gateway routing.
  * Implement conversational CRUD routes (`/conversations` list, retrieve, and append message).
  * Ensure existing Streamlit desktop companion is completely untouched.

### Phase 2: Flutter Chat UX
* **Goal:** Create the primary Chat interface and conversation switching.
* **Deliverables:**
  * Implement the new 3-tab navigation structure.
  * Build the primary Conversation screen displaying user & assistant messages.
  * Add the slide-out workspace / conversation switching drawer.
  * Add live inline mission status cards with expandable progress summaries.
  * Build the simple attachments selector drawer.

### Phase 3: Approvals & Streams
* **Goal:** Establish seamless, low-overhead WebSocket streams and thumb-friendly approvals.
* **Deliverables:**
  * Build the card-based Approvals tab queue.
  * Hook up the WebSocket receiver to parse structured progression updates instead of technical log packages.
  * Set up APNs/FCM push channels on the backend and device token registry.
  * Implement `squados://` custom deep-linking schemes in GoRouter.

### Phase 4: Future Companion Innovations
* **Goal:** Augment the companion with smart mobile features.
* **Deliverables:**
  * Integrate Hold-to-Record voice inputs.
  * Create glanceable home-screen widgets for Android & iOS.
  * Add smart suggestions / pre-baked prompt responses.
  * Develop lightweight Wear OS and iOS Live Activities components for active mission tracking.
