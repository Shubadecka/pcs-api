import os
import psycopg2
from dotenv import load_dotenv
from typing import Optional, Any, List, Dict

# Load environment variables from .env file
load_dotenv()

def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    """
    Establishes a connection to the PostgreSQL database.
    
    Returns:
        Optional[psycopg2.extensions.connection]: Database connection object if successful, None if failed
    """
    try:
        connection = psycopg2.connect(
            dbname="palmer_server",
            user="tim",
            password=os.getenv("PG_PASSWORD"),
            host="/var/run/postgresql",
            port="5432"
        )
        return connection
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return None

def close_db_connection(connection: Optional[psycopg2.extensions.connection]) -> None:
    """
    Closes the database connection if it exists.
    
    Args:
        connection (Optional[psycopg2.extensions.connection]): Database connection to close
    """
    if connection:
        try:
            connection.close()
        except psycopg2.Error as e:
            print(f"Error closing database connection: {e}")

def execute_query(connection: psycopg2.extensions.connection, query: str, params: tuple = None) -> Optional[List[Dict[str, Any]]]:
    """
    Executes a SQL query and returns the results.
    
    Args:
        connection (psycopg2.extensions.connection): Database connection
        query (str): SQL query to execute
        params (tuple, optional): Parameters for the query. Defaults to None.
    
    Returns:
        Optional[List[Dict[str, Any]]]: List of dictionaries containing query results if successful, None if failed
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            
            # If the query is a SELECT statement, fetch and return results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results
            
            # For non-SELECT statements (INSERT, UPDATE, DELETE), commit the transaction
            connection.commit()
            return None
            
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")
        connection.rollback()
        return FileNotFoundError
