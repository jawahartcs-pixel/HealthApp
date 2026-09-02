---
name: Streamlit preview cache
description: Why Streamlit previews can show hashed JavaScript import failures after restarts or long inactive sessions.
---

Streamlit serves hashed JavaScript bundles with long-lived public caching. After a restart or an inactive preview session, the browser can retain an older bundle reference and report a failed dynamic import even when the referenced files are healthy.

**Why:** The server can remain healthy, return HTTP 200 for the root and every referenced chunk, while the browser session still has a stale module/WebSocket state.

**How to apply:** Keep Streamlit dependency resolution out of the run command, restart the workflow once, and have the user close/reopen or hard-refresh the preview so the root HTML and module graph are fetched as one consistent set.