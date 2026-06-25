from database.db import engine
from models.screenshot import Base

Base.metadata.create_all(bind=engine)

print("Tables created successfully")
