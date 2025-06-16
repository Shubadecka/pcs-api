from pathlib import Path
import os
from fastapi import HTTPException

BASE_STORAGE_PATH = Path(os.getenv("BASE_STORAGE_PATH", "/media/tim/nautishub_cloud/palmer_server/storage_folder"))

def get_safe_path(user_provided_path: str) -> Path:
    """Constructs a safe path within the BASE_STORAGE_PATH and resolves it."""
    # Prevent path traversal attacks by normalizing the path
    # and ensuring it's a child of BASE_STORAGE_PATH.
    # os.path.join correctly handles leading slashes in user_provided_path.
    full_path = Path(os.path.join(BASE_STORAGE_PATH, user_provided_path.lstrip('/'))).resolve()

    if BASE_STORAGE_PATH not in full_path.parents and full_path != BASE_STORAGE_PATH:
        raise HTTPException(status_code=403, detail="Access denied: Path is outside of allowed storage area.")
    return full_path

def sanitize_filename(filename: str) -> str:
    """Sanitizes a filename to prevent path traversal attacks."""
    return filename.replace('/', '_').replace('\\', '_').replace('..', '_')

def dir_is_root(path: Path) -> bool:
    """Checks if a path is the root directory."""
    return path == BASE_STORAGE_PATH