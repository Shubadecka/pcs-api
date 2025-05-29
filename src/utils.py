from typing import Optional
from psycopg2.extensions import connection  # type: ignore

def get_user_id(conn: connection, username: str) -> Optional[int]:
    """
    Get a user's ID from their username.
    
    Args:
        conn: Database connection
        username: Username to look up
        
    Returns:
        Optional[int]: User ID if found, None if not found
    """
    query = """
        SELECT user_id 
        FROM users 
        WHERE username = %s
    """
    result = conn.execute(query, (username,))
    if result and result[0]:
        return result[0]['user_id']
    return None
