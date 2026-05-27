# THE PRESIDENT CHRONICLE ／ マリモクロニクル

マリモグループ社長・深川真が2007年12月9日から2025年に至るまで社員に贈り続けた **全 272 通のメッセージ（全 709,501 字）** を、松岡正剛『情報の歴史21』に倣った編集工学的クロニクルとして再編集したプロジェクト。

「思想・組織・社会・経済」という 4 つの軌道を縦帯で照応させ、リーダー個人の声・組織の歩み・時代の地を一つの読み物として編む試み。

---

## ディレクトリ構成

```
the-president-chronicle/
├── README.md                       ← このファイル
├── chronicle/                      ← 出力された HTML クロニクル群
│   ├── chronicle_TOP.html             統合版（メイン・3 トラック構成）
│   ├── chronicle_TOP_mixed.html       混合版（1 列・全軌道を時系列で）
│   ├── chronicle_TOP_makimono.html    巻物版（縦書き・横スクロール）
│   ├── chronicle_TOP_3track.html      3 トラック版（旧）
│   ├── chronicle_TOP_4track_backup.html 4 トラック版（旧）
│   └── chronicle_FULLTEXT_complete.html 全 268 号 本文全文 完全版
├── docs/                           ← 編集成果物
│   ├── STEP1_第1号〜第10号_萌芽分析.docx
│   ├── STEP2_編集工学的クロニクル設計.docx
│   ├── STEP2_編集工学的クロニクル設計ワークベンチ.xlsx
│   └── STEP3_書籍編集構造案.docx
├── scripts/                        ← ビルドスクリプト
│   ├── build_unified.py               全文統合 HTML を生成
│   ├── build_unified_top.py           統合版 TOP を生成
│   ├── build_mixed_top.py             混合版を生成
│   ├── extract_bodies_html.py         docx → 書式付き本文 JSON
│   ├── inject_track_markers.py        ★★／★ マーカーを DATA に注入
│   └── build_related.py               IDF タグから関連記事グラフ
├── data/                           ← 補助データ
│   ├── related.json                   関連記事グラフ
│   └── titles_only.js                 号番号 → タイトル
└── skill/
    └── editorial-chronicle.skill      Claude 用編集工学クロニクルスキル
```

---

## 主要成果物の見方

### 1. ビジュアル・クロニクル（HTML）

ブラウザで `chronicle/*.html` を開けば独立動作。CDN 依存なし、オフラインでも可。

| ファイル | 特徴 |
|---|---|
| `chronicle_TOP.html` | **メイン版**。縦の年表に 3 トラック（深川真／MARIMO WAY／社会・経済）を並走、現在の年・照応キー・詩的字句が左右にスクロール追従 |
| `chronicle_TOP_mixed.html` | 全 4 軌道を区別せず、3 列ランダム配置 ＋ 社長メッセージは号数順保持の混合版 |
| `chronicle_TOP_makimono.html` | 縦書き・横スクロールの巻物版（実験） |
| `chronicle_FULLTEXT_complete.html` | 全 268 号の本文全文。書式（太字・赤字・リスト）保持、タグベース関連記事ナビ付き |

### 2. 編集成果物（docx）

- **STEP1**：第1号〜第10号からの萌芽分析（思想・組織・時代の関係性）
- **STEP2**：クロニクル全体設計（フェーズ／トラック／照応キー）
- **STEP3**：書籍化のための編集構造提案

### 3. ビルドパイプライン

```
社長メッセージ docx 群
   ↓ extract_bodies_html.py
all_messages_html.json（書式付き本文）
   ↓
社長メッセージマッピング.xlsx
   ↓ build_related.py
related.json（タグ関連グラフ）
   ↓
chronicle.json（年・フェーズ・象徴号データ）
   ↓ inject_track_markers.py
chronicle.json（★★/★ マーカー付き）
   ↓
build_unified.py    → chronicle_FULLTEXT_complete.html
build_unified_top.py → chronicle_TOP.html
build_mixed_top.py  → chronicle_TOP_mixed.html
```

### 4. 編集工学クロニクル化スキル

`skill/editorial-chronicle.skill` は他の組織の長期コミュニケーション群（社長レター、創業者通信、月次ニュースレター等）にも汎用適用できる Claude 用スキル。Cowork でインストールして使用可。

---

## 方法論

松岡正剛『情報の歴史21』に倣い、**4 トラック並走 × 照応キー × 縦帯照応** という編集工学の語彙を借用。

- **照応キー**：各年に与える一語または二語の概念。「開示」「万策」「再生」「面影」「喪失」「転回」「交代」「人づくり」など、その年のトラック横断で立ち上がる動詞性。
- **縦帯照応**：同じ年で複数トラックが共鳴する瞬間。例：2008 年 1 月 深川真『万策尽きたのか？』× 9 月 リーマン破綻 → "万策" の縦帯。
- **3 階層タイポグラフィ**：象徴 (★★, 2x) ／ 普通 (★, 1.5x) ／ 細目 (1x)
- **面影編集**：リーダー自身が過去を語り直した号を、編集者がさらに編集するメタ層

詳細は `skill/editorial-chronicle.skill` 内の `references/methodology.md` 参照。

---

## ライセンス／著作権

社長メッセージ本文の著作権はマリモグループに帰属。本プロジェクトは社内利用および編集工学的研究を目的とする。
