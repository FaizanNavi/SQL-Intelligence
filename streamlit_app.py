import streamlit as st
import requests

st.set_page_config(page_title="SQL Intelligence Agent", page_icon="🗄️", layout="wide")
st.title("🗄️ SQL Intelligence Agent")
st.markdown("Ask questions in plain English — the agent generates SQL, validates safety, executes, and explains the results.")

BACKEND = "http://127.0.0.1:8008"

with st.sidebar:
    st.header("🔒 Safety Features")
    st.markdown("""
- Blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`
- Only allows `SELECT` queries
- Auto-fixes failed SQL (up to 3 retries)
    """)
    st.divider()
    st.header("📋 Database Schema")
    if st.button("Load Schema", use_container_width=True):
        try:
            res = requests.get(f"{BACKEND}/schema", timeout=10)
            if res.status_code == 200:
                st.code(res.json().get("schema", ""), language="sql")
        except Exception:
            st.error("Cannot connect to backend.")
    st.divider()
    st.header("💡 Example Questions")
    examples = [
        "What are total sales by country?",
        "Who is the top salesperson by profit?",
        "Show me all Dark Chocolate sales",
        "What is the average revenue per product?",
        "Which country has the highest profit margin?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=ex):
            st.session_state.prefill = ex

if "messages" not in st.session_state:
    st.session_state.messages = []
if "prefill" not in st.session_state:
    st.session_state.prefill = ""

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg and msg["sql"]:
            with st.expander("🔍 SQL Generated"):
                st.code(msg["sql"], language="sql")
                meta = msg.get("meta", {})
                col1, col2 = st.columns(2)
                col1.metric("Execution Time", f"{meta.get('time', 0):.1f}ms")
                col2.metric("Was Safe", "✅" if meta.get("safe") else "❌")

prompt = st.chat_input("Ask a question about the data...")
if st.session_state.prefill and not prompt:
    prompt = st.session_state.prefill
    st.session_state.prefill = ""

if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    try:
        with st.spinner("Generating & executing SQL..."):
            res = requests.post(f"{BACKEND}/query", json={"question": prompt, "session_id": "streamlit"}, timeout=60)
        if res.status_code == 200:
            data = res.json()
            answer = data.get("answer", "No answer generated.")
            sql = data.get("sql_generated", "")
            exec_time = data.get("execution_time_ms", 0)
            safe = data.get("was_safe", False)
            fix_attempts = data.get("fix_attempts", 0)
            with st.chat_message("assistant"):
                st.markdown(answer)
                with st.expander("🔍 SQL & Execution Details"):
                    st.code(sql, language="sql")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Execution Time", f"{exec_time:.1f}ms")
                    col2.metric("Safe Query", "✅" if safe else "❌ Blocked")
                    col3.metric("Fix Attempts", fix_attempts)
            st.session_state.messages.append({
                "role": "assistant", "content": answer,
                "sql": sql, "meta": {"time": exec_time, "safe": safe}
            })
        else:
            st.error(f"Backend error {res.status_code}: {res.text}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Is `uvicorn app.main:app --port 8008` running?")
    except Exception as e:
        st.error(f"Error: {e}")
