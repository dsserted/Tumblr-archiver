"""
tumblrcrawler.py

Crawls a Tumblr blog via the official API (using PyTumblr2) and saves:
  - all post JSON, combined, to  <OUTPUT_DIR>/<BLOG_NAME>/posts.json
  - referenced media to          <OUTPUT_DIR>/<BLOG_NAME>/<original_filename>

posts.json is a list of dictionaries 

Safe to re-run: posts already in posts.json and media files already on
disk are skipped. posts.json is flushed to disk periodically and again at
the end (even on Ctrl+C), so an interrupted run only loses work back to
the last flush, not the whole run.
"""

import re
import json
import time
import argparse
from pathlib import Path

import requests
import pytumblr2

# ---------------- CONFIG ----------------
POSTS_PER_REQUEST = 20    # posts fetched per API call
REQUEST_DELAY = 0.5       # seconds to sleep between API calls
MAX_POSTS = None           
FLUSH_EVERY = 100         # write posts.json to disk after this many new posts
# ----------------------------------------------------
def load_existing_posts():
    if POSTS_JSON_PATH.exists():
        with open(POSTS_JSON_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_all_posts(posts_list):
    with open(POSTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(posts_list, f, ensure_ascii=False, indent=2)


def get_total_posts():
    info = client.blog_info(BLOG_NAME)
    return info["blog"]["total_posts"]


def check_rate_limit():
    """Look at the remaining request budget and pause if it's getting low."""
    try:
        limits = client.get_ratelimit_data()
        remaining = limits.get("perhour_remaining")
        if remaining is not None and remaining < 20:
            print(f"  only {remaining} requests left this hour - pausing 60s")
            time.sleep(60)
    except Exception:
        pass  # don't let a missing/odd ratelimit response kill the run

def fetch_new_posts(already_downloaded):
    """Fetches only the newest (total - already_downloaded) posts, newest-first,
    and yields them one at a time."""
    total = get_total_posts()
    new_count = total - already_downloaded
    if MAX_POSTS is not None:
        new_count = min(new_count, MAX_POSTS)
    if new_count <= 0:
        print("Nothing new to fetch.")
        return

    print(f"{already_downloaded} post(s) already saved, {total} on blog - fetching {new_count} new post(s)")

    offset = 0
    while offset < new_count:
        batch_size = min(POSTS_PER_REQUEST, new_count - offset)
        resp = client.posts(BLOG_NAME, limit=batch_size, offset=offset)
        posts = resp.get("posts", [])
        if not posts:
            break  # blog had fewer posts than total_posts claimed

        for post in posts:
            yield post

        offset += len(posts)
        print(f"  ...{offset}/{new_count} new posts fetched")

        check_rate_limit()
        time.sleep(REQUEST_DELAY)


def normalize_media(media):
    """NPF 'media' shows up as a single dict (video) or a list of size
    variants (image, largest-first) - always return a list."""
    if isinstance(media, dict):
        return [media]
    if isinstance(media, list):
        return media
    return []


def iter_media_urls(post):
    """Pull every image/video URL out of a post plus reblog trail content.
    consume_in_npf_by_default=True means content is always NPF block
    shape, regardless of how the post was originally authored — so
    is_blocks_post_format must not be used to decide how to parse it."""
    urls = []

    def urls_from_blocks(blocks):
        for block in blocks:
            if not isinstance(block, dict):
                print(f"  unexpected block (skipped): {type(block).__name__} -> {block!r}")
                continue
            media = normalize_media(block.get("media"))
            if media:
                urls.append(media[0]["url"])

    urls_from_blocks(post.get("content", []))
    for trail_item in post.get("trail", []):
        urls_from_blocks(trail_item.get("content", []))

    return urls
 
_SIZED_MEDIA_RE = re.compile(r'/([0-9a-f]+)/([0-9a-f-]+)/s\d+x\d+/[^/]+$')

def local_media_filename(url):
    clean = url.split("?")[0].rstrip("/")
    m = _SIZED_MEDIA_RE.search(clean)
    if m:
        ext = Path(clean).suffix
        return f"{m.group(1)}_{m.group(2)}{ext}"
    return Path(clean).name
 
def download_media(url):
    name = local_media_filename(url)
    out_path = MEDIA_DIR / name
    if out_path.exists():
        return
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(resp.content)
    except requests.RequestException as e:
        print(f"    failed to download {url}: {e}")

def main():
    global OUTPUT_DIR
    global MEDIA_DIR
    global POSTS_JSON_PATH
    global BLOG_NAME
    global client 
    
    parser = argparse.ArgumentParser(description="Crawl through a tumblr blog using Tumblr API")
    parser.add_argument("CONSUMER_KEY", help="Consumer key generated by the tumblr API. Check the github documentation for help on how to obtain one")
    parser.add_argument("BLOG_NAME", 
                        help="The name of your blog without .tumblr.com, eg \"staff\"")
    parser.add_argument("OUTPUT_DIR", 
                        help="The location where your blog will be downloaded, eg \"D:\MyFolder \"")
    args = parser.parse_args()
    CONSUMER_KEY = args.CONSUMER_KEY
    BLOG_NAME = args.BLOG_NAME         #
    OUTPUT_DIR = Path(args.OUTPUT_DIR).resolve()
    
    MEDIA_DIR = OUTPUT_DIR / BLOG_NAME
    POSTS_JSON_PATH = MEDIA_DIR / "posts.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    client = pytumblr2.TumblrRestClient(CONSUMER_KEY,consume_in_npf_by_default=True, convert_npf_to_legacy_html=True)
    posts_list = load_existing_posts()
    print(f"{len(posts_list)} post(s) already saved in {POSTS_JSON_PATH}")

    new_posts_collected = []   # newest-first; prepended to posts_list at the end
    new_posts = 0
    failed_posts = 0

    try:
        for post in fetch_new_posts(len(posts_list)):
            post_id = str(post["id"])
            try:
                new_posts_collected.append(post)
                new_posts += 1
                for url in iter_media_urls(post):
                    download_media(url)

                if new_posts % FLUSH_EVERY == 0:
                    save_all_posts(new_posts_collected + posts_list)
                    print(f"  flushed posts.json ({len(new_posts_collected) + len(posts_list)} total)")
            except Exception as e:
                failed_posts += 1
                print(f"  problem with post {post_id}: {e}")
    finally:
        posts_list = new_posts_collected + posts_list
        save_all_posts(posts_list)  # always flush, even on Ctrl+C or a crash

    print(f"\nDone. {new_posts} new post(s) saved, {failed_posts} failed.")
    print(f"Posts:  {POSTS_JSON_PATH}  ({len(posts_list)} total)")
    print(f"Media:  {MEDIA_DIR}")

if __name__ == "__main__":
    main()