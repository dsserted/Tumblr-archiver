# -*- coding: utf-8 -*-
"""
Created on Sat Jun 13 11:51:36 2026

@author: Asus
"""
import re
import json
from datetime import datetime

def sort_read_entries_text(filepath_list):
    full_entries = []
    for filepath in filepath_list:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split on "Post id:" but keep the delimiter
        raw_entries = re.split(r'(?=^Post id:)', content, flags=re.MULTILINE)
        raw_entries = [e.strip() for e in raw_entries if e.strip()]
        full_entries = full_entries + raw_entries
    
    entries = []
    for entry in full_entries:
        # Extract the date
        date_match = re.search(r'^Date:\s*(.+)$', entry, re.MULTILINE)
        if date_match:
            date_str = date_match.group(1).strip()
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S GMT')
            except ValueError:
                date = datetime.min  # Push unparseable dates to the end
        else:
            date = datetime.min
    
        entries.append((date, entry))
    
    return entries

def sort_read_entries_json(filepath_list):
    blocks = []
    for filepath in filepath_list:
        text = filepath.read_text(encoding="utf-8")
        blocks = blocks + json.loads(text)
    for entry in blocks:
        date = entry["date-gmt"]
        try:
            date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S GMT')
        except ValueError:
            date = datetime.min 
        entry["date-gmt"] = date
    return blocks

def rewrite_sorted_text(filepath, output_path=None):
    entries = sort_read_entries_text(filepath)

    # Sort in reverse chronological order (newest first)
    entries.sort(key=lambda x: x[0], reverse=True)

    sorted_content = '\n\n'.join(entry for _, entry in entries)

    out = output_path or filepath
    with open(out, 'w', encoding='utf-8') as f:
        f.write(sorted_content + '\n')

def rewrite_sorted_json(filepath_list, output_path=None):
    blocks = sort_read_entries_json(filepath_list)
    blocks_sorted = sorted(blocks,key=lambda d: d['date-gmt'],reverse=True)
    for entry in blocks:
        entry["date-gmt"] = str(entry["date-gmt"])
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(blocks_sorted))
