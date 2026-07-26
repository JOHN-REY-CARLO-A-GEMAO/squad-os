# API Guidelines & Specification — Squad OS

This document covers the high-level API design philosophy, versioning rules, authentication flows, and real-time communication standards for the Squad OS ecosystem.

---

## 1. API Design Philosophy

Squad OS APIs are designed with the following principles:
* **Stateless REST Operations:** Resource management, system metadata configurations, and background checks are performed over standard, versioned HTTP endpoints.
* **Stream-Based Event Delivery:** All active mission progressions, raw agent thinking ticks, and notifications are streamed in real time over low-overhead WebSockets.
* **Idempotency by Default:** Any transaction-altering client write command must submit a unique UUID `request_id` to prevent duplicate operations in unreliable networking environments.

---

## 2. API Versioning Strategy

To evolve endpoints and database contracts independently of client applications (desktop, CLI, or mobile):
1. **URI Versioning:** All endpoints are explicitly versioned in the URI using a `/v1/` prefix (e.g., `/api/v1/handshake`).
2. **Capability Negotiation:** During the initial client-server handshake, clients and servers negotiate supported feature flags and protocol behaviors, allowing backward and forward compatibility.
3. **Payload Schema Versioning:** Every structured event in our system contains a `payload_schema_version` column to indicate the structure of its nested payload data, enabling older events to be processed correctly.

---

## 3. Real-Time WebSocket Standards

WebSockets maintain persistent bi-directional communication channels.
* **Routing:** Subscriptions are conversation-specific (e.g., `ws://<host>:<port>/api/v1/streams?conversation_id={id}`).
* **Ordering Guarantee:** Every message streamed over WebSockets contains a sequence ID. Clients can detect missed packets and request replays deterministically.

---

## 4. Mobile Companion Endpoint Reference

Detailed payload specifications, API handshake routes, unified timeline structures, WebSocket update streams, QR pairing handshakes, and event namespace assignments are fully detailed inside the main blueprint document:

👉 **[docs/MOBILE_REMOTE_COMPANION_PLAN.md](docs/MOBILE_REMOTE_COMPANION_PLAN.md)**
