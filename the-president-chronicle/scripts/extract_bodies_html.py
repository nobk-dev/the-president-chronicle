#!/usr/bin/env python3
"""社長メッセージ docx 群から、bold/underline/赤字・色/リスト/1字下げ/改行を保持して
本文を HTML 化し、/sessions/hopeful-cool-bell/all_messages_html.json に保存する。

出力フォーマット:
{
  "1": {"title": "...", "body_html": "<p>...</p>...", "date": "平成..."},
  ...
}

- 段落の頭が U+3000 → <p class="ind">（1 字下げ）
- 中央寄せ → <p class="ctr">、右寄せ → <p class="rgt">（ただし「目次へ」は除外）
- bold → <strong>、italic → <em>、underline → <u>
- 赤字（明確に赤系）/ 青字 / その他色付き → <span style="color:#XXX">
- numPr 付き段落の連続 → <ul>/<ol> にまとめる
- 段落内の \n → <br>
- 空行は <p class="sp"></p>
- "目次へ" は除外
- 末尾の日付（DATE_PAT）は date フィールドへ抽出
"""
import json
import os
import re
import sys
import unicodedata
from html import escape
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

BASE = "/sessions/hopeful-cool-bell/mnt/uploads/"
OUT = Path("/sessions/hopeful-cool-bell/all_messages_html.json")

DATE_PAT = re.compile(
    r"^\s*("
    r"(?:平成|令和|昭和)\s*[元一二三四五六七八九十百\d]+\s*年.*?[日)）]"
    r"|"
    r"(?:平成|令和|昭和)\s*[元一二三四五六七八九十百\d]+\s*年\s*元旦"
    r"|"
    r"\d{4}年\s*\d+月\s*\d+日.*?[日)）]"
    r")\s*$"
)


def is_date_only(text: str) -> bool:
    return bool(DATE_PAT.match(text.strip()))


def color_class(rgb_hex: str) -> str | None:
    """色分類: 赤系 → 'red', 青系 → 'blue', その他色付き → None（rawで指定）"""
    if not rgb_hex:
        return None
    rgb_hex = rgb_hex.upper()
    if rgb_hex in ("000000", "1A1A1A"):
        return None
    try:
        r = int(rgb_hex[0:2], 16)
        g = int(rgb_hex[2:4], 16)
        b = int(rgb_hex[4:6], 16)
    except Exception:
        return None
    # 赤系
    if r >= 150 and g <= 100 and b <= 100:
        return "red"
    # 青系
    if b >= 150 and r <= 120:
        return "blue"
    # 緑系
    if g >= 130 and r <= 100 and b <= 100:
        return "green"
    return None  # raw


def run_to_html(run) -> str:
    """python-docx の Run を HTML フラグメントに変換。"""
    text = run.text or ""
    if not text:
        return ""
    out = escape(text).replace("\n", "<br>")

    # 太字
    bold = run.bold is True
    italic = run.italic is True
    underline = run.underline is True

    # 色
    cls_color = None
    raw_color = None
    try:
        if run.font.color and run.font.color.rgb is not None:
            rgb = str(run.font.color.rgb)
            cls_color = color_class(rgb)
            if cls_color is None and rgb.upper() not in ("000000", "1A1A1A"):
                raw_color = "#" + rgb
    except Exception:
        pass

    # ハイライト（強調背景）
    highlight = None
    try:
        if run.font.highlight_color is not None:
            highlight = "mark"
    except Exception:
        pass

    # ラップ順: span(color) > u > em > strong > text
    if cls_color:
        out = f'<span class="c-{cls_color}">{out}</span>'
    elif raw_color:
        out = f'<span style="color:{raw_color}">{out}</span>'
    if highlight:
        out = f"<mark>{out}</mark>"
    if underline:
        out = f"<u>{out}</u>"
    if italic:
        out = f"<em>{out}</em>"
    if bold:
        out = f"<strong>{out}</strong>"
    return out


def get_numpr(p) -> tuple | None:
    """段落の numbering 情報を返す。 (numId, ilvl) or None"""
    pPr = p._p.find(qn("w:pPr"))
    if pPr is None:
        return None
    numPr = pPr.find(qn("w:numPr"))
    if numPr is None:
        return None
    numId_el = numPr.find(qn("w:numId"))
    ilvl_el = numPr.find(qn("w:ilvl"))
    numId = numId_el.get(qn("w:val")) if numId_el is not None else None
    ilvl = ilvl_el.get(qn("w:val")) if ilvl_el is not None else "0"
    return (numId, ilvl)


def get_alignment_class(p) -> str | None:
    al = p.alignment
    if al is None:
        return None
    # 0=LEFT, 1=CENTER, 2=RIGHT, 3=JUSTIFY
    val = int(al)
    if val == 1:
        return "ctr"
    if val == 2:
        return "rgt"
    if val == 3:
        return "jst"
    return None


def para_to_html(p) -> tuple[str, dict]:
    """段落を HTML フラグメントに変換。 (html, meta) — meta には list, alignment 情報。"""
    runs_html = "".join(run_to_html(r) for r in p.runs)
    meta = {
        "list": get_numpr(p),
        "align": get_alignment_class(p),
        "style": p.style.name if p.style else "",
        "raw_text": p.text or "",
    }
    return runs_html, meta


def is_issue_heading(p) -> int | None:
    """Heading 1 で第N号で始まるなら N を返す。"""
    if not (p.style and p.style.name == "Heading 1"):
        return None
    text = (p.text or "").strip()
    m = re.match(r"^第\s*(\d+)\s*号", text)
    if m:
        return int(m.group(1))
    return None


def extract_title(p) -> str:
    """Heading 1 から「…」内のタイトルを抽出。"""
    text = (p.text or "").strip()
    m = re.search(r"「([^」]+)」", text)
    if m:
        return f"「{m.group(1)}」"
    # fallback: 第N号 を除いた残り
    return re.sub(r"^第\s*\d+\s*号\s*", "", text)


def build_body_html(paras_with_meta: list[tuple[str, dict]]) -> tuple[str, str]:
    """段落リストを HTML に。末尾の日付段落は date として返す。"""
    # 末尾の右寄せ「目次へ」を含む空気は捨て、後ろから日付段落を探す
    # まず後ろから空白パラ・「目次へ」パラ・装飾パラを除外
    cleaned = []
    for html, meta in paras_with_meta:
        raw = meta["raw_text"].strip()
        # 「目次へ」スキップ
        if raw == "目次へ":
            continue
        # ＝＝＝ など装飾線
        if raw and re.match(r"^[=＝─━ー\-]{3,}$", raw):
            continue
        cleaned.append((html, meta))

    # 末尾の日付を分離
    date = ""
    while cleaned:
        html, meta = cleaned[-1]
        raw = meta["raw_text"].strip()
        if not raw:
            cleaned.pop()
            continue
        if is_date_only(raw):
            date = raw
            cleaned.pop()
            break
        break

    # 末尾の空段落を更にトリム
    while cleaned and not cleaned[-1][1]["raw_text"].strip():
        cleaned.pop()
    # 先頭の空段落もトリム
    while cleaned and not cleaned[0][1]["raw_text"].strip():
        cleaned.pop(0)

    # リスト集約のため走査
    out_parts = []
    i = 0
    while i < len(cleaned):
        html, meta = cleaned[i]
        list_info = meta["list"]
        if list_info is not None:
            # リスト集約
            list_items = []
            cur_numId = list_info[0]
            while i < len(cleaned) and cleaned[i][1]["list"] is not None and cleaned[i][1]["list"][0] == cur_numId:
                inner_html = cleaned[i][0]
                list_items.append(f"<li>{inner_html}</li>")
                i += 1
            out_parts.append(f"<ul class=\"body-list\">{''.join(list_items)}</ul>")
            continue

        raw = meta["raw_text"]
        align = meta["align"]
        style_name = meta["style"]

        if not raw.strip():
            out_parts.append('<p class="sp"></p>')
            i += 1
            continue

        # Heading 2 以降は h タグに
        if style_name and style_name.startswith("Heading "):
            try:
                lvl = int(style_name.replace("Heading ", "").strip())
            except Exception:
                lvl = 2
            if lvl >= 2:
                out_parts.append(f'<h{min(lvl+1,4)} class="body-h">{html}</h{min(lvl+1,4)}>')
                i += 1
                continue

        # 1 字下げ判定: 段落の生テキストが U+3000 で始まる
        cls = []
        if raw.startswith("　"):
            cls.append("ind")
        if align == "ctr":
            cls.append("ctr")
        elif align == "rgt":
            cls.append("rgt")
        elif align == "jst":
            cls.append("jst")

        # html の先頭の U+3000 は CSS インデントを使うので消す（重複表示防止）
        # ただし表示安定のためテキストはそのままにする方針もあり。今回は CSS 制御に任せる。
        # → そのまま残す。CSS で text-indent しないので、U+3000 が視覚的インデントを担う。

        cls_attr = f' class="{" ".join(cls)}"' if cls else ""
        out_parts.append(f"<p{cls_attr}>{html}</p>")
        i += 1

    return "".join(out_parts), date


def process_docx(path: str) -> dict:
    doc = Document(path)
    paragraphs = list(doc.paragraphs)
    issues = {}

    # まず全段落を走査してヘッディング位置を特定
    boundaries = []  # list of (paragraph index, issue_no)
    for idx, p in enumerate(paragraphs):
        no = is_issue_heading(p)
        if no is not None:
            boundaries.append((idx, no))

    if not boundaries:
        # フォールバック：第1号目次など。スキップ
        return issues

    # 各 issue range
    for bi, (idx, no) in enumerate(boundaries):
        start = idx + 1
        end = boundaries[bi + 1][0] if bi + 1 < len(boundaries) else len(paragraphs)
        title = extract_title(paragraphs[idx])
        # 本文範囲の段落
        body_paras = paragraphs[start:end]
        items = [para_to_html(p) for p in body_paras]
        body_html, date = build_body_html(items)
        issues[no] = {
            "title": title,
            "body_html": body_html,
            "date": date,
        }
    return issues


def main():
    files = []
    for f in os.listdir(BASE):
        fnorm = unicodedata.normalize("NFC", f)
        if fnorm.startswith("社長メッセージ_") and fnorm.endswith(".docx") and "-" not in fnorm:
            files.append(f)
    files.sort()
    print(f"Found {len(files)} canonical docx files")

    all_issues = {}
    for f in files:
        path = os.path.join(BASE, f)
        try:
            issues = process_docx(path)
            print(f"  {unicodedata.normalize('NFC', f)}: {len(issues)} issues")
            for no, data in issues.items():
                if no in all_issues:
                    print(f"    WARN: 第{no}号 was already in another file (overwriting)")
                all_issues[no] = data
        except Exception as e:
            print(f"  ERROR processing {f}: {e}")

    print(f"\nTotal issues: {len(all_issues)}")
    nos = sorted(all_issues.keys())
    print(f"Range: {nos[0]} - {nos[-1]}")
    expected = set(range(1, max(nos) + 1))
    KESSU = {168, 174, 176, 256, 261}
    missing = sorted(expected - set(nos) - KESSU)
    print(f"Missing (excluding KESSU): {missing}")

    OUT.write_text(json.dumps(all_issues, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT} ({OUT.stat().st_size:,} bytes)")

    # Sanity-check first issue
    print("\n=== Sample 第1号 ===")
    s = all_issues[1]
    print(f"title: {s['title']!r}")
    print(f"date: {s['date']!r}")
    print(f"body_html[:400]: {s['body_html'][:400]}")


if __name__ == "__main__":
    main()
