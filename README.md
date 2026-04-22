# miniWebBrowser

Python + PyQt6 で作る学習用ミニWebブラウザ。
URLを入力するとページを取得し、見出し・段落・リンクを整形して表示します。

---

## 1. ぱっと見の全体像

```
 ┌──────────────────────────────────────────────────────────┐
 │ [← 戻る] [URL入力欄..............] [Go] [📋 履歴]         │ ← ナビゲーションバー
 ├───────────────────────────────┬──────────────────────────┤
 │                               │ 📋 閲覧履歴              │
 │   ページ表示エリア            │  - タイトル / URL        │
 │   (QTextBrowser)              │  - タイトル / URL        │ ← 履歴パネル
 │                               │  ...                     │   (トグルで開閉)
 │                               │ [履歴をクリア]           │
 └───────────────────────────────┴──────────────────────────┘
```

ユーザー操作の流れ：

```
URL入力 / リンククリック / 戻る / 履歴ダブルクリック
        │
        ▼
 [ main.py ] BrowserWindow._navigate(url)
        │  UI をローディング状態に切替
        ▼
 [ main.py ] FetchWorker (QThread)  ← UIを固まらせないため別スレッド
        │
        ▼
 [ fetcher.py ] fetch_page(url)     ← requests で HTTP GET
        │  (成功フラグ, HTML or エラー文) を返す
        ▼
 [ parser.py ] parse_html / get_title  ← BeautifulSoup で整形
        │  QTextBrowser 用の簡易 HTML & <title> 抽出
        ▼
 [ main.py ] _on_fetch_finished
        │  - QTextBrowser に setHtml
        │  - ウィンドウタイトル更新
        │  - 履歴スタック & 履歴ログに追加
        ▼
       表示完了
```

---

## 2. ファイル構成

```
miniWebBrowser/
├── main.py           ← エントリーポイント / UI / 状態管理
├── fetcher.py        ← HTTP通信 (requests)
├── parser.py         ← HTML解析 (BeautifulSoup)
├── requirements.txt  ← 依存ライブラリ
├── PLAN.md           ← 開発計画 (Step1〜7)
└── README.md         ← このファイル
```

### 各ファイルの責務

| ファイル | 役割 | 主な関数 / クラス |
|---|---|---|
| [main.py](main.py) | GUI・イベント処理・履歴管理 | `BrowserWindow`, `FetchWorker` |
| [fetcher.py](fetcher.py) | URL → HTML文字列 | `fetch_page(url)` |
| [parser.py](parser.py) | HTML → 表示用HTML / タイトル抽出 | `parse_html(html, base_url)`, `get_title(html)` |

---

## 3. 論理的ロジック (ふるまいの詳細)

### 3-1. ナビゲーション (`_navigate` / [main.py:172](main.py:172))

1. 表示エリアを「読み込み中...」に差し替える
2. URL入力欄・Go・戻るを一時無効化 (多重クリック防止)
3. `FetchWorker` (QThread) を生成し、別スレッドで `fetch_page` を実行
4. 終了シグナル `finished(success, content, url)` が `_on_fetch_finished` に届く

### 3-2. 通信 (`fetch_page` / [fetcher.py:14](fetcher.py:14))

- `requests.get` でタイムアウト10秒、User-Agentを独自値に設定
  - Wikipediaがデフォルトの `python-requests` を403で弾くため
- `response.apparent_encoding` で文字コードを自動判定
- 例外は種類別にユーザー向け日本語メッセージへ変換
  - 接続エラー / タイムアウト / HTTPエラー / URL形式不正 / その他

### 3-3. HTML整形 (`parse_html` / [parser.py:40](parser.py:40))

- `script`, `style`, `nav`, `footer`, `header`, `aside`, `form`, `noscript` を除去
- `h1〜h3` は段階的なフォントサイズ、`h4〜h6` は太字のpタグに降格
- `p` / `li` は一定サイズ、`li` は先頭に `•` と左インデント
- インライン要素は `_render_inline` で再帰展開
  - `<a href>` はそのまま残し、`urljoin` で相対URL → 絶対URL に変換
- 何も抽出できなかった場合は `get_text()` の結果をフォールバック表示

### 3-4. 履歴管理 (main.py)

ブラウザ内部に2系統の履歴を保持：

| 変数 | 用途 |
|---|---|
| `_history` | 「戻る」ボタン用のスタック (URLのみ) |
| `_history_log` | 履歴パネル表示用 (URL + タイトル) |

- 成功したページだけが履歴に追加される
- 「戻る」は `_history` を2つpopして直前のURLへ再ナビゲート
- 履歴パネルは `QListWidget` で最新が上。ダブルクリックで再訪問
- 履歴パネルは既定で非表示。「📋 履歴」トグルボタンで `QSplitter` の右側を開閉

### 3-5. 非同期化 (`FetchWorker` / [main.py:32](main.py:32))

- `QThread` を継承し、`run()` で `fetch_page` を実行
- 完了時に `pyqtSignal(bool, str, str)` を emit
- メインUIスレッドはブロックされないため、重いページでも固まらない

---

## 4. 対応済み機能チェックリスト

PLAN.md の Step に沿った進捗です。

### Step 1〜6: レベル1ブラウザ (最小機能)
- [x] PyQt6 でウィンドウ表示 (Step 1)
- [x] URL入力欄 + Goボタン + 表示エリアのUI (Step 2)
- [x] `requests` による HTTP 通信 & エラーハンドリング (Step 3)
- [x] 文字コード自動判定 (Step 3)
- [x] BeautifulSoup によるHTMLパース (Step 4)
- [x] 見出し / 段落 / リストのスタイル分け (Step 5)
- [x] 不要タグ (script/style/nav/footer等) の除去 (Step 5)
- [x] `<a>` リンクのクリック遷移 (Step 6)
- [x] 相対URL → 絶対URL 変換 (Step 6)
- [x] URL入力欄へ現在URLを反映 (Step 6)

### Step 7: 仕上げ・安定化
- [x] ローディング表示 (7-1)
- [x] 戻るボタン (7-2)
- [x] ウィンドウタイトル連動 (7-3)
- [x] QThread による非同期通信 (7-4)

### 追加機能
- [x] 閲覧履歴パネル (タイトル + URL / ダブルクリックで再訪問)
- [x] 履歴パネルのトグル表示 (既定は非表示)
- [x] 履歴クリアボタン
- [x] Wikipedia 403 対策のUser-Agent設定

### 未対応 (将来拡張の候補)
- [ ] 進む (forward) ボタン
- [ ] 画像表示
- [ ] ブックマーク / 永続化 (ファイル保存)
- [ ] タブブラウジング
- [ ] 検索エンジン統合
- [ ] フォーム送信 (POST)

---

## 5. 起動方法

```bash
pip install -r requirements.txt
python main.py
```

Python 3.11+ 推奨。
