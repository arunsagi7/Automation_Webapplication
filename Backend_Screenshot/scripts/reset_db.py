from database.db import engine
from models.screenshot import Base

print("Dropping existing tables...")
Base.metadata.drop_all(bind=engine)

print("Creating new tables with updated columns...")
Base.metadata.create_all(bind=engine)

print("✅ Database reset successfully. You can now run the app.")
