import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from .sql_agents import SQLAgentNodes, SQLState
from ..utils.config import MAX_FIX_RETRIES
logger = logging.getLogger(__name__)
class SQLOrchestrator:
    def __init__(self):
        self.agents = SQLAgentNodes()
        self.workflow = self._create_workflow()
    def _create_workflow(self):
        workflow = StateGraph(SQLState)
        workflow.add_node("analyze_schema", self.agents.schema_node)
        workflow.add_node("generate_sql", self.agents.sql_generator_node)
        workflow.add_node("validate_safety", self.agents.validate_node)
        workflow.add_node("execute_query", self.agents.execute_node)
        workflow.add_node("fix_query", self.agents.fix_node)
        workflow.add_node("explain_results", self.agents.explain_node)
        workflow.set_entry_point("analyze_schema")
        workflow.add_edge("analyze_schema", "generate_sql")
        workflow.add_edge("generate_sql", "validate_safety")
        workflow.add_conditional_edges(
            "validate_safety",
            self._after_validation,
            {"execute": "execute_query", "blocked": "explain_results"}
        )
        workflow.add_conditional_edges(
            "execute_query",
            self._after_execution,
            {"explain": "explain_results", "fix": "fix_query"}
        )
        workflow.add_edge("fix_query", "validate_safety")
        workflow.add_edge("explain_results", END)
        return workflow.compile()
    def _after_validation(self, state: SQLState) -> str:
        if state.get("is_safe"):
            return "execute"
        return "blocked"
    def _after_execution(self, state: SQLState) -> str:
        if not state.get("error"):
            return "explain"
        attempts = state.get("fix_attempts", 0)
        if attempts < MAX_FIX_RETRIES:
            logger.info(f"Execution failed, routing to fix (attempt {attempts + 1}/{MAX_FIX_RETRIES})")
            return "fix"
        else:
            logger.info(f"Max fix attempts ({MAX_FIX_RETRIES}) reached, giving up")
            return "explain"
    def run(self, query: str, conversation_history: list = None) -> Dict[str, Any]:
        initial_state = {
            "query": query,
            "schema": "",
            "sql_query": "",
            "is_safe": False,
            "safety_reason": "",
            "data_result": "",
            "error": "",
            "final_answer": "",
            "fix_attempts": 0,
            "conversation_history": conversation_history or [],
            "execution_time_ms": 0.0
        }
        logger.info(f"SQL Agent query: {query}")
        result = self.workflow.invoke(initial_state)
        return result
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    orchestrator = SQLOrchestrator()
    print("SQL Intelligence Graph compiled successfully!")
    print("Nodes:", list(orchestrator.workflow.get_graph().nodes.keys()))
