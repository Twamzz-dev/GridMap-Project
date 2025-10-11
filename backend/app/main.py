from fastapi import FastAPI
from app.routes import energy
from app.database import engine
from app.models import energy as energy_models

# Create database tables
energy_models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GridMap MVP API",
    description="API for solar energy monitoring and analysis",
    version="1.0.0"
)

# Include routers
app.include_router(energy.router, prefix="/api/v1", tags=["energy"])

@app.get("/")
def read_root():
    return {"message": "Welcome to GridMap MVP API", "docs": "/docs"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}