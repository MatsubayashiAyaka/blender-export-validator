# CHANGELOG

このプロジェクトの変更履歴を記録します。

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
