# To run: uvicorn main:app --reload --host 0.0.0.0 --port 1442

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.database import init_db_pool, close_db_pool
from app.routes import auth_router, entry_router, page_router


logger = logging.getLogger("api")


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Buffer the request body so it can be read by both this middleware and the route
        body = await request.body()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(request.scope, receive)

        response = await call_next(request)

        if response.status_code >= 400:
            # Collect the response body to include the error detail in the log
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            try:
                body_text = body.decode("utf-8") if body else "<empty>"
            except Exception:
                body_text = "<binary or undecodable body>"

            logger.warning(
                "HTTP %s %s -> %d\n  Request body : %s\n  Response body: %s",
                request.method,
                request.url.path,
                response.status_code,
                body_text,
                response_body.decode("utf-8", errors="replace"),
            )

            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup: Initialize database pool
    await init_db_pool()
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    yield
    
    # Shutdown: Close database pool
    await close_db_pool()


# Create FastAPI app
app = FastAPI(
    title="Journal Transcription API",
    description="Backend API for Journal Transcription App",
    version="1.0.0",
    lifespan=lifespan,
)


# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s [%(name)s]: %(message)s",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ErrorLoggingMiddleware)


# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions with a consistent error format."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Internal server error",
            "error": str(exc) if settings.api_host == "localhost" else None
        }
    )


# Include routers under /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(entry_router, prefix="/api")
app.include_router(page_router, prefix="/api")


# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {
        "status": "online",
        "message": "Journal Transcription API is running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
