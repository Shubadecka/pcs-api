from fastapi import APIRouter, HTTPException
from typing import List
import hashlib
import logging

logger = logging.getLogger(__name__)

from .schema import (
    GetUserResponse,
    PostUserRequest, PostUserResponse,
    DeleteUserRequest, DeleteUserResponse
)
from src.psql_utils import get_db_connection, execute_query, close_db_connection
from src.utils import get_user_id

router = APIRouter()

def is_admin(conn, user_id: int) -> bool:
    """Check if a user is an admin."""
    query = """
        SELECT is_admin 
        FROM users 
        WHERE user_id = %s AND is_active = true
    """
    result = execute_query(conn, query, (user_id,))
    if result:
        return result[0]['is_admin']
    return False

def get_user_directories(conn, user_id: int) -> List[str]:
    """Get all directories a user has access to."""
    query = """
        SELECT rd.directory_path
        FROM root_directories rd
        JOIN user_root_directory_access urda ON rd.directory_id = urda.directory_id
        WHERE urda.user_id = %s
    """
    result = execute_query(conn, query, (user_id,))
    return [row['directory_path'] for row in result] if result else []

@router.get("/user", response_model=GetUserResponse)
async def get_user(action_user: str, target_user: str):
    """Get information about a user."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Get action user's ID and check if admin
        action_user_id = get_user_id(conn, action_user)
        if not action_user_id:
            raise HTTPException(status_code=404, detail="Action user not found")
        
        if not is_admin(conn, action_user_id):
            raise HTTPException(status_code=403, detail="Only admins can perform this action")

        # Get target user info
        query = """
            SELECT user_id, username, is_admin, is_active
            FROM users
            WHERE username = %s
        """
        result = execute_query(conn, query, (target_user,))
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        user_info = result[0]
        directories = get_user_directories(conn, user_info['user_id'])

        return GetUserResponse(
            success=True,
            message="User information retrieved successfully",
            username=user_info['username'],
            directories=directories,
            is_admin=user_info['is_admin'],
            is_disabled=not user_info['is_active']
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user information: {str(e)}")
    finally:
        close_db_connection(conn)

@router.post("/user", response_model=PostUserResponse)
async def post_user(request: PostUserRequest):
    """
    Create or update a user.

    If the user already exists, update their information.
    If the user does not exist, create a new user.

    If the user is being created, the following fields are required:
    - username
    - password
    - email
    - is_admin

    If the user is being updated, the following fields are not required, if empty, they will not be updated:
    - is_admin
    - password
    - email
    - extra_directories
    - remove_directories
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Get the action user's ID
        action_user_id = get_user_id(conn, request.action_user)
        if not action_user_id:
            raise HTTPException(status_code=404, detail="Action user not found")
        
        # Check if action user is admin
        if not is_admin(conn, action_user_id):
            raise HTTPException(status_code=403, detail="Only admins can perform this action")

        # Hash the password if provided
        hashed_password = None
        if request.password:
            hashed_password = hashlib.sha256(request.password.encode()).hexdigest()

        # Check if user exists
        user_query = "SELECT user_id FROM users WHERE username = %s"
        user_result = execute_query(conn, user_query, (request.username,))
        
        if user_result:
            user_id = user_result[0]['user_id']
            # Update existing user
            update_fields = []
            update_values = []
            
            if hashed_password:
                update_fields.append("hashed_pass = %s")
                update_values.append(hashed_password)
            if request.is_admin is not None:
                update_fields.append("is_admin = %s")
                update_values.append(request.is_admin)
            if request.email:
                update_fields.append("email = %s")
                update_values.append(request.email)
            
            if update_fields:
                update_query = f"""
                    UPDATE users 
                    SET {', '.join(update_fields)}, is_active = true
                    WHERE user_id = %s
                """
                update_values.append(user_id)
                execute_query(conn, update_query, tuple(update_values))

            # Add access to specified new directories
            if request.extra_directories:
                access_query = """
                    INSERT INTO user_root_directory_access (user_id, directory_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, directory_id) DO NOTHING
                """
                dir_exists_query = "SELECT directory_id FROM root_directories WHERE directory_path = %s"
                add_dir_query = """
                    INSERT INTO root_directories (directory_path, created_by_user_id)
                    VALUES (%s, %s)
                    RETURNING directory_id
                """
                for dir_path in request.extra_directories:
                    dir_result = execute_query(conn, dir_exists_query, (dir_path,))
                    if not dir_result:
                        dir_result = execute_query(conn, add_dir_query, (dir_path, user_id))
                    dir_id = dir_result[0]['directory_id']
                    execute_query(conn, access_query, (user_id, dir_id))

            # Remove access to specified removed directories
            if request.remove_directories:
                remove_access_query = """
                    DELETE FROM user_root_directory_access
                    WHERE user_id = %s AND directory_id = %s
                """
                for dir_path in request.remove_directories:
                    dir_result = execute_query(conn, dir_exists_query, (dir_path,))
                    if dir_result:
                        execute_query(conn, remove_access_query, (user_id, dir_result[0]['directory_id']))

        else:
            # Create new user
            if not all([request.is_admin is not None, request.password, request.username, request.email]):
                raise HTTPException(status_code=400, detail="is_admin, password, username, and email are required for new users")

            insert_query = """
                INSERT INTO users (username, email, hashed_pass, is_admin, is_active)
                VALUES (%s, %s, %s, %s, true)
                RETURNING user_id
            """
            result = execute_query(conn, insert_query, (
                request.username,
                request.email,
                hashed_password,
                request.is_admin
            ))
            user_id = result[0]['user_id']

            # Create user's root directory
            dir_query = """
                INSERT INTO root_directories (directory_path, created_by_user_id)
                VALUES (%s, %s)
                RETURNING directory_id
            """
            dir_result = execute_query(conn, dir_query, (request.username, user_id))
            dir_id = dir_result[0]['directory_id']

            # Give user access to their directory
            access_query = """
                INSERT INTO user_root_directory_access (user_id, directory_id)
                VALUES (%s, %s)
            """
            execute_query(conn, access_query, (user_id, dir_id))

            # Handle directory access changes
            if request.extra_directories:
                for dir_path in request.extra_directories:
                    # Get directory_id
                    dir_query = "SELECT directory_id FROM root_directories WHERE directory_path = %s"
                    dir_result = execute_query(conn, dir_query, (dir_path,))
                    if dir_result:
                        dir_id = dir_result[0]['directory_id']
                        # Add access
                        access_query = """
                            INSERT INTO user_root_directory_access (user_id, directory_id)
                            VALUES (%s, %s)
                            ON CONFLICT (user_id, directory_id) DO NOTHING
                        """
                        execute_query(conn, access_query, (user_id, dir_id))

            if request.remove_directories:
                for dir_path in request.remove_directories:
                    # Get directory_id
                    dir_query = "SELECT directory_id FROM root_directories WHERE directory_path = %s"
                    dir_result = execute_query(conn, dir_query, (dir_path,))
                    if dir_result:
                        dir_id = dir_result[0]['directory_id']
                        # Remove access
                        remove_query = """
                            DELETE FROM user_root_directory_access
                            WHERE user_id = %s AND directory_id = %s
                        """
                        execute_query(conn, remove_query, (user_id, dir_id))

        # Get updated directory list
        directories = get_user_directories(conn, user_id)

        return PostUserResponse(
            success=True,
            message="User created/updated successfully",
            directories=directories,
            is_admin=is_admin(conn, user_id),
            is_disabled=False
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating/updating user: {str(e)}")
    finally:
        close_db_connection(conn)

@router.delete("/user", response_model=DeleteUserResponse)
async def delete_user(request: DeleteUserRequest):
    """Disable a user and remove their access."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Get action user's ID and check if admin
        action_user_id = get_user_id(conn, request.action_user)
        if not action_user_id:
            raise HTTPException(status_code=404, detail="Action user not found")
        
        if not is_admin(conn, action_user_id):
            raise HTTPException(status_code=403, detail="Only admins can perform this action")

        # Get target user's ID
        user_query = "SELECT user_id FROM users WHERE username = %s"
        user_result = execute_query(conn, user_query, (request.target_user,))
        
        if not user_result:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user_result[0]['user_id']

        # Remove all directory access
        remove_access_query = """
            DELETE FROM user_root_directory_access
            WHERE user_id = %s
        """
        execute_query(conn, remove_access_query, (user_id,))

        # Delete chat history
        delete_chat_query = """
            DELETE FROM chat_histories
            WHERE user_id = %s
        """
        execute_query(conn, delete_chat_query, (user_id,))

        # Mark user as disabled
        disable_query = """
            UPDATE users
            SET is_active = false, is_admin = false, row_modified_datetime_utc = now()
            WHERE user_id = %s
        """
        execute_query(conn, disable_query, (user_id,))

        return DeleteUserResponse(
            success=True,
            message=f"User {request.target_user} has been disabled"
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disabling user: {str(e)}")
    finally:
        close_db_connection(conn)
