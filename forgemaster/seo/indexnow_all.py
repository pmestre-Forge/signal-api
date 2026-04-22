"""Submit ALL current URLs (sitemap-derived) to IndexNow."""
import json
import re
import urllib.request
from pathlib import Path

KEY = "ebd6a484f9eb524633a11f8b3d6e4537"
HOST = "botwire.dev"

sitemap = (Path(__file__).parent.parent.parent / "static" / "sitemap.xml").read_text()
urls = re.findall(r"<loc>([^<]+)</loc>", sitemap)

payload = {
    "host": HOST,
    "key": KEY,
    "keyLocation": f"https://{HOST}/{KEY}.txt",
    "urlList": urls,
}

for endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"[{endpoint}] HTTP {r.status} — submitted {len(urls)} URLs")
    except Exception as e:
        print(f"[{endpoint}] {e}")
