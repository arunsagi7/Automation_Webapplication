import asyncio
import sys
import uvicorn

if __name__ == "__main__":
    # Force the correct Windows loop for Playwright
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Disable reload=True on Windows to prevent loop conflicts
    uvicorn.run(
        "main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=False
    )
