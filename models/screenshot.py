from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ScreenshotResult(Base):
    __tablename__ = "screenshot_results"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    screenshot_path = Column(String)
    status = Column(String) # Added status field
    ads_found = Column(Integer, nullable=True)
    matches_found = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
