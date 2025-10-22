from app.database import SessionLocal
from app.models.installation import Installation

def check_db():
    db = SessionLocal()
    try:
        installations = db.query(Installation).all()
        if installations:
            print(f"Found {len(installations)} installations:")
            for inst in installations:
                print(f"- {inst.name} ({inst.location_name})")
        else:
            print("No installations found in database!")
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_db()