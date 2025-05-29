from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from router import login, file_storage, admin_tools

# Create FastAPI app with base URL prefix
app = FastAPI(
    title="Palmer Cloud Storage API",
    description="Backend API for Palmer Cloud Storage",
    version="1.0.0",
    root_path="/palmer_server"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(login.router, prefix="/login", tags=["Login"])
app.include_router(file_storage.router, prefix="/files", tags=["File Storage"])
app.include_router(admin_tools.router, prefix="/admin", tags=["Admin Tools"])

@app.get("/")
async def root():
    """
    Root endpoint to verify API is running
    """
    return {
        "status": "online",
        "message": "Palmer Cloud Storage API is running",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn  # type: ignore
    uvicorn.run(
        "main:app",
        host="localhost",
        port=1442,
        reload=True  # Enable auto-reload during development
    )
