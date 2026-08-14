# -*- coding: utf-8 -*-
"""
crawler_file.py

Generates an html file from a blog crawl produced by tumblrcrawler.py
"""
import re
import json
import argparse
import sys
from collections import Counter
from pathlib import Path
from html import escape
 
# ── Parsing ────────────────────────────────────────────────────────────────────
_TAGS = Counter()
 
def parse_entries_json(filepath: Path) -> list[dict]:
    """Turns a json file into a list of dictionaries, which each element of the list being one post"""
    text = filepath.read_text(encoding="utf-8")
    blocks = json.loads(text)
    return blocks

# ── CSS ─────────────────────────────────────────────────────────────
 
CSS = """
:root {
    --bg:        #0f0f11;
    --surface:   #1a1a1f;
    --border:    #2e2e38;
    --accent:    #a78bfa;
    --accent2:   #f472b6;
    --text:      #e4e4f0;
    --muted:     #7c7c99;
    --tag-bg:    #25252f;
    --radius:    12px;
    --font-body: 'Georgia', 'Times New Roman', serif;
    --font-ui:   'Inter', 'Segoe UI', system-ui, sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: var(--bg); color: var(--text);
    font-family: var(--font-body); font-size: 16px;
    line-height: 1.7; padding: 2rem 1rem 4rem;
}
header {
    text-align: center; padding: 3rem 1rem 2.5rem;
    border-bottom: 1px solid var(--border); margin-bottom: 2.5rem;
}
header h1 {
    font-family: var(--font-ui); font-size: 1.5rem; font-weight: 700;
    letter-spacing: -.02em;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
figure iframe {
    width: 100%;
    height: auto;
    min-height: 200px;
    border: none;
    display: block;
}
figure.tmblr-embed iframe {
    aspect-ratio: 16/9;   
}
figure {
    margin: 0;
}
figure[data-provider="spotify"] iframe,
figure:has(iframe.spotify_audio_player) iframe {
    width: 100%;
    height: 380px;      
    aspect-ratio: unset;
    display: block;
    border: none;
}
header p { font-family: var(--font-ui); font-size: .85rem; color: var(--muted); margin-top: .4rem;}
.feed { max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.5rem;}
.tagsearch { max-width: 220px; max-height: 240px; margin: 0 auto; display: flex;  flex-flow: row wrap; gap: 0.25rem;overflow-y: auto;
    overflow-x: hidden;}
.tagsearch .tags {display: contents;cursor: pointer;user-select: none;}
.tagsearch .tags .tag.committed {order: -1;background: var(--accent); color: var(--text)}
.tagsearch .tags .tag.hidden {display: none;}
.tagsearch .tags .tag:hover{ border-color: var(--accent);}
.post {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); overflow: hidden; transition: border-color .2s;
}
.post.hidden {display: none;}
.post:hover { border-color: var(--accent);}
.post-inner { display: flex; flex-direction: column; }
.tmblr-full { background: var(--surface); overflow: hidden; }
.tmblr-full img { width: 100%; height: auto; max-height: 640px; object-fit: contain; display: block; }
.tmblr-full video { width: 100%; height: auto; max-height: 640px; object-fit: contain; display: block; }
.tmblr-full + .tmblr-full { border-top: 1px solid var(--border); }
.post-content { padding: 1.4rem 1.6rem; display: flex; flex-direction: column; gap: .75rem; min-width: 0; }
.post-meta {
    font-family: var(--font-ui); font-size: .72rem; color: var(--muted);
    display: flex; align-items: center; gap: .6rem; flex-wrap: wrap;
}
.post-meta a { color: var(--accent); text-decoration: none; }
.post-meta a:hover { text-decoration: underline; }
.post-title { font-family: var(--font-ui); font-size: 1rem; font-weight: 600; color: var(--text); }
.post-body { font-size: .95rem; color: var(--text); word-break: break-word; }
.post-body p { margin-bottom: .5rem; }
.post-body p:last-child { margin-bottom: 0; }
.post-body .question blockquote {
    border-left: 3px solid var(--accent); margin: .6rem 0;
    padding-left: .9rem; color: var(--muted); font-style: italic;
}
.post-body blockquote {
    border-left: 3px solid var(--accent); margin: .6rem 0;
    padding-left: .9rem; color: var(--text);
}
.post-body a { color: var(--accent); }
.poll-row {display: block; background: var(--tag-bg); border: 1px solid var(--border);
    border-radius: 20px; padding: 10px 16px; margin-bottom: 12px; color: var(--muted); text-decoration: none;}
.poll-row p {margin: 0; }
.tags { display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .25rem; }
.tag {
    background: var(--tag-bg); color: var(--muted); font-family: var(--font-ui);
    font-size: .7rem; padding: .2rem .55rem; border-radius: 999px; border: 1px solid var(--border);
}
.npf_color_joey {color: #ff4b33;}
.npf_color_monica {color: #ff9400;}
.npf_color_phoebe {color: #e2a300;}
.npf_color_ross {color: #0bda51;}
.npf_color_rachel {color: #1e90ff;}
.npf_color_chandler {color: #8f00ff;}
.npf_color_niles {color: #ff69b4;}
.npf_color_frasier {color: #191970;}
.npf_color_mr_big {color: #051219;}
.no-body { color: var(--muted); font-style: italic; font-size: .9rem; }
.missing-img {
    min-height: 60px; display: flex; align-items: center; justify-content: center;
    font-family: var(--font-ui); font-size: .78rem; color: var(--muted);
    text-align: center; padding: 1rem; background: var(--background);
}
ol li {
    list-style-position: inside;
}
/* ── Audio posts (Tumblr audio) ── */
.audio-caption {display: flex; align-items: center; gap: .9rem;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 10px; padding: .65rem .9rem; }
.audio-details {display: flex; flex-direction: column; gap: .1rem;
    flex: 1; min-width: 0;}
.tmblr-audio-meta.title {font-family: var(--font-ui);font-weight: 600;
    font-size: .88rem; color: #fff; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; }
.tmblr-audio-meta.artist {font-family: var(--font-ui); font-size: .78rem;
    color: rgba(255,255,255,.8); white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; }
.tmblr-audio-meta.album:empty { display: none;}
.tmblr-full img.album-cover {width: 48px; height: 48px; border-radius: 8px;
    object-fit: cover; flex-shrink: 0;}
.tmblr-full img.album-cover:not([src]),
.tmblr-full img.album-cover[src=""] {
    display: none;
}
.tmblr-full audio {width: 100%; margin-top: .5rem; accent-color: var(--accent);
    color-scheme: dark; }

/* ── Toolbar ── */
.toolbar {position: absolute;top: 1.25rem;left: 50%;transform: translateX(-50%);
z-index: 100;display: flex;align-items: center;gap: .5rem;}
.toolbar.left {left: 35%}
.search-wrap {position: relative;}
.search-input {background: var(--surface);border: 1px solid var(--border);border-radius: var(--radius);color: var(--text);font-family: var(--font-ui);font-size: .85rem;padding: .4rem .75rem;width: 220px;outline: none;
transition: border-color .2s;}
.search-input.left {width:80px;}
.search-input:focus { border-color: var(--accent); }
.search-input::placeholder { color: var(--muted); }
.dropdown {position: absolute;top: calc(100% + .5rem);left: 0;width: 240px;
background: var(--surface);border: 1px solid var(--border);border-radius: var(--radius);padding: .5rem;display: flex;flex-direction: column;gap: .25rem;box-shadow: 0 8px 24px rgba(0,0,0,.4);}
.dropdown.hidden {display: none;}
.dropdown-label {font-family: var(--font-ui);font-size: .65rem;text-transform: uppercase;letter-spacing: .08em;color: var(--muted);padding: .35rem .5rem .15rem;}
.dropdown-row {display: flex;align-items: center;justify-content: space-between;padding: .4rem .6rem;border-radius: 8px;transition: background .15s;}
.dropdown-row:hover {background: var(--tag-bg);}
.dropdown-row span {font-family: var(--font-ui);font-size: .85rem;color: var(--text);}
/* toggle switch */
.toggle {width: 36px;height: 20px;background: var(--border);border-radius: 999px;position: relative;cursor: pointer;transition: background .25s;flex-shrink: 0;}
.toggle.active { background: var(--accent); }
.toggle-btn {position: absolute;top: 3px;left: 3px;width: 14px;height: 14px;background: var(--text);border-radius: 50%;transition: left .25s;}
.toggle.active .toggle-btn { left: 19px; }

/* action buttons */
.action-btn {background: var(--surface);border: 1px solid var(--border);border-radius: var(--radius);color: var(--text);font-family: var(--font-ui);
    font-size: .85rem;padding: .4rem .85rem;cursor: pointer;transition: border-color .2s;white-space: nowrap;}
.action-btn:hover { border-color: var(--accent); }
"""

# ── Video,Image,Embed Parsing ─────────────────────────────────────────────────────────────
_SIZED_MEDIA_RE = re.compile(r'/([0-9a-f]+)/([0-9a-f-]+)/s\d+x\d+/[^/]+$')

def local_media_filename(url):
    clean = url.split("?")[0].rstrip("/")
    m = _SIZED_MEDIA_RE.search(clean)
    if m:
        ext = Path(clean).suffix
        return f"{m.group(1)}_{m.group(2)}{ext}"
    return Path(clean).name
def localize_image_url(url: str, archive_path: Path) -> str:
    name = local_media_filename(url)
    local_path = archive_path / name
    if local_path.is_file():
        return f'{escape(name)}"'
    print(f"Couldn't locate file {url}")
    return url
def localize_video_url(url: str, archive_path: Path) -> str:
    parts = url.split("?")[0].rstrip("/").split("/")
    name = parts[-1]
    local_path = archive_path / name
    if local_path.is_file():
        return f'{escape(name)}"'
    print(f"Couldn't locate file {url}")
    return url
def format_html(text, formatting):
    # Collect all formatting boundaries
    boundaries = {0, len(text)}
    for fmt in formatting:
        start = max(0, min(len(text), fmt["start"]))
        end = max(0, min(len(text), fmt["end"]))
        if start < end:
            boundaries.add(start)
            boundaries.add(end)
    boundaries = sorted(boundaries)
    result = []
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        segment = escape(text[start:end])
        active = [
            fmt for fmt in formatting
            if fmt["start"] <= start and fmt["end"] >= end
        ]
        for fmt in reversed(active):
            fmt_type = fmt["type"]

            if fmt_type == "bold":
                segment = f"<strong>{segment}</strong>"

            elif fmt_type == "italic":
                segment = f"<em>{segment}</em>"

            elif fmt_type == "link":
                url = escape(fmt.get("url", ""), quote=True)
                segment = f'<a href="{url}">{segment}</a>'

            elif fmt_type == "color":
                color = escape(fmt.get("hex", ""), quote=True)
                segment = f'<span style="color: {color};">{segment}</span>'
        result.append(segment)
    return "".join(result)

# ── HTML generation ─────────────────────────────────────────────────────────────
def build_body(post: dict,archive_path: Path) -> str:
    """Builds the body of the tumblr post"""
    body_html = r'<div class="post-body">'
    layout = 0
    if post["type"] == "answer":
        name = post["asking_name"]
        text = ""
        blog = f'<p><span class="tumblr_blog">{name}</span>:</p><blockquote>'
        if post.get("trail"):
            layout = len(post["trail"][0]["layout"][0]["blocks"])
            for i in range(layout):
                ask = post["trail"][0]["content"][i]["text"]
                text += f'<p>{ask}</p>'
        elif post.get("content"):
            layout = len(post["layout"][0]["blocks"])
            for i in range(layout):
                ask = post["content"][i]["text"]
                text += f'<p>{ask}</p>'
        body_html += blog
        body_html += f'<p>{text}</p></blockquote>'
    if post.get("trail"):
        for e in reversed(post.get("trail")):
            if e.get("blog"):
                name = e["blog"]["name"]
                url = e["blog"]["url"]
                post_id = e["post"]["id"]
                blog = f'<p><a class="tumblr_blog" href="{url}/post/{post_id}">{name}</a>:</p><blockquote>'
            else:
                name = e["broken_blog_name"] 
                blog = f'<p><span class="tumblr_blog">{name}</span>:</p><blockquote>'
            body_html += blog
        for e in post.get("trail"):
            for i in range(layout,len(e["content"])):
                if e["content"][i]["type"] == "text":
                    text = e["content"][i]["text"]
                    if e["content"][i].get("formatting"):
                        formatting = e["content"][i]["formatting"]
                        text = format_html(text,formatting)
                    content = f'<p style="white-space: pre-line;">{text}</p>'
                    body_html += content
                elif e["content"][i]["type"] == "image":
                    image = e["content"][i]["media"][0]
                    url = localize_image_url(image["url"],archive_path)
                    width = image["width"]
                    height = image["height"]
                    content = f'<div class="npf_row"><figure class="tmblr-full" data-orig-height="{height}" data-orig-width="{width}"><img src="{url}" loading="lazy" data-orig-height="{height}" data-orig-width="{width}"/></figure></div>'
                    body_html += content
                elif e["content"][i]["type"] == "video" and e["content"][i]["provider"] == "tumblr":
                    video = e["content"][i]
                    url = video["url"]
                    media = video["media"]
                    poster = video.get("poster")
                    filmstrip = video.get("filmstrip")
                    duration = video.get("duration")
                    src = localize_video_url(url,archive_path)
                    width = media["width"]
                    height = media["height"]
                    content = f'<figure class="tmblr-full" data-orig-height="{height}" data-orig-width="{width}" data-npf="{{"type":"video","provider":"tumblr","url":"{url}","media":{media},"poster":{poster},"filmstrip":{filmstrip},"duration":{duration}}}"><video controls="controls" playsinline="playsinline"><source src="{src}" loading="lazy" type="video/mp4"></source></video></figure>'
                    body_html += content 
                elif e["content"][i]["type"] == "video" and e["content"][i]["provider"] == "youtube":
                    video = e["content"][i]
                    url = video["url"]
                    width = video["embed_iframe"]["width"]
                    height = video["embed_iframe"]["height"]
                    embed_html = video["embed_html"]
                    content = f'<figure class="tmblr-full tmblr-embed" data-provider="youtube" data-url="{url}" data-orig-width="{width}" data-orig-height="{height}">{embed_html}</figure>'
                    body_html += content
                elif e["content"][i]["type"] == "audio" and e["content"][i]["provider"] == "spotify":
                    audio = e["content"][i]
                    url = audio["url"]
                    title = audio["title"]
                    artist = audio["artist"]
                    album = audio["album"]
                    poster = audio["poster"]
                    attribution = audio["attribution"]
                    embed_html = audio["embed_html"]
                    embed_url = audio["embed_url"]
                    npf_json = json.dumps({"type": "audio", "provider": "spotify", "url": url, "title": title, "artist": artist, "album": album, "poster": poster, "attribution": attribution, "embed_html": embed_html})
                    content = f'<figure data-npf=\'{escape(npf_json)}\'><iframe class="spotify_audio_player" src="{embed_url}" frameborder="0" allowtransparency="true" width="500" height="580"></iframe></figure>'
                    body_html += content
                elif e["content"][i]["type"] == "audio" and e["content"][i]["provider"] == "tumblr":
                    audio = e["content"][i]
                    url = audio["media"]["url"]
                    title = audio["title"]
                    artist = audio.get("artist") if audio.get("artist") else ""
                    album = audio.get("album") if audio.get("album") else ""
                    if  audio.get("poster"):
                        image = audio.get("poster")[0]["url"]
                    else:
                        image = None
                    url = re.sub(r"(https://64\.media\.tumblr\.com/[a-f0-9]+)(?:/[^/]+)+/[^/]+\.mp3$",r"\1.mp3",url)
                    local_path = archive_path / url
                    if not local_path.is_file():
                        url = audio["url"]
                    content = f"""<figure class="tmblr-full"><figcaption class="audio-caption"><span class="tmblr-audio-meta audio-details"><span class="tmblr-audio-meta title">{title}</span><span class="tmblr-audio-meta artist">{artist}</span><span class="tmblr-audio-meta album">{album}</span></span>"""
                    if image != None:
                        content += f"""<img class="album-cover" src="{image}" loading="lazy"/>""" 
                    content += f"""</figcaption><audio controls="controls"><source src="{url}" loading="lazy" type="audio/mpeg"></source></audio></figure>"""
                    body_html += content
                elif e["content"][i]["type"] == "poll":
                    poll = e["content"][i]
                    client_id = poll["client_id"]
                    question = poll["question"]
                    answers = poll["answers"]
                    settings = poll["settings"]
                    content = f"""<div data-npf='{{"type":"poll","client_id":{client_id},"question":{question},"answers":{answers},"settings":{settings} }}' class="poll-post"></div><p class="poll-question">{question}</p>"""
                    for answer in answers:
                        content += f'<a class="poll-row"><p>{answer["answer_text"]}</p></a>'
                    body_html += content
            body_html += r'</blockquote>'
    if post.get("content"):
        for i in range(layout,len(post["content"])):
            e = post["content"][i]
            if e["type"] == "text":
                text = e["text"]
                if e.get("formatting"):
                    formatting = e["formatting"]
                    text = format_html(text,formatting)
                content = f'<p style="white-space: pre-line;">{text}</p>'
                body_html += content
            elif e["type"] == "image":
                image = e["media"][0]
                url = localize_image_url(image["url"],archive_path)
                width = image["width"]
                height = image["height"]
                content = f'<div class="npf_row"><figure class="tmblr-full" data-orig-height="{height}" data-orig-width="{width}"><img src="{url}" loading="lazy" data-orig-height="{height}" data-orig-width="{width}"/></figure></div>'
                body_html += content
            elif e["type"] == "video" and e["provider"] == "tumblr":
                video = e
                url = video["url"]
                media = video["media"]
                poster = video.get("poster")
                filmstrip = video.get("filmstrip")
                duration = video.get("duration")
                src = localize_video_url(url,archive_path)
                width = media["width"]
                height = media["height"]
                content = f'<figure class="tmblr-full" data-orig-height="{height}" data-orig-width="{width}" data-npf="{{"type":"video","provider":"tumblr","url":"{url}","media":{media},"poster":{poster},"filmstrip":{filmstrip},"duration":{duration}}}"><video controls="controls" playsinline="playsinline"><source src="{src}" loading="lazy" type="video/mp4"></source></video></figure>'
                body_html += content
            elif e["type"] == "video" and e["provider"] == "youtube":
                video = e
                url = video["url"]
                width = video["embed_iframe"]["width"]
                height = video["embed_iframe"]["height"]
                embed_html = video["embed_html"]
                content = f'<figure class="tmblr-full tmblr-embed" data-provider="youtube" data-url="{url}" data-orig-width="{width}" data-orig-height="{height}">{embed_html}</figure>'
                body_html += content
            elif e["type"] == "audio" and e["provider"] == "spotify":
                audio = e
                url = audio["url"]
                title = audio["title"]
                artist = audio["artist"]
                album = audio["album"]
                poster = audio["poster"]
                attribution = audio["attribution"]
                embed_html = audio["embed_html"]
                embed_url = audio["embed_url"]
                npf_json = json.dumps({"type": "audio", "provider": "spotify", "url": url, "title": title, "artist": artist, "album": album, "poster": poster, "attribution": attribution, "embed_html": embed_html})
                content = f'<figure data-npf=\'{escape(npf_json)}\'><iframe class="spotify_audio_player" src="{embed_url}" frameborder="0" allowtransparency="true" width="500" height="580"></iframe></figure>'
                body_html += content
            elif e["type"] == "audio" and e["provider"] == "tumblr":
                audio = e
                url = audio["media"]["url"]
                title = audio["title"]
                artist = audio.get("artist") if audio.get("artist") else ""
                album = audio.get("album") if audio.get("album") else ""
                if  audio.get("poster"):
                    image = audio.get("poster")[0]["url"]
                else:
                    image = None
                url = re.sub(r"(https://64\.media\.tumblr\.com/[a-f0-9]+)(?:/[^/]+)+/[^/]+\.mp3$",r"\1.mp3",url)
                local_path = archive_path / url
                if not local_path.is_file():
                    url = audio["url"]
                content = f"""<figure class="tmblr-full"><figcaption class="audio-caption"><span class="tmblr-audio-meta audio-details"><span class="tmblr-audio-meta title">{title}</span><span class="tmblr-audio-meta artist">{artist}</span><span class="tmblr-audio-meta album">{album}</span></span>"""
                if image != None:
                    content += f"""<img class="album-cover" src="{image}" loading="lazy"/>""" 
                content += f"""</figcaption><audio controls="controls"><source src="{url}" loading="lazy" type="audio/mpeg"></source></audio></figure>"""
                body_html += content
            elif e["type"] == "poll":
                poll = e
                client_id = poll["client_id"]
                question = poll["question"]
                answers = poll["answers"]
                settings = poll["settings"]
                content = f"""<div data-npf='{{"type":"poll","client_id":{client_id},"question":{question},"answers":{answers},"settings":{settings} }}' class="poll-post"></div><p class="poll-question">{question}</p>"""
                for answer in answers:
                    content += f'<a class="poll-row"><p>{answer["answer_text"]}</p></a>'
                body_html += content
    return body_html + r'</div>'
def get_parent_blog_name(parent_post_url: str) -> str | None:
    """Extract the blog name from parent_post_url."""
    if not parent_post_url:
        return None
    patterns = [
        r'https?://([^./]+)\.tumblr\.com/',           # name.tumblr.com/post/...
        r'https?://www\.tumblr\.com/blog/view/([^/]+)/',  # tumblr.com/blog/view/name/...
        r'https?://([^./]+)\.blog/',                  # name.blog 
    ]
    for pattern in patterns:
        m = re.match(pattern, parent_post_url)
        if m and m.group(1) != "www":
            return m.group(1)
    return None
def build_post_html_crawler(entry: dict, archive_path: Path) -> str:
    """Turn a post formatted as a dictionary into an html <article>, for
    archives produced by tumblr_crawler.py (raw Tumblr API / PyTumblr2 shape)."""

    # meta
    date_fmt = entry["date"]
    meta_parts = [f'<span>{escape(date_fmt)}</span>']
    if entry.get("post_url"):
        meta_parts.append(
            f'<a href="{escape(entry["post_url"])}" target="_blank">#{escape(str(entry["id"]))}</a>'
        )
    if entry.get("parent_post_url"):
        reblogged_from = get_parent_blog_name(entry.get("parent_post_url"))
        if reblogged_from:
            meta_parts.append(
                f'<span>reblogged from <em>{escape(reblogged_from)}</em></span>'
            )
    meta_html = '<div class="post-meta">' + "".join(meta_parts) + '</div>'

    # title - only seen on original (non-reblog) text posts in the legacy API shape
    title_html = f'<div class="post-title">{escape(entry["title"])}</div>' if entry.get("title") else ""

   # body
    body_html = build_body(entry,archive_path)

    # tags
    tags_html = ""
    if entry.get("tags"):
        tags_html = (
            '<div class="tags">'
            + "".join(f'<span class="tag">#{escape(t)}</span>' for t in entry["tags"])
            + '</div>'
        )
        for tag in entry["tags"]:
            _TAGS[tag.strip().lower()] += 1

    content_inner = "\n".join(filter(None, [meta_html, title_html, body_html, tags_html]))
    content_div = f'<div class="post-content">{content_inner}</div>'
    return f'<article class="post"><div class="post-inner">{content_div}</div></article>'
def build_html(entries: list[dict], blog_title: str, blog_name: str, archive_path: Path) -> str:
    """Create the final archive html file"""
    posts_html = "\n".join(build_post_html_crawler(e,archive_path) for e in entries) 
    OrderedTagsHtml = ""
    for tag in _TAGS.most_common():
        OrderedTagsHtml = OrderedTagsHtml +  r'<div class="tags"><span class="tag">' + tag[0] + r'</span></div>' + '\n\t\t' 
    temp = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{blog_name}</title>
<style>{CSS}</style>
</head>
<body>
<div class="toolbar left">
    <div class="search-wrap">
        <button class="search-input left" id="theme-button">Theme</button>
        <div id="theme-dropdown" class="dropdown hidden">
            <div class="dropdown-label">Themes</div>
            <div class="dropdown-row">
                <span>Nightfall</span>
                <div class="toggle active" id="theme_1">
                    <div class="toggle-btn"></div>
                </div>
            </div>
            <div class="dropdown-row">
                <span>Parchment</span>
                <div class="toggle" id="theme_2">
                    <div class="toggle-btn"></div>
                </div>
            </div>
            <div class="dropdown-row">
                <span>Abyss</span>
                <div class="toggle" id="theme_3">
                    <div class="toggle-btn"></div>
                </div>
            </div>
            <div class="dropdown-row">
                <span>Strawberry Milk</span>
                <div class="toggle" id="theme_4">
                    <div class="toggle-btn"></div>
                </div>
            </div>
            <div class="dropdown-row">
                <span>Citrus</span>
                <div class="toggle" id="theme_5">
                    <div class="toggle-btn"></div>
                </div>
            </div>
        </div>
    </div> 
</div>
<div class="toolbar">
  <div class="search-wrap">
    <input class="search-input" type="text" placeholder="Search posts…" id="search-input">
    <div id="menu-dropdown" class="dropdown hidden">
      <div class="dropdown-label">Filters</div>
      <div class="dropdown-row">
        <span>Video</span>
        <div class="toggle active" id="toggle-videos">
          <div class="toggle-btn"></div>
        </div>
      </div>
      <div class="dropdown-row">
        <span>Image</span>
        <div class="toggle active" id="toggle-images">
          <div class="toggle-btn"></div>
        </div>
      </div>
      <div class="dropdown-row">
        <span>Text</span>
        <div class="toggle active" id="toggle-text">
          <div class="toggle-btn"></div>
        </div>
      </div>
      <div class="dropdown-label">Tags</div>
      <div class="tagsearch">
        {OrderedTagsHtml}
      </div>
    </div>
  </div>
</div>
<header>
  <h1>{blog_title}</h1>
  <p>Tumblr Archive &mdash; {len(entries)} posts</p>
</header>
<main class="feed">
{posts_html}
</main>
"""
    return temp + r"""<script>
    const searchInput = document.getElementById('search-input');
    const themeButton = document.getElementById('theme-button');
    const menuDropdown = document.getElementById('menu-dropdown');
    const themeDropdown = document.getElementById('theme-dropdown');
    const committedTags = [];
    const theme1 = document.getElementById('theme_1');
    const theme2 = document.getElementById('theme_2');
    const theme3 = document.getElementById('theme_3');
    const theme4 = document.getElementById('theme_4');
    const theme5 = document.getElementById('theme_5');
    let video_filter = true;
    let image_filter = true;
    let text_filter = true;
    var r = document.querySelector(':root');

    searchInput.addEventListener('focus', () => {
        menuDropdown.classList.remove('hidden');
    });
    themeButton.addEventListener('click', () => {
        themeDropdown.classList.remove('hidden');
    });
    menuDropdown.addEventListener('mousedown', (e) => {
        e.preventDefault();
    });
    themeDropdown.addEventListener('mousedown', (e) => {
        e.preventDefault();
    });
    searchInput.addEventListener('blur', () => {
        menuDropdown.classList.add('hidden');
    });
    themeButton.addEventListener('blur', () => {
        themeDropdown.classList.add('hidden');
    });
    document.querySelectorAll('.tagsearch .tag').forEach(tag => {
        tag.addEventListener('click', () => {
            if (tag.classList.contains('committed')) {
                tag.classList.remove('committed');
                const index = committedTags.indexOf(tag.textContent.toLowerCase());
                committedTags.splice(index, 1);
            }
            else {
                committedTags.push(tag.textContent.toLowerCase())
                tag.classList.add('committed');
            }
            Search(searchInput.value.toLowerCase()); 
        });
    });
    theme1.addEventListener('click', () => {
        theme1.classList.add('active');
        theme2.classList.remove('active');
        theme3.classList.remove('active')
        theme4.classList.remove('active')
        theme5.classList.remove('active')
        r.style.setProperty('--bg',      '#0f0f11');
        r.style.setProperty('--surface', '#1a1a1f');
        r.style.setProperty('--border',  '#2e2e38');
        r.style.setProperty('--accent',  '#a78bfa');
        r.style.setProperty('--accent2', '#f472b6');
        r.style.setProperty('--text',    '#e4e4f0');
        r.style.setProperty('--muted',   '#7c7c99');
        r.style.setProperty('--tag-bg',  '#25252f');
    });
    theme2.addEventListener('click', () => {
        theme1.classList.remove('active');
        theme2.classList.add('active');
        theme3.classList.remove('active');
        theme4.classList.remove('active');
        theme5.classList.remove('active');
        r.style.setProperty('--bg',      '#f5f0e8');
        r.style.setProperty('--surface', '#ede6d6');
        r.style.setProperty('--border',  '#d4c9b0');
        r.style.setProperty('--accent',  '#8b5e3c');
        r.style.setProperty('--accent2', '#c2745a');
        r.style.setProperty('--text',    '#2c1f0e');
        r.style.setProperty('--muted',   '#8a7560');
        r.style.setProperty('--tag-bg',  '#e0d8c8');
    });
    theme3.addEventListener('click', () => {
        theme1.classList.remove('active');
        theme2.classList.remove('active');
        theme3.classList.add('active');
        theme4.classList.remove('active');
        theme5.classList.remove('active');
        r.style.setProperty('--bg',      '#060d12');
        r.style.setProperty('--surface', '#0d1f2d');
        r.style.setProperty('--border',  '#163347');
        r.style.setProperty('--accent',  '#00c9a7');
        r.style.setProperty('--accent2', '#0096ff');
        r.style.setProperty('--text',    '#cce8e0');
        r.style.setProperty('--muted',   '#4a7f72');
        r.style.setProperty('--tag-bg',  '#0d2233');
    });
    theme4.addEventListener('click', () => {
        theme1.classList.remove('active');
        theme2.classList.remove('active');
        theme3.classList.remove('active');
        theme4.classList.add('active');
        theme5.classList.remove('active');
        r.style.setProperty('--bg',      '#ecf7f7');
        r.style.setProperty('--surface', '#efc7be');
        r.style.setProperty('--border',  '#e1dfe0');
        r.style.setProperty('--accent',  '#ff6b9d');
        r.style.setProperty('--accent2', '#ff3d7f');
        r.style.setProperty('--text',    '#bb3377');
        r.style.setProperty('--muted',   '#fe46a5');
        r.style.setProperty('--tag-bg',  '#ffe9eb');
    });
    theme5.addEventListener('click', () => {
        theme1.classList.remove('active');
        theme2.classList.remove('active');
        theme3.classList.remove('active');
        theme4.classList.remove('active');
        theme5.classList.add('active');
        r.style.setProperty('--bg',      '#1a1000');
        r.style.setProperty('--surface', '#261800');
        r.style.setProperty('--border',  '#4a3200');
        r.style.setProperty('--accent',  '#ffaa00');
        r.style.setProperty('--accent2', '#ff6600');
        r.style.setProperty('--text',    '#fff3cc');
        r.style.setProperty('--muted',   '#b8862a');
        r.style.setProperty('--tag-bg',  '#332200');
    });

    // Search
    function Search(term) {
        function escapeRegex(str) {
            return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }
    document.querySelectorAll('.post').forEach(post => {
        const image = post.querySelector('img');
        const video = post.querySelector('video');
        var tags_match = true;
        committedTags.forEach(committedTag => {
            var matchesCommitted = false;
            post.querySelectorAll('.tag').forEach(tag => {
                matchesCommitted = (matchesCommitted||new RegExp('^' + escapeRegex(committedTag) + '$').test(tag.textContent.toLowerCase().slice(1)));
            }); 
            tags_match = tags_match&&matchesCommitted; 
        });
        if (term.charAt(0) == "#") {
            var matches = false;
            post.querySelectorAll('.tag').forEach(tag => {
                matches = (matches||new RegExp('^' + escapeRegex(term)).test(tag.textContent.toLowerCase()))
            });
            if (!(matches || term === '' )||(!video_filter&&video)||(!image_filter&&image)||(!text_filter&&!image&&!video)||!(tags_match)) {
                post.classList.add('hidden');
            } else {
                post.classList.remove('hidden');
            } 
        }
        else { 
        const matches = new RegExp('\\b' + escapeRegex(term)).test(post.textContent.toLowerCase());
        if (!(matches || term === '' )||(!video_filter&&video)||(!image_filter&&image)||(!text_filter&&!image&&!video)||!(tags_match)) {
            post.classList.add('hidden');
        } else {
            post.classList.remove('hidden');
        }
        }   
    });
    document.querySelectorAll('.tagsearch .tag').forEach(tag => {
        const matches = new RegExp('^' + escapeRegex(term).slice(1)).test(tag.textContent.toLowerCase());
        if (!(matches || term === '' )&&(term.charAt(0) == "#")) {
            tag.classList.add('hidden');
        } else {
            tag.classList.remove('hidden');
        }
    });
    }
    function lazyLoadIframes() {
    const iframes = document.querySelectorAll('iframe[data-src]');
    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const iframe = entry.target;
                iframe.src = iframe.dataset.src;
                observer.unobserve(iframe);
            }
        });
    }, {
        root: null,
        rootMargin: '200px',
        threshold: 0.0
    });
    iframes.forEach(iframe => observer.observe(iframe));
    }
    lazyLoadIframes();
    searchInput.addEventListener('input', () => Search(searchInput.value.toLowerCase(), false));

    // Toggle switches 
    document.getElementById('toggle-videos').addEventListener('click', function() {
        this.classList.toggle('active');
        video_filter = !video_filter;
        Search(term = searchInput.value.toLowerCase());
    });
    document.getElementById('toggle-images').addEventListener('click', function() {
        this.classList.toggle('active');
        image_filter = !image_filter;
        Search(term = searchInput.value.toLowerCase());
    });
    document.getElementById('toggle-text').addEventListener('click', function() {
        this.classList.toggle('active');
        text_filter = !text_filter;
        Search(term = searchInput.value.toLowerCase());
    });
</script>
</body>
</html>"""
 
# ── Entry point ─────────────────────────────────────────────────────────────────
 
def main():
    parser = argparse.ArgumentParser(description="Render a Tumblr archive .txt as an HTML viewer.")
    parser.add_argument("archive", help=r"Path to the archive of a blog, eg D:\MyFolder\blogname")
    parser.add_argument("--blog_name", default="Tumblr Archive", 
                        help="The name your browser will display for the html file")
    parser.add_argument("--blog_title", 
                        help="The blog title display at the top of your feed. By default, set to the name of your blog")
    args = parser.parse_args()
    
    archive_path = Path(args.archive).resolve()
    if not archive_path.exists():
        print(f"Error: file not found: {archive_path}", file=sys.stderr)
        sys.exit(1)
 
    output_path = archive_path / f'{args.blog_name}.html'
    texts_answers = archive_path / "posts.json"
    
    print(f"Parsing {archive_path.name} …")
    entries = parse_entries_json(texts_answers)
    print(f"Found {len(entries)} entries.")
    
    blog_title = args.blog_title if args.blog_title else archive_path.name
    html = build_html(entries, blog_title,args.blog_name,archive_path)
    output_path.write_text(html, encoding="utf-8")
    print(f"Written to: {output_path}")
    print(f"Done — open: {output_path}")
 
if __name__ == "__main__":
    main()
