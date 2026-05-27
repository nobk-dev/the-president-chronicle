#!/usr/bin/env python3
"""全トラック混合版：4 つの軌道（思想・組織・社会・経済）を区別せず、
1 列の年代記として混ぜて時系列に並べる版。
- 月日付の抽出を試み、可能なら時系列でソート
- 重要度のみ視覚化（★★／★／無印）
- ソース（トラック）はクリック時のドロワーで識別

出力: chronicle_TOP_mixed.html
"""
import json
import random
import re
from pathlib import Path

SRC = Path("/sessions/hopeful-cool-bell/_v29_main.html")
DST = Path("/sessions/hopeful-cool-bell/mnt/THE PRESIDENT CHRONICLE/chronicle_TOP_mixed.html")
TITLES_PATH = Path("/sessions/hopeful-cool-bell/titles_only.js")
LOGO_B64 = Path("/sessions/hopeful-cool-bell/logo_marimo_240.txt").read_text(encoding="utf-8").strip()


def extract_data():
    s = SRC.read_text(encoding="utf-8")
    m1 = re.search(r"const _D1 = (\{.*?\});\nconst _D2", s, re.S)
    m2 = re.search(r"const _D2 = (\{.*?\});\nconst _D3", s, re.S)
    m3 = re.search(r"const _D3 = (\{.*?\});\n", s, re.S)
    return {**json.loads(m1.group(1)), **json.loads(m2.group(1)), **json.loads(m3.group(1))}


def load_titles():
    s = TITLES_PATH.read_text(encoding="utf-8")
    m = re.search(r"const TITLES=(\{.*\});", s)
    return json.loads(m.group(1))


def parse_marker(item):
    s = item.strip()
    if s.startswith("★★"):
        return ("maj", s[2:].strip())
    if s.startswith("★"):
        return ("mid", s[1:].strip())
    return ("def", s)


def smart_split(text):
    out, buf, depth = [], "", 0
    for ch in text:
        if ch in "［[":
            depth += 1
        elif ch in "］]":
            depth = max(0, depth - 1)
        if ch == "／" and depth == 0:
            if buf.strip():
                out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(buf.strip())
    return out


# 月日抽出パターン（先頭から）
MONTH_PATTERNS = [
    (re.compile(r"^(\d{1,2})/(\d{1,2})"), lambda m: (int(m.group(1)), int(m.group(2)))),
    (re.compile(r"^(\d{1,2})月(\d{1,2})日"), lambda m: (int(m.group(1)), int(m.group(2)))),
    (re.compile(r"^(\d{1,2})月"), lambda m: (int(m.group(1)), 1)),
    (re.compile(r"^(初頭|春|早春)"), lambda m: (2, 1)),
    (re.compile(r"^(初夏)"), lambda m: (6, 1)),
    (re.compile(r"^(夏)"), lambda m: (7, 1)),
    (re.compile(r"^(秋)"), lambda m: (10, 1)),
    (re.compile(r"^(冬|年末)"), lambda m: (12, 1)),
    (re.compile(r"^(年頭|年初)"), lambda m: (1, 1)),
]


def extract_date(text):
    """項目テキストから (month, day) を抽出。なければ (0, 0)。"""
    for pat, fn in MONTH_PATTERNS:
        m = pat.search(text)
        if m:
            mo, da = fn(m)
            return (max(1, min(12, mo)), max(1, min(31, da)))
    return (0, 0)


def escape(s):
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def build_html():
    data = extract_data()
    titles = load_titles()

    phases_by_id = {p["id"]: p for p in data["phases"]}
    issues_by_year = {}
    for iss in data["allIssues"]:
        yr = int(iss["y"])
        issues_by_year.setdefault(yr, []).append(iss)
    keyByNo = {k["no"]: k for k in data["keyIssues"]}

    def month_from_iss_y(y):
        fy = int(y)
        return max(1, min(12, round((y - fy) * 12) + 1))

    def render_year(y):
        phase = phases_by_id.get(y["phase"], {})
        items = []

        # 思想 / 組織 / 社会 / 経済 のテキストを項目化
        for field in ("thought", "org", "society", "economy"):
            text = y.get(field) or ""
            for raw in smart_split(text):
                rank, cleaned = parse_marker(raw)
                mo, da = extract_date(cleaned)
                items.append({
                    "kind": field,
                    "rank": rank,
                    "text": cleaned,
                    "mo": mo,
                    "da": da,
                    "sort": mo * 100 + da if mo else 9999,  # 月日なしは末尾
                })

        # Track I: 全号を項目化
        year_issues = sorted(issues_by_year.get(y["year"], []), key=lambda i: i["y"])
        for iss in year_issues:
            k = keyByNo.get(iss["no"])
            title = titles.get(str(iss["no"])) or (k and k["title"]) or f"第{iss['no']}号"
            mo = month_from_iss_y(iss["y"])
            rank = "def"
            if k:
                if k["rank"] == 5:
                    rank = "maj"
                elif k["rank"] == 4:
                    rank = "mid"
                else:
                    rank = "def"
            items.append({
                "kind": "issue",
                "rank": rank,
                "no": iss["no"],
                "text": title,
                "mo": mo,
                "da": 1,
                "sort": mo * 100 + 1,
            })

        # 社長メッセージは号数で固定順、それ以外はランダム
        # 両者を「順序保持」マージで混ぜることで、社長メッセージは 1→2→3 順を維持しつつ
        # 他項目がランダムに挟まる
        issues = sorted([i for i in items if i["kind"] == "issue"], key=lambda i: i["no"])
        others = [i for i in items if i["kind"] != "issue"]
        rng = random.Random(y["year"])
        rng.shuffle(others)

        def merge_preserving_order(a, b, rng):
            result, ai, bi = [], 0, 0
            while ai < len(a) or bi < len(b):
                ra, rb = len(a) - ai, len(b) - bi
                if ra == 0:
                    result.extend(b[bi:]); break
                if rb == 0:
                    result.extend(a[ai:]); break
                if rng.random() < ra / (ra + rb):
                    result.append(a[ai]); ai += 1
                else:
                    result.append(b[bi]); bi += 1
            return result

        items = merge_preserving_order(issues, others, rng)

        def render_item(it):
            mo_label = f"{it['mo']}月" if it["mo"] else ""
            mo_part = f"<span class='ev-mo'>{mo_label}</span>" if mo_label else ""
            if it["kind"] == "issue":
                rank_cls = f"r-{it['rank']}"
                rno = f"<span class='ev-no'>第 {it['no']} 号</span>"
                return f"<a class='ev kind-issue {rank_cls}' data-no='{it['no']}' href='#no={it['no']}'>{rno}{mo_part}<span class='ev-ttl'>{escape(it['text'])}</span></a>"
            else:
                rank_cls = f"r-{it['rank']}"
                kind_cls = f"kind-{it['kind']}"
                return f"<div class='ev {kind_cls} {rank_cls}'>{mo_part}<span class='ev-ttl'>{escape(it['text'])}</span></div>"

        item_html = "".join(render_item(it) for it in items)

        return f"""
<section class="yr" data-year="{y['year']}" data-phase="{y['phase']}">
  <header class="yr-head">
    <div class="yr-stripe" style="background:{phase.get('color','#888')};"></div>
    <div class="yr-meta">
      <div class="yr-num">{y['year']}</div>
      <div class="yr-phase">P{phase.get('num', y['phase'])}／{escape(phase.get('name',''))}</div>
    </div>
    <div class="yr-title">
      <div class="yr-key">◆ {escape(y.get('key',''))}</div>
      <h2 class="yr-band">{escape(y.get('bandTitle',''))}</h2>
      <p class="yr-poetic">{escape(y.get('poetic',''))}</p>
    </div>
  </header>
  <div class="yr-content">
    {item_html}
  </div>
</section>
"""

    year_sections = "\n".join(render_year(y) for y in data["years"])

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>マリモクロニクル ／ 混合版（全 4 軌道を時系列に）</title>
<style>
:root{{
  --paper:#f5f2ea; --paper-warm:#fbf8ee; --ink:#14223f; --ink-soft:#3a3630;
  --ink-mute:#6b6657; --ink-faint:#8a8276; --rule:#bdb7a9; --rule-soft:#d4cdb8;
  --vermilion:#8b3a2a; --marimo-blue:#0096D6; --warm-amber:#c87632; --warm-grey:#6b6657;
  --serif-en:"Cormorant Garamond","Garamond",Georgia,serif;
  --serif-jp:"Noto Serif JP","YuMincho","Hiragino Mincho Pro",serif;
  --sans-jp:"Noto Sans JP","Yu Gothic","Hiragino Sans",sans-serif;
}}
*{{box-sizing:border-box;}}
html,body{{margin:0;padding:0;background:var(--paper);color:var(--ink-soft);font-family:var(--serif-jp);}}

/* ヘッダー */
.site-head{{padding:18px 32px;border-bottom:1px solid var(--rule);background:var(--paper-warm);display:flex;align-items:center;gap:18px;position:sticky;top:0;z-index:10;}}
.site-head .logo{{height:46px;}}
.site-head .brand{{font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.22em;color:var(--vermilion);text-transform:uppercase;}}
.site-head .title{{font-family:var(--sans-jp);font-weight:900;font-size:17px;letter-spacing:0.06em;color:var(--ink);}}
.site-head .title .sub{{display:inline-block;margin-left:10px;font-size:11px;font-weight:500;color:var(--ink-mute);letter-spacing:0.04em;}}
.site-head .nav-link{{margin-left:auto;font-family:var(--sans-jp);font-size:11.5px;color:var(--ink);text-decoration:none;border:1px solid var(--ink);padding:7px 14px;font-weight:700;letter-spacing:0.06em;}}
.site-head .nav-link:hover{{background:var(--ink);color:#fff;}}
.alt-link{{margin-left:8px;font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.16em;color:var(--vermilion);text-decoration:none;border-bottom:1px dotted var(--vermilion);}}

/* 全体 */
.chronicle{{max-width:1100px;margin:0 auto;padding:48px 32px 120px;}}
.intro{{margin-bottom:48px;border-bottom:1px solid var(--rule);padding-bottom:32px;}}
.intro .en{{font-family:var(--serif-en);font-style:italic;font-size:12px;letter-spacing:0.22em;color:var(--vermilion);text-transform:uppercase;margin-bottom:10px;}}
.intro h1{{font-family:var(--serif-jp);font-size:40px;font-weight:700;color:var(--ink);margin:0 0 8px;line-height:1.3;}}
.intro p{{font-family:var(--serif-jp);font-size:14.5px;line-height:1.9;color:var(--ink-soft);margin:0 0 6px;}}

/* 年セクション */
.yr{{margin-bottom:64px;}}
.yr-head{{display:grid;grid-template-columns:12px 130px 1fr;gap:16px;margin-bottom:24px;}}
.yr-stripe{{width:6px;height:100%;min-height:64px;background:#888;}}
.yr-meta .yr-num{{font-family:var(--serif-en);font-size:36px;font-weight:500;color:var(--ink);line-height:1;}}
.yr-meta .yr-phase{{margin-top:8px;font-family:var(--sans-jp);font-size:10.5px;letter-spacing:0.10em;color:var(--ink-faint);text-transform:uppercase;line-height:1.4;}}
.yr-title .yr-key{{font-family:var(--sans-jp);font-weight:800;font-size:13px;color:var(--vermilion);letter-spacing:0.12em;margin-bottom:6px;}}
.yr-title .yr-band{{margin:0 0 8px;font-family:var(--sans-jp);font-weight:900;font-size:22px;color:var(--ink);letter-spacing:0.04em;line-height:1.4;}}
.yr-title .yr-poetic{{font-family:var(--serif-jp);font-size:13px;color:var(--ink-soft);line-height:1.7;margin:0;padding:8px 0 0;border-top:1px dotted var(--rule);}}

/* コンテンツエリア：3 列 × 行優先（grid-auto-flow:row）で横読み順序保持 */
.yr-content{{padding-left:158px;display:grid;grid-template-columns:1fr 1fr 1fr;grid-auto-flow:row;gap:6px 28px;align-items:start;}}

/* 項目共通 */
.ev{{display:block;margin:3px 0;padding:1px 0 1px 14px;font-size:13.5px;line-height:1.65;color:var(--ink-mute);border-left:1px solid transparent;text-decoration:none;font-family:var(--serif-jp);}}
.ev .ev-mo{{font-family:var(--serif-en);font-style:italic;font-size:10.5px;color:var(--ink-faint);margin-right:7px;letter-spacing:0.08em;}}
.ev .ev-no{{font-family:var(--serif-en);font-style:italic;font-size:11px;color:var(--marimo-blue);margin-right:6px;font-weight:700;letter-spacing:0.14em;}}
.ev .ev-ttl{{color:inherit;}}

/* ランク（重要度） — タイポと色のみで階層、明朝で重み付け */
.ev.r-mid{{font-size:15.5px;font-weight:600;color:var(--ink);margin:6px 0;padding:3px 0 3px 14px;border-left:2.5px solid;line-height:1.55;}}
.ev.r-maj{{font-size:20px;font-weight:700;color:var(--ink);margin:11px 0;padding:5px 0 5px 14px;letter-spacing:0.01em;line-height:1.45;border-left:3px solid;}}

/* 種類別のアクセント色 */
.ev.kind-thought{{border-left-color:var(--marimo-blue);}}
.ev.kind-org{{border-left-color:var(--marimo-blue);}}
.ev.kind-society{{border-left-color:var(--warm-amber);}}
.ev.kind-economy{{border-left-color:var(--warm-grey);}}
.ev.r-def{{border-left-color:var(--rule);}}

/* === 社長メッセージ（kind-issue）はテキストの色とタイポだけで強調、カード化しない === */
.ev.kind-issue {{
  cursor: pointer;
  background: transparent;
  border-left: 2.5px solid var(--marimo-blue);
  padding: 3px 0 3px 12px;
  margin: 5px 0;
  font-size: 15px;
  line-height: 1.55;
  color: var(--ink);
  font-weight: 600;
  font-family: var(--serif-jp);
  transition: color 0.15s, transform 0.15s;
}}
.ev.kind-issue:hover {{ transform: translateX(2px); }}
.ev.kind-issue:hover .ev-ttl {{ color: var(--marimo-blue); }}
.ev.kind-issue .ev-no {{ color: var(--marimo-blue); font-weight: 700; font-size: 11.5px; }}
.ev.kind-issue .ev-mo {{ color: var(--ink-mute); }}
.ev.kind-issue .ev-ttl {{ color: var(--ink); font-weight: 700; }}

/* r-mid（4-star）社長メッセージ */
.ev.r-mid.kind-issue {{
  border-left-width: 3px;
  font-size: 16.5px;
  font-weight: 700;
  padding: 4px 0 4px 13px;
  line-height: 1.5;
}}
.ev.r-mid.kind-issue .ev-no {{ font-size: 13px; }}
.ev.r-mid.kind-issue .ev-ttl {{ font-weight: 700; }}

/* r-maj（5-star）社長メッセージ */
.ev.r-maj.kind-issue {{
  border-left-width: 4px;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: 0.01em;
  padding: 6px 0 6px 14px;
  line-height: 1.42;
  margin: 10px 0;
}}
.ev.r-maj.kind-issue .ev-no {{ display: block; font-size: 13.5px; margin-bottom: 4px; font-weight: 700; }}
.ev.r-maj.kind-issue .ev-mo {{ display: inline; }}
.ev.r-maj.kind-issue .ev-ttl {{ display: block; font-weight: 700; color: var(--ink); }}

/* レスポンシブ */
@media(max-width:760px){{
  .yr-head{{grid-template-columns:8px 1fr;}}
  .yr-meta{{grid-column:1/-1;display:flex;align-items:baseline;gap:12px;}}
  .yr-content{{padding-left:0;}}
}}
</style>
</head>
<body>

<header class="site-head">
  <img src="data:image/png;base64,{LOGO_B64}" class="logo" alt="MARIMO" />
  <div>
    <div class="brand">President Chronicle</div>
    <div class="title">マリモクロニクル<span class="sub">— 混合版／全軌道を時系列で</span></div>
  </div>
  <a href="chronicle_TOP.html" class="nav-link">統合版（3トラック）へ</a>
  <a href="chronicle_FULLTEXT_complete.html" class="alt-link">全文 →</a>
</header>

<main class="chronicle">
  <section class="intro">
    <div class="en">President Chronicle ／ Mixed Edition</div>
    <h1>マリモクロニクル</h1>
    <p>深川真が、社員に贈り続けた全 272 通のメッセージ。全 709,501 文字で語る。</p>
    <p style="font-size:12px;color:var(--ink-mute);margin-top:14px;">思想・組織・社会・経済の <strong>4 軌道を区別せず</strong>、各年の出来事と社長メッセージを<strong>ランダムに 3 列</strong>へ配置した混合版。色の左バーで軌道を識別（青＝マリモ／オレンジ＝社会／グレー＝経済）。同じ年でもリロードのたびに違う表情を見せる、編集工学的タブロー。</p>
  </section>

  {year_sections}

</main>

<script>
// 号項目クリック → 全文ページへ
document.querySelectorAll(".ev.kind-issue").forEach(el => {{
  el.addEventListener("click", e => {{
    e.preventDefault();
    const no = el.dataset.no;
    if (no) location.href = `chronicle_FULLTEXT_complete.html#no=${{no}}`;
  }});
}});
</script>

</body>
</html>
"""


def main():
    html = build_html()
    DST.write_text(html, encoding="utf-8")
    print(f"Wrote {DST}")
    print(f"Size: {len(html):,} chars / {len(html.encode('utf-8')):,} bytes")


if __name__ == "__main__":
    main()
