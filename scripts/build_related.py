#!/usr/bin/env python3
"""社長メッセージマッピング.xlsx のタグから related articles graph を構築。
出力: /sessions/hopeful-cool-bell/related.json
形式: { "1": [{"no":N,"t":"タイトル","s":1.23,"shared":["タグ1","タグ2"]}, ...] }
"""
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

XLSX = "/sessions/hopeful-cool-bell/mnt/uploads/社長メッセージマッピング.xlsx"
OUT = Path("/sessions/hopeful-cool-bell/related.json")
TOP_K = 6  # max related articles per issue
MIN_SHARED = 1  # require at least this many shared tags

df = pd.read_excel(XLSX, sheet_name="号数マッピング")

# 号数 → int
def parse_no(v):
    if pd.isna(v):
        return None
    s = str(v).strip()
    m = re.match(r"^第(\d+)号$", s)
    if m:
        return int(m.group(1))
    # 号外, 174, 176 など
    return None  # exclude these from related computation

def split_tags(s):
    if pd.isna(s):
        return []
    parts = re.split(r"[、,，/／・]", str(s))
    out = []
    for p in parts:
        p = p.strip()
        if p:
            out.append(p)
    return out

# Build issue -> tags
issues = {}
titles = {}
for _, row in df.iterrows():
    no = parse_no(row["号数"])
    if no is None:
        continue
    tags = split_tags(row.get("タグ"))
    main_theme = row.get("メインテーマ")
    if not pd.isna(main_theme):
        # メインテーマ も加える（重み高）
        tags.append(f"@{str(main_theme).strip()}")
    if not tags:
        continue
    issues[no] = set(tags)
    titles[no] = str(row.get("タイトル") or f"第{no}号").strip()

print(f"Issues with tags: {len(issues)}")

# Build tag -> issues, compute IDF
tag_to_issues = defaultdict(set)
for no, tags in issues.items():
    for t in tags:
        tag_to_issues[t].add(no)

N = len(issues)
idf = {}
for t, ns in tag_to_issues.items():
    df_count = len(ns)
    # smoothed IDF; メインテーマ (@-prefixed) gets a boost
    idf[t] = math.log(1 + N / df_count)
    if t.startswith("@"):
        idf[t] *= 1.4  # メインテーマ boost

# Compute related per issue
related = {}
for no, tags in issues.items():
    scores = defaultdict(float)
    shared_tags_map = defaultdict(list)
    for t in tags:
        for other_no in tag_to_issues[t]:
            if other_no == no:
                continue
            scores[other_no] += idf[t]
            shared_tags_map[other_no].append(t)
    # filter and sort
    candidates = []
    for other_no, sc in scores.items():
        shared = shared_tags_map[other_no]
        if len(shared) < MIN_SHARED:
            continue
        # tie-break: prefer issues with more shared tags, then closer in number
        candidates.append((sc, len(shared), -abs(other_no - no), other_no, shared))
    candidates.sort(reverse=True)
    rel_list = []
    for sc, ns_count, _, other_no, shared in candidates[:TOP_K]:
        # clean shared tags (strip @ prefix for display)
        shared_clean = [s[1:] if s.startswith("@") else s for s in shared]
        # de-dup while preserving order
        seen = set()
        shared_dedup = []
        for s in shared_clean:
            if s not in seen:
                seen.add(s)
                shared_dedup.append(s)
        rel_list.append({
            "no": other_no,
            "t": titles.get(other_no, f"第{other_no}号"),
            "s": round(sc, 2),
            "shared": shared_dedup[:5],  # show up to 5 shared
        })
    related[no] = rel_list

# stats
counts = [len(v) for v in related.values()]
print(f"Related lists: {len(related)}")
print(f"Avg related per issue: {sum(counts)/len(counts):.2f}")
print(f"Min/Max: {min(counts)} / {max(counts)}")

# sample
print("\n=== Sample related (第1号) ===")
for r in related.get(1, []):
    print(f"  第{r['no']}号: {r['t']} (score={r['s']}, shared={r['shared']})")
print("\n=== Sample related (第106号) ===")
for r in related.get(106, []):
    print(f"  第{r['no']}号: {r['t']} (score={r['s']}, shared={r['shared']})")
print("\n=== Sample related (第260号) ===")
for r in related.get(260, []):
    print(f"  第{r['no']}号: {r['t']} (score={r['s']}, shared={r['shared']})")

OUT.write_text(json.dumps(related, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"\nWrote {OUT} ({OUT.stat().st_size:,} bytes)")
