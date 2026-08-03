import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, db
from scripts.seed_data import seed_administrator, seed_system_modules, Session

def reset_database():
    print("🧹 Dropping all tables...")
    app = create_app()
    with app.app_context():
        db.drop_all()
        print("🏗️ Creating fresh database tables...")
        db.create_all()
    
    print("🌱 Seeding baseline data...")
    session = Session()
    try:
        seed_administrator(session)
        seed_system_modules(session)
        print("✅ Database reset and seeded successfully!")
    except Exception as e:
        session.rollback()
        print(f"❌ Error during seeding: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    reset_database()
