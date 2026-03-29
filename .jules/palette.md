## 2026-03-29 - [Timestamp Formatting and Sidebar Context]
**Learning:** In technical dashboards like SquadOS, raw ISO timestamps in logs can create visual clutter and cognitive load. Providing tooltips for primary navigation (the Branch Explorer) significantly helps new users understand the context of the actions they are about to take.
**Action:** Always format ISO timestamps into a human-readable `HH:MM:SS` format for live log views, and use `st.button`'s `help` parameter to add accessible, hoverable context to navigation elements.
