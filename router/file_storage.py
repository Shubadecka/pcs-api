from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Response
from typing import List, Optional
import shutil
import zipfile
import io
import base64
import os
from pathlib import Path
from datetime import datetime

import httpx

from .schema import (
    ListFilesResponse, FileItem,
    UploadFileResponse,
    CreateDirectoryRequest, CreateDirectoryResponse,
    DownloadFileResponse, DownloadDirectoryResponse,
    DeleteFileResponse, DeleteDirectoryResponse
)
from src.psql_utils import get_db_connection, execute_query, close_db_connection
from src.utils import get_user_id
from src.file_utils import get_safe_path, sanitize_filename, dir_is_root, BASE_STORAGE_PATH

OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OCR_MODEL = os.getenv("OCR_MODEL", "")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

async def transcribe_image(file_path: Path) -> Optional[str]:
    """Send an image to the local Ollama instance for OCR transcription."""
    if not OCR_MODEL:
        return None

    image_data = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    payload = {
        "model": OCR_MODEL,
        "prompt": "Transcribe all text visible in this image exactly as written. Output only the transcribed text with no commentary.",
        "images": [image_data],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"http://localhost:{OLLAMA_PORT}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
    except Exception:
        return None

router = APIRouter()

@router.get("/list-files", response_model=ListFilesResponse)
async def list_files(path: str):
    """Lists files and directories at the given path."""
    try:
        safe_req_path = get_safe_path(path)

        if not safe_req_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        if not safe_req_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        items = []
        for entry in safe_req_path.iterdir():
            items.append(FileItem(name=sanitize_filename(entry.name), is_directory=entry.is_dir()))
        
        # Sharing logic
        can_share_here = dir_is_root(safe_req_path)

        return ListFilesResponse(files=items, can_share_here=can_share_here)
    except HTTPException as http_exc:
        raise http_exc # Re-raise HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@router.put("/upload-file", response_model=UploadFileResponse)
async def upload_file(directory: str = Form(...), file: UploadFile = File(...)):
    """Uploads a file to the specified directory."""
    try:
        safe_dir_path = get_safe_path(directory)
        file_name = sanitize_filename(file.filename)

        if not safe_dir_path.exists() or not safe_dir_path.is_dir():
            raise HTTPException(status_code=404, detail="Target directory not found or is not a directory")

        # Sanitize the filename
        file_path = safe_dir_path / file_name

        if file_path.exists():
            # Handle file overwrite or return error, e.g.:
            raise HTTPException(status_code=409, detail=f"File '{file_name}' already exists in the directory.")

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        transcription = None
        if file_path.suffix.lower() in IMAGE_EXTENSIONS:
            transcription = await transcribe_image(file_path)

        return UploadFileResponse(
            success=True,
            message="File uploaded successfully",
            filename=file_name,
            transcription=transcription,
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    finally:
        if hasattr(file, 'file'): # Ensure file object exists before trying to close
            file.file.close()

@router.put("/create-directory", response_model=CreateDirectoryResponse)
async def create_directory(request: CreateDirectoryRequest):
    """Creates a new directory at the specified path."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        safe_new_dir_path = get_safe_path(request.path)

        if safe_new_dir_path.exists():
            raise HTTPException(status_code=409, detail="Directory or file already exists at this path")

        safe_new_dir_path.mkdir(parents=True, exist_ok=False) # exist_ok=False to ensure it's newly created
        
        # If the directory is not in the storage root, it cannot be shared, so we return success=True
        if safe_new_dir_path.parents[0] != BASE_STORAGE_PATH:
            return CreateDirectoryResponse(success=True, message="Directory created successfully, but cannot be shared outside of storage root")
        
        # Otherwise, share the directory with the current user and the users in shared_with
        current_user_id = get_user_id(conn, request.current_user)
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User not found")

        # Insert into root_directories
        # The path stored should probably be relative to BASE_STORAGE_PATH or a logical root
        db_directory_path = str(safe_new_dir_path.relative_to(BASE_STORAGE_PATH))
        
        dir_insert_query = """
            INSERT INTO root_directories (directory_path, created_by_user_id)
            VALUES (%s, %s) RETURNING directory_id;
        """
        dir_result = execute_query(conn, dir_insert_query, (db_directory_path, current_user_id))
        
        if not dir_result or not dir_result[0] or 'directory_id' not in dir_result[0]:
            # If insertion failed, attempt to clean up the created directory from filesystem
            if safe_new_dir_path.exists():
                safe_new_dir_path.rmdir() # rmdir only works on empty dirs
            raise HTTPException(status_code=500, detail="Failed to record directory in database.")
        
        directory_id = dir_result[0]['directory_id']

        # Logic for shared_with
        for shared_user_username in request.shared_with:
            shared_user_id = get_user_id(conn, shared_user_username)
            if shared_user_id:
                access_query = """INSERT INTO root_directory_user_access (user_id, directory_id)
                                VALUES (%s, %s);"""
                execute_query(conn, access_query, (shared_user_id, directory_id))

        return CreateDirectoryResponse(success=True, message="Directory created successfully")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        # Attempt to clean up if an error occurred after directory creation but before DB commit
        if 'safe_new_dir_path' in locals() and safe_new_dir_path.exists() and not dir_result: 
             # Check if dir_result is not set, implying DB operation might have failed or not run
            try:
                safe_new_dir_path.rmdir() # Again, only works on empty dirs
            except OSError:
                pass # Couldn't remove, maybe not empty or other issue
        raise HTTPException(status_code=500, detail=f"Error creating directory: {str(e)}")
    finally:
        close_db_connection(conn) 

@router.get("/download-file", response_model=DownloadFileResponse)
async def download_file(path: str):
    """Downloads a file from the specified path."""
    try:
        safe_file_path = get_safe_path(path)

        if not safe_file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        if not safe_file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        # Read the file content
        with safe_file_path.open("rb") as file:
            file_content = file.read()

        return DownloadFileResponse(
            success=True,
            message="File downloaded successfully",
            file=file_content
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

@router.get("/download-directory", response_model=DownloadDirectoryResponse)
async def download_directory(path: str):
    """Downloads a directory as a zip file from the specified path."""
    try:
        safe_dir_path = get_safe_path(path)

        if not safe_dir_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
        if not safe_dir_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        # Create a BytesIO object to store the zip file
        zip_buffer = io.BytesIO()
        
        # Create the zip file
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Walk through the directory
            for file_path in safe_dir_path.rglob('*'):
                if file_path.is_file():
                    # Get the relative path for the file in the zip
                    arcname = file_path.relative_to(safe_dir_path)
                    # Add the file to the zip
                    zip_file.write(file_path, arcname)

        # Get the value of the BytesIO buffer
        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()

        return DownloadDirectoryResponse(
            success=True,
            message="Directory downloaded successfully",
            file=zip_content
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading directory: {str(e)}")
    finally:
        if 'zip_buffer' in locals():
            zip_buffer.close() 

@router.delete("/file", response_model=DeleteFileResponse)
async def delete_file(path: str):
    """Moves a file to the deleted_files directory."""
    try:
        safe_file_path = get_safe_path(path)
        deleted_files_dir = Path("/media/tim/nautishub_cloud/palmer_server/storage_folder/deleted_files")

        if not safe_file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        if not safe_file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        # Ensure deleted_files directory exists
        deleted_files_dir.mkdir(parents=True, exist_ok=True)

        # Create the destination path in deleted_files
        dest_path = deleted_files_dir / safe_file_path.name

        # If a file with the same name exists in deleted_files, add a timestamp
        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = deleted_files_dir / f"{safe_file_path.stem}_{timestamp}{safe_file_path.suffix}"

        # Move the file
        shutil.move(str(safe_file_path), str(dest_path))

        return DeleteFileResponse(
            success=True,
            message="File moved to deleted_files successfully"
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting (moving) file: {str(e)}")

@router.delete("/directory", response_model=DeleteDirectoryResponse)
async def delete_directory(path: str):
    """Moves a directory to the deleted_files directory."""
    try:
        safe_dir_path = get_safe_path(path)
        deleted_files_dir = Path("/media/tim/nautishub_cloud/palmer_server/storage_folder/deleted_files")

        if not safe_dir_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
        if not safe_dir_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        # Ensure deleted_files directory exists
        deleted_files_dir.mkdir(parents=True, exist_ok=True)

        # Create the destination path in deleted_files
        dest_path = deleted_files_dir / safe_dir_path.name

        # If a directory with the same name exists in deleted_files, add a timestamp
        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = deleted_files_dir / f"{safe_dir_path.name}_{timestamp}"

        # Move the directory
        shutil.move(str(safe_dir_path), str(dest_path))

        return DeleteDirectoryResponse(
            success=True,
            message="Directory moved to deleted_files successfully"
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting (moving) directory: {str(e)}") 