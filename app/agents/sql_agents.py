import json
import logging
import time
from typing import Dict, Any, TypedDict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..database.sqlite_manager import SQLiteManager
from ..utils.safety import validate_sql
from ..utils.config import GROQ_API_KEY, LLM_MODEL, GROQ_BASE_URL, MAX_FIX_RETRIES
logger = logging.getLogger(__name__)
class SQLState(TypedDict):
    query: str
    schema: str
    sql_query: str
    is_safe: bool
    safety_reason: str
    data_result: str
    error: str
    final_answer: str
    fix_attempts: int
    conversation_history: List[Dict]
    execution_time_ms: float
class SQLAgentNodes:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=GROQ_API_KEY,
            openai_api_base=GROQ_BASE_URL,
            temperature=0.1,
        )
        self.db = SQLiteManager()
    def schema_node(self, state: SQLState) -> Dict[str, Any]:
        if state.get("schema"):
            logger.info("Schema already cached, skipping fetch")
            return {}
        logger.info("Fetching database schema...")
        schema = self.db.get_schema()
        return {"schema": schema}
    def sql_generator_node(self, state: SQLState) -> Dict[str, Any]:
        logger.info(f"Generating SQL for: {state['query']}")
        history_context = ""
        if state.get("conversation_history"):
            recent = state["conversation_history"][-5:]
            history_context = "Previous questions in this session:\n"
            for h in recent:
                history_context += f"Q: {h.get('question', '')}\nSQL: {h.get('sql', '')}\n\n"
        prompt = ChatPromptTemplate.from_template(
            "You are a SQL expert. Generate a READ-ONLY SELECT query for the question.\n\n"
            "Database schema:\n{schema}\n\n"
            "{history}"
            "Question: {query}\n\n"
            "Rules:\n"
            "- ONLY generate SELECT queries (no INSERT, UPDATE, DELETE, DROP)\n"
            "- Use the exact table and column names from the schema\n"
            "- If the question references a previous query, use the conversation history\n"
            "- Return ONLY the raw SQL query, no explanation or markdown\n"
        )
        response = (prompt | self.llm).invoke({
            "schema": state["schema"],
            "query": state["query"],
            "history": history_context
        })
        sql = response.content.strip()
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[1] if "\n" in sql else sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip().strip("`").strip()
        logger.info(f"Generated SQL: {sql[:100]}...")
        return {"sql_query": sql}
    def validate_node(self, state: SQLState) -> Dict[str, Any]:
        logger.info("Validating SQL safety...")
        is_safe, reason = validate_sql(state["sql_query"])
        if not is_safe:
            logger.warning(f"SQL BLOCKED: {reason}")
        else:
            logger.info("SQL validation passed")
        return {"is_safe": is_safe, "safety_reason": reason}
    def fix_node(self, state: SQLState) -> Dict[str, Any]:
        attempt = state.get("fix_attempts", 0) + 1
        logger.info(f"Fix attempt {attempt}/{MAX_FIX_RETRIES}")
        prompt = ChatPromptTemplate.from_template(
            "The following SQL query failed with an error. Fix it.\n\n"
            "Original question: {query}\n"
            "Schema:\n{schema}\n\n"
            "Failed SQL:\n{sql}\n\n"
            "Error: {error}\n\n"
            "Generate a corrected SELECT query. Return ONLY the SQL, no explanation."
        )
        response = (prompt | self.llm).invoke({
            "query": state["query"],
            "schema": state["schema"],
            "sql": state["sql_query"],
            "error": state.get("error", "Unknown error")
        })
        fixed_sql = response.content.strip().strip("`").strip()
        if fixed_sql.startswith("```"):
            fixed_sql = fixed_sql.split("\n", 1)[1] if "\n" in fixed_sql else fixed_sql[3:]
        if fixed_sql.endswith("```"):
            fixed_sql = fixed_sql[:-3]
        fixed_sql = fixed_sql.strip()
        return {"sql_query": fixed_sql, "fix_attempts": attempt, "error": ""}
    def execute_node(self, state: SQLState) -> Dict[str, Any]:
        if not state.get("is_safe"):
            return {
                "error": f"Query blocked by safety checker: {state.get('safety_reason', 'Unknown')}",
                "data_result": "",
                "final_answer": f"I can't run that query. {state.get('safety_reason', 'Safety check failed.')}"
            }
        logger.info("Executing SQL query...")
        start_time = time.time()
        try:
            df = self.db.execute_query(state["sql_query"])
            execution_time = (time.time() - start_time) * 1000
            if df is None or df.empty:
                return {
                    "data_result": "No results found.",
                    "error": "",
                    "execution_time_ms": execution_time
                }
            result_str = df.to_string(index=False, max_rows=20)
            result_json = df.head(50).to_json(orient="records")
            logger.info(f"Query returned {len(df)} rows in {execution_time:.1f}ms")
            return {
                "data_result": result_str,
                "error": "",
                "execution_time_ms": execution_time
            }
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"SQL execution error: {e}")
            return {
                "error": str(e),
                "data_result": "",
                "execution_time_ms": execution_time
            }
    def explain_node(self, state: SQLState) -> Dict[str, Any]:
        if state.get("error") and not state.get("data_result"):
            if state.get("fix_attempts", 0) >= MAX_FIX_RETRIES:
                return {
                    "final_answer": f"I couldn't generate a valid query for your question after {MAX_FIX_RETRIES} attempts. Error: {state['error']}"
                }
            return {"final_answer": f"Error: {state['error']}"}
        if not state.get("data_result") or state["data_result"] == "No results found.":
            return {"final_answer": "The query returned no results. Try rephrasing your question or checking the data."}
        logger.info("Explaining results...")
        prompt = ChatPromptTemplate.from_template(
            "Explain these database results for the original question.\n\n"
            "Question: {query}\n"
            "SQL used: {sql}\n"
            "Results:\n{data}\n\n"
            "Provide a clear, professional summary of the findings. "
            "Include specific numbers from the data."
        )
        response = (prompt | self.llm).invoke({
            "query": state["query"],
            "sql": state["sql_query"],
            "data": state["data_result"][:3000]
        })
        history = state.get("conversation_history", [])
        history.append({
            "question": state["query"],
            "sql": state["sql_query"],
            "answer_preview": response.content[:200]
        })
        return {
            "final_answer": response.content,
            "conversation_history": history
        }
