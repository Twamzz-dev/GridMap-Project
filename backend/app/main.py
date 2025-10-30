import logging, time
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.requests import Request
from app.routes import energy
from app.database import engine
from app.models import energy as energy_models
import redis
from sqlalchemy.exc import SQLAlchemyError
from app.database import SessionLocal
import os

# Secure headers middleware
class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
        return response

# Request logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000  # ms
        logging.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.2f}ms")
        return response

energy_models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GridMap MVP API",
    description="API for solar energy monitoring and analysis",
    version="1.0.0"
)

# Enable compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Enable CORS (allow local dev and safe defaults)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Add secure headers
app.add_middleware(SecureHeadersMiddleware)

# Add request logging middleware
app.add_middleware(LoggingMiddleware)

# API versioning: v1
app.include_router(energy.router, prefix="/api/v1", tags=["energy"])

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

@app.get("/")
def read_root():
    return {"message": "Welcome to GridMap MVP API", "docs": "/docs"}

@app.get("/health")
def health_check():
    # Check DB
    db_status, redis_status = 'ok', 'ok'
    try:
        db = SessionLocal()
        db.execute('SELECT 1')
    except SQLAlchemyError as e:
        db_status = f"error: {str(e)}"
    finally:
        db.close()
    # Check Redis
    try:
        pong = redis_client.ping()
        if not pong:
            redis_status = "error: cannot ping Redis"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    return {"db": db_status, "redis": redis_status}