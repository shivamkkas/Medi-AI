from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Import routers
from .routers import user_router, func_router
from .internal import admin
from .dependency import configure_swagger_authentication,get_current_active_user
from . import models
from .database import engine
from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer



models.Base.metadata.create_all(bind=engine)

# Load environment variables
load_dotenv()

# Create FastAPI application
app = FastAPI(
    title="Multi-User Health Platform",
    description="A comprehensive health management and recommendation platform",
    version="1.0.0",
    # Optional: Add contact info
    contact={
        "name": "Platform Support",
        "email": "support@healthplatform.com",
    },
    swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect"
)
# oauth2_scheme = OAuth2PasswordBearer(
#     tokenUrl="users/login",  # This should match your token endpoint
#     auto_error=True
# )
configure_swagger_authentication(app)


# CORS Configuration
origins = [
    "http://localhost",
    "http://localhost:3000",  # React default port
    "http://localhost:8000",  # Common FastAPI port
    "https://localhost:5000"  # Production frontend domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global dependencies (optional)
# Uncomment and adjust as needed
# app = FastAPI(dependencies=[Depends(get_query_token)])

# Include Routers
app.include_router(user_router.router, prefix="/api/users", tags=["users"])
app.include_router(func_router.router, prefix="/api/functions", tags=["functions"])
app.include_router(admin.router,prefix="/api/admin",tags=["admin"],dependencies=[Depends(get_current_active_user)],)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Health Platform API",
        "status": "operational",
        "version": "1.0.0"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "authentication": "operational"
    }

# Error handlers can be added here
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Log the exception
    print(f"Unhandled exception: {exc}")
    
    return {
        "status": "error",
        "message": "An unexpected error occurred",
        "detail": str(exc)
    }

# Optional: Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    print("Application is starting up...")
    # Perform startup tasks like:
    # - Database connection checks
    # - Cache warming
    # - External service connectivity tests

@app.on_event("shutdown")
async def shutdown_event():
    print("Application is shutting down...")
    # Perform cleanup tasks
    # - Close database connections
    # - Clear caches
    # - Log shutdown event