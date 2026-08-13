"""
crawler_file.py

Generates an html file from a TumblThree archive of a blog. By default assumes 
a json formatted archive, though it also works with the text format.
"""
import re
import json
import sorter
import argparse
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime
from html import escape
 
# ── Parsing ────────────────────────────────────────────────────────────────────
 
_FIELDS = r'(?:Tags|Downloaded files|Post id|Date|Post url|Slug|Reblog key|Reblog url|Reblog name|Title|Body|Question|Answer)'
_ANCHOR  = rf'^{_FIELDS}\s*:'
_TAGS = Counter()
 
def parse_entries_json(filepath: Path) -> list[dict]:
    """Turns a json file into a list of dictionaries, which each element of the list being one post"""
    text = filepath.read_text(encoding="utf-8")
    blocks = json.loads(text)
    return blocks

def parse_entries_text(filepath: Path) -> list[dict]:
    """Turns a text file into a list of dictionaries, which each element of the list being one post"""
    def _extract_field_block(text: str, field: str) -> tuple[str, str]:
        """Return (field_content, text_with_field_removed)."""
        pattern = rf'^{re.escape(field)}:\s*(.*?)(?={_ANCHOR}|\Z)'
        m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if not m:
            return "", text
        content = m.group(1).strip()
        cleaned = text[:m.start()] + text[m.end():]
        return content, cleaned.strip()
    text = filepath.read_text(encoding="utf-8")
    raw_blocks = re.split(r'(?=^Post id:)', text, flags=re.MULTILINE)
    entries = []
 
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
 
        # Pull out multi-line fields first, removing them from the block
        dl_raw,   block = _extract_field_block(block, "Downloaded files")
        body,     block = _extract_field_block(block, "Body")
        tags_raw, block = _extract_field_block(block, "Tags")
        question_raw, block = _extract_field_block(block, "Question")
        answer_raw, block = _extract_field_block(block, "Answer")
 
        # Parse downloaded filenames (comma-separated, possibly multi-line)
        downloaded = [
            t.strip().strip('"').strip("'")
            for t in re.split(r',', dl_raw)
            if t.strip().strip('"').strip("'")
        ]
 
        # Now only single-line fields remain — safe to use a simple line regex
        def field(name, b=block):
            m = re.search(rf'^{re.escape(name)}:\s*(.*)$', b, re.MULTILINE)
            return m.group(1).strip() if m else ""
 
        date_str = field("Date")
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S GMT")
        except ValueError:
            date = datetime.min
        if question_raw :
            entries.append({
                "post_id":     field("Post id"),
                "date":        date,
                "date_str":    date_str,
                "post_url":    field("Post url"),
                "slug":        field("Slug"),
                "reblog_url":  field("Reblog url"),
                "reblog_name": field("Reblog name"),
                "question":    question_raw,
                "answer":    answer_raw,
                "tags":        tags_raw,
                "downloaded":  None,
                "title":       None,
                "body":        None,
            })
        else:
            entries.append({
                "post_id":     field("Post id"),
                "date":        date,
                "date_str":    date_str,
                "post_url":    field("Post url"),
                "slug":        field("Slug"),
                "reblog_url":  field("Reblog url"),
                "reblog_name": field("Reblog name"),
                "title":       field("Title"),
                "body":        body,
                "tags":        tags_raw,
                "downloaded":  downloaded,
                "question":    None,
            })
 
    return entries
 
 
# ── HTML generation ─────────────────────────────────────────────────────────────
 
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
def localize_media_sources(body: str, downloaded: list[str]) -> str:
    """Replaces online media sources with the locally downloaded files."""
    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    VIDEO_EXTS = {'.mp4', '.mov', '.webm'}

    # One ordered queue — preserves the original download order
    remaining = list(downloaded)

    def replace_figure(m):
        figure_html = m.group(0)

        if re.search(r'<video', figure_html, re.IGNORECASE):
            target_exts = VIDEO_EXTS
        elif re.search(r'<img', figure_html, re.IGNORECASE):
            target_exts = IMAGE_EXTS
        else:
            return figure_html

        # Find the first file in remaining that matches this figure's type
        for i, fname in enumerate(remaining):
            if Path(fname).suffix.lower() in target_exts:
                remaining.pop(i)
                if re.search(r'<video', figure_html, re.IGNORECASE):
                    figure_html = re.sub(r'\sposter="[^"]*"', '', figure_html)
                    figure_html = re.sub(r'autoplay="autoplay" ','', figure_html)             
                    figure_html = re.sub(r' muted="muted"','', figure_html)
                else:
                    figure_html = re.sub(r'\ssrcset="[^"]*"', '', figure_html)
                    figure_html = re.sub(r'\ssizes="[^"]*"', '', figure_html)
                figure_html = re.sub(r'src="[^"]*"', f'src="{escape(fname)}" loading="lazy"', figure_html)
                return figure_html

        return figure_html  # no matching file found — leave untouched

    return re.sub(r'<figure[^>]*>.*?</figure>', replace_figure, body, flags=re.DOTALL | re.IGNORECASE)

def fix_youtube_embeds(body: str) -> str:
    """Remove origin=https://safe.txmblr.com from youtube embeds"""
    def fix_src(m):
        src = m.group(1)
        src = re.sub(r'(?:&amp;|&)origin=[^&"]+', '', src)
        return f'data-src="{src}"'  
    return re.sub(r'src="(https://www\.youtube\.com/embed/[^"]+)"', fix_src, body)

def build_post_html_text(entry: dict,archive_path: Path) -> str:
    """Turn a post formatted as a dictionary into an html <article>, for archives that use text format"""
    has_media = bool(entry.get("downloaded"))
 
    # meta
    date_fmt = (
        entry.get("date").strftime("%b %d, %Y — %H:%M UTC")
        if entry.get("date") != datetime.min else entry.get("date_str")
    )
    meta_parts = [f'<span>{escape(date_fmt)}</span>']
    if entry.get("post_url"):
        meta_parts.append(
            f'<a href="{escape(entry["post_url"])}" target="_blank">#{escape(entry["post_id"])}</a>'
        )
    if entry.get("reblog_name") and entry.get("reblog_name").strip().lower() not in ("", "title:"):
        meta_parts.append(
            f'<span>reblogged from <em>{escape(entry["reblog_name"])}</em></span>'
        )
    meta_html = '<div class="post-meta">' + "".join(meta_parts) + '</div>'
 
    # title
    title_html = f'<div class="post-title">{escape(entry["title"])}</div>' if entry["title"] else ""
 
    # body 
    body_html = ""
    if entry.get("body"):
        body = entry.get("body")
        if has_media:
            body = localize_media_sources(body, entry["downloaded"])
            for i in range(len(entry["downloaded"])):
                p = Path(entry["downloaded"][i])
                if not (archive_path / p).is_file():
                    if (archive_path / p.with_suffix(".png")).is_file():
                        entry["downloaded"][i] = str(p.with_suffix(".png"))
                        #print(f'Successfully fixed {str(p)} by converting to .png')
                    elif (archive_path / p.with_suffix(".jpg")).is_file():
                        entry["downloaded"][i] = str(p.with_suffix(".jpg"))
                        #print(f'Successfully fixed {str(p)} by converting to .jpg')
                    else:
                        print(f'ERROR: Couldn\'t fix {str(p)}')
        body = fix_youtube_embeds(body)
        if body:
            body_html = '<div class="post-body">' + body + '</div>'
        elif not has_media:
            plain = re.sub(r'<[^>]+>', '', body).strip()
            if plain:
                body_html = f'<div class="post-body"><p>{escape(plain)}</p></div>'
    elif entry["question"]:
        question = entry["question"]
        answer = entry["answer"]
        body_html = '<div class="post-body"><div class="question"><blockquote>' + question + '</blockquote></div>' + answer + '</div>'
    if not body_html and not has_media:
        body_html = '<div class="no-body">[no text content]</div>'
 
    # tags
    tags_html = ""
    if entry["tags"]:
       tag_list = [t.strip() for t in entry["tags"].split(",") if t.strip()]
       if tag_list:
           tags_html = (
               '<div class="tags">'
               + "".join(f'<span class="tag">#{escape(t)}</span>' for t in tag_list)
               + '</div>'
           )
       for tag in tag_list:
           _TAGS[tag.strip().lower()] += 1

    content_inner = "\n".join(filter(None, [meta_html, title_html, body_html, tags_html]))
    content_div = f'<div class="post-content">{content_inner}</div>'
    return f'<article class="post"><div class="post-inner">{content_div}</div></article>'

def build_post_html_json(entry: dict, archive_path: Path) -> str:
    """Turn a post formatted as a dictionary into an html <article>, for archives that use json format"""
    has_media = "downloaded-media-files" in entry
 
    # meta
    date_fmt = (entry["date-gmt"])
    meta_parts = [f'<span>{escape(date_fmt)} GMT</span>']
    if entry["url"]: 
        meta_parts.append(
            f'<a href="{escape(entry["url"])}" target="_blank">#{escape(entry["id"])}</a>'
        )
    if "reblogged-from-name" in entry:
        meta_parts.append(
            f'<span>reblogged from <em>{escape(entry["reblogged-from-name"])}</em></span>'
        )
    meta_html = '<div class="post-meta">' + "".join(meta_parts) + '</div>'
 
    # title
    title_html = f'<div class="post-title">{escape(entry["regular-title"])}</div>' if (("regular-title" in entry) and (entry["regular-title"])) else ""
 
    body_html = ""
    if (("regular-body" in entry) and (entry["regular-body"])):
        body = entry["regular-body"]
        if "downloaded-media-files" in entry:
            body = localize_media_sources(body, entry["downloaded-media-files"])
            for i in range(len(entry["downloaded-media-files"])):
                p = Path(entry["downloaded-media-files"][i])
                if not (archive_path / p).is_file():
                    if (archive_path / p.with_suffix(".png")).is_file():
                        entry["downloaded-media-files"][i] = str(p.with_suffix(".png"))
                        #print(f'Successfully fixed {str(p)} by converting to .png')
                    elif (archive_path / p.with_suffix(".jpg")).is_file():
                        entry["downloaded-media-files"][i] = str(p.with_suffix(".jpg"))
                        #print(f'Successfully fixed {str(p)} by converting to .jpg')
                    else:
                        print(f'ERROR: Couldn\'t fix {str(p)}')
        body = fix_youtube_embeds(body)
        if body:
            body_html = '<div class="post-body">' + body + '</div>'
        elif not has_media:
            plain = re.sub(r'<[^>]+>', '', body).strip()
            if plain:
                body_html = f'<div class="post-body"><p>{escape(plain)}</p></div>'
    elif "question" in entry:
        question = entry["question"]
        answer = entry["answer"]
        body_html = '<div class="post-body"><div class="question"><blockquote>' + question + '</blockquote></div>' + answer + '</div>'
    if not body_html and not has_media:
        body_html = '<div class="no-body">[no text content]</div>'
 
    # tags — comma-separated
    tags_html = ""
    if entry["tags"]:
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
def build_html(entries: list[dict], blog_title: str, blog_name: str, archive_path: Path, json: bool = True) -> str:
    """Create the final archive html file"""
    if json==True:
        posts_html = "\n".join(build_post_html_json(e,archive_path) for e in entries) 
    else:
        posts_html = "\n".join(build_post_html_text(e,archive_path) for e in entries)
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
    parser.add_argument("archive", help="Path to the TumblThree archive of a blog, eg r'TumblThree-v2.20.1-x64-Application\Blogs\blogname' ")
    parser.add_argument('--json', action=argparse.BooleanOptionalAction, default=True, help="Use --no-json optional argument if you crawled your blog in text format")
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
    texts = archive_path / "texts.txt"
    answers = archive_path / "answers.txt"
    texts_answers = archive_path / "text_answers.txt"
    
    print(f"Parsing {archive_path.name} …")
    if args.json==True: 
        sorter.rewrite_sorted_json([texts,answers], "text_answers.txt") 
        entries = parse_entries_json(texts_answers)
    else:
        sorter.rewrite_sorted_text([texts,answers], "text_answers.txt") 
        entries = parse_entries_text(texts_answers)
    print(f"Found {len(entries)} entries.")
    
    blog_title = args.blog_title if args.blog_title else archive_path.name
    html = build_html(entries, blog_title,args.blog_name,archive_path,args.json)
    output_path.write_text(html, encoding="utf-8")
    texts_answers.unlink() 
    print(f"Written to: {output_path}")
    print(f"Done — open: {output_path}")
 
if __name__ == "__main__":
    main()