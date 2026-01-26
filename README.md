# Export Validator（Blender アドオン）

Export Validator は、**FBX エクスポート前にメッシュの問題を検出・可視化する Blender 用バリデーションアドオン**です。  
Unity / Unreal Engine などのリアルタイムエンジン向け制作において、インポート後にトラブルになりやすい問題を事前に検知し、修正漏れを防ぎます。

本リポジトリは **テクニカルアーティスト向けポートフォリオツール** として設計されています。

- Blender ネイティブな UX（非モーダル Sidebar パネル）
- 非破壊設計（自動修正は行わない）
- 実制作で役立つ実践的な検証項目
- 選択・フォーカス中心の高速ワークフロー

---

## 主な機能

### Geometry（ジオメトリ検証）
- Face Orientation（裏返り / 法線不整合）
- Ngon 検出
- ルーズジオメトリ（孤立頂点 / 孤立エッジ）

### Transform（トランスフォーム検証）
- 非一様スケール
- 負スケール
- 未適用 Transform

### UV / データ検証
- UV 未設定
- UV マップ過多

### ワークフロー
- エクスポート時 Gate ダイアログ（確認漏れ防止）
- Sidebar パネルでのフィルタリング（Severity / Object / Type）
- 「Check Faces」ボタンによる問題面の選択 + フォーカス
- 必要時のみ Rescan（常駐ハンドラなし・軽量）

### 安定性
- VIEW_3D コンテキスト安全なオペレーター実行
- Blender 4.2 Node Wrangler poll traceback 回避対応（デフォルト有効）

---

## 対応バージョン

- Blender 3.6 以降
- Blender 4.2.x で動作確認済み

---

## インストール方法（Release ZIP）

1. Releases から ZIP をダウンロード
2. Blender → Edit → Preferences → Add-ons
3. Install… → ZIP を選択
4. Export Validator を有効化

パネル位置：
- 3D Viewport → Sidebar（Nキー）→ Tool → Export Validator

---

## 使い方

1. メッシュオブジェクトを選択（複数可）
2. Rescan を実行
3. 必要に応じてフィルターを使用
4. 問題項目をクリックして対象オブジェクトを選択
5. Face Orientation / Ngon は Check Faces を実行して面を直接選択
6. 手動で修正
7. File > Export > FBX (.fbx) でエクスポート（Gate ダイアログが表示）

---

## 技術仕様（Face Orientation 判定）

- 閉メッシュ：
  重心ベースの絶対判定  
  dot(normal, center→face) < 0

- 非閉メッシュ：
  隣接面の整合性 / ワインディング方向による相対判定

閉メッシュと開メッシュの両方に対応したハイブリッド方式を採用しています。

---

## 技術アーキテクチャ

### 設計目標
- エンジンインポート前に問題を検出
- 修正コストの削減
- Blender ネイティブな操作感
- 非破壊・軽量動作

### 実装
- Blender Python API
- bmesh トポロジ解析
- ハイブリッド Face Orientation 検出
- VIEW_3D コンテキスト安全オペレーター
- 常駐ハンドラなし（手動 Rescan のみ）
- Node Wrangler 互換対策

### 設計方針
- 自動修正は行わない（アーティスト主導）
- Select & Focus ワークフロー
- モーダル UI 不使用
- 制作スピード重視の最小UI

---

## このツールの目的

実制作では「エンジンにインポートしてから問題に気付く」よりも、  
**Blender 内で事前に修正する方が圧倒的に効率的** です。

本ツールは以下を重視して設計しています：

- パイプライン思考
- アーティスト向けツール設計
- 実用的なジオメトリ解析
- 安定した Blender アドオン構成

---

## ライセンス

MIT License

---

## Author

Matsubayashi Ayaka
