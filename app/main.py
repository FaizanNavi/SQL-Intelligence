import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from .agents.orchestrator import SQLOrchestrator
from .utils.config import HOST, PORT
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
app = FastAPI(
    title="SQL Intelligence Agent",
    description="Natural language → SQL → validate → execute → explain",
    version="1.0.0"
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
orchestrator = SQLOrchestrator()
sessions: Dict[str, list] = {}
class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question about the data")
    session_id: Optional[str] = Field("default", description="Session ID for follow-up questions")
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the total sales by country?",
                "session_id": "demo"
            }
        }
@app.get("/health")
async def health():
    return {"status": "ok", "service": "sql-intelligence-agent"}
@app.post("/query")
async def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    history = sessions.get(request.session_id, [])
    result = orchestrator.run(request.question, conversation_history=history)
    sessions[request.session_id] = result.get("conversation_history", [])
    return {
        "question": request.question,
        "sql_generated": result.get("sql_query", ""),
        "answer": result.get("final_answer", ""),
        "execution_time_ms": result.get("execution_time_ms", 0),
        "fix_attempts": result.get("fix_attempts", 0),
        "was_safe": result.get("is_safe", False)
    }
@app.get("/schema")
async def get_schema():
    return {"schema": orchestrator.agents.db.get_schema()}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
