import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, db

def clear_database():
    print("🧹 Clearing all database tables and rows...")
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ Database successfully wiped clean!")

if __name__ == "__main__":
    clear_database()
