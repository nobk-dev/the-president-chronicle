#!/usr/bin/env python3
"""1列統合版（年代記スタイル）と縦書き版（巻物スタイル）の TOP を生成。

入力: 既存 _v29_main.html から _D1 / _D2 / _D3 を抽出
出力:
  - chronicle_TOP.html         （1列統合版・縦スクロール）
  - chronicle_TOP_makimono.html （縦書き巻物版・横スクロール）
"""
import json
import re
from pathlib import Path

SRC = Path("/sessions/hopeful-cool-bell/_v29_main.html")
DST_DIR = Path("/sessions/hopeful-cool-bell/mnt/THE PRESIDENT CHRONICLE/")
TITLES_PATH = Path("/sessions/hopeful-cool-bell/titles_only.js")
LOGO_PATH = Path("/sessions/hopeful-cool-bell/logo_b64_tiny.txt")


def extract_data():
    s = SRC.read_text(encoding="utf-8")
    m1 = re.search(r"const _D1 = (\{.*?\});\nconst _D2", s, re.S)
    m2 = re.search(r"const _D2 = (\{.*?\});\nconst _D3", s, re.S)
    m3 = re.search(r"const _D3 = (\{.*?\});\n", s, re.S)
    d1 = json.loads(m1.group(1))
    d2 = json.loads(m2.group(1))
    d3 = json.loads(m3.group(1))
    data = {**d1, **d2, **d3}
    return data


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


def render_track_items(text, kind=None):
    """Track の文字列をマーカー付き HTML span 列に。"""
    if not text:
        return ""
    items = smart_split(text)
    out = []
    for it in items:
        cls, cleaned = parse_marker(it)
        kind_cls = f" kind-{kind}" if kind else ""
        out.append(f'<span class="ev ev-{cls}{kind_cls}">{escape(cleaned)}</span>')
    return "".join(out)


def escape(s):
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def build_unified_html(data, titles):
    """1列統合版：縦スクロール、各年が1ブロック。"""
    phases_by_id = {p["id"]: p for p in data["phases"]}
    issues_by_year = {}
    for iss in data["allIssues"]:
        yr = int(iss["y"])
        issues_by_year.setdefault(yr, []).append(iss)
    keyByNo = {k["no"]: k for k in data["keyIssues"]}

    def render_year_section(y):
        phase = phases_by_id.get(y["phase"], {})
        # Track I: 思想 + その年の象徴号カード
        thought_html = render_track_items(y.get("thought", ""))
        # Track I の象徴号（rank 5/4のみカード化）
        year_issues = issues_by_year.get(y["year"], [])
        notable = [iss for iss in year_issues if iss["no"] in keyByNo]
        notable.sort(key=lambda iss: iss["y"])
        issue_cards = []
        for iss in notable:
            k = keyByNo[iss["no"]]
            if k["rank"] >= 4:
                title = titles.get(str(iss["no"]), k["title"])
                rank_cls = f"r{k['rank']}"
                month = max(1, min(12, int((iss["y"] - int(iss["y"])) * 12) + 1))
                issue_cards.append(
                    f'<div class="issue-card {rank_cls}" data-no="{iss["no"]}">'
                    f'<span class="ic-no">第 {iss["no"]} 号</span>'
                    f'<span class="ic-mo">{month}月</span>'
                    f'<span class="ic-ttl">{escape(title)}</span>'
                    f'</div>'
                )
        org_html = render_track_items(y.get("org", ""))
        soc_html = render_track_items(y.get("society", ""), kind="society")
        eco_html = render_track_items(y.get("economy", ""), kind="economy")

        phase_label = f'Phase {phase.get("num", y["phase"])} ／ {phase.get("name","")}'
        phase_color = phase.get("color", "#888")

        return f"""
<section class="year-block" data-year="{y['year']}" data-phase="{y['phase']}">
  <header class="year-head">
    <div class="year-stripe" style="background:{phase_color};"></div>
    <div class="year-meta">
      <div class="year-num">{y['year']}</div>
      <div class="year-phase">{phase_label}</div>
    </div>
    <div class="year-title">
      <div class="year-key">◆ {escape(y.get('key',''))}</div>
      <h2 class="year-band">{escape(y.get('bandTitle',''))}</h2>
      <p class="year-poetic">{escape(y.get('poetic',''))}</p>
    </div>
  </header>
  <div class="year-tracks">
    <div class="track track-thought">
      <div class="track-h">TRACK I ／ 深川真、あるいは一経営者として</div>
      {''.join(issue_cards)}
      <div class="track-text">{thought_html}</div>
    </div>
    <div class="track track-org">
      <div class="track-h">TRACK II ／ MARIMO THE WAY</div>
      <div class="track-text">{org_html}</div>
    </div>
    <div class="track track-world">
      <div class="track-h">TRACK III ／ そのとき、社会・経済は？</div>
      <div class="track-subblock track-society">
        <span class="sub-h">社会</span>
        <div class="track-text">{soc_html}</div>
      </div>
      <div class="track-subblock track-economy">
        <span class="sub-h">経済</span>
        <div class="track-text">{eco_html}</div>
      </div>
    </div>
  </div>
</section>
"""

    year_sections = "\n".join(render_year_section(y) for y in data["years"])

    logo_b64 = LOGO_PATH.read_text(encoding="utf-8").strip()
    logo_data = f"data:image/png;base64,{logo_b64}"

    total_issues = len(data["allIssues"])
    total_years = len(data["years"])

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>マリモクロニクル — 統合版（縦の年代記）</title>
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
html,body{{margin:0;padding:0;background:var(--paper);color:var(--ink-soft);font-family:var(--sans-jp);}}

/* ヘッダー */
.site-head{{padding:18px 32px;border-bottom:1px solid var(--rule);background:var(--paper-warm);display:flex;align-items:center;gap:18px;position:sticky;top:0;z-index:10;}}
.site-head .brand{{font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.22em;color:var(--vermilion);text-transform:uppercase;}}
.site-head .title{{font-family:var(--sans-jp);font-weight:900;font-size:18px;letter-spacing:0.06em;color:var(--ink);}}
.site-head .title .sub{{display:inline-block;margin-left:14px;font-size:11px;font-weight:500;color:var(--ink-mute);letter-spacing:0.04em;}}
.site-head .logo{{display:inline-block;height:36px;}}
.site-head .nav-link{{margin-left:auto;font-family:var(--sans-jp);font-size:11.5px;color:var(--ink);text-decoration:none;border:1px solid var(--ink);padding:7px 14px;font-weight:700;letter-spacing:0.06em;}}
.site-head .nav-link:hover{{background:var(--ink);color:#fff;}}
.alt-link{{margin-left:8px;font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.16em;color:var(--vermilion);text-decoration:none;border-bottom:1px dotted var(--vermilion);}}

/* 全体コンテナ */
.chronicle{{max-width:920px;margin:0 auto;padding:48px 32px 120px;}}
.chronicle-intro{{margin-bottom:64px;border-bottom:1px solid var(--rule);padding-bottom:32px;}}
.chronicle-intro h1{{font-family:var(--serif-jp);font-size:44px;font-weight:700;letter-spacing:0.04em;color:var(--ink);margin:0 0 8px;line-height:1.3;}}
.chronicle-intro .en{{font-family:var(--serif-en);font-style:italic;font-size:13px;letter-spacing:0.22em;color:var(--vermilion);text-transform:uppercase;margin-bottom:20px;}}
.chronicle-intro p{{font-family:var(--serif-jp);font-size:14.5px;line-height:1.95;color:var(--ink-soft);letter-spacing:0.03em;margin:0 0 6px;}}
.chronicle-intro .stats{{margin-top:24px;display:flex;gap:32px;font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.16em;color:var(--ink-faint);}}
.chronicle-intro .stats .num{{font-size:26px;font-style:normal;color:var(--ink);font-weight:500;}}

/* 年セクション */
.year-block{{margin-bottom:80px;position:relative;}}
.year-head{{display:grid;grid-template-columns:14px 140px 1fr;gap:18px;align-items:start;margin-bottom:28px;}}
.year-stripe{{height:100%;min-height:80px;width:8px;background:#888;}}
.year-meta{{font-family:var(--serif-en);}}
.year-meta .year-num{{font-size:42px;font-weight:500;color:var(--ink);letter-spacing:0.02em;line-height:1;}}
.year-meta .year-phase{{margin-top:8px;font-style:italic;font-size:10px;letter-spacing:0.18em;color:var(--ink-faint);text-transform:uppercase;line-height:1.4;}}
.year-title .year-key{{font-family:var(--sans-jp);font-weight:800;font-size:13px;color:var(--vermilion);letter-spacing:0.12em;margin-bottom:8px;}}
.year-title .year-band{{margin:0 0 10px;font-family:var(--sans-jp);font-weight:900;font-size:24px;color:var(--ink);letter-spacing:0.04em;line-height:1.4;}}
.year-title .year-poetic{{font-family:var(--serif-jp);font-size:13.5px;font-style:normal;color:var(--ink-soft);letter-spacing:0.04em;line-height:1.7;margin:0;padding:8px 0 0;border-top:1px dotted var(--rule);}}

/* トラックエリア */
.year-tracks{{padding-left:172px;}}
.track{{margin-bottom:24px;}}
.track-h{{font-family:var(--serif-en);font-style:italic;font-size:10px;letter-spacing:0.22em;color:var(--ink-faint);text-transform:uppercase;border-bottom:1px solid var(--rule);padding-bottom:5px;margin-bottom:12px;}}
.track-text{{font-family:var(--sans-jp);}}

/* 項目 */
.ev{{display:block;font-size:11.5px;line-height:1.5;padding:1px 0 1px 12px;position:relative;color:var(--ink-mute);}}
.ev::before{{content:"・";position:absolute;left:0;color:var(--ink-faint);}}
.ev-mid{{font-size:14px;line-height:1.45;padding:3px 0 3px 12px;border-left:2.5px solid var(--ink);font-weight:700;color:var(--ink);margin:5px 0 5px -2px;padding-left:10px;}}
.ev-mid::before{{display:none;}}
.ev-maj{{font-size:19px;line-height:1.32;padding:5px 0 5px 12px;font-weight:800;letter-spacing:-0.005em;color:var(--ink);margin:9px 0 9px -3px;border-left:3px solid var(--vermilion);padding-left:11px;}}
.ev-maj::before{{display:none;}}

/* Track ごとの色 */
.track-thought .ev-mid{{border-left-color:var(--marimo-blue);}}
.track-thought .ev-maj{{border-left-color:var(--marimo-blue);}}
.track-org .ev-mid{{border-left-color:var(--marimo-blue);}}
.track-org .ev-maj{{border-left-color:var(--marimo-blue);}}
.track-society .ev-mid{{border-left-color:var(--warm-amber);}}
.track-society .ev-maj{{border-left-color:var(--warm-amber);}}
.track-economy .ev-mid{{border-left-color:var(--warm-grey);}}
.track-economy .ev-maj{{border-left-color:var(--warm-grey);}}

/* 統合トラック内のサブヘッダ */
.track-world .track-subblock{{margin-bottom:12px;}}
.track-world .sub-h{{display:inline-block;padding:1px 7px 2px;font-weight:700;font-size:9.5px;color:#fff;letter-spacing:0.18em;line-height:1.2;margin-bottom:6px;}}
.track-society .sub-h{{background:var(--warm-amber);}}
.track-economy .sub-h{{background:var(--warm-grey);}}

/* 社長メッセージカード（r5 / r4 のみ目立つカードに） */
.issue-card{{display:block;margin:6px 0;padding:8px 12px 9px;background:transparent;border-left:4px solid var(--marimo-blue);font-family:var(--sans-jp);cursor:pointer;text-decoration:none;color:inherit;transition:background 0.15s;}}
.issue-card:hover{{background:rgba(0,150,214,0.06);}}
.issue-card.r5{{background:rgba(0,150,214,0.18);border:1px solid var(--marimo-blue);border-left-width:4px;padding:10px 13px 11px;}}
.issue-card.r5:hover{{background:rgba(0,150,214,0.26);}}
.issue-card .ic-no{{font-family:var(--serif-en);font-style:italic;font-size:11.5px;letter-spacing:0.16em;color:var(--marimo-blue);font-weight:700;margin-right:6px;}}
.issue-card .ic-mo{{font-family:var(--serif-en);font-style:italic;font-size:10.5px;color:var(--ink-faint);margin-right:6px;}}
.issue-card .ic-ttl{{font-size:14.5px;line-height:1.45;font-weight:700;color:var(--ink);}}
.issue-card.r5 .ic-ttl{{display:block;font-size:21px;line-height:1.3;font-weight:800;letter-spacing:-0.005em;margin-top:3px;}}

/* レスポンシブ */
@media(max-width:760px){{
  .year-head{{grid-template-columns:8px 1fr;gap:12px;}}
  .year-meta{{grid-column:1 / -1;display:flex;align-items:baseline;gap:12px;}}
  .year-meta .year-num{{font-size:30px;}}
  .year-tracks{{padding-left:0;}}
}}
</style>
</head>
<body>

<header class="site-head">
  <a href="chronicle_TOP.html" class="logo-link" title="TOP"><img src="{logo_data}" class="logo" alt="MARIMO" /></a>
  <div>
    <div class="brand">President Chronicle</div>
    <div class="title">マリモクロニクル<span class="sub">— 統合版／縦の年代記</span></div>
  </div>
  <a href="chronicle_FULLTEXT_complete.html" class="nav-link">全 268 号 完全版 →</a>
  <a href="chronicle_TOP_makimono.html" class="alt-link">巻物（縦書き版）</a>
</header>

<main class="chronicle">
  <section class="chronicle-intro">
    <div class="en">President Chronicle ／ Editorial Engineering</div>
    <h1>マリモクロニクル</h1>
    <p>深川真が、社員に贈り続けた全 272 通のメッセージ。<br>2007 年 12 月 9 日から 2025 年現在に至る、思想・組織・社会・経済の<strong>縦帯照応</strong>を、年代記として一列に編んだ統合版です。</p>
    <p style="font-size:12px;color:var(--ink-mute);">編集工学的に、年ごとに 4 つの層（思想／組織／社会／経済）を縦帯で照応させ、象徴号は青いブロック、★★は朱バー、★は黒バーで視覚化しています。</p>
    <div class="stats">
      <div><span class="num">{total_years}</span> Years</div>
      <div><span class="num">{total_issues}</span> Issues</div>
      <div><span class="num">7</span> Phases</div>
    </div>
  </section>

  {year_sections}

</main>

<script>
// 号カードクリック → 全文ページへ
document.querySelectorAll(".issue-card").forEach(card => {{
  card.addEventListener("click", e => {{
    const no = card.dataset.no;
    if (no) location.href = `chronicle_FULLTEXT_complete.html#no=${{no}}`;
  }});
}});
</script>

</body>
</html>
"""


def build_makimono_html(data, titles):
    """縦書き巻物版：横スクロール、右が古い／左が新しい。"""
    phases_by_id = {p["id"]: p for p in data["phases"]}
    issues_by_year = {}
    for iss in data["allIssues"]:
        yr = int(iss["y"])
        issues_by_year.setdefault(yr, []).append(iss)
    keyByNo = {k["no"]: k for k in data["keyIssues"]}

    def render_year_column(y):
        phase = phases_by_id.get(y["phase"], {})
        thought_html = render_track_items(y.get("thought", ""))
        org_html = render_track_items(y.get("org", ""))
        soc_html = render_track_items(y.get("society", ""), kind="society")
        eco_html = render_track_items(y.get("economy", ""), kind="economy")

        # Track I: r5/r4 issues as cards
        year_issues = issues_by_year.get(y["year"], [])
        notable = [iss for iss in year_issues if iss["no"] in keyByNo]
        notable.sort(key=lambda iss: iss["y"])
        issue_cards = []
        for iss in notable:
            k = keyByNo[iss["no"]]
            if k["rank"] >= 4:
                title = titles.get(str(iss["no"]), k["title"])
                rank_cls = f"r{k['rank']}"
                issue_cards.append(
                    f'<div class="m-issue {rank_cls}" data-no="{iss["no"]}">'
                    f'<span class="m-no">第 {iss["no"]} 号</span>'
                    f'<span class="m-ttl">{escape(title)}</span>'
                    f'</div>'
                )

        return f"""
<section class="m-year" data-year="{y['year']}" data-phase="{y['phase']}">
  <header class="m-year-head" style="border-color:{phase.get('color','#888')};">
    <div class="m-year-num">{y['year']}</div>
    <div class="m-year-key">◆ {escape(y.get('key',''))}</div>
    <div class="m-year-band">{escape(y.get('bandTitle',''))}</div>
  </header>
  <div class="m-tracks">
    <div class="m-track m-track-thought">
      <div class="m-track-h">深川真</div>
      {''.join(issue_cards)}
      <div class="m-text">{thought_html}</div>
    </div>
    <div class="m-track m-track-org">
      <div class="m-track-h">MARIMO WAY</div>
      <div class="m-text">{org_html}</div>
    </div>
    <div class="m-track m-track-world">
      <div class="m-track-h">社会・経済</div>
      <div class="m-subblock m-society"><span class="m-sub-h">社会</span><div class="m-text">{soc_html}</div></div>
      <div class="m-subblock m-economy"><span class="m-sub-h">経済</span><div class="m-text">{eco_html}</div></div>
    </div>
  </div>
  <footer class="m-year-foot">
    <div class="m-poetic">{escape(y.get('poetic',''))}</div>
  </footer>
</section>
"""

    # 巻物：右が古い（最初）→左が新しい
    # year_sections は日付順なので、CSS で flex-direction: row-reverse で逆転
    year_columns = "\n".join(render_year_column(y) for y in data["years"])

    logo_b64 = LOGO_PATH.read_text(encoding="utf-8").strip()
    logo_data = f"data:image/png;base64,{logo_b64}"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>マリモクロニクル — 巻物（縦書き）</title>
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
html,body{{margin:0;padding:0;background:var(--paper);color:var(--ink-soft);font-family:var(--sans-jp);height:100vh;overflow:hidden;}}

/* ヘッダー（横方向、左固定） */
.m-head{{position:fixed;top:0;left:0;right:0;height:54px;padding:0 24px;border-bottom:1px solid var(--rule);background:var(--paper-warm);display:flex;align-items:center;gap:14px;z-index:10;}}
.m-head .logo{{height:34px;}}
.m-head .brand{{font-family:var(--serif-en);font-style:italic;font-size:10.5px;letter-spacing:0.22em;color:var(--vermilion);text-transform:uppercase;}}
.m-head .title{{font-family:var(--sans-jp);font-weight:900;font-size:16px;letter-spacing:0.06em;color:var(--ink);}}
.m-head .sub{{font-size:10.5px;font-weight:500;color:var(--ink-mute);letter-spacing:0.04em;margin-left:8px;}}
.m-head .scroll-hint{{margin-left:auto;font-family:var(--serif-en);font-style:italic;font-size:11px;color:var(--ink-faint);letter-spacing:0.16em;}}
.m-head a{{font-family:var(--sans-jp);font-size:11px;color:var(--ink);text-decoration:none;border:1px solid var(--ink);padding:5px 12px;font-weight:700;letter-spacing:0.04em;margin-left:6px;}}
.m-head a:hover{{background:var(--ink);color:#fff;}}

/* 巻物本体：横スクロール、右が古い→左が新しい */
.makimono{{position:fixed;top:54px;left:0;right:0;bottom:0;overflow-x:auto;overflow-y:hidden;writing-mode:vertical-rl;text-orientation:mixed;}}
.makimono-inner{{display:flex;flex-direction:row-reverse;height:100%;padding:32px;writing-mode:vertical-rl;}}

/* 各年のカラム（縦書きで右→左に進む） */
.m-year{{display:flex;flex-direction:row;height:100%;writing-mode:vertical-rl;border-left:1px solid var(--rule-soft);padding:0 24px;}}
.m-year:first-child{{border-left:none;}}
.m-year-head{{padding:8px 18px 12px;border-right:3px solid;border-color:#888;margin-right:18px;height:100%;}}
.m-year-head .m-year-num{{font-family:var(--serif-en);font-size:36px;color:var(--ink);font-weight:500;letter-spacing:0.02em;writing-mode:horizontal-tb;text-align:center;margin-bottom:14px;}}
.m-year-head .m-year-key{{font-family:var(--sans-jp);font-weight:800;font-size:14px;color:var(--vermilion);letter-spacing:0.12em;margin-bottom:10px;}}
.m-year-head .m-year-band{{font-family:var(--sans-jp);font-weight:900;font-size:18px;color:var(--ink);letter-spacing:0.06em;line-height:1.6;}}

/* トラック（横並びのバンド：思想／MARIMO WAY／社会経済） */
.m-tracks{{display:flex;flex-direction:row;gap:24px;height:100%;}}
.m-track{{padding:0 8px;border-right:1px dotted var(--rule-soft);min-width:60px;}}
.m-track:last-child{{border-right:none;}}
.m-track-h{{font-family:var(--serif-en);font-style:italic;font-size:10px;letter-spacing:0.22em;color:var(--ink-faint);text-transform:uppercase;writing-mode:vertical-rl;padding-top:8px;margin-bottom:14px;border-top:1px solid var(--rule);}}
.m-text{{font-family:var(--sans-jp);}}

.ev{{display:block;font-size:12px;line-height:1.7;padding:1px 12px 1px 0;position:relative;color:var(--ink-mute);writing-mode:vertical-rl;margin:6px 0;}}
.ev::before{{content:"・";position:absolute;top:0;color:var(--ink-faint);}}
.ev-mid{{font-size:15px;font-weight:700;color:var(--ink);border-right:2.5px solid var(--ink);padding:6px 12px 6px 0;margin:8px -2px;}}
.ev-mid::before{{display:none;}}
.ev-maj{{font-size:21px;font-weight:800;letter-spacing:0.02em;color:var(--ink);border-right:3px solid var(--vermilion);padding:8px 14px 8px 0;margin:12px -3px;line-height:1.5;}}
.ev-maj::before{{display:none;}}

.m-track-thought .ev-mid,.m-track-thought .ev-maj{{border-right-color:var(--marimo-blue);}}
.m-track-org .ev-mid,.m-track-org .ev-maj{{border-right-color:var(--marimo-blue);}}
.ev.kind-society.ev-mid,.ev.kind-society.ev-maj{{border-right-color:var(--warm-amber);}}
.ev.kind-economy.ev-mid,.ev.kind-economy.ev-maj{{border-right-color:var(--warm-grey);}}

/* サブブロック（社会/経済） */
.m-subblock{{margin-bottom:14px;}}
.m-sub-h{{display:inline-block;padding:1px 7px 2px;font-weight:700;font-size:10px;color:#fff;letter-spacing:0.18em;margin-bottom:6px;writing-mode:horizontal-tb;}}
.m-society .m-sub-h{{background:var(--warm-amber);}}
.m-economy .m-sub-h{{background:var(--warm-grey);}}

/* 号カード（縦書きの中の象徴号） */
.m-issue{{display:block;margin:8px 0;padding:8px 12px;border-right:4px solid var(--marimo-blue);font-family:var(--sans-jp);cursor:pointer;color:inherit;text-decoration:none;}}
.m-issue:hover{{background:rgba(0,150,214,0.06);}}
.m-issue.r5{{background:rgba(0,150,214,0.18);border:1px solid var(--marimo-blue);border-right-width:4px;padding:11px 14px;}}
.m-issue.r5:hover{{background:rgba(0,150,214,0.26);}}
.m-issue .m-no{{font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.16em;color:var(--marimo-blue);font-weight:700;margin-bottom:4px;writing-mode:horizontal-tb;display:inline-block;}}
.m-issue .m-ttl{{display:block;font-size:14px;font-weight:700;color:var(--ink);line-height:1.6;margin-top:6px;}}
.m-issue.r5 .m-ttl{{font-size:20px;font-weight:800;line-height:1.5;letter-spacing:0.02em;}}

/* フッター（詩的字句） */
.m-year-foot{{padding:8px 0 8px 18px;margin-left:18px;border-left:1px dotted var(--rule);height:100%;}}
.m-poetic{{font-family:var(--serif-jp);font-size:13px;color:var(--ink-soft);letter-spacing:0.04em;line-height:2;writing-mode:vertical-rl;}}
</style>
</head>
<body>

<header class="m-head">
  <a href="chronicle_TOP.html" class="logo-link"><img src="{logo_data}" class="logo" alt="MARIMO" /></a>
  <div>
    <div class="brand">President Chronicle</div>
    <div class="title">マリモクロニクル<span class="sub">— 巻物／縦書き版</span></div>
  </div>
  <span class="scroll-hint">← scroll right to advance through time（→ 古／← 新）</span>
  <a href="chronicle_TOP.html">統合版へ</a>
  <a href="chronicle_FULLTEXT_complete.html">全文へ</a>
</header>

<div class="makimono">
  <div class="makimono-inner">
    {year_columns}
  </div>
</div>

<script>
document.querySelectorAll(".m-issue").forEach(card => {{
  card.addEventListener("click", () => {{
    const no = card.dataset.no;
    if (no) location.href = `chronicle_FULLTEXT_complete.html#no=${{no}}`;
  }});
}});

// 巻物：縦スクロールホイールを横スクロールにマップ
const mk = document.querySelector(".makimono");
mk.addEventListener("wheel", e => {{
  if (e.deltaY !== 0 && e.deltaX === 0) {{
    e.preventDefault();
    mk.scrollLeft += e.deltaY;
  }}
}}, {{ passive: false }});
</script>

</body>
</html>
"""


def main():
    data = extract_data()
    titles = load_titles()

    # 統合版
    unified_html = build_unified_html(data, titles)
    out1 = DST_DIR / "chronicle_TOP.html"
    out1.write_text(unified_html, encoding="utf-8")
    print(f"Wrote {out1} ({len(unified_html):,} chars)")

    # 縦書き巻物版
    makimono_html = build_makimono_html(data, titles)
    out2 = DST_DIR / "chronicle_TOP_makimono.html"
    out2.write_text(makimono_html, encoding="utf-8")
    print(f"Wrote {out2} ({len(makimono_html):,} chars)")


if __name__ == "__main__":
    main()
