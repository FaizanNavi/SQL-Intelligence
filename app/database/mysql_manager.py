from sqlalchemy import create_engine, text
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()
class MySQLManager:
    def __init__(self):
        user = os.getenv("MYSQL_USER", "root")
        password = os.getenv("MYSQL_PASSWORD", "")
        host = os.getenv("MYSQL_HOST", "localhost")
        port = os.getenv("MYSQL_PORT", "3306")
        db = os.getenv("MYSQL_DB", "regulatory_data")
        self.engine = create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db}")
    def get_schema(self):
        query = 
        df = pd.read_sql(query, self.engine)
        schema_text = ""
        for table in df['table_name'].unique():
            cols = df[df['table_name'] == table]
            col_desc = ", ".join([f"{row['column_name']} ({row['data_type']})" for _, row in cols.iterrows()])
            schema_text += f"Table: {table}\nColumns: {col_desc}\n\n"
        return schema_text
    def execute_query(self, sql_query):
        with self.engine.connect() as connection:
            result = connection.execute(text(sql_query))
            if result.returns_rows:
                return pd.DataFrame(result.fetchall(), columns=result.keys())
            return None
if __name__ == "__main__":
    try:
        db = MySQLManager()
        print("Schema Preview:")
    except Exception as e:
        print(f"Connection Status: Waiting for configuration ({e})")
