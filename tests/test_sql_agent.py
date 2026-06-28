import pytest
from app.utils.safety import validate_sql
from app.database.sqlite_manager import SQLiteManager, init_sample_database
class TestSQLSafety:
    def test_select_is_safe(self):
        is_safe, _ = validate_sql("SELECT * FROM sales")
        assert is_safe is True
    def test_select_with_where(self):
        is_safe, _ = validate_sql("SELECT name FROM users WHERE id = 1")
        assert is_safe is True
    def test_cte_is_safe(self):
        is_safe, _ = validate_sql("WITH cte AS (SELECT * FROM sales) SELECT * FROM cte")
        assert is_safe is True
    def test_drop_is_blocked(self):
        is_safe, reason = validate_sql("DROP TABLE users")
        assert is_safe is False
        assert "DROP" in reason
    def test_delete_is_blocked(self):
        is_safe, _ = validate_sql("DELETE FROM sales WHERE id = 1")
        assert is_safe is False
    def test_update_is_blocked(self):
        is_safe, _ = validate_sql("UPDATE sales SET price = 0")
        assert is_safe is False
    def test_insert_is_blocked(self):
        is_safe, _ = validate_sql("INSERT INTO sales VALUES (1, 'test')")
        assert is_safe is False
    def test_truncate_is_blocked(self):
        is_safe, _ = validate_sql("TRUNCATE TABLE sales")
        assert is_safe is False
    def test_statement_chaining_blocked(self):
        is_safe, _ = validate_sql("SELECT 1; DROP TABLE users")
        assert is_safe is False
    def test_sql_comment_injection_blocked(self):
        is_safe, _ = validate_sql("SELECT * FROM sales -- DROP TABLE users")
        assert is_safe is False
    def test_empty_query(self):
        is_safe, _ = validate_sql("")
        assert is_safe is False
    def test_trailing_semicolon_ok(self):
        is_safe, _ = validate_sql("SELECT * FROM sales;")
        assert is_safe is True
class TestSQLiteManager:
    def test_init_creates_database(self):
        db = SQLiteManager()
        assert db is not None
    def test_get_schema(self):
        db = SQLiteManager()
        schema = db.get_schema()
        assert "sales" in schema.lower()
        assert "products" in schema.lower()
        assert "regions" in schema.lower()
    def test_get_table_names(self):
        db = SQLiteManager()
        tables = db.get_table_names()
        assert "sales" in tables
        assert "products" in tables
    def test_execute_select(self):
        db = SQLiteManager()
        df = db.execute_query("SELECT COUNT(*) as cnt FROM sales")
        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["cnt"] > 0
    def test_execute_with_join(self):
        db = SQLiteManager()
        df = db.execute_query()
        assert df is not None
        assert len(df) > 0
    def test_sample_data_exists(self):
        db = SQLiteManager()
        df = db.execute_query("SELECT * FROM sales LIMIT 5")
        assert len(df) == 5
        assert "salesperson" in df.columns
        assert "revenue" in df.columns
class TestSQLState:
    def test_initial_state(self):
        state = {
            "query": "What are total sales?",
            "schema": "",
            "sql_query": "",
            "is_safe": False,
            "safety_reason": "",
            "data_result": "",
            "error": "",
            "final_answer": "",
            "fix_attempts": 0,
            "conversation_history": [],
            "execution_time_ms": 0.0
        }
        assert state["query"] == "What are total sales?"
        assert state["fix_attempts"] == 0
        assert isinstance(state["conversation_history"], list)
