# CHANGELOG

このプロジェクトの変更履歴を記録します。

本プロジェクトはセマンティックバージョニング（SemVer）に従います。  
MAJOR.MINOR.PATCH

- MAJOR: 破壊的変更
- MINOR: 機能追加
- PATCH: バグ修正・ドキュメント改善・軽微な修正

---

## [1.0.1]

### Changed
- Author 情報を個人名に更新
- README に Technical Architecture / 設計思想セクションを追加
- ドキュメント構成を整理（README / CHANGELOG / LICENSE）

### Fixed
- Check Faces 実行時の選択状態安定化（単一オブジェクト正規化）
- VIEW_3D コンテキストを明示したオペレーター実行に修正し、他エディタ巻き込みを防止
- Blender 4.2 + Node Wrangler 有効時に発生する poll Traceback の抑止処理を強化

### Technical
- コンテキスト安全性の改善（bpy.ops override）
- UI 再描画由来の例外発生リスクを低減
- Release / GitHub 配布フローを整理

### Notes
- 安定性・ドキュメント改善のためのパッチリリース

---

## [1.0.0]

### Added
- エクスポート時の Gate ダイアログ
- Sidebar Validator パネル
- フィルタリング機能（Severity / Object / Type）
- Face Orientation チェック（閉メッシュ / 非閉メッシュ両対応）
- Ngon 検出 + Check Faces
- ルーズジオメトリ検出
- Transform チェック（非一様スケール / 負スケール / 未適用Transform）
- UV チェック（UV未設定 / UVマップ過多）

### Technical
- VIEW_3D コンテキスト安全なオペレーター実行
- Blender 4.2 Node Wrangler poll traceback 回避対応
- エクスポート前自動検証ワークフローの実装

### Notes
- 初回リリース
