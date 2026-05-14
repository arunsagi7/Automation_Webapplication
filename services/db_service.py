from database.db import SessionLocal
from models.screenshot import ScreenshotResult

def save_screenshot_result(website: str, image_path: str, status: str, ads_found: int = 0, matches_found: int = 0):
    """Saves the result of a screenshot process to the database."""
    db = SessionLocal()
    try:
        new_result = ScreenshotResult(
            url=website,
            screenshot_path=image_path,
            status=status,
            ads_found=ads_found,
            matches_found=matches_found
        )
        db.add(new_result)
        db.commit()
        db.refresh(new_result)
        return new_result
    except Exception as e:
        db.rollback()
        print(f"[DB ERROR] {e}")
        raise e
    finally:
        db.close()

def get_all_results():
    """Fetches all history from the database, ordered by latest first."""
    db = SessionLocal()
    try:
        results = db.query(ScreenshotResult).order_by(ScreenshotResult.created_at.desc()).all()
        # Convert SQLAlchemy objects to dictionaries for JSON response
        return [
            {
                "id": r.id,
                "url": r.url,
                "screenshot_path": r.screenshot_path,
                "status": r.status,
                "ads_found": r.ads_found,
                "matches_found": r.matches_found,
                "created_at": r.created_at.isoformat()
            }
            for r in results
        ]
    finally:
        db.close()
