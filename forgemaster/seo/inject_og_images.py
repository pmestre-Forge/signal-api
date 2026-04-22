"""Retroactively add og:image + twitter:image pointing at /og/{slug}.svg to all article HTML files."""
import re
from pathlib import Path

ARTICLES = Path(__file__).parent.parent.parent / "static" / "articles"

for html_file in sorted(ARTICLES.glob("*.html")):
    slug = html_file.stem
    if slug == "index":
        continue
    content = html_file.read_text(encoding="utf-8")
    if 'property="og:image"' in content:
        continue  # already has it

    og_url = f"https://botwire.dev/og/{slug}.svg"
    injection = (
        f'\n<meta property="og:image" content="{og_url}">'
        f'\n<meta name="twitter:image" content="{og_url}">'
    )

    # Insert before </head>
    new_content, n = re.subn(r"(</head>)", injection + r"\n\1", content, count=1)
    if n == 1:
        html_file.write_text(new_content, encoding="utf-8")
        print(f"  injected og:image -> {slug}")
    else:
        print(f"  SKIP {slug} (no </head> found)")

# Also index.html in root needs og:image
landing = ARTICLES.parent / "index.html"
if landing.exists():
    c = landing.read_text(encoding="utf-8")
    if 'property="og:image"' not in c:
        inj = '\n<meta property="og:image" content="https://botwire.dev/og/index.svg">\n<meta name="twitter:image" content="https://botwire.dev/og/index.svg">'
        c2, n = re.subn(r"(</head>)", inj + r"\n\1", c, count=1)
        if n == 1:
            landing.write_text(c2, encoding="utf-8")
            print("  injected og:image -> landing page")

# Cookbook
cb = ARTICLES / "cookbook.html"
if cb.exists():
    c = cb.read_text(encoding="utf-8")
    if 'property="og:image"' not in c:
        inj = '\n<meta property="og:image" content="https://botwire.dev/og/cookbook.svg">\n<meta name="twitter:image" content="https://botwire.dev/og/cookbook.svg">'
        c2, n = re.subn(r"(</head>)", inj + r"\n\1", c, count=1)
        if n == 1:
            cb.write_text(c2, encoding="utf-8")
            print("  injected og:image -> cookbook")

print("\nDone.")
