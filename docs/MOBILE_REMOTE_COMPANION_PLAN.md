# Squad OS Mobile Remote Companion App: Version 2 Architecture & Product Design Blueprint

---

## 1. Product Vision & Goals

The Squad OS Mobile Companion is a high-performance, conversation-first **Remote Companion and AI Operating Controller**.

Rather than serving as a heavy administrative console mimicking desktop interfaces (with complex DAG editors, technical stdout streams, and raw file trees), the companion behaves as a lightweight, intuitive, yet developer-centric interface optimized for one-handed operation. The phone becomes a remote control for your autonomous development team. It is designed to feel closest to **Claude Mobile, ChatGPT Mobile, Cursor, Linear, and Slack**, while remaining uniquely tailored around multi-agent orchestrations.

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
1. **The Conversation is the Canvas:** The primary interface is a unified conversational timeline. Execution details, approvals, files, errors, and system status updates are delivered inline as rich interactive timeline cards rather than separated tabs or complex dashboard widgets.
2. **Invisible Orchestration, Expandable Transparency:** The system defaults to a clean, natural assistant voice ("I am refactoring the authentication router now"). The heavy under-the-hood worker mechanics (DAG progression, planner phases, coder status) are represented as glanceable status streams that can be expanded on-demand.
3. **One-Handed Actionability (HITL via AI Inbox):** Key human decisions—such as reviewing code changes, validating test passes, and confirming risky deployments—are packaged as swipeable, tap-friendly interactive approval cards inside a dedicated AI Inbox requiring minimal typing.
4. **Instant Shared Context:** Every interaction, workspace context chip, and shared memory automatically synchronizes between mobile devices and the desktop control center, establishing a seamless loop of continuous work.
5. **Production-Grade Scalability:** Built upon a resilient Event-Sourced architecture with formal schema versioning, strict sync protocol semantics, offline-first execution queues, capability negotiation, and multi-layered security.

---

## 2. Event Sourcing & State Hierarchy

To scale cleanly across years of multi-agent and multi-platform iterations, the Squad OS Mobile Companion moves away from raw state updates and adopts an **Event Sourced Architectural Model**.

### 2.1 The Event-Sourced Model
Instead of treating `conversation_events` as an ephemeral database logging table, the **Event Stream** is the **Single Source of Truth**. Every state transition—such as a user sending a message, a mission starting, an agent making a thought, a file being modified, or an approval being granted—is appended as an immutable event in the log.

```
Conversation Log (Append-Only Event Sourcing)
  ├── EVENT 101: CHAT.MESSAGE (User: "Refactor Auth")
  ├── EVENT 102: MISSION.STARTED (Mission #91)
  ├── EVENT 103: AGENT.THINKING (Coder: "Identified route redundancy")
  ├── EVENT 104: CODE.DIFF (Proposed changes in auth_service.dart)
  ├── EVENT 105: INBOX.APPROVAL_REQUESTED (Confirm deletion of legacy configs)
  └── EVENT 106: INBOX.APPROVAL_GRANTED (User approved deletion via mobile)
```

Both the desktop and mobile applications maintain memory-efficient projections (local state models) by reading this event stream. This design guarantees:
* **Reliable Replays:** A mobile client recovering from a signal drop can replay missing sequence numbers rather than requesting full page refreshes.
* **Seamless Multi-Device Sync:** The Desktop Control Center and Mobile Companion automatically project the exact same state because they listen and dispatch to the same immutable log.
* **Rich Auditing & Diagnostics:** Complete deterministic replay of what an autonomous agent did, when it asked the user, and exactly what context was active.
* **Simplified Agent Training:** The event history acts as high-fidelity offline training sequences for future coordination LLMs.

### 2.2 Relational Information Hierarchy
Within this event-driven architecture, the structural nesting organizes resources cleanly:

```
Workspace (Project Container)
   └── Conversation
           ├── Metadata (AI config: models, prompt, temp)
           ├── Conversation Memory (Project context: branch, constraints, env)
           └── Unified Event Timeline
                   ├── Base Event (Immutable entry with namespace & type)
                   │     └── Nested Children (Sub-events associated with a parent ID)
                   └── Mission Snapshot (Aggregated cache for quick-resume)
```

---

## 3. Database Architecture & SQLite Schema Extensions

To support separating metadata from project memory, persisting mission snapshots, and allowing nested timeline events, the SQLite database is updated with clean relational mappings.

```
   +-------------------+              +-------------------------+
   |    workspaces     |              |      conversations      |
   |-------------------|              |-------------------------|
   | id (PK)           |1           * | id (PK)                 |
   | name              |------------->| workspace_id (FK)       |
   | description       |              | title                   |
   | created_at        |              | summary                 |
   +-------------------+              | goal                    |
                                      | system_prompt           |
                                      | active_model            |
                                      | temperature             |
                                      | created_at, updated_at  |
                                      +-------------------------+
                                                   |
                                                   | 1
                                                   |
                                                   v *
                                      +-------------------------+
                                      |  conversation_memories  |
                                      |-------------------------|
                                      | id (PK)                 |
                                      | conversation_id (FK)    |
                                      | memory_key (Indexed)    |
                                      | memory_value            |
                                      | updated_at              |
                                      +-------------------------+
                                                   |
                                                   | 1
                                                   |
                                                   v *
                                      +-------------------------+
                                      |   conversation_events   |
                                      |-------------------------|
                                      | id (PK)                 |
                                      | parent_event_id (FK)    | -- Support Nesting!
                                      | conversation_id (FK)    |
                                      | event_namespace         | -- e.g. CHAT, MISSION, AGENT
                                      | event_type              | -- e.g. MESSAGE, STARTED, THINKING
                                      | payload_json            |
                                      | mission_id (FK, Opt)    |
                                      | event_version           |
                                      | created_at              |
                                      +-------------------------+
                                                   |
                                                   | 1 (cached state)
                                                   v 1 (optional mapping)
                                      +-------------------------+
                                      |    mission_snapshots    |
                                      |-------------------------|
                                      | mission_id (PK, FK)     |
                                      | status                  |
                                      | progress                |
                                      | latest_thought          |
                                      | next_action             |
                                      | eta                     |
                                      | confidence              |
                                      | token_usage             |
                                      | estimated_cost          |
                                      | last_updated            |
                                      +-------------------------+
```

### SQLite Schema Specification

```sql
-- 1. Workspaces Table
CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Conversations Table (Contains Metadata that directly changes AI execution parameters)
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    goal TEXT,
    system_prompt TEXT,
    active_model TEXT DEFAULT 'claude-3-5-sonnet',
    temperature REAL DEFAULT 0.2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conversations_workspace_id ON conversations(workspace_id);

-- 3. Conversation Memories Table (Contains Project-specific context fields modifying the workspace configuration)
CREATE TABLE IF NOT EXISTS conversation_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    memory_key TEXT NOT NULL, -- e.g. 'branch', 'framework', 'environment', 'constraints', 'preferences'
    memory_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_conv_memory_key ON conversation_memories(conversation_id, memory_key);

-- 4. Conversation Events Table (Immutable Event-Sourcing Timeline, Supporting Infinite Nesting)
CREATE TABLE IF NOT EXISTS conversation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_event_id INTEGER, -- Non-cyclic recursive foreign key allowing sub-events under a parent event card
    conversation_id INTEGER NOT NULL,
    event_namespace TEXT NOT NULL, -- e.g. 'CHAT', 'MISSION', 'AGENT', 'TOOL', 'DEPLOY', 'PLUGIN', 'STORE', 'GIT', 'INBOX'
    event_type TEXT NOT NULL,      -- e.g. 'MESSAGE', 'STARTED', 'THINKING', 'ACTION', 'JOURNAL', 'APPROVAL_REQUESTED', 'COMPLETE'
    payload_json TEXT NOT NULL,    -- Schema-versioned event data payload
    mission_id INTEGER,            -- Optional direct foreign key connecting timeline events to database mission entries
    event_version INTEGER DEFAULT 1, -- Incremental sequence ID for payload schema structures
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_event_id) REFERENCES conversation_events(id) ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_events_conversation_id ON conversation_events(conversation_id);
CREATE INDEX IF NOT EXISTS idx_events_parent_id ON conversation_events(parent_event_id);
CREATE INDEX IF NOT EXISTS idx_events_mission_id ON conversation_events(mission_id);
CREATE INDEX IF NOT EXISTS idx_events_namespace_type ON conversation_events(event_namespace, event_type);

-- 5. Mission Snapshots Table (Accelerated State Recovery Cache for Web Socket Dropouts)
CREATE TABLE IF NOT EXISTS mission_snapshots (
    mission_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL, -- 'QUEUED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'FOLLOWUP'
    progress REAL DEFAULT 0.0, -- Percentage complete (0.0 to 1.0)
    latest_thought TEXT,
    next_action TEXT,
    eta INTEGER DEFAULT 0, -- Estimated completion time remaining in seconds
    confidence TEXT DEFAULT 'HIGH', -- 'HIGH', 'MEDIUM', 'LOW'
    token_usage INTEGER DEFAULT 0,
    estimated_cost REAL DEFAULT 0.0, -- USD Cost
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE
);

-- 6. Devices Table (Enhanced Push Notification Support with Revocation & Security Fields)
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default_user',
    push_token TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL, -- 'ios' or 'android'
    device_model TEXT,
    is_active INTEGER DEFAULT 1, -- Boolean tracking revocation status
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. System Notifications Table
CREATE TABLE IF NOT EXISTS system_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    deep_link TEXT, -- e.g. 'squados://conversations/14?event_id=102'
    status TEXT DEFAULT 'PENDING', -- 'PENDING', 'SENT', 'FAILED'
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);
```

---

## 4. REST & WebSocket API Specification

Every API endpoint is strictly versioned under `/api/v1` to support continuous schema evolution.

### 4.1 REST API Endpoints

#### 1. Capability Negotiation (Handshake)
Must be requested by the mobile client immediately upon establishing connection to discover API limitations, supported features, and schema versions.
* **Endpoint:** `POST /api/v1/handshake`
* **Request:**
```json
{
  "client_version": "2.0.0",
  "capabilities": [
    "voice_input",
    "live_agent_streams",
    "nested_events",
    "mission_snapshots",
    "qr_pairing"
  ]
}
```
* **Response:**
```json
{
  "server_version": "2.0.4",
  "schema_version": "1.2.0",
  "negotiated_capabilities": {
    "voice_input": true,
    "live_agent_streams": true,
    "nested_events": true,
    "mission_snapshots": true,
    "qr_pairing": true
  },
  "max_payload_mb": 15
}
```

#### 2. Get Conversations for Workspace
* **Endpoint:** `GET /api/v1/workspaces/{workspace_id}/conversations`
* **Response:**
```json
{
  "conversations": [
    {
      "id": 14,
      "workspace_id": 1,
      "title": "JWT Auth Migration",
      "summary": "Refactoring outdated authentication handlers in secure modules",
      "goal": "Introduce robust refresh-token rotation",
      "active_model": "claude-3-5-sonnet",
      "temperature": 0.2,
      "system_prompt": "You are a senior security engineer specializing in Flutter and Supabase.",
      "last_event_at": "2026-05-15T14:32:00Z"
    }
  ]
}
```

#### 3. Fetch Unified Timeline (Event Log Retrieval)
* **Endpoint:** `GET /api/v1/conversations/{id}`
* **Query Parameters:** `limit` (int, default: 50), `parent_only` (bool, default: false - retrieves top-level event cards only to support nested client hydration), `cursor` (string, optional)
* **Response:**
```json
{
  "conversation_id": 14,
  "workspace_id": 1,
  "events": [
    {
      "id": 101,
      "parent_event_id": null,
      "event_namespace": "CHAT",
      "event_type": "MESSAGE",
      "event_version": 1,
      "created_at": "2026-05-15T14:30:00Z",
      "payload": {
        "role": "user",
        "content": "Add verification helper to auth_service.dart."
      }
    },
    {
      "id": 102,
      "parent_event_id": null,
      "event_namespace": "MISSION",
      "event_type": "STARTED",
      "mission_id": 91,
      "event_version": 1,
      "created_at": "2026-05-15T14:30:15Z",
      "payload": {
        "goal": "Add verification helper to auth_service.dart",
        "message": "Assistant spawned Mission #91 to refactor auth_service.dart."
      }
    },
    {
      "id": 103,
      "parent_event_id": 102, -- Nested child event! Shows in expandable sub-history of Mission #91
      "event_namespace": "AGENT",
      "event_type": "THINKING",
      "mission_id": 91,
      "event_version": 1,
      "created_at": "2026-05-15T14:30:45Z",
      "payload": {
        "agent": "CoderAgent",
        "thought": "I detected 4 unused configuration templates in the auth package that conflict with the new JWT helper.",
        "confidence": "HIGH"
      }
    },
    {
      "id": 104,
      "parent_event_id": 102,
      "event_namespace": "INBOX",
      "event_type": "APPROVAL_REQUESTED",
      "mission_id": 91,
      "event_version": 1,
      "created_at": "2026-05-15T14:31:45Z",
      "payload": {
        "approval_id": 412,
        "status": "PENDING",
        "message": "Confirm deletion of 4 outdated configuration templates.",
        "changes_summary": "Deleting legacy templates from /config/secure/."
      }
    }
  ]
}
```

#### 4. Update Conversation Memory (Context Chips)
Updating the active configuration memory of a conversational context.
* **Endpoint:** `PUT /api/v1/conversations/{id}/context`
* **Request:**
```json
{
  "context_memory": {
    "framework": "Flutter",
    "branch": "feature/jwt-refresh",
    "environment": "Supabase Production",
    "constraints": "Do not use legacy provider classes. Use modern Riverpod structures."
  }
}
```
* **Response:**
```json
{
  "status": "SUCCESS",
  "updated_context_memory": {
    "framework": "Flutter",
    "branch": "feature/jwt-refresh",
    "environment": "Supabase Production",
    "constraints": "Do not use legacy provider classes. Use modern Riverpod structures."
  }
}
```

#### 5. Universal Semantic Search Endpoint
Provides vector-based search across all historical messages, actions, files, errors, and approvals, falling back cleanly to SQLite full-text search (FTS) based on backend capabilities.
* **Endpoint:** `GET /api/v1/conversations/{id}/search`
* **Query Parameters:** `q` (string, required), `filter_namespace` (string, optional), `limit` (int, default: 20)
* **Response:**
```json
{
  "query": "the login bug",
  "engine_used": "vector_search", -- or "sqlite_fts"
  "results": [
    {
      "event_id": 104,
      "event_namespace": "INBOX",
      "event_type": "APPROVAL_REQUESTED",
      "similarity_score": 0.892,
      "matched_snippet": "Reviewing security exception caused by expired sessions during **login** validations in auth_service.dart.",
      "timestamp": "2026-05-15T14:31:45Z"
    }
  ]
}
```

---

### 4.2 WebSocket Event Streams

Clients maintain a single persistent connection per active session: `ws://<host>:<port>/api/v1/streams?conversation_id={id}`. Authenticators expect standard JWT headers or a validated ticket passed during handshake negotiation.

#### 1. AI Session Card Update (Snapshots)
Dispatched instantly whenever a critical state transition occurs in an active running mission.
```json
{
  "event_namespace": "MISSION",
  "event_type": "SNAPSHOT_UPDATE",
  "event_version": 1,
  "payload": {
    "mission_id": 91,
    "status": "IN_PROGRESS",
    "progress": 0.75,
    "eta": 120,
    "latest_thought": "I detected a missing validation boundary for access token expiry inside auth_service.dart. Writing a custom verification wrapper.",
    "next_action": "Updating validation wrappers and executing the Flutter test suite.",
    "confidence": "HIGH",
    "token_usage": 24551,
    "estimated_cost": 0.3202
  }
}
```

#### 2. Fine-Grained Agent Activity (Agent Ticks)
Streamed frequently (every 500ms) during intensive execution blocks, designed to populate nested children under the active mission event.
```json
{
  "event_namespace": "AGENT",
  "event_type": "TICK",
  "event_version": 1,
  "payload": {
    "mission_id": 91,
    "parent_event_id": 102,
    "agent": "CoderAgent",
    "status": "WORKING",
    "activity": "EDITING",
    "active_file": "lib/services/auth_service.dart",
    "current_action": "Writing jwt_verify_claims() function body...",
    "subtask_progression": ["Understand boundaries ✓", "Write tests ✓", "Implement ⚡", "Validate ○"]
  }
}
```

---

## 5. Mobile UI & UX Screen Architecture

The interface adopts an elegant, accessible **4-Tab Navigation Layout** with structural overlays.

```
+-----------------------------------------------------+
|                                                     |
|                   SQUAD OS MOBILE                   |
|                                                     |
|  +-------+   +--------+   +-----------+   +------+  |
|  | Today |   |  Chat  |   | AI Inbox  |   | Settings|
|  |  [T]  |   |  [C]   |   |   [A!]    |   |  [S]  |  |
|  +-------+   +--------+   +-----------+   +------+  |
|                                                     |
+-----------------------------------------------------+
```

### Tab 1: Today Dashboard (The Workspace Pulse)
* **Design Philosophy:** Replaces default technical lists with a glanceable executive layout. It is only focused on what requires immediate attention *now*.
* **UI Modules:**
  * **Critical Actions Required:** Card stack representing unhandled AI Inbox alerts (needs immediate verification/approvals).
  * **Active Missions Summary:** Miniature horizontal cards of currently running agents, displaying circular timers, ETA, and progress.
  * **Recent Milestones:** Completed tasks from today/yesterday shown in high-level clean formats.

### Tab 2: Chat Canvas (The Project Interface)
* **Custom Context Chips (Header):** Tap-friendly pills at the top (`🌿 feature/jwt`, `📱 Flutter`, `☁️ Supabase`). Tapping a pill triggers a native sliding sheet with quick selection wheels to change environmental targets on-the-fly.
* **Unified Event Stream:** Vertical list displaying formatted events.
* **AI Session Card (Sticky/Anchored):** Displays details when a mission is active:
  * **Auto-Collapse Feature:** To avoid huge scrolling timelines, granular compilation/thinking logs under the mission are collapsed by default. The card displays a summary line: *"Coder is editing auth_service.dart (14 sub-events hidden) [Show]"*.
  * **Visual Metrics:** Live duration ticker, running cost calculator ($0.00), confidence badge (`HIGH` / `MEDIUM` / `LOW`), and remaining ETA.
  * **Inline Quick Actions:** Tap buttons embedded inside completed/failed timeline entries (`Open Diff`, `Summarize`, `Deploy`, `Rollback`, `Share`).
* **Global Command Palette Drawer:**
  * Triggered via a downward swipe gesture anywhere, long press on the screen, or tapping the Search header icon.
  * Opens a fuzzy-matched overlay list mimicking Spotlight or Raycast. Allows searching and firing global actions (`/deploy`, `/switch-workspace`, `/create-mission`, `/clear-cache`, `/reconnect`).

### Tab 3: AI Inbox (The HITL Controller)
* **Design Philosophy:** Replaces simple flat "Approvals" with a multi-layered action hub.
* **Inbox Folders / Filters (Top):** Horizontal segmented pill controls:
  `[ All ]  [ Needs Approval ]  [ Needs Review ]  [ Needs Attention ]  [ Warnings ]`
* **Card UI Elements:**
  * Displays details of why the human is blocking progress.
  * Collapsible Unified Git Diff view highlighting additions in green and deletions in red with syntax-aware line formatting.
  * Touch-friendly control elements: Primary green "Approve", secondary orange "Request Changes", and an integrated keyboard voice prompt input to dictate quick guidance.

### Tab 4: Settings & Diagnostics
* **Active Environment Configuration:** Connects to backends via hostname, WebSockets, or pairing.
* **Trusted Devices Registry:** List of authorized devices with individual revoke capability buttons.
* **Background Sync Diagnostics:** Shows latency stats, offline outbound queues, and synchronization health indicators.

---

## 6. Feature Specifications

### 6.1 Context Chips as Live Objects
Custom Context Chips located at the top of the Chat Canvas represent key variables of the conversation's active memory (`branch`, `framework`, `environment`).
* **Behavior:** Tapping a Context Chip displays an interactive modal list of options dynamically fetched from the workspace server (e.g., active branches on the git repo, configured runtime environments).
* **Sync Loop:** When a user selects a new value (e.g., swapping active branch from `main` to `feature/jwt-refresh`), the client triggers:
  1. A native visual transition on the chip (flashes to indicate updating).
  2. A REST `PUT /api/v1/conversations/{id}/context` request.
  3. A local database write to ensure offline persistence.
  4. An instant local broadcast. The Desktop Control Center listening to the WebSocket stream receives the update and automatically executes a git checkout to match the user's mobile target.

### 6.2 Secure Desktop QR Pairing Protocol
To completely eliminate the insecurity of manual password exchanges or raw local network scans, Squad OS implements a multi-step **Trusted Device Handshake via QR Code**.

```
  [Desktop App]                                                 [Mobile App]
        |                                                             |
        | 1. Generates short-lived session nonce                      |
        | 2. Renders secure pairing QR                                |
        |                                                             |
        |             =================================>              |
        |                        [Scan QR]                            |
        |                                                             |
        |                                                             | 3. Parses URI & extracts:
        |                                                             |    - Nonce, Host, DeviceID
        |                                                             | 4. Requests token via secure HTTPS
        |                                                             |
        |<============================================================|
        |                 [POST /api/v1/pair/request]                 |
        |                                                             |
        |                                                             |
        | 5. Prompts Confirmation Dialog:                             |
        |    "Approve Mobile Device #12?"                             |
        |                                                             |
        |             =================================>              |
        |                     [Admin Clicks Approve]                  |
        |                                                             |
        | 6. Generates Cryptographic Keys                             |
        | 7. Issues JWT Token Pairs                                   |
        |                                                             |
        |<============================================================|
        |                      [GET /v1/pair/token]                   |
        |                                                             |
        |                                                             | 8. Saves Secure JWT in Keychain
        |                                                             | 9. Connects via Secure WSS
```

#### The Protocol Details:
1. **QR Generation:** The Desktop client requests a signed ephemeral pairing ticket from the coordinator backend containing:
   ```json
   {
     "pairing_url": "squados://pair",
     "nonce": "a7b3c9f28d...",
     "device_id": "desktop_coordinator_01",
     "expires_at": 1782531200
   }
   ```
2. **Scanning:** Mobile scans the QR, validates the protocol scheme, and dispatches a pairing execution payload directly over HTTPS using TLS.
3. **Backend Validation & Pinning:** The backend caches the connection request.
4. **Desktop HITL Clearance:** Desktop displays an overlay confirmation dialog: *"Allow 'iPhone 15 Pro' to pair and command this workspace?"*.
5. **Session Initiation:** Upon confirmation, the backend flags the nonce as approved and generates an asymmetrical RSA public/private key-pair, issuing signed JWT refresh and access tokens pinned to that mobile device ID.
6. **Encrypted WebSocket Handshake:** Future communication is established using secure WSS with message payloads fully validated against active device registries.

### 6.3 Background Sync Engine Architecture
To survive low-coverage areas, transit tunnels, and active signal drops, the mobile companion relies on a dedicated background system sync engine.

```
+-------------------------------------------------------------------------+
|                          CLIENT APPLICATION LAYER                       |
+-------------------------------------------------------------------------+
                                 |         ^
                                 v         | [Notify updates]
+-------------------------------------------------------------------------+
|                           LOCAL CACHE DATABASE                          |
+-------------------------------------------------------------------------+
        |                                                         ^
        v [Read / Write Events]                                   | [Hydrate Cache]
+----------------------------------------------------+   +----------------+
|               OUTBOUND EVENT QUEUE                 |   | DOWNLOAD ENGINE|
+----------------------------------------------------+   +----------------+
        |                                                         ^
        v [Batch dispatch]                                        | [Poll / Stream]
+----------------------------------------------------+            |
|              SYNC CONTROLLER & RESOLVER            |<===========+
+----------------------------------------------------+
        |                                  ^
        v [WSS / HTTPS]                    | [Push Trigger Notification]
+-------------------------------------------------------------------------+
|                           BACKEND SERVICE API                           |
+-------------------------------------------------------------------------+
```

* **Core Components:**
  * **Outbound Queue:** Houses serialized requests (JSON updates, timeline comments, approvals) in chronological order with logical sequence markers.
  * **Retry & Backoff Manager:** Executes connection attempts using exponential backoff logic (e.g. 1s -> 2s -> 4s -> 8s -> 16s -> maximum 60s cap) with added jitter to prevent API request storms.
  * **Conflict Resolution Processor:** Reconciles differences when offline events overlap with changes updated on the remote host during signal drops.

### 6.4 Offline Conflict Resolution Policy Matrix
Because Squad OS is collaborative, conflicting state modifications are possible while offline. The Sync Engine applies strict policy bindings per table resource:

| Resource Type | Conflict Scenario | Applied Policy | Technical Resolution |
| :--- | :--- | :--- | :--- |
| **Chat Timeline Messages** | User posts message offline while another user/agent posts messages online | **Merge** | Chronological ordering using verified client-side sequence clock tracking with absolute server-receive indexing. |
| **Mission State Execution** | User pauses mission offline, but worker finishes mission online | **Server Wins** | The active agent execution state on the server takes precedence; client adjusts its visual state to match server logs. |
| **Workspace Settings** | Editing environmental values offline while updated elsewhere | **Last Write Wins** | Field updates compare cryptographic timestamps; the highest epoch value overwrites previous states. |
| **Files & Code Assets** | Modifying attachments offline that are changed on disk | **Manual Resolve** | The event log flags the attachment with a conflicted state. The user must choose whether to overwrite, download server state, or split into a branch. |
| **AI Inbox Approvals** | User attempts to approve an item that was cancelled/processed online | **Server Wins** | The transaction rejects on the client; UI prompts a warning notification: *"This approval request was already processed."* |

### 6.5 Mission Journal Architecture
Upon successful completion of any mission, the orchestrator automatically generates a **Mission Journal**, recording it as an immutable timeline event.

* **Markdown Document Specification:**
  ```markdown
  # Mission Complete: #91 Refactor Authentication

  ## 📝 Executive Summary
  Successfully integrated OAuth validation handlers and migrated configuration schemas to secure token formats inside lib/services/auth_service.dart.

  ## 📂 Files Modified
  - `lib/services/auth_service.dart` (+42 lines, -12 lines)
  - `test/auth_test.dart` (+15 lines)

  ## 🧪 Testing Results
  - Total Tests Run: 14
  - Passed: 14 (100% Green)
  - Coverage: 92.4% (No regressions detected)

  ## ⏱️ Execution Metrics
  - Total Duration: 4 minutes 12 seconds
  - AI Models Used: Claude 3.5 Sonnet, GPT-4o
  - Token Consumption: 28,144 Input | 4,212 Output
  - Estimated Session Cost: **$0.34 USD**

  ## 💡 Lessons Learned & Technical Debt
  Identified legacy Provider bindings in adjacent modules during router integration. Recommending a future refactoring sweep of the payments package to align with modern Riverpod patterns.
  ```

---

## 7. Comprehensive UI & UX Mockups

### 7.1 Today Dashboard (Tab 1 Landing)

```
+-------------------------------------------------------------+
|  📅 TODAY                                    [🔍 Palette] [⚙️] |
+-------------------------------------------------------------+
|                                                             |
|  🚨 ACTION REQUIRED                                         |
|  +-------------------------------------------------------+  |
|  | [AI INBOX] Mission #91: Delete legacy secure configs |  |
|  | Requested by: CoderAgent | Status: PENDING            |  |
|  | > Confirm deletion of 48 config files.                |  |
|  |                                                       |  |
|  |     [❌ Reject]               [⚡ Quick Review]        |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  ⚡ ACTIVE CREW                                              |
|  +-------------------------------------------------------+  |
|  | Mission #94: Run Payment Migrations                   |  |
|  | Running 2m 4s | ETA: 4m 12s | Progress: [████░░░░] 50% |  |
|  | Active Agent: CoderAgent (editing stripe_service.dart) |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  ✅ COMPLETED YESTERDAY                                      |
|  - Mission #90: Setup secure cookie parsing (Cost: $0.12)   |
|  - Mission #89: Configure SSL proxy routes (Cost: $0.08)     |
|                                                             |
+-------------------------------------------------------------+
|  [Today]          Chat            AI Inbox         Settings |
+-------------------------------------------------------------+
```

### 7.2 Unified Conversation Timeline with AI Session Card (Tab 2)

```
+-------------------------------------------------------------+
|  [=] Mobile App Backend Workspace                 [🖥️ Handoff] |
|                                                             |
|  [ 🌿 feature/jwt ]  [ 📱 Flutter ]  [ ☁️ Supabase ]        |
+-------------------------------------------------------------+
|                                                             |
|  💬 You                                                      |
|     Refactor authentication to use secure JWT.              |
|                                                             |
|  🤖 Assistant                                               |
|     Got it. Spawning security experts to update the router. |
|                                                             |
|  ==================== ACTIVE SQUAD ======================== |
|  [⚡] Mission #91: Refactor Authentication                   |
|  Elapsed: 3m 42s | ETA: 1m 30s | Status: RUNNING [██████░░] |
|  Confidence: HIGH (94%) | Est. Cost: $0.28                  |
|                                                             |
|  Planner    ✓ Understanding boundaries                       |
|  Researcher ✓ Analyzing security patterns                   |
|  Coder      ⚡ Editing: lib/services/auth_service.dart       |
|  Tester     ○ Waiting                                       |
|                                                             |
|  Latest Thought: "Detected a missing validation helper for  |
|  access tokens in JWT parser. Writing test cases now."      |
|  Next Action: "Run local unit tests."                       |
|                                                             |
|  [+] 14 detailed compiler sub-events hidden...         [v] |
|  ========================================================== |
|                                                             |
|  💬 You                                                      |
|     Use Riverpod instead of Provider.                       |
|                                                             |
|  🤖 Assistant                                               |
|     Understood. Forwarding directive to Coder.              |
|                                                             |
+-------------------------------------------------------------+
|  [+] Message...                                        [🎤] |
+-------------------------------------------------------------+
|   Today          [Chat]           AI Inbox         Settings |
+-------------------------------------------------------------+
```

### 7.3 High-Contrast AI Inbox (Tab 3 UI)

```
+-------------------------------------------------------------+
|  📥 AI INBOX                                            [1] |
|                                                             |
|  [ All ]  [ Needs Approval (1) ]  [ Needs Attention ]  [✔]  |
+-------------------------------------------------------------+
|  CARD 1 OF 1                                                |
|  Mission: #91 Refactor Authentication                       |
|  Requested by: CoderAgent | Level: HIGH CONFIDENCE (91%)    |
|                                                             |
|  ⚠️ ACTION REQUIRED                                         |
|  "The team wants to delete 48 obsolete security config      |
|   templates from the workspace."                            |
|                                                             |
|  +-------------------------------------------------------+  |
|  | 📂 View Proposed Deletion Diff (48 files)         [v] |  |
|  | - config/secure/legacy_rsa.json (DELETED)             |  |
|  | - config/secure/temp_key.pem (DELETED)                |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  +-------------------------------------------------------+  |
|  | [ Approve Deletion (Green / Primary) ]                 |  |
|  +-------------------------------------------------------+  |
|  | [ Reject / Request Adjustments (Red) ]                |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  +-------------------------------------------------------+  |
|  | Optional feedback (e.g. Keep config.json)             |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
|   Today           Chat           [AI Inbox]        Settings |
+-------------------------------------------------------------+
```

---

## 8. Security & Trust Architecture

For a remote operations tool, security is paramount. The Mobile Companion applies strict defense-in-depth principles across all components.

1. **Cryptographic Key Storage:**
   * Local session cookies, API tokens, and JWT payloads are encrypted at rest using platform-native hardware security wrappers: **Apple Keychain Services** (iOS) and **Android Keystore System** (Android).
2. **Access Token & Refresh Flow:**
   * Uses short-lived access tokens (15-minute expiration) paired with securely stored refresh tokens.
   * Access tokens are automatically rotated without interrupting current UI streaming threads.
3. **Hardware Device Binding & Revocation:**
   * Every paired device is tied to a unique platform fingerprint and cryptographic key pair.
   * The Desktop app or Administrator console can issue a one-click revocation signal, instantly invalidating the device's refresh token on the database.
4. **Encrypted WebSocket Authentications:**
   * WebSockets require a secure authentication handshake ticket. Initial connection passes a short-lived token over query parameters, which is immediately validated and destroyed upon connection setup.
5. **Human-In-The-Loop Audit Trails:**
   * Sensitive tasks (code compilation, deployments, structural deletions) require verifiable signatures.
   * Every action taken in the **AI Inbox** is logged as an immutable, signed ledger event under the `conversation_events` table for high-fidelity compliance audits.

---

## 9. Plugin & Event Contract

Squad OS is built to be modular. To prevent schema bloating or UI breaking changes whenever third-party development packages (issued as `.sqad` extensions) are installed, we establish a standardized **Ecosystem Plugin Event Contract**.

### 9.1 Namespace Assignments
The database and WebSocket routers reserve the following namespaces for external extensions:
* `PLUGIN.*`: Dispatched by external tools to insert custom execution timelines.
* `TOOL.*`: Emitted when agents utilize custom environment executors.
* `STORE.*`: Triggered when packages are updated, verified, or uninstalled.

### 9.2 Standardized Custom UI Payloads (`PLUGIN.UI`)
Plugins can inject custom UI modules directly into the conversation feed without native app compilation by emitting a structured `PLUGIN.UI` event with standard interactive layouts:

```json
{
  "event_namespace": "PLUGIN",
  "event_type": "UI",
  "event_version": 1,
  "payload": {
    "plugin_id": "stripe_billing_helper",
    "title": "Stripe Sync Completed",
    "layout_components": [
      {
        "type": "HEADER",
        "text": "Stripe Webhook Sync"
      },
      {
        "type": "METRIC_ROW",
        "label": "Webhooks Registered",
        "value": "12 Active"
      },
      {
        "type": "STATUS_INDICATOR",
        "state": "SUCCESS",
        "text": "All test hooks passed."
      },
      {
        "type": "BUTTON",
        "action_id": "trigger_test_webhook",
        "label": "Send Test Event"
      }
    ]
  }
}
```
The mobile client parses these standardized JSON UI descriptors and renders them natively using a modular design system, ensuring complete interface consistency across the entire ecosystem.

---

## 10. Migration & Implementation Roadmap

To transition this production specification into active service, we structure development into **8 iterative phases**, protecting current operational stability while introducing these new layers.

### Phase 1: Event Sourcing & Core DB Transition
* **Goals:** Create SQLite tables supporting event-sourcing schemas and separated conversation metadata.
* **Deliverables:**
  - Execute schema migration establishing `workspaces`, `conversations`, `conversation_memories`, `conversation_events`, and `mission_snapshots`.
  - Populate initial records and run backward-compatibility adapters mapping old `missions` feeds to basic timeline entries.
* **Verification:** Unit tests verifying relational database inserts, nested queries, and sequence-based fetching under 5ms.

### Phase 2: Handshake & Versioned REST Endpoints
* **Goals:** Deploy capability negotiation handshake and versioned REST endpoints under `/api/v1`.
* **Deliverables:**
  - Implement `POST /api/v1/handshake` logic on backend.
  - Establish `GET /api/v1/conversations/{id}` endpoints supporting `parent_only` hierarchy parsing.
* **Verification:** Simulated client handshake runs asserting correct schema and feature flag configurations.

### Phase 3: Real-Time Event Stream Routing
* **Goals:** Introduce structured WebSocket emitters using namespaces and sequence IDs.
* **Deliverables:**
  - Update background worker dispatchers to emit structured JSON events matching namespaces (e.g. `AGENT.TICK`, `MISSION.SNAPSHOT_UPDATE`).
  - Develop client-side event router in mobile Flutter codebase.
* **Verification:** Automated WebSocket subscription test suites asserting correct sub-event grouping under parent event cards.

### Phase 4: Secure QR Handshake Protocol
* **Goals:** Implement reliable, cryptographic QR Pairing between Desktop and Mobile clients.
* **Deliverables:**
  - Add Desktop interface rendering ephemeral nonces as QR codes.
  - Implement Mobile scan handlers and backend confirmation routing workflows.
* **Verification:** Handshake security verification validating correct token issuance and device authorization status in SQLite database.

### Phase 5: The AI Inbox (Tab 3 Implementation)
* **Goals:** Replace simple approvals with the comprehensive AI Inbox experience.
* **Deliverables:**
  - Implement categorized inbox list layouts natively in mobile client.
  - Embed formatted inline unified Git Diff preview viewers.
* **Verification:** Simulated human-in-the-loop approvals verifying correct event logging and system notification updates.

### Phase 6: Today Dashboard & Command Palette
* **Goals:** Build Tab 1 executive overview landing page and the global Command Palette.
* **Deliverables:**
  - Construct Today dashboard showing active crew states, pending approvals, and cost summaries.
  - Build fuzzy-matched modal dialog triggered by swipe gestures.
* **Verification:** Accessibility, touch-target, and layout validations.

### Phase 7: Sync Engine & Conflict Resolutions
* **Goals:** Ensure full operation under offline conditions with robust conflict management.
* **Deliverables:**
  - Implement outbound synchronization queues and exponential retry controllers.
  - Embed the formal conflict resolution matrix logic matching table behaviors.
* **Verification:** Integration tests simulating signal dropouts during active agent missions to verify correct "Server Wins" and "Merge" state reconciliations.

### Phase 8: Ecosystem Plugins & Extensible UI
* **Goals:** Rollout plugin contract allowing dynamic UI rendering under standard layouts.
* **Deliverables:**
  - Establish `PLUGIN.UI` JSON interpreter in Mobile UI layers.
  - Reserve namespaces across backend filters.
* **Verification:** End-to-end integration tests deploying custom third-party extensions to verify real-time layout rendering inside the companion chat canvas.
