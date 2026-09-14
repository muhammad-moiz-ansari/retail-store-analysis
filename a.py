from pathlib import Path
from urllib.parse import urljoin, urlparse
import time

import requests
from bs4 import BeautifulSoup

PAGE = "https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/"
LIMIT = 30
OUTPUT = Path("caviar_videos")
OUTPUT.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers["User-Agent"] = "CAVIAR-Dataset-Downloader/1.0"

response = session.get(PAGE, timeout=60)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

# Collect unique video links in page order, then select a few.
urls = list(dict.fromkeys(
    urljoin(response.url, link["href"])
    for link in soup.select("a[href]")
    if urlparse(link["href"]).path.lower().endswith(".mpg")
))[:LIMIT]

if not urls:
    raise RuntimeError("No video links found.")

print(f"Selected {len(urls)} videos.")
failed = []

for index, url in enumerate(urls, start=1):
    name = Path(urlparse(url).path).name
    destination = OUTPUT / name
    temporary = destination.with_suffix(".mpg.part")

    if destination.exists() and destination.stat().st_size > 0:
        print(f"[{index}/{len(urls)}] Skipping existing file: {name}")
        continue

    for attempt in range(1, 4):
        try:
            print(f"[{index}/{len(urls)}] Downloading: {name}")

            with session.get(url, stream=True, timeout=(30, 120)) as video:
                video.raise_for_status()

                content_type = video.headers.get("Content-Type", "").lower()
                if "text/html" in content_type:
                    raise ValueError("Server returned HTML instead of a video.")

                with temporary.open("wb") as file:
                    for chunk in video.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file.write(chunk)

                if temporary.stat().st_size == 0:
                    raise ValueError("Downloaded file is empty.")

            temporary.replace(destination)
            print(f"  Saved: {name}")
            break

        except (requests.RequestException, OSError, ValueError) as error:
            print(f"  Attempt {attempt} failed: {error}")
            if attempt < 3:
                time.sleep(3)
            else:
                failed.append(name)

print(f"\nOutput folder: {OUTPUT.resolve()}")
if failed:
    print("Failed downloads:", ", ".join(failed))
else:
    print("All selected videos downloaded.")