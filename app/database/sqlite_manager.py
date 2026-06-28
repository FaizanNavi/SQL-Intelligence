import sqlite3
import logging
import pandas as pd
from pathlib import Path
from typing import Optional
from ..utils.config import DB_PATH, MAX_RESULT_ROWS
logger = logging.getLogger(__name__)
def init_sample_database():
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salesperson TEXT NOT NULL,
            country TEXT NOT NULL,
            product TEXT NOT NULL,
            units_sold INTEGER,
            revenue REAL,
            cost REAL,
            profit REAL,
            sale_date TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT,
            unit_price REAL,
            unit_cost REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL UNIQUE,
            region TEXT,
            market_size TEXT
        )
    """)
    if cursor.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0:
        sample_sales = [
            ("Alice", "India", "Dark Chocolate", 120, 2400.0, 1800.0, 600.0, "2025-01-15"),
            ("Bob", "USA", "Milk Chocolate", 85, 1700.0, 1275.0, 425.0, "2025-01-20"),
            ("Alice", "India", "White Chocolate", 60, 900.0, 720.0, 180.0, "2025-02-01"),
            ("Charlie", "UK", "Dark Chocolate", 200, 4000.0, 3000.0, 1000.0, "2025-02-10"),
            ("Bob", "USA", "Truffle Box", 45, 2250.0, 1575.0, 675.0, "2025-02-15"),
            ("Diana", "Germany", "Milk Chocolate", 150, 3000.0, 2250.0, 750.0, "2025-03-01"),
            ("Alice", "India", "Dark Chocolate", 180, 3600.0, 2700.0, 900.0, "2025-03-10"),
            ("Charlie", "UK", "Truffle Box", 90, 4500.0, 3150.0, 1350.0, "2025-03-15"),
            ("Eve", "Japan", "Matcha Chocolate", 110, 2750.0, 1925.0, 825.0, "2025-03-20"),
            ("Bob", "USA", "Dark Chocolate", 95, 1900.0, 1425.0, 475.0, "2025-04-01"),
            ("Diana", "Germany", "White Chocolate", 75, 1125.0, 900.0, 225.0, "2025-04-05"),
            ("Eve", "Japan", "Dark Chocolate", 130, 2600.0, 1950.0, 650.0, "2025-04-10"),
            ("Alice", "India", "Truffle Box", 55, 2750.0, 1925.0, 825.0, "2025-04-15"),
            ("Charlie", "UK", "Milk Chocolate", 160, 3200.0, 2400.0, 800.0, "2025-05-01"),
            ("Bob", "USA", "Matcha Chocolate", 40, 1000.0, 700.0, 300.0, "2025-05-10"),
        ]
        cursor.executemany(
            "INSERT INTO sales (salesperson, country, product, units_sold, revenue, cost, profit, sale_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            sample_sales
        )
        sample_products = [
            ("Dark Chocolate", "Premium", 20.0, 15.0),
            ("Milk Chocolate", "Standard", 20.0, 15.0),
            ("White Chocolate", "Standard", 15.0, 12.0),
            ("Truffle Box", "Luxury", 50.0, 35.0),
            ("Matcha Chocolate", "Specialty", 25.0, 17.5),
        ]
        cursor.executemany(
            "INSERT INTO products (name, category, unit_price, unit_cost) VALUES (?, ?, ?, ?)",
            sample_products
        )
        sample_regions = [
            ("India", "Asia", "Medium"),
            ("USA", "North America", "Large"),
            ("UK", "Europe", "Large"),
            ("Germany", "Europe", "Large"),
            ("Japan", "Asia", "Large"),
        ]
        cursor.executemany(
            "INSERT INTO regions (country, region, market_size) VALUES (?, ?, ?)",
            sample_regions
        )
        conn.commit()
        logger.info("Sample database created with sales, products, and regions tables")
    conn.close()
class SQLiteManager:
    def __init__(self):
        init_sample_database()
        self.db_path = DB_PATH
    def get_schema(self) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        schema_text = ""
        for (table_name,) in tables:
            columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
            col_desc = ", ".join([f"{col[1]} ({col[2]})" for col in columns])
            count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            sample = cursor.execute(f"SELECT * FROM {table_name} LIMIT 2").fetchall()
            sample_str = ""
            if sample:
                col_names = [col[1] for col in columns]
                sample_str = f"\n  Sample: {dict(zip(col_names, sample[0]))}"
            schema_text += f"Table: {table_name} ({count} rows)\n  Columns: {col_desc}{sample_str}\n\n"
        conn.close()
        return schema_text
    def execute_query(self, sql: str) -> Optional[pd.DataFrame]:
        conn = sqlite3.connect(self.db_path)
        try:
            df = pd.read_sql_query(sql, conn)
            conn.close()
            if len(df) > MAX_RESULT_ROWS:
                logger.warning(f"Query returned {len(df)} rows, truncating to {MAX_RESULT_ROWS}")
                df = df.head(MAX_RESULT_ROWS)
            return df
        except Exception as e:
            conn.close()
            raise e
    def get_table_names(self):
        conn = sqlite3.connect(self.db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        conn.close()
        return [t[0] for t in tables]
if __name__ == "__main__":
    db = SQLiteManager()
    print("Schema:")
    print(db.get_schema())
    print("Tables:", db.get_table_names())
