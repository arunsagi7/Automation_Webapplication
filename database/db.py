# Database connection and utility functions
# This file is currently a placeholder for your database logic.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:tnlAmqVcFYfWKVXBKmbaOXObeAtGnJNy@yamanote.proxy.rlwy.net:26422/railway"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)