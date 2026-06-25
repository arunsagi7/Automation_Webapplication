"""
update_frontend_urls.py
-----------------------
Replaces the Render backend URL with your new Hostinger URL
across all frontend files and netlify.toml.

Usage:
    python update_frontend_urls.py https://your-new-backend-url.com

Example:
    python update_frontend_urls.py https://api.yourdomain.com
"""

import sys
import os
import re

OLD_URL = "https://creative-scanner-backend-2.onrender.com"

# Files that contain the Render URL
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "Frontend_Screenshot")

TARGET_FILES = [
    "index.html",
    "login.html",
    "crm-excel.html",
    "final-report.html",
    "ppt-store.html",
    "qc-checker.html",
    "reach-report.html",
    "netlify.toml",
]

def replace_url(new_url: str):
    new_url = new_url.rstrip("/")
    updated = []
    skipped = []

    for filename in TARGET_FILES:
        filepath = os.path.join(FRONTEND_DIR, filename)
        if not os.path.exists(filepath):
            skipped.append(filename)
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if OLD_URL not in content:
            skipped.append(f"{filename} (URL not found — may already be updated)")
            continue

        new_content = content.replace(OLD_URL, new_url)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        count = content.count(OLD_URL)
        updated.append(f"  ✅ {filename} ({count} replacement{'s' if count > 1 else ''})")

    print(f"\nReplacing: {OLD_URL}")
    print(f"     With: {new_url}\n")

    if updated:
        print("Updated files:")
        for line in updated:
            print(line)
    if skipped:
        print("\nSkipped:")
        for s in skipped:
            print(f"  ⚠️  {s}")

    print("\nDone! Commit and push Frontend_Screenshot to deploy to Netlify.")
    print("  git add Frontend_Screenshot/")
    print('  git commit -m "feat: switch backend to Hostinger"')
    print("  git push")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_frontend_urls.py https://your-new-backend-url.com")
        sys.exit(1)

    new_url = sys.argv[1]
    if not new_url.startswith("http"):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)

    replace_url(new_url)
