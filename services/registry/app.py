"""Telemetry dashboard. Stores hashes and tag codes. Never content."""
import sqlite3
import streamlit as st

st.set_page_config(page_title="AITrust-ID Registry", layout="wide")
st.title("AITrust-ID Registry")
st.caption("Hashes and tag codes only. No prompts, no outputs, no user identifiers.")

db = sqlite3.connect("/data/registry.db", check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS assertions (
    id TEXT PRIMARY KEY, sha256 TEXT, origin_host TEXT, captured_at TEXT,
    tags TEXT, abstentions TEXT, latency_ms REAL)""")

rows = db.execute("SELECT captured_at, origin_host, tags, latency_ms "
                  "FROM assertions ORDER BY captured_at DESC LIMIT 500").fetchall()
if rows:
    st.dataframe(rows, use_container_width=True)
else:
    st.info("No assertions recorded yet. Retention default is 30 days.")
