"""
Agent: sql_db_agent
-------------------
Connects to SQL databases (SQLite/PostgreSQL) to read schemas, execute queries, and update records.
Includes strict safety rails against destructive commands (DROP, TRUNCATE) unless explicitly bypassed.
"""

import sqlite3
import os
import csv

DESCRIPTION = (
    "A Database Administrator Agent. Use this to inspect SQL schemas, run queries, and modify database records. "
    "By default, this connects to the local SQLite database 'database.db'. "
    "Destructive queries like DROP or TRUNCATE are blocked for safety."
)

PARAMETERS = {
    "action": {
        "type": "string",
        "required": True,
        "description": "Must be one of: 'get_schema', 'execute_query', or 'backup_table'.",
    },
    "query_or_table": {
        "type": "string",
        "required": False,
        "description": "The SQL query to run (if action is execute_query) or the table name (if action is backup_table).",
    }
}

# The default local database for the agent to play with
DB_PATH = os.path.join(os.getcwd(), "database.db")

def _get_connection():
    # In a real enterprise system, this could read DB_URI from .env (e.g., postgres://...)
    # For this Swarm, we use a local SQLite file so it works out of the box.
    return sqlite3.connect(DB_PATH)

def sql_db_agent(action: str, query_or_table: str = "") -> dict:
    """Interacts with the SQL Database."""
    action = action.lower().strip()
    
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        if action == "get_schema":
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            schema_info = []
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                col_defs = [f"{col[1]} ({col[2]})" for col in columns]
                schema_info.append(f"Table '{table_name}': {', '.join(col_defs)}")
                
            conn.close()
            
            if not schema_info:
                return {"success": True, "schema": "Database is currently empty. No tables found."}
                
            return {"success": True, "schema": "\n".join(schema_info)}
            
        elif action == "execute_query":
            if not query_or_table:
                return {"error": "execute_query requires a SQL string in 'query_or_table'."}
                
            # SAFETY RAIL: Block destructive queries
            q_upper = query_or_table.upper()
            if "DROP " in q_upper or "TRUNCATE " in q_upper or "ALTER " in q_upper:
                return {"error": "SECURITY BLOCK: Destructive commands (DROP, TRUNCATE, ALTER) are disabled for safety."}
                
            try:
                cursor.execute(query_or_table)
                conn.commit()
                
                if q_upper.strip().startswith("SELECT"):
                    columns = [description[0] for description in cursor.description]
                    rows = cursor.fetchall()
                    conn.close()
                    
                    # Convert to list of dicts for easy JSON parsing
                    results = [dict(zip(columns, row)) for row in rows]
                    
                    # Prevent massive context window blowouts (limit to 50 rows)
                    if len(results) > 50:
                        return {
                            "success": True,
                            "results": results[:50],
                            "warning": f"Results truncated. Total rows: {len(results)}. Showing first 50."
                        }
                    return {"success": True, "results": results}
                else:
                    rows_affected = cursor.rowcount
                    conn.close()
                    return {"success": True, "message": f"Query executed successfully. Rows affected: {rows_affected}"}
            except sqlite3.OperationalError as e:
                return {"error": f"SQL Syntax/Operational Error: {str(e)}"}
                
        elif action == "backup_table":
            if not query_or_table:
                return {"error": "backup_table requires a table name in 'query_or_table'."}
                
            table = query_or_table.strip()
            cursor.execute(f"SELECT * FROM {table}")
            
            if not cursor.description:
                return {"error": f"Table '{table}' does not exist or has no columns."}
                
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            
            backup_path = os.path.join(os.getcwd(), "archive", f"{table}_backup.csv")
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            with open(backup_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)
                
            return {"success": True, "message": f"Table '{table}' backed up to {backup_path}"}
            
        else:
            return {"error": "Invalid action. Use 'get_schema', 'execute_query', or 'backup_table'."}
            
    except Exception as e:
        return {"error": f"Database agent failure: {str(e)}"}
