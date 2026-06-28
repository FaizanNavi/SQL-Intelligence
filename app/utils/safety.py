import re
import logging
from typing import Tuple
logger = logging.getLogger(__name__)
FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "CREATE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "SHUTDOWN", "KILL"
]
INJECTION_PATTERNS = [
    r";\s*(DROP|DELETE|UPDATE|INSERT)",
    r"--",
    r"/\*",
    r"UNION\s+SELECT",
]
def validate_sql(sql: str) -> Tuple[bool, str]:
    if not sql or not sql.strip():
        return False, "Empty query"
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        return False, f"Only SELECT queries are allowed. Got: {sql_upper[:20]}..."
    for keyword in FORBIDDEN_KEYWORDS:
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            return False, f"Blocked: query contains forbidden keyword '{keyword}'"
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, sql_upper):
            return False, f"Blocked: potential SQL injection detected"
    cleaned = sql.strip().rstrip(";")
    if ";" in cleaned:
        return False, "Blocked: multiple statements not allowed"
    logger.info(f"SQL validation passed: {sql[:50]}...")
    return True, "Query is safe"
if __name__ == "__main__":
    test_cases = [
        ("SELECT * FROM sales", True),
        ("SELECT name FROM users WHERE id = 1", True),
        ("DROP TABLE users", False),
        ("SELECT 1; DROP TABLE users", False),
        ("DELETE FROM sales WHERE id = 1", False),
        ("UPDATE sales SET price = 0", False),
        ("SELECT * FROM sales -- this is a comment", False),
        ("WITH cte AS (SELECT * FROM sales) SELECT * FROM cte", True),
    ]
    for sql, expected in test_cases:
        is_safe, reason = validate_sql(sql)
        status = "✅" if is_safe == expected else "❌"
        print(f"{status} {sql[:50]:50s} → safe={is_safe} ({reason})")
