import asyncio
from services.browser import open_website

async def main():
    print("Starting single URL scan test...")
    results = await open_website(urls=["https://www.espncricinfo.com/"])
    print("Results:", results)

if __name__ == "__main__":
    # Windows: Proactor loop for subprocess (deprecated to set policy on Python 3.14+).
    import sys

    if sys.platform == "win32" and sys.version_info < (3, 14):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
