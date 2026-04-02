## 2025-05-15 - Enhancing Agentic Feedback Loops
**Learning:** In Multi-Agent Systems like SquadOS, where backend operations (planning, hiring, execution) are asynchronous and can take time, providing immediate visual feedback during the transition from "Chat Input" to "Mission Queued" is critical. Using `st.spinner` and `st.toast` bridge the "expectancy gap" for the user.
**Action:** Always wrap mission submission or complex tool calls in visual feedback containers and use `st.toast` for non-intrusive success confirmations.

## 2025-05-15 - Descriptive Empty States
**Learning:** Plain `st.write` for empty states (e.g., "No logs found") feels unfinished and can be mistaken for a bug. Using `st.info` with context-relevant icons (🖼️, 📜, 🧠) provides a more intentional and polished UX.
**Action:** Replace all fallback "No data" messages with `st.info` and appropriate icons to guide the user.
