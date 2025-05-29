from fastapi import APIRouter, HTTPException  # type: ignore
import hashlib
from datetime import datetime, timedelta

from src.psql_utils import get_db_connection, execute_query, close_db_connection
from src.auth import generate_verification_code, send_verification_email
from src.utils import get_user_id
from .schema import LoginRequest, LoginResponse, TwoFactorAuthRequest, TwoFactorAuthResponse

router = APIRouter()

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

@router.get("/", response_model=LoginResponse)
async def login(request: LoginRequest):
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
        user_result = execute_query(conn, user_query, (request.username,))
        
        if not user_result or not user_result[0]['is_active']:
            return LoginResponse(
                is_valid=False,
                message="Invalid username or account is disabled"
            )

        user = user_result[0]
        
        # Verify password
        hashed_input = hash_password(request.password)
        if hashed_input != user['hashed_pass']:
            return LoginResponse(
                is_valid=False,
                message="Invalid password"
            )

        # Check if device is remembered
        device_query = """
            SELECT device_id, device_remembered_datetime_utc 
            FROM devices 
            WHERE incoming_device_id = %s AND user_id = %s
        """
        device_result = execute_query(conn, device_query, (request.device_identifier, user['user_id']))
        if device_result:   
            is_device_remembered = device_result[0]['device_remembered_datetime_utc'] > datetime.utcnow() - timedelta(days=30)
        else:
            is_device_remembered = False

        # Generate and store validation code
        validation_code = generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        validation_query = """
            INSERT INTO validation_codes 
            (user_id, validation_code, expires_at) 
            VALUES (%s, %s, %s)
        """
        execute_query(conn, validation_query, (user['user_id'], validation_code, expires_at))

        # Send validation email
        try:
            send_verification_email(user['email'], validation_code)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send validation email: {str(e)}")

        return LoginResponse(
            is_valid=True,
            is_admin=user['is_admin'],
            is_device_remembered=is_device_remembered,
            message="Validation code sent to your email"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db_connection(conn)

@router.get("/two-factor-auth", response_model=TwoFactorAuthResponse)
async def verify_two_factor_auth(request: TwoFactorAuthRequest):
    """
    Verify the two-factor authentication code.
    Checks if the code matches and is within the 5-minute window.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        # Get user ID using utility function
        user_id = get_user_id(conn, request.username)
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
            ORDER BY row_created_datetime_utc DESC 
            LIMIT 1
        """
        validation_result = execute_query(conn, validation_query, (user_id,))

        if not validation_result:
            return TwoFactorAuthResponse(
                is_valid=False,
                message="No validation code found"
            )

        validation = validation_result[0]
        
        # Check if code matches and hasn't expired
        if (validation['validation_code'] != request.validation_code or 
            datetime.utcnow() > validation['expires_at']):
            return TwoFactorAuthResponse(
                is_valid=False,
                message="Invalid or expired validation code"
            )

        # Delete the used validation code
        delete_query = """
            DELETE FROM validation_codes 
            WHERE validation_codes_id = %s
        """
        execute_query(conn, delete_query, (validation['validation_codes_id'],))

        return TwoFactorAuthResponse(
            is_valid=True,
            message="Validation successful"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db_connection(conn)
