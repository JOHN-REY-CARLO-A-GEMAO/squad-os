# Squad OS Mobile Remote Companion App: Version 2 Architecture & Product Design Blueprint

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
3. **One-Handed Actionability (HITL):** Key human decisions—such as reviewing code changes, validating test passes, and confirming risky deployments—are packaged as swipeable, tap-friendly interactive approval cards requiring minimal typing.
4. **Instant Shared Context:** Every interaction, workspace context chip, and shared memory automatically synchronizes between mobile devices and the desktop control center, establishing a seamless loop of continuous work.

---

## 2. Information & State Hierarchy

To support a project-centric design, the mobile application moves away from flat chat history and adopts a robust hierarchical workspace structure similar to Claude Projects.

```
Workspace (Project Container)
   └── Conversation
           └── Context Memory & Context Chips
           └── Unified Event Timeline
                   ├── Messages (User Prompt / Assistant Response)
                   ├── AI Session Card (Live WebSocket state card)
                   ├── Agent Stream (Dynamic agent execution feedback)
                   ├── Mission Event (Started, Completed, Failed milestones)
                   ├── Approval Event (Interactive HITL decision cards)
                   ├── File Upload / Attachment (Developer-focused media)
                   └── System Notification (Out-of-band alerts)
```

### Architectural Components
* **Workspace:** Represents a logical boundaries or repository context (e.g., `Mobile App`, `SquadOS Backend`, `AI Research`). Conversations belong strictly to a Workspace.
* **Conversation:** A persistent channel of coordination. Unlike simple chats, conversations hold active context memory which guides all future prompts sent within that thread.
* **Context Memory:** A set of persistent variables (Active Branch, Environment, Preferred Framework, Target Goal, System Constraints) attached directly to the Conversation and editable via Context Chips.
* **Unified Event Timeline:** A chronological stream where all forms of interaction (messages, logs, errors, attachments, system events, and task transitions) are merged into a single scrollable feed.

---

## 3. Database Architecture & Schema Extensions

To support the V2 architecture while preserving backward compatibility with the existing `missions`, `tasks`, and `approvals` tables, we extend the database using a set of relational tables. This schema ensures a conversation-first representation without disrupting desktop background workers.

```
   +-------------------+              +----------------------+
   |    workspaces     |              |     conversations    |
   |-------------------|              |----------------------|
   | id (PK)           |1           * | id (PK)              |
   | name              |------------->| workspace_id (FK)    |
   | description       |              | title                |
   | created_at        |              | context_memory_json  |
   +-------------------+              +----------------------+
                                                 |
                                                 | 1
                                                 |
                                                 v *
                                      +----------------------+
                                      |  conversation_events |
                                      |----------------------|
                                      | id (PK)              |
                                      | conversation_id (FK) |
                                      | event_type           |
                                      | payload_json         |
                                      | created_at           |
                                      | mission_id (FK, Opt) |
                                      +----------------------+
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

-- 2. Conversations Table (Supports Persistent Context Memory)
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    context_memory_json TEXT DEFAULT '{}', -- JSON containing Active Branch, Environment, Constraints, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

-- Indexing for fast workspace-to-conversations retrieval
CREATE INDEX IF NOT EXISTS idx_conversations_workspace_id ON conversations(workspace_id);

-- 3. Conversation Events Table (The Chronological Unified Timeline)
CREATE TABLE IF NOT EXISTS conversation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    event_type TEXT NOT NULL, -- 'MESSAGE', 'MISSION_EVENT', 'APPROVAL_EVENT', 'NOTIFICATION', 'FILE_UPLOAD', 'VOICE_MESSAGE', 'SYSTEM_EVENT'
    payload_json TEXT NOT NULL, -- Contains fields specific to the event type
    mission_id INTEGER, -- Optional foreign key connecting this timeline event to the running mission
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_events_conversation_id ON conversation_events(conversation_id);
CREATE INDEX IF NOT EXISTS idx_events_mission_id ON conversation_events(mission_id);

-- 4. Devices Table (Push Notification Support)
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default_user',
    push_token TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL, -- 'ios' or 'android'
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Notifications Table
CREATE TABLE IF NOT EXISTS system_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    deep_link TEXT, -- e.g., 'squados://conversations/14?event_id=102'
    status TEXT DEFAULT 'PENDING', -- 'PENDING', 'SENT', 'FAILED'
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);
```

---

## 4. REST & WebSocket API Specification

### 4.1 REST API Endpoints

#### 1. List Workspaces with Nesting
* **Endpoint:** `GET /api/v1/workspaces`
* **Response:**
```json
{
  "workspaces": [
    {
      "id": 1,
      "name": "Mobile App Backend",
      "description": "Flutter mobile repository and Supabase backend",
      "created_at": "2026-05-10T08:00:00Z",
      "conversations_count": 3
    }
  ]
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
      "context_memory": {
        "framework": "Flutter",
        "database": "Supabase",
        "branch": "feature/auth",
        "goal": "Refactor authentication to secure JWT",
        "preferences": "Use Riverpod, no Provider patterns"
      },
      "last_event_at": "2026-05-15T14:32:00Z"
    }
  ]
}
```

#### 3. Fetch Unified Timeline (Conversation Details)
* **Endpoint:** `GET /api/v1/conversations/{id}`
* **Query Parameters:** `limit` (int, default: 50), `cursor` (string, optional - for pagination)
* **Response:**
```json
{
  "conversation_id": 14,
  "workspace_id": 1,
  "title": "JWT Auth Migration",
  "context_memory": {
    "framework": "Flutter",
    "branch": "feature/auth",
    "goal": "Refactor authentication"
  },
  "events": [
    {
      "id": 101,
      "event_type": "MESSAGE",
      "created_at": "2026-05-15T14:30:00Z",
      "payload": {
        "role": "user",
        "content": "Add verification helper to auth_service.dart."
      }
    },
    {
      "id": 102,
      "event_type": "MISSION_EVENT",
      "mission_id": 91,
      "created_at": "2026-05-15T14:30:15Z",
      "payload": {
        "status": "STARTED",
        "goal": "Add verification helper to auth_service.dart",
        "message": "Assistant spawned Mission #91 to refactor auth_service.dart."
      }
    },
    {
      "id": 103,
      "event_type": "APPROVAL_EVENT",
      "mission_id": 91,
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
* **Endpoint:** `PUT /api/v1/conversations/{id}/context`
* **Request:**
```json
{
  "context_memory": {
    "framework": "Flutter",
    "branch": "feature/jwt-refresh",
    "goal": "Secure session handling",
    "preferences": "Prefer JWT secure storage over standard shared_preferences"
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
    "goal": "Secure session handling",
    "preferences": "Prefer JWT secure storage over standard shared_preferences"
  }
}
```

#### 5. Submit Message / Unified Prompt
* **Endpoint:** `POST /api/v1/conversations/{id}/messages`
* **Request (Multipurpose Form Data for Text, Voice, or Code attachments):**
```json
{
  "content": "Incorporate OTP login validation inside auth_service.dart",
  "attachment": {
    "type": "CODE_SNIPPET",
    "name": "otp_handler.dart",
    "payload": "class OtpValidator { bool verify(String code) { return code == '123456'; } }"
  }
}
```
* **Response:**
```json
{
  "routing_decision": "SPAWN_MISSION",
  "message": "Understood. Starting Mission #92 to integrate OTP validation.",
  "mission_id": 92,
  "conversation_event_id": 104
}
```

#### 6. Universal Conversation Search
* **Endpoint:** `GET /api/v1/conversations/{id}/search`
* **Query Parameters:** `q` (string, required), `filter_type` (string, optional - e.g., 'MESSAGES', 'MISSIONS', 'FILES', 'ERRORS')
* **Response:**
```json
{
  "query": "JWT",
  "results": [
    {
      "event_id": 103,
      "event_type": "APPROVAL_EVENT",
      "matched_snippet": "...review the **JWT** verification key rotation mechanism...",
      "timestamp": "2026-05-15T14:31:45Z"
    }
  ]
}
```

---

### 4.2 WebSocket Event Streams

Clients maintain a single persistent WebSocket connection per active session: `ws://<host>:<port>/api/v1/streams?conversation_id={id}`. This connection delivers real-time timeline modifications and fine-grained agent activity.

#### 1. AI Session Card Update
Pushed immediately whenever the high-level mission state changes, including thoughts and expected timelines.
```json
{
  "event_type": "SESSION_CARD_UPDATE",
  "payload": {
    "mission_id": 91,
    "goal": "Refactor authentication to secure JWT",
    "status": "IN_PROGRESS",
    "progress_percent": 75,
    "elapsed_time_seconds": 322,
    "remaining_time_seconds": 120,
    "latest_thought": "I detected a missing validation boundary for access token expiry inside auth_service.dart. I will write a custom verification wrapper.",
    "next_planned_action": "Updating validation wrappers and executing the Flutter test suite.",
    "awaiting_approval": false
  }
}
```

#### 2. Fine-Grained Agent Activity Stream (Agent Streaming)
Pushed frequently (e.g., every 500ms - 1s) while an active agent is modifying code, inspecting files, or compiling.
```json
{
  "event_type": "AGENT_STREAM_TICK",
  "payload": {
    "mission_id": 91,
    "agent_role": "CoderAgent",
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

The application adopts an accessible, high-contrast, clutter-free **3-Tab Navigation Architecture** with contextual overlays.

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

### 1. Chat Tab (The Project Canvas)
* **Editable Context Chips (Top):** Horizontal list of tags (`Flutter`, `feature/auth`, `Supabase`, `Riverpod`). Tapping any tag displays an inline overlay with quick dropdowns and text inputs to modify the conversation's active memory.
* **Unified Scroll Feed:** Messages, system logs, code snippets, git diffs, and milestones populate chronologically.
* **Inline AI Session Card:** When a mission runs, a floating or anchored card highlights the active crew. It shows:
  - Estimated Time of Arrival (ETA) with a circular progress indicator.
  - Expandable Agent Stream panel (collapsing developer noise into clean, bite-sized ticks).
* **Smart Contextual Quick Actions (Bottom):** Context-aware pill-buttons appearing above the text input after events (e.g. `Retry`, `Explain Failure`, `Summarize Output`, `Run Tests`, `Open Desktop`, `Deploy`).
* **Input Gateway:** Multi-attachment selector (`+` icon) supporting camera, gallery, standard documents, code snippets, git diffs, stack traces, and markdown text alongside a hold-to-record voice gateway.

### 2. Approvals Tab (Interactive HITL Inbox)
* **Single-Card Execution Focus:** High-contrast queue of items requiring developer clearance. Each approval card uses green/primary styles for "Approve", orange/secondary for "Request Adjustments", and includes a direct input field for optional natural language guidance.
* **Context-First Preview:** Tapping an approval reveals an inline expander showing the exact git diff (collapsible) or file modifications proposed, keeping reviews lightweight yet secure.

### 3. Settings Tab (Administration & Synchronization)
* **Desktop Coordination Profiles:** Quick configurations for active environments, pairing codes, and backend instances.
* **Ecosystem Store Administration:** Lists active installed packages (`.sqad` modules), system statistics (token usage, execution cost), and offline sync diagnostic utilities.

---

## 6. Comprehensive Feature Specifications

### 6.1 Conversational Projects & Workspaces
Instead of treating conversations as a flat, chronological feed of historical actions, conversations are logically organized under Workspaces.
* **Structure:** A slider-drawer from the left (accessible via `[=]` hamburger or slide swipe) allows swapping between active projects (e.g., `Mobile App`, `Main Core`). Swapping workspaces immediately updates the conversation feed and context memory active on screen.
* **Hierarchy Display:**
```
📂 MOBILE APP
  • JWT Auth Migration (Active ⚡)
  • Payments Integration (Idle)
📂 SQUAD OS CORE
  • Secure Sandboxing (Active ⚡)
```

### 6.2 Conversation Timeline (Unified Event Stream)
Every element in the timeline is an event. To avoid visual cognitive fatigue, events have highly distinct, card-based designs:
* **User Messages:** Right-aligned, dark/primary background, highlighting attached files or transcribed voice records.
* **Assistant Responses:** Left-aligned, light grey background, utilizing standard Markdown styling.
* **Mission Milestones:** Anchored, center-aligned, border-accented cards showing state changes (e.g., `[⚡] Mission #91 Started`, `[✅] Mission #91 Completed`).
* **Approval Actions:** Chronologically inserted approval requests which freeze conversation input until answered, providing immediate continuity.

### 6.3 Live Agent Stream
Visualizes developer micro-activity in real time:
* **UI Behavior:** A miniature panel within the active AI Session Card displays current agent activity.
* **State Visualization:**
  - **Planner:** `Done (14s)`
  - **Researcher:** `Done (42s)`
  - **Coder:** `Running ⚡ Editing auth_service.dart (line 112)`
  - **Tester:** `Waiting`
* When an agent updates a file or runs an execution loop, the stream displays temporary text ticks (e.g. `[Compiler] Successfully compiled lib/services/auth_service.dart in 450ms`, `[Test Engine] 12/14 test cases passed`). This mimics an active developer terminal but filters out verbose environment noise.

### 6.4 Conversation Memory (Claude-style Projects)
Conversations maintain persistent key-value parameters:
* **Environment:** `Flutter (Dart 3.3.0)`
* **Active Branch:** `feature/jwt-validation`
* **Goal:** `Incorporate secure token claims handling`
* **User Preferences:** `Do not use legacy provider classes. Use modern Riverpod structures.`
* **Implementation:** These memory keys are added as hidden instructions to every conversational prompt sent to the model behind `/api/v1/messages`, ensuring the developer's contextual specifications are remembered from the first message through implementation.

### 6.5 Interactive Attachments Selector
The `+` drawer opens an expandable tray supporting diverse assets:
* **Developer Asset Handling:**
  - **Code Snippet:** Includes language-specific syntax highlighting and formatting.
  - **Git Diff:** Parses files into red/green unified formats, allowing scrollable, side-by-side verification before sending.
  - **Stack Trace:** Highlights key execution files and packages involved in crashes, automatically omitting standard environment library frames.
  - **Terminal Logs:** Highlights error bounds and warning segments.

### 6.6 Custom Context Chips
* **Visual Representation:** Positioned at the header of the chat, these horizontal capsules display primary memory values:
  `[ 🌿 feature/jwt ]  [ 📱 Flutter ]  [ ☁️ Supabase ]`
* **Interaction:** Tapping any chip opens a sliding sheet from the bottom, allowing developers to change the active branch, environment variables, or goal specifications on-the-fly. This instantly triggers a `PUT /api/v1/conversations/{id}/context` call, reflecting adjustments in future mission prompts.

### 6.7 Contextual Quick Actions
Contextual buttons appear dynamically above the chat box to accelerate inputs:
* **Mission Failed:** `[ 🔄 Retry Execution ]  [ ❓ Explain Failure ]  [ 🔎 Analyze Log ]`
* **Mission Succeeded:** `[ 🚀 Deploy Staging ]  [ 🖥️ Open Desktop ]  [ 📝 Summarize Changes ]`
* **Awaiting Review:** `[ ✅ Approve All ]  [ ❌ Reject & Fix ]`

### 6.8 Seamless Desktop Handoff
Provides unified state transition coordination between mobile and desktop devices.
* **Handoff Mechanism:** When viewing an active conversation on a mobile client, tapping `[🖥️ Open Desktop]` triggers a localized handoff protocol.
* **The Handoff Sequence:**
  1. Mobile client dispatches handoff request containing `workspace_id`, `conversation_id`, and `mission_id` to the coordinator.
  2. The coordinator validates the developer's credentials.
  3. The coordinator broadcasts a secure handoff event via Local WebSockets or shared SQLite databases.
  4. The Desktop Dashboard automatically focuses, bringing the identical Workspace, Conversation context, Live logs, DAG workflow diagrams, and code preview to the user's primary monitor.

### 6.9 Live Activities & OS-Level Updates
Enables real-time mission monitoring from outside the companion app.
* **Dynamic Island (iOS):** Displays compact agent execution indicators: `[⚡] Auth Coder: auth_service.dart`.
* **Lock Screen / Live Activity (iOS & Android Notification):**
  - Displays Mission Goal and high-level progress (e.g., `Progress: [████████░░] 80%`).
  - Active Step indicator: `Coder is validating secure token cookies`.
  - Simple action buttons: `[ Pause ]  [ View Details ]`.

### 6.10 Universal Timeline Search
* **Capabilities:** Search handles free-text parsing across messages, file names, approvals, logs, and errors.
* **UX Flow:** Tapping the search icon at the top of the conversation opens an overlays bar. Search results highlight matched occurrences (e.g., matching the word "JWT" in code segments, chat messages, or task logs) and allow immediate timeline jump-scroll.

### 6.11 Resilient Offline Mode
To protect productivity during connectivity drops:
* **Caching Layer:** Local SQLite database caches the conversation timelines, context parameters, pending approvals, and assets locally.
* **Outbound Message Queue:** When connection is lost, messages are held in a pending state locally with a `⏳` icon.
* **Automatic Re-synchronization:** Once connectivity is restored, the mobile companion dispatches the pending queue sequentially, applies an active clock-skew synchronization pattern, and prompts conflict resolutions if shared resources were modified out-of-sync.

---

## 7. Comprehensive Mockups & Conversational Timelines

### Unified Conversation Timeline with AI Session Card

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
|                                                             |
|  Planner    ✓ Understanding boundaries                       |
|  Researcher ✓ Analyzing security patterns                   |
|  Coder      ⚡ Editing: lib/services/auth_service.dart       |
|  Tester     ○ Waiting                                       |
|                                                             |
|  Latest Thought: "Detected a missing validation helper for  |
|  access tokens in JWT parser. Writing test cases now."      |
|  Next Action: "Run local unit tests."                       |
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
|       Chat              Approvals              Settings     |
+-------------------------------------------------------------+
```

### Context Editing Sheet (Bottom Slide-out)

```
+-------------------------------------------------------------+
|                                                             |
|                      Edit Context                           |
|                                                             |
|  Active Branch                                              |
|  [ feature/jwt-refresh                                 ]   |
|                                                             |
|  Target Environment                                         |
|  [ Supabase / Flutter Production                       ]   |
|                                                             |
|  Implementation Constraints                                 |
|  (e.g., Do not use Provider classes)                        |
|  +-------------------------------------------------------+  |
|  | Prefer JWT secure storage over standard               |  |
|  | shared_preferences. Keep dependencies lightweight.   |  |
|  +-------------------------------------------------------+  |
|                                                             |
|                     [ 💾 Apply Changes ]                     |
+-------------------------------------------------------------+
```

### Mobile Developer Attachments Selector

```
+-------------------------------------------------------------+
|                                                             |
|  Select Developer Attachment                                |
|                                                             |
|  [📷 Camera]        [🖼️ Gallery]       [📁 Standard Files]  |
|  [📋 Clipboard]     [🎤 Voice Record]  [📦 ZIP Archive]     |
|  [💻 Code Snippet]  [➕ Git Diff]       [⚠️ Stack Trace]      |
|                                                             |
+-------------------------------------------------------------+
```

### High-Contrast Approvals Card

```
+-------------------------------------------------------------+
|  Approvals Queue                                        [1] |
+-------------------------------------------------------------+
|  CARD 1 OF 1                                                |
|  Mission: #91 Refactor Authentication                       |
|  Requested by: CoderAgent                                   |
|                                                             |
|  ⚠️ ACTION REQUIRED                                         |
|  "The team wants to delete 48 obsolete security config      |
|   templates from the workspace."                            |
|                                                             |
|  +-------------------------------------------------------+  |
|  | 📂 View Proposed Deletion Diff (48 files)         [v] |  |
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
|       Chat             [Approvals]             Settings     |
+-------------------------------------------------------------+
```

---

## 8. Migration & Implementation Roadmap

To transition the mobile companion design into a production specification, we organize development into **8 iterative, product-maturity-driven phases**. This avoids breaking current backend tasks while sequentially unlocking features.

### Phase 1: Conversation Foundation
* **Goals:** Create database extensions for conversations, timelines, and basic endpoints while ensuring the backend supports core routing.
* **Deliverables:**
  - Establish SQLite schema changes (`workspaces`, `conversations`, `conversation_events`).
  - Implement basic REST API CRUD endpoints (`/conversations` list, retrieve details, and post prompts).
  - Modify backend task managers to hook conversational milestones.
* **Dependencies:** None.
* **Risks:** Database migrations locking SQLite files during intensive runs.
* **Success Criteria:** Retrieve a complete chronologically-ordered conversation history from the database in <10ms.

### Phase 2: Workspace Architecture
* **Goals:** Create logical workspace boundary layers and group conversations cleanly.
* **Deliverables:**
  - Deploy `workspaces` table and relations.
  - Implement side-drawer navigation on mobile to swap workspaces.
  - Build workspace API endpoints (`GET /api/v1/workspaces`).
* **Dependencies:** Phase 1 complete.
* **Risks:** Unassociated historical conversation threads losing structural grouping.
* **Success Criteria:** Swap workspaces, bringing the correct workspace-specific conversations and context models to the active viewport immediately.

### Phase 3: Live Agent Streams
* **Goals:** Establish granular agent-tick WebSocket events to visualize actions dynamically.
* **Deliverables:**
  - Build a centralized streaming coordinator on the backend to publish task transitions.
  - Expose the agent ticks payload over WebSocket paths.
  - Implement the UI agent-activity panel highlighting currently active steps and logs.
* **Dependencies:** Phase 1 WebSocket routing.
* **Risks:** High network overhead on mobile cellular connections due to verbose streams.
* **Success Criteria:** Throttle agent updates to a maximum of 1 update per 500ms while maintaining clear live telemetry on the mobile client.

### Phase 4: Approvals
* **Goals:** Redesign Human-In-The-Loop actions into accessible, single-thumb execution cards.
* **Deliverables:**
  - Create high-contrast approval components.
  - Link approvals to the unified conversation event timeline.
  - Deploy `/api/v1/approvals` GET queues and action endpoints.
* **Dependencies:** Phase 1 event stream database representation.
* **Risks:** Blocking execution flows if the user closes the app during a critical action.
* **Success Criteria:** Trigger a notification, tap, review diffs, and approve an action in less than 3 taps.

### Phase 5: Offline Sync
* **Goals:** Build local client synchronization strategies to manage intermittent cellular signals.
* **Deliverables:**
  - Build local caching mechanisms (local SQLite or key-value stores) in Flutter.
  - Build outbound offline queues tracking pending actions and uploads.
  - Implement background synchronizers with automatic re-try logic.
* **Dependencies:** Phase 1 and 4 APIs.
* **Risks:** Sync conflicts if files are modified on desktop while mobile is offline.
* **Success Criteria:** Ensure the client remains fully responsive during simulated airplane mode and auto-sends messages upon network re-establishment.

### Phase 6: Desktop Handoff
* **Goals:** Build seamless continuous coordination between active devices.
* **Deliverables:**
  - Build handoff APIs accepting destination contexts.
  - Implement the pairing protocols and URL schemes (`squados://`).
  - Write coordinator handlers in desktop Streamlit / FastAPI layers to automatically focus on matching files, terminal outputs, and DAGs.
* **Dependencies:** Phase 1 databases.
* **Risks:** Security vulnerabilities if paired tokens or WebSocket handoffs are intercepted on local networks.
* **Success Criteria:** Tap "Open Desktop" on mobile, and watch the matching workspace, logs, and files open on the workstation in <1.5s.

### Phase 7: Voice
* **Goals:** Implement Hold-to-Record voice inputs for fast coordination.
* **Deliverables:**
  - Build hold-to-record voice buttons in the companion input.
  - Integrate backend Whisper translation pipelines to process transcription.
  - Deliver transcribed text as a standard message inside `/api/v1/messages`.
* **Dependencies:** Phase 1.
* **Risks:** High audio latency or noisy transcription on low-quality microphones.
* **Success Criteria:** Record a 10-second command, compile transcription, and dispatch a mission successfully with a clean user experience.

### Phase 8: Widgets, Wear OS, Dynamic Island
* **Goals:** Create system-level widgets, lock screen updates, and Apple Watch / Wear OS micro-interfaces.
* **Deliverables:**
  - Build Android and iOS homescreen widgets highlighting active mission progress.
  - Implement Apple Dynamic Island & Live Activities structures.
  - Develop Wear OS micro-apps displaying active agent lists and quick approval buttons.
* **Dependencies:** Phase 3 WebSocket updates.
* **Risks:** High OS-level background battery drain on mobile systems.
* **Success Criteria:** View live mission percentage and the currently running agent directly from the mobile lock screen without opening the app.
