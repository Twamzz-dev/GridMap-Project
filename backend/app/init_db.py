from datetime import datetime
from app.database import SessionLocal, Base, engine

# Import all models to ensure they are registered with SQLAlchemy
from app.models.installation import Installation
from app.models.energy import ProductionData  # Import ProductionData model as well

def init_db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a new session
    db = SessionLocal()
    
    try:
        # Check if we already have installations
        existing = db.query(Installation).first()
        if existing is None:
            # Add sample installations
            sample_installations = [
                Installation(
                    name="Solar Farm Alpha",
                    capacity_kw=1000.0,
                    location_name="NAIROBI",
                    location_lat=-1.2921,
                    location_lng=36.8219,
                    owner_type="commercial",
                    status="active"
                ),
                Installation(
                    name="Residential Solar Array Beta",
                    capacity_kw=10.0,
                    location_name="MOMBASA",
                    location_lat=-4.0435,
                    location_lng=39.6682,
                    owner_type="residential",
                    status="active"
                )
            ]
            
            # Add installations to the session
            for installation in sample_installations:
                db.add(installation)
            
            # Commit the changes
            db.commit()
            print("Sample installations created successfully!")
        else:
            print("Database already contains installations. Skipping initialization.")
            
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialization completed!")