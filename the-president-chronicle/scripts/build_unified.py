#!/usr/bin/env python3
"""全 8 巻を 1 つの完全版 HTML に統合。
- 全 268 号の本文・タイトル・日付を完全収録
- 左サイドバー：Vol タブ＋号一覧（フィルタ／検索付き）
- 右コンテンツ：本文＋日付（明朝、日付右揃え）
- 前後ナビ、巻またぎ自動遷移
"""
import json
import re
from pathlib import Path

OUT = Path("/sessions/hopeful-cool-bell/mnt/THE PRESIDENT CHRONICLE/chronicle_FULLTEXT_complete.html")
# 旧プレーン版（フォールバック用、サイズ計算用）
src_plain = json.load(open("/sessions/hopeful-cool-bell/all_messages.json", encoding="utf-8"))
# 新書式付き版（メイン本文）
src_html = json.load(open("/sessions/hopeful-cool-bell/all_messages_html.json", encoding="utf-8"))
related_raw = json.load(open("/sessions/hopeful-cool-bell/related.json", encoding="utf-8"))
RELATED = {int(k): v for k, v in related_raw.items()}

KESSU = {168, 174, 176, 256, 261}
TARGET = 87000

# Compute volume ranges (素のテキスト長で巻分け、構造は変えない)
nos_all = sorted(int(k) for k in src_plain.keys() if int(k) not in KESSU)
ranges = []
cur = []
cur_size = 0
for n in nos_all:
    sz = len(src_plain[str(n)].get("body", ""))
    if cur_size + sz > TARGET and cur:
        ranges.append((cur[0], cur[-1]))
        cur = []
        cur_size = 0
    cur.append(n)
    cur_size += sz
if cur:
    ranges.append((cur[0], cur[-1]))

THEMES = [
    ("開示と兆し",     "2007–2008", "Phase 1a–1b"),
    ("万策と再生",     "2008–2009", "Phase 1b"),
    ("公共と多角",     "2010–2012", "Phase 2"),
    ("制度と接続",     "2013",      "Phase 2"),
    ("生活と多角化",   "2014–2015", "Phase 2–3"),
    ("構えと面影",     "2016–2018", "Phase 3–4"),
    ("殻を破る／転回", "2019–2022", "Phase 4–5"),
    ("交代と人づくり", "2022–2025", "Phase 5–6"),
]

# Load TITLES
titles_text = open("/sessions/hopeful-cool-bell/titles_only.js", encoding="utf-8").read()
m = re.search(r"const TITLES=(\{.*\});", titles_text)
TITLES = json.loads(m.group(1))

DATE_PAT = re.compile(
    r"(?:^|\n)\s*("
    r"(?:平成|令和|昭和)\s*[元一二三四五六七八九十百\d]+\s*年.*?[日)）]"
    r"|"
    r"(?:平成|令和|昭和)\s*[元一二三四五六七八九十百\d]+\s*年\s*元旦"
    r"|"
    r"\d{4}年\s*\d+月\s*\d+日.*?[日)）]"
    r")\s*$"
)


def clean_body_plain(b: str):
    """フォールバック用のプレーン整形。"""
    b = "\n".join(line for line in b.split("\n") if line.strip() != "目次へ")
    b = b.replace("目次へ", "")
    b = re.sub(r"\n{3,}", "\n\n", b).strip()
    b = re.sub(r"\n*[=＝─━]{3,}.*$", "", b, flags=re.S).strip()
    date = ""
    m = DATE_PAT.search(b)
    if m:
        date = m.group(1).strip()
        b = b[: m.start()].rstrip()
    return b, date


def plain_to_html(b: str) -> str:
    """フォールバック：プレーンテキストを <p class="ind"> 化。"""
    out = []
    for raw_line in b.split("\n"):
        if not raw_line.strip():
            out.append('<p class="sp"></p>')
            continue
        # HTML エスケープ
        esc = (raw_line
               .replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;"))
        cls = "ind" if raw_line.startswith("　") else ""
        cls_attr = f' class="{cls}"' if cls else ""
        out.append(f"<p{cls_attr}>{esc}</p>")
    return "".join(out)


# Build all items + vol mapping
items = {}
vol_of = {}
for vi, (start, end) in enumerate(ranges, 1):
    for n in range(start, end + 1):
        if n in KESSU:
            continue
        if str(n) not in src_plain:
            continue
        # 書式付き本文を優先、なければフォールバック
        h_data = src_html.get(str(n))
        if h_data and h_data.get("body_html"):
            body_html = h_data["body_html"]
            date = h_data.get("date", "")
            title = h_data.get("title") or TITLES.get(str(n), f"第{n}号")
            # 文字数は素のテキスト長で（src_plain）
            plain, _ = clean_body_plain(src_plain[str(n)].get("body", ""))
            char_count = len(plain) + (len(date) if date else 0)
        else:
            plain, date = clean_body_plain(src_plain[str(n)].get("body", ""))
            body_html = plain_to_html(plain)
            title = TITLES.get(str(n), f"第{n}号")
            char_count = len(plain) + (len(date) if date else 0)
        items[n] = {
            "t": title,
            "b": body_html,
            "d": date,
            "f": char_count,
            "v": vi,
        }
        vol_of[n] = vi

items_json = json.dumps(items, ensure_ascii=False, separators=(",", ":"))

# Filter RELATED to only include issues that exist in items
related_filtered = {}
for no, rels in RELATED.items():
    if no not in items:
        continue
    rels2 = [r for r in rels if r["no"] in items]
    if rels2:
        related_filtered[no] = rels2
related_json = json.dumps(related_filtered, ensure_ascii=False, separators=(",", ":"))

# Vols metadata
vols_meta = []
for vi, (s, e) in enumerate(ranges, 1):
    th, period, phase = THEMES[vi-1]
    nos_in_vol = [n for n in range(s, e+1) if n not in KESSU and str(n) in src_plain]
    total_chars = sum(items[n]["f"] for n in nos_in_vol)
    vols_meta.append({"i": vi, "s": s, "e": e, "th": th, "p": period, "ph": phase, "n": len(nos_in_vol), "c": total_chars})

vols_json = json.dumps(vols_meta, ensure_ascii=False, separators=(",", ":"))

total_issues = sum(v["n"] for v in vols_meta)
total_chars = sum(v["c"] for v in vols_meta)

# ロゴを base64 で埋め込み（4.7KB）
logo_b64 = open("/sessions/hopeful-cool-bell/logo_b64_tiny.txt", encoding="utf-8").read().strip()
LOGO_DATAURI = f"data:image/png;base64,{logo_b64}"

html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>THE PRESIDENT CHRONICLE ／ 本文全文 完全版</title>
<style>
:root{{color-scheme:light;--paper:#f5f2ea;--paper-warm:#fbf8ee;--paper-edge:#ece4ce;--ink:#14223f;--ink-soft:#3a3630;--ink-mute:#6b6657;--ink-faint:#8a8276;--rule:#bdb7a9;--rule-soft:#d4cdb8;--vermilion:#8b3a2a;--marimo-blue:#0096D6;--serif-en:"Cormorant Garamond","Garamond",Georgia,serif;--serif-jp:"Noto Serif JP","YuMincho","Hiragino Mincho Pro",serif;--sans-jp:"Noto Serif JP","YuMincho","Hiragino Mincho Pro",serif;}}
*{{box-sizing:border-box;}}
html,body{{margin:0;padding:0;background:var(--paper);color:var(--ink-soft);font-family:var(--sans-jp);}}
.layout{{display:grid;grid-template-columns:320px 1fr;min-height:100vh;}}
.sidebar{{background:var(--paper-warm);border-right:1px solid var(--rule);padding:24px 18px 30px;overflow-y:auto;height:100vh;position:sticky;top:0;}}
.brand-logo{{display:block;text-align:center;margin-bottom:14px;}}
.brand-logo img{{display:inline-block;height:42px;width:auto;opacity:0.92;transition:opacity 0.15s;}}
.brand-logo:hover img{{opacity:1;}}
.brand{{font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.22em;color:var(--vermilion);text-transform:uppercase;}}
a.brand-title-link{{display:block;text-decoration:none;color:inherit;}}
a.brand-title-link:hover .brand-title{{color:var(--vermilion);}}
.brand-title{{margin-top:6px;font-family:var(--sans-jp);font-weight:900;font-size:18px;letter-spacing:0.06em;color:var(--ink);line-height:1.4;transition:color 0.15s;}}
.brand-title .arrow{{display:inline-block;color:var(--vermilion);font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.18em;margin-top:6px;border-bottom:1px dotted var(--vermilion);padding-bottom:1px;font-weight:500;}}
.brand-meta{{margin-top:8px;font-family:var(--serif-en);font-style:italic;font-size:10.5px;letter-spacing:0.16em;color:var(--ink-faint);}}
.search{{margin:14px 0 4px;}}
.search input{{width:100%;padding:8px 10px;border:1px solid var(--rule);background:#fff;font-family:var(--sans-jp);font-size:12px;letter-spacing:0.02em;color:var(--ink);outline:none;}}
.search input:focus{{border-color:var(--vermilion);}}
.vols-tabs{{margin:14px 0 8px;display:flex;flex-wrap:wrap;gap:4px;border-bottom:1px dotted var(--rule);padding-bottom:10px;}}
.vol-tab{{appearance:none;border:1px solid var(--rule);background:transparent;padding:5px 9px;font-family:var(--serif-en);font-style:italic;font-size:10.5px;letter-spacing:0.1em;color:var(--ink-mute);cursor:pointer;transition:background 0.12s,color 0.12s,border-color 0.12s;}}
.vol-tab:hover{{color:var(--ink);border-color:var(--ink);}}
.vol-tab.active{{background:var(--vermilion);color:#fff;border-color:var(--vermilion);}}
.vol-tab .vn{{font-weight:700;}}
.vol-current{{margin-top:8px;font-family:var(--sans-jp);font-size:11.5px;letter-spacing:0.04em;color:var(--ink);font-weight:700;}}
.vol-current .vmeta{{display:block;margin-top:2px;font-family:var(--serif-en);font-style:italic;font-size:9.5px;letter-spacing:0.14em;color:var(--ink-faint);font-weight:400;}}
.sb-list{{margin-top:14px;font-family:var(--sans-jp);}}
.sb-list-h{{font-size:10px;letter-spacing:0.14em;color:var(--ink-faint);margin-bottom:6px;text-transform:uppercase;font-family:var(--serif-en);font-style:italic;}}
.sb-item{{display:block;padding:7px 9px 8px;margin-bottom:3px;cursor:pointer;border-left:2px solid transparent;color:var(--ink-soft);text-decoration:none;font-size:11.5px;line-height:1.32;letter-spacing:0.02em;transition:background 0.12s,border-color 0.12s,color 0.12s;}}
.sb-item:hover{{background:rgba(20,34,63,0.05);}}
.sb-item.active{{background:rgba(139,58,42,0.08);border-left-color:var(--vermilion);color:var(--ink);font-weight:600;}}
.sb-item .sn{{font-family:var(--serif-en);font-style:italic;font-size:9.5px;letter-spacing:0.14em;color:var(--vermilion);margin-right:6px;}}
.sb-item.hidden{{display:none;}}
.content{{padding:48px 64px 90px;max-width:820px;margin:0 auto;width:100%;}}
.main-area{{display:flex;flex-direction:column;align-items:center;}}
.crumb{{font-family:var(--serif-en);font-style:italic;font-size:10.5px;letter-spacing:0.2em;color:var(--ink-faint);text-transform:uppercase;margin-bottom:14px;}}
.crumb a{{color:var(--vermilion);text-decoration:none;border-bottom:1px dotted var(--vermilion);transition:color 0.12s,border-color 0.12s;}}
.crumb a:hover{{color:var(--ink);border-bottom-color:var(--ink);}}
.top-link{{display:inline-block;margin-top:10px;margin-bottom:24px;padding:7px 14px;border:1px solid var(--ink);font-family:var(--sans-jp);font-size:11.5px;font-weight:700;letter-spacing:0.06em;color:var(--ink);text-decoration:none;transition:background 0.12s,color 0.12s;}}
.top-link:hover{{background:var(--ink);color:#fff;}}
.no-tag{{display:inline-block;padding:4px 12px 5px;background:var(--vermilion);color:#fff;font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.18em;margin-bottom:14px;}}
h1.ttl{{margin:0 0 10px;font-family:var(--serif-jp);font-weight:700;font-size:32px;letter-spacing:0.04em;color:var(--ink);line-height:1.4;}}
.meta{{font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.16em;color:var(--ink-faint);margin-bottom:32px;border-bottom:1px solid var(--rule);padding-bottom:16px;}}
.body{{font-family:var(--serif-jp);font-size:16px;line-height:2.05;letter-spacing:0.03em;color:var(--ink-soft);text-align:justify;}}
.body p{{margin:0 0 1.05em;line-height:2.05;}}
.body p.ind{{}}
.body p.sp{{margin:0;height:0.55em;}}
.body p.ctr{{text-align:center;}}
.body p.rgt{{text-align:right;}}
.body p.jst{{text-align:justify;}}
.body strong{{font-weight:700;color:var(--ink);}}
.body u{{text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:3px;}}
.body em{{font-style:italic;}}
.body mark{{background:rgba(255,210,30,0.32);padding:0 2px;color:inherit;}}
.body .c-red{{color:#a02020;}}
.body .c-blue{{color:#1f5db8;}}
.body .c-green{{color:#2a7a4f;}}
.body ul.body-list,.body ol.body-list{{padding-left:1.7em;margin:0.4em 0 1.1em;}}
.body ul.body-list{{list-style:disc;}}
.body ol.body-list{{list-style:decimal;}}
.body .body-list li{{margin-bottom:0.45em;line-height:1.95;padding-left:0.2em;}}
.body h2.body-h{{margin:1.6em 0 0.8em;font-family:var(--sans-jp);font-weight:800;font-size:18.5px;letter-spacing:0.04em;color:var(--ink);border-left:3px solid var(--vermilion);padding-left:10px;}}
.body h3.body-h{{margin:1.4em 0 0.7em;font-family:var(--sans-jp);font-weight:700;font-size:16.5px;letter-spacing:0.04em;color:var(--ink);}}
.body h4.body-h{{margin:1.2em 0 0.6em;font-family:var(--sans-jp);font-weight:700;font-size:15.5px;letter-spacing:0.04em;color:var(--ink-soft);}}
.dateline{{margin-top:36px;padding-top:8px;text-align:right;font-family:var(--serif-jp);font-size:13.5px;letter-spacing:0.06em;color:var(--ink-mute);font-style:normal;}}
.related{{margin-top:48px;padding-top:24px;border-top:1px solid var(--rule);}}
.related-h{{font-family:var(--serif-en);font-style:italic;font-size:11px;letter-spacing:0.22em;color:var(--vermilion);text-transform:uppercase;margin-bottom:4px;}}
.related-h2{{font-family:var(--sans-jp);font-weight:900;font-size:15px;letter-spacing:0.06em;color:var(--ink);margin-bottom:14px;}}
.related-list{{display:grid;grid-template-columns:1fr;gap:0;}}
.related-item{{display:block;padding:11px 14px 12px;border:1px solid var(--rule-soft);border-bottom:none;text-decoration:none;color:var(--ink-soft);font-family:var(--sans-jp);transition:background 0.12s,border-color 0.12s,color 0.12s;}}
.related-item:last-child{{border-bottom:1px solid var(--rule-soft);}}
.related-item:hover{{background:rgba(139,58,42,0.05);border-color:var(--vermilion);color:var(--ink);}}
.related-item .rno{{font-family:var(--serif-en);font-style:italic;font-size:10.5px;letter-spacing:0.16em;color:var(--vermilion);margin-right:10px;}}
.related-item .rttl{{font-size:13.5px;font-weight:600;letter-spacing:0.03em;line-height:1.5;}}
.related-item .rshared{{margin-top:4px;font-family:var(--sans-jp);font-size:10.5px;color:var(--ink-faint);letter-spacing:0.04em;}}
.related-item .rshared .rt{{display:inline-block;padding:1px 6px;margin-right:4px;background:rgba(139,58,42,0.07);color:var(--ink-mute);border-radius:1px;}}
.related-empty{{font-family:var(--sans-jp);font-size:11.5px;color:var(--ink-faint);font-style:italic;}}
.foot-nav{{margin-top:54px;padding-top:24px;border-top:1px solid var(--rule);display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;}}
.foot-nav button{{appearance:none;border:1px solid var(--ink);background:transparent;color:var(--ink);padding:11px 18px;font-family:var(--sans-jp);font-size:12px;font-weight:600;letter-spacing:0.06em;cursor:pointer;transition:background 0.12s,color 0.12s;}}
.foot-nav button:hover{{background:var(--ink);color:#fff;}}
.foot-nav button:disabled{{opacity:0.3;cursor:not-allowed;}}
.foot-nav .center{{font-family:var(--serif-en);font-style:italic;font-size:10.5px;letter-spacing:0.18em;color:var(--ink-faint);align-self:center;}}
.intro{{padding:0 0 24px;border-bottom:1px solid var(--rule);margin-bottom:32px;}}
.intro h2{{margin:0 0 10px;font-family:var(--sans-jp);font-weight:900;font-size:24px;letter-spacing:0.06em;color:var(--ink);}}
.intro p{{margin:0 0 8px;font-family:var(--sans-jp);font-size:13px;line-height:1.85;color:var(--ink-soft);letter-spacing:0.02em;}}
.intro .stats{{display:flex;gap:24px;margin-top:16px;flex-wrap:wrap;}}
.intro .stat{{display:flex;flex-direction:column;}}
.intro .stat .num{{font-family:var(--serif-en);font-size:28px;font-weight:500;color:var(--ink);letter-spacing:0.04em;}}
.intro .stat .lbl{{font-family:var(--serif-en);font-style:italic;font-size:10px;letter-spacing:0.18em;color:var(--ink-faint);text-transform:uppercase;}}
@media(max-width:880px){{.layout{{grid-template-columns:1fr;}}.sidebar{{position:static;height:auto;}}.content{{padding:30px 24px 60px;}}}}
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <a href="chronicle_TOP.html" class="brand-logo" title="クロニクル本体（TOP）に戻る"><img src="{LOGO_DATAURI}" alt="MARIMO" /></a>
    <div class="brand">President Chronicle</div>
    <a href="chronicle_TOP.html" class="brand-title-link" title="クロニクル本体（TOP）に戻る">
      <div class="brand-title">マリモクロニクル<br>本文全文 完全版<br><span class="arrow">← TOP に戻る</span></div>
    </a>
    <div class="brand-meta">{total_issues} 本 ／ {total_chars:,} 字</div>
    <div class="search"><input id="searchBox" type="text" placeholder="🔍 タイトル検索" /></div>
    <div class="vols-tabs" id="volsTabs"></div>
    <div class="vol-current" id="volCurrent"></div>
    <div class="sb-list">
      <div class="sb-list-h">Issues in this volume</div>
      <div id="sbList"></div>
    </div>
  </aside>
  <main class="content" id="content">
    <div class="intro">
      <h2>マリモクロニクル ／ 本文全文 完全版</h2>
      <a href="chronicle_TOP.html" class="top-link">← クロニクル本体（TOP）に戻る</a>
      <p>マリモグループ社長・深川真が 2007 年 12 月 9 日から 2025 年現在に至るまで社員に届け続けた社長メッセージ全 268 号（欠番 5 号を除く）の本文を、編集工学的クロニクルとして 8 巻に再編成した完全版です。左サイドバーから巻を選び、号タイトルをクリックすると本文が表示されます。</p>
      <p style="color:var(--ink-mute);font-size:11.5px;">明朝タイトル ／ 日付右揃え ／ 巻またぎ前後ナビ ／ タイトル検索付き。<br>左の「Vol」タブで巻切替、検索ボックスでタイトル絞り込みが可能です。</p>
      <div class="stats">
        <div class="stat"><span class="num">8</span><span class="lbl">Volumes</span></div>
        <div class="stat"><span class="num">{total_issues}</span><span class="lbl">Issues</span></div>
        <div class="stat"><span class="num">{total_chars:,}</span><span class="lbl">Characters</span></div>
        <div class="stat"><span class="num">19</span><span class="lbl">Years</span></div>
      </div>
    </div>
  </main>
</div>
<script>
const ITEMS={items_json};
const VOLS={vols_json};
const RELATED={related_json};
const NOS_ALL=Object.keys(ITEMS).map(n=>parseInt(n,10)).sort((a,b)=>a-b);

let currentVol = 1;
let currentNo = null;

function escapeHtml(s){{return String(s||"").replace(/[&<>"']/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));}}

const volsTabs = document.getElementById("volsTabs");
const volCurrent = document.getElementById("volCurrent");
const sbList = document.getElementById("sbList");
const content = document.getElementById("content");
const searchBox = document.getElementById("searchBox");

function renderVolsTabs(){{
  volsTabs.innerHTML = VOLS.map(v=>{{
    const cls = (v.i === currentVol) ? "active" : "";
    return `<button class="vol-tab ${{cls}}" data-vol="${{v.i}}"><span class="vn">Vol.${{v.i}}</span></button>`;
  }}).join("");
}}

function renderVolCurrent(){{
  const v = VOLS[currentVol-1];
  volCurrent.innerHTML = `Vol.${{v.i}} ／ ${{v.th}}<span class="vmeta">No.${{v.s}}–${{v.e}} ／ ${{v.n}} 本 ／ ${{v.p}}</span>`;
}}

function renderList(){{
  const v = VOLS[currentVol-1];
  const nosInVol = NOS_ALL.filter(n => ITEMS[n].v === currentVol);
  const q = searchBox.value.trim().toLowerCase();
  sbList.innerHTML = nosInVol.map(no=>{{
    const item = ITEMS[no];
    const cls = (no === currentNo) ? "active" : "";
    const visible = (!q || item.t.toLowerCase().includes(q));
    const hidden = visible ? "" : "hidden";
    return `<a class="sb-item ${{cls}} ${{hidden}}" data-no="${{no}}" href="#no=${{no}}"><span class="sn">No.${{no}}</span>${{escapeHtml(item.t)}}</a>`;
  }}).join("");
}}

function renderRelatedHtml(no){{
  const rels = RELATED[no];
  if (!rels || rels.length === 0){{
    return '';
  }}
  const items = rels.map(r => {{
    const sharedHtml = (r.shared && r.shared.length)
      ? `<div class="rshared">${{r.shared.map(s=>`<span class="rt">${{escapeHtml(s)}}</span>`).join('')}}</div>`
      : '';
    return `<a class="related-item" href="#no=${{r.no}}" data-no="${{r.no}}"><span class="rno">第 ${{r.no}} 号</span><span class="rttl">${{escapeHtml(r.t)}}</span>${{sharedHtml}}</a>`;
  }}).join('');
  return `
    <div class="related">
      <div class="related-h">Related Issues</div>
      <div class="related-h2">関連記事 ／ タグでつながる号</div>
      <div class="related-list">${{items}}</div>
    </div>
  `;
}}

function renderIssue(no){{
  const item = ITEMS[no];
  if (!item){{
    content.innerHTML = `<div style="padding:60px 0;text-align:center;color:var(--ink-faint);">第 ${{no}} 号は欠番です。</div>`;
    return;
  }}
  currentNo = no;
  currentVol = item.v;
  const v = VOLS[currentVol-1];
  const idx = NOS_ALL.indexOf(no);
  const prev = idx > 0 ? NOS_ALL[idx - 1] : null;
  const next = idx < NOS_ALL.length - 1 ? NOS_ALL[idx + 1] : null;
  content.innerHTML = `
    <div class="crumb"><a href="chronicle_TOP.html">← クロニクル本体（TOP）に戻る</a> ／ Vol.${{v.i}} ／ ${{v.th}} ／ ${{v.p}}</div>
    <span class="no-tag">第 ${{no}} 号</span>
    <h1 class="ttl">${{escapeHtml(item.t)}}</h1>
    <div class="meta">No. ${{no}} ／ Vol.${{v.i}} ／ ${{v.p}} ／ 全文 ${{item.f.toLocaleString()}} 字</div>
    <div class="body">${{item.b}}</div>
    ${{item.d ? `<div class="dateline">${{escapeHtml(item.d)}}</div>` : ""}}
    ${{renderRelatedHtml(no)}}
    <div class="foot-nav">
      <button onclick="goPrev()" ${{prev === null ? "disabled" : ""}}>← 第 ${{prev || ""}} 号</button>
      <span class="center">${{idx+1}} / ${{NOS_ALL.length}}</span>
      <button onclick="goNext()" ${{next === null ? "disabled" : ""}}>第 ${{next || ""}} 号 →</button>
    </div>
  `;
  renderVolsTabs();
  renderVolCurrent();
  renderList();
  // Auto-scroll list to current
  const activeItem = sbList.querySelector(".sb-item.active");
  if (activeItem) activeItem.scrollIntoView({{block:"nearest",behavior:"smooth"}});
}}

function goPrev(){{
  const idx = NOS_ALL.indexOf(currentNo);
  if (idx > 0) location.hash = "no=" + NOS_ALL[idx - 1];
}}
function goNext(){{
  const idx = NOS_ALL.indexOf(currentNo);
  if (idx < NOS_ALL.length - 1) location.hash = "no=" + NOS_ALL[idx + 1];
}}
function parseHash(){{
  const m = location.hash.match(/no=(\\d+)/);
  return m ? parseInt(m[1], 10) : null;
}}
function dispatch(){{
  const no = parseHash();
  if (no) renderIssue(no);
  else {{
    renderVolsTabs();
    renderVolCurrent();
    renderList();
  }}
}}

window.addEventListener("hashchange", dispatch);
volsTabs.addEventListener("click", (e) => {{
  const btn = e.target.closest(".vol-tab");
  if (!btn) return;
  currentVol = parseInt(btn.dataset.vol, 10);
  renderVolsTabs();
  renderVolCurrent();
  renderList();
}});
sbList.addEventListener("click", (e) => {{
  const a = e.target.closest(".sb-item");
  if (!a) return;
  e.preventDefault();
  location.hash = "no=" + a.dataset.no;
}});
searchBox.addEventListener("input", () => {{
  renderList();
}});

dispatch();
</script>
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
size_chars = len(html)
size_bytes = len(html.encode("utf-8"))
print(f"Wrote {OUT}")
print(f"Size: {size_chars:,} chars / {size_bytes:,} UTF-8 bytes")
print(f"Issues: {total_issues}, total chars: {total_chars:,}")
