from fastapi import APIRouter, HTTPException  # type: ignore
import hashlib
from datetime import datetime, timedelta, timezone

from src.psql_utils import get_db_connection, execute_query, close_db_connection
from src.auth import generate_verification_code, send_verification_email
from src.utils import get_user_id
from .schema import LoginRequest, LoginResponse, TwoFactorAuthRequest, TwoFactorAuthResponse

router = APIRouter()

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

@router.get("/", response_model=LoginResponse)
async def login(username: str, password: str, device_identifier: str):
    """
    Handle user login request.
    Validates credentials and sends 2FA code if valid.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed in /login")

    try:
        # Check if user exists and is active
        user_query = """
            SELECT user_id, username, email, hashed_pass, is_admin, is_active 
            FROM users 
            WHERE username = %s
        """
        user_result = execute_query(conn, user_query, (username,))
        
        if not user_result or not user_result[0]['is_active']:
            return LoginResponse(
                is_correct_password=False,
                message="Invalid username or account is disabled"
            )

        user = user_result[0]
        
        # Verify password
        hashed_input = hash_password(password)
        if hashed_input != user['hashed_pass']:
            return LoginResponse(
                is_correct_password=False,
                message="Invalid password"
            )

        # Check if device is remembered
        device_query = """
            SELECT device_id, device_remembered_datetime_utc 
            FROM devices 
            WHERE incoming_device_id = %s AND user_id = %s
        """
        device_result = execute_query(conn, device_query, (device_identifier, user['user_id']))
        if device_result:   
            is_device_remembered = device_result[0]['device_remembered_datetime_utc'] > datetime.now(timezone.utc) - timedelta(days=30)
        else:
            is_device_remembered = False

        # Generate and store validation code
        validation_code = generate_verification_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        row_created_datetime_utc = datetime.now(timezone.utc)
        
        validation_query = """
            INSERT INTO validation_codes 
            (user_id, validation_code, expires_at, row_created_datetime_utc) 
            VALUES (%s, %s, %s, %s)
        """
        execute_query(conn, validation_query, (user['user_id'], validation_code, expires_at, row_created_datetime_utc))

        # Send validation email
        try:
            send_verification_email(user['email'], validation_code)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send validation email: {str(e)}")

        return LoginResponse(
            is_correct_password=True,
            is_admin=user['is_admin'],
            is_device_remembered=is_device_remembered,
            message="Validation code sent to your email"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db_connection(conn)

@router.get("/two-factor-auth", response_model=TwoFactorAuthResponse)
async def verify_two_factor_auth(username: str, validation_code: int):
    """
    Verify the two-factor authentication code.
    Checks if the code matches and is within the 5-minute window.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        # Get user ID using utility function
        user_id = get_user_id(conn, username)
        if not user_id:
            return TwoFactorAuthResponse(
                is_valid=False,
                message="Invalid username"
            )

        # Get the most recent validation code for this user
        validation_query = """
            SELECT validation_codes_id, validation_code, expires_at
            FROM validation_codes 
            WHERE user_id = %s 
            AND code_used = false
            ORDER BY row_created_datetime_utc DESC 
            LIMIT 1
        """
        validation_result = execute_query(conn, validation_query, (user_id,))

        if not validation_result:
            return TwoFactorAuthResponse(
                is_valid=False,
                message="No validation code found"
            )

        stored_validation_code = validation_result[0]['validation_code']
        stored_expires_at = validation_result[0]['expires_at']
        
        # Check if code matches and hasn't expired
        print(f"input code: {validation_code}, stored code: {stored_validation_code}")
        print(f"current time: {datetime.now(timezone.utc)}, expires at: {stored_expires_at}")
        print(f"code not matches: {stored_validation_code != validation_code}")
        print(f"code expired: {datetime.now(timezone.utc) > stored_expires_at}")
        current_time = datetime.now(timezone.utc)
        if (stored_validation_code != validation_code or 
            current_time > stored_expires_at):
            return TwoFactorAuthResponse(
                is_valid=False,
                message="Invalid or expired validation code"
            )

        # Delete the used validation code
        delete_query = """
            UPDATE validation_codes
            SET code_used = true
            WHERE validation_code = %s
        """
        execute_query(conn, delete_query, (validation_code,))

        return TwoFactorAuthResponse(
            is_valid=True,
            message="Validation successful"
        )

    except Exception as e:
        raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db_connection(conn)
