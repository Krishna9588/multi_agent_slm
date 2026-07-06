# Sql Db Agent (sql_db_agent.py)

## Brief Description
A Database Administrator Agent. Use this to inspect SQL schemas, run queries, and modify database records.

## Prerequisites
1. **Database Engine**: PostgreSQL, MySQL, or SQLite.
2. **Connection String**: The Database URI.

## Step-by-Step Setup Guide
1. Ensure your database is running and accessible.
2. Export the connection string in your environment:
   `export DATABASE_URL="postgresql://user:password@localhost:5432/dbname"`

## How to Update
- The code for this agent lives in `agents/sql_db_agent.py`.
- To modify its behavior or add new parameters, edit the `PARAMETERS` dictionary and the primary function in the Python file.
