# export_validator/core/checkers.py
"""
Checker classes for validating mesh objects before export.
"""

from abc import ABC, abstractmethod
from typing import List, Set, Tuple, Dict
import re
import bpy
import bmesh
from mathutils import Vector

from .issues import Issue, Severity, IssueID


class BaseChecker(ABC):
    """チェッカーの基底クラス"""
    
    @abstractmethod
    def check(self, obj: bpy.types.Object) -> List[Issue]:
        """
        オブジェクトを検証し、問題のリストを返す
        
        Args:
            obj: 検証対象のBlenderオブジェクト
            
        Returns:
            検出された問題のリスト
        """
        pass


class MaterialChecker(BaseChecker):
    """マテリアル関連の検証"""
    
    def check(self, obj: bpy.types.Object) -> List[Issue]:
        issues = []
        
        # E001: No Materials
        if len(obj.material_slots) == 0:
            issues.append(Issue(
                id=IssueID.NO_MATERIALS,
                severity=Severity.ERROR,
                category="No Materials",
                object_name=obj.name,
                message="No material slots",
                hint="Properties > Material",
                can_select=False,
                select_data=None
            ))
            return issues  # マテリアルがなければ空スロットチェックは不要
        
        # W007: Empty Material Slots
        empty_slots = []
        for i, slot in enumerate(obj.material_slots):
            if slot.material is None:
                empty_slots.append(i)
        
        if empty_slots:
            slot_str = ", ".join(str(i) for i in empty_slots)
            issues.append(Issue(
                id=IssueID.EMPTY_MATERIAL_SLOTS,
                severity=Severity.WARNING,
                category="Empty Material Slots",
                object_name=obj.name,
                message=f"Slot(s) {slot_str} empty",
                hint="Assign material or remove slot",
                can_select=False,
                select_data=None
            ))
        
        return issues


class UVChecker(BaseChecker):
    """UV関連の検証"""
    
    def check(self, obj: bpy.types.Object) -> List[Issue]:
        issues = []
        mesh = obj.data
        
        # E002: Missing UV
        if len(mesh.uv_layers) == 0:
            issues.append(Issue(
                id=IssueID.MISSING_UV,
                severity=Severity.ERROR,
                category="Missing UV",
                object_name=obj.name,
                message="No UV map found",
                hint="UV Editing workspace",
                can_select=False,
                select_data=None
            ))
        
        return issues


class TransformChecker(BaseChecker):
    """Transform関連の検証"""
    
    SCALE_TOLERANCE = 0.0001
    ROTATION_TOLERANCE = 0.0001
    
    def check(self, obj: bpy.types.Object) -> List[Issue]:
        issues = []
        
        scale = obj.scale
        rotation = obj.rotation_euler
        
        # W001: Unapplied Scale
        if not self._is_unit_scale(scale):
            scale_str = f"({scale.x:.2f}, {scale.y:.2f}, {scale.z:.2f})"
            issues.append(Issue(
                id=IssueID.UNAPPLIED_SCALE,
                severity=Severity.WARNING,
                category="Unapplied Scale",
                object_name=obj.name,
                message=scale_str,
                hint="Ctrl+A > Apply Scale",
                can_select=False,
                select_data=None
            ))
        
        # W002: Unapplied Rotation
        if not self._is_zero_rotation(rotation):
            rot_str = f"({rotation.x:.2f}, {rotation.y:.2f}, {rotation.z:.2f})"
            issues.append(Issue(
                id=IssueID.UNAPPLIED_ROTATION,
                severity=Severity.WARNING,
                category="Unapplied Rotation",
                object_name=obj.name,
                message=rot_str,
                hint="Ctrl+A > Apply Rotation",
                can_select=False,
                select_data=None
            ))
        
        # W003: Negative Scale
        negative_axes = self._get_negative_axes(scale)
        if negative_axes:
            axes_str = ", ".join(negative_axes)
            issues.append(Issue(
                id=IssueID.NEGATIVE_SCALE,
                severity=Severity.WARNING,
                category="Negative Scale",
                object_name=obj.name,
                message=f"Negative on {axes_str}",
                hint="Apply Scale or flip normals",
                can_select=False,
                select_data=None
            ))
        
        return issues
    
    def _is_unit_scale(self, scale) -> bool:
        """スケールが(1,1,1)かどうか"""
        return (
            abs(scale.x - 1.0) < self.SCALE_TOLERANCE and
            abs(scale.y - 1.0) < self.SCALE_TOLERANCE and
            abs(scale.z - 1.0) < self.SCALE_TOLERANCE
        )
    
    def _is_zero_rotation(self, rotation) -> bool:
        """回転が(0,0,0)かどうか"""
        return (
            abs(rotation.x) < self.ROTATION_TOLERANCE and
            abs(rotation.y) < self.ROTATION_TOLERANCE and
            abs(rotation.z) < self.ROTATION_TOLERANCE
        )
    
    def _get_negative_axes(self, scale) -> List[str]:
        """マイナスのスケールを持つ軸のリストを返す"""
        negative = []
        if scale.x < 0:
            negative.append("X")
        if scale.y < 0:
            negative.append("Y")
        if scale.z < 0:
            negative.append("Z")
        return negative


class FaceOrientationChecker(BaseChecker):
    """面の向き（法線 / Face Orientation）関連の検証。

    Blender の表示機能である "Face Orientation"（青/赤）そのものを
    参照せず、幾何学的な判定で「反転面（flipped faces）」の疑いが強い面を
    検出する。

    判定はメッシュの状態に応じて使い分ける:

    - 閉メッシュ（全エッジがちょうど2面接続）
        重心ベースの絶対判定（外向き判定）
    - 開メッシュ
        隣接面の巡回方向からの相対判定（整合性チェック）

    UI上のカテゴリ名は "Face Orientation" とする。
    Severity はメッシュの種類に関わらず WARNING。
    """
    
    def check(self, obj: bpy.types.Object) -> List[Issue]:
        issues = []
        mesh = obj.data
        
        if len(mesh.polygons) == 0:
            return issues
        
        try:
            # --- 最新のメッシュ状態を取得する ---
            # Edit Mode の編集内容がメッシュデータに未反映のまま検証が走ると、
            # 修正後でも古い法線で判定してしまうことがある。
            # 基本的に Rescan は Object Mode に戻してから走るが、
            # どの経路で呼ばれても最新状態になるようここでも同期しておく。
            try:
                # 可能なら Edit Mode の変更を反映
                obj.update_from_editmode()
            except Exception:
                pass
            try:
                mesh.update()
            except Exception:
                pass

            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.faces.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.verts.ensure_lookup_table()

            # 重要: bmesh の法線を必ず最新化する
            # これをしないと、修正後でも古い face.normal を参照し続けるケースがある。
            bm.normal_update()

            # bmesh の index は保証されないため明示的に更新する。
            # これをしないと「選択したはずの面が違う」などの不具合が起きやすい。
            bm.faces.index_update()
            bm.edges.index_update()
            bm.verts.index_update()
            
            # メッシュが閉じているか（Manifold）を判定
            is_closed = self._is_closed_mesh(bm)
            
            if is_closed:
                # 閉メッシュ: 重心法（絶対判定）
                flipped_indices, focus_index = self._detect_flipped_closed_mesh(bm, obj)
                
                if flipped_indices:
                    issues.append(Issue(
                        id=IssueID.FLIPPED_FACES,
                        severity=Severity.WARNING,
                        category="Face Orientation",
                        object_name=obj.name,
                        message=f"{len(flipped_indices)} flipped faces (closed mesh)",
                        hint="Mesh > Normals > Flip",
                        can_select=True,
                        select_data={
                            "type": "faces",
                            "indices": flipped_indices,
                            # Check Faces ボタンでフォーカスすべき代表面
                            # (Rescan のたびに再計算される)
                            "focus_index": focus_index,
                            "mesh_type": "closed",
                            "priority": 1  # 高優先度
                        }
                    ))
            else:
                # 開メッシュ: 隣接面比較（相対判定）
                inconsistent_indices, focus_index = self._detect_inconsistent_open_mesh(bm)
                
                if inconsistent_indices:
                    issues.append(Issue(
                        id=IssueID.FLIPPED_FACES,
                        # v1.0.0 要件: Face Orientation は常に WARNING
                        severity=Severity.WARNING,
                        category="Face Orientation",
                        object_name=obj.name,
                        message=f"{len(inconsistent_indices)} inconsistent faces (open mesh)",
                        hint="Mesh > Normals > Recalculate Outside",
                        can_select=True,
                        select_data={
                            "type": "faces",
                            "indices": inconsistent_indices,
                            "focus_index": focus_index,
                            "mesh_type": "open",
                            "priority": 2  # 低優先度（閉メッシュ優先）
                        }
                    ))
            
            bm.free()
        
        except Exception as e:
            print(f"[Validator] FaceOrientationChecker error for {obj.name}: {e}")
        
        return issues
    
    def _is_closed_mesh(self, bm: bmesh.types.BMesh) -> bool:
        """
        メッシュが閉じているか（Manifold）を判定
        
        すべてのエッジが正確に2つの面に接続されていれば閉メッシュ
        """
        if len(bm.faces) == 0:
            return False
        
        for edge in bm.edges:
            # エッジに接続された面の数が2でなければ開メッシュ
            if len(edge.link_faces) != 2:
                return False
        
        return True
    
    def _detect_flipped_closed_mesh(self, bm: bmesh.types.BMesh, obj: bpy.types.Object) -> Tuple[List[int], int]:
        """
        閉メッシュでの反転面検出（重心法）
        
        メッシュの重心から各面の中心への方向と法線を比較
        法線が内側を向いていれば反転
        """
        flipped_indices: List[int] = []
        # フォーカス候補（最も「内向き」度合いが強い面）
        focus_index: int = -1
        worst_dot: float = 1.0

        # --- World space で判定する（未適用スケール/回転でも精度を落としにくい）
        mw = obj.matrix_world
        nmat = mw.to_3x3().inverted().transposed()

        # メッシュ重心（world）
        centroid_world = Vector((0.0, 0.0, 0.0))
        for v in bm.verts:
            centroid_world += (mw @ v.co)
        centroid_world /= max(1, len(bm.verts))

        for face in bm.faces:
            face_center_world = mw @ face.calc_center_median()
            direction = face_center_world - centroid_world
            if direction.length == 0:
                # まれに重心と一致する場合はスキップ
                continue
            direction.normalize()

            normal_world = (nmat @ face.normal).normalized()
            d = normal_world.dot(direction)
            # dot > 0: 外向き, dot < 0: 内向き（反転疑い）
            if d < 0.0:
                flipped_indices.append(face.index)
                # より内向き（d がより小さい）面を代表としてフォーカス
                if d < worst_dot:
                    worst_dot = d
                    focus_index = face.index

        # 安全策: focus_index が未設定なら先頭
        if focus_index == -1 and flipped_indices:
            focus_index = flipped_indices[0]

        # 代表面を先頭にしておく（UI/ログの安定）
        if focus_index in flipped_indices:
            flipped_indices = [focus_index] + [i for i in flipped_indices if i != focus_index]

        return flipped_indices, focus_index
    
    def _detect_inconsistent_open_mesh(self, bm: bmesh.types.BMesh) -> Tuple[List[int], int]:
        """開メッシュでの反転疑い面検出（隣接面比較 / 相対判定）。

        開メッシュは "内外" が定義できないため、閉メッシュのような絶対判定は行わない。
        代わりに、隣接面との「巡回方向（winding）」の整合性を用いて、
        反転面（または局所的に向きが混在している面）を検出する。

        v1.1.3 の方針:
        - "同じ向きで共有エッジを辿っている"（same_winding）エッジの本数を
          面ごとにスコア化する
        - スコアが一定以上（または隣接数に対して割合が高い）面のみを不整合とみなす
        - フォーカスは最もスコアが高い面（= 反転の疑いが強い）を優先する

        返り値:
            (inconsistent_face_indices, focus_index)
        """

        if len(bm.faces) == 0:
            return [], -1

        # 面ごとのスコア: same_winding になっている共有エッジの本数
        same_winding_score: Dict[int, int] = {f.index: 0 for f in bm.faces}
        degree: Dict[int, int] = {f.index: 0 for f in bm.faces}

        # 共有エッジ（両側に面があるエッジ）のみで評価
        for edge in bm.edges:
            if len(edge.link_faces) != 2:
                continue
            f1, f2 = edge.link_faces[0], edge.link_faces[1]
            v1, v2 = edge.verts[0], edge.verts[1]
            w1 = self._get_edge_winding(f1, v1, v2)
            w2 = self._get_edge_winding(f2, v1, v2)
            if w1 == 0 or w2 == 0:
                continue

            degree[f1.index] += 1
            degree[f2.index] += 1

            # 正しい整合性: winding は逆（w1 != w2）
            # 同じなら、そのエッジ周りで向きが混在している可能性が高い
            if w1 == w2:
                same_winding_score[f1.index] += 1
                same_winding_score[f2.index] += 1

        # 不整合判定: スコアが閾値以上 かつ 割合が高い
        inconsistent: List[int] = []
        for fi, score in same_winding_score.items():
            deg = degree.get(fi, 0)
            if deg == 0:
                # 隣接面が無い（孤立面など）はここでは対象外
                continue

            ratio = score / float(deg)

            # 閾値:
            # - 共有エッジが2本以上ある場合: 半分以上が same_winding なら強い疑い
            # - 共有エッジが1本しかない場合: 1本でも same_winding なら疑い（ただし軽め）
            # これにより「隣の1枚だけ逆」などを拾いつつ、誤検知を減らす。
            if (deg >= 2 and ratio >= 0.5 and score >= 1) or (deg == 1 and score == 1):
                inconsistent.append(fi)

        # フォーカス面: same_winding スコアが最大の面（同点なら index が小さい方）
        focus_index = -1
        if inconsistent:
            inconsistent.sort(key=lambda i: (-same_winding_score.get(i, 0), i))
            focus_index = inconsistent[0]

        return inconsistent, focus_index
    
    def _get_edge_winding(self, face: bmesh.types.BMFace, v1: bmesh.types.BMVert, v2: bmesh.types.BMVert) -> int:
        """
        面内でのエッジの巡回方向を取得
        
        Returns:
            1: v1→v2の順で巡回
            -1: v2→v1の順で巡回
        """
        verts = list(face.verts)
        
        for i in range(len(verts)):
            if verts[i] == v1 and verts[(i + 1) % len(verts)] == v2:
                return 1
            if verts[i] == v2 and verts[(i + 1) % len(verts)] == v1:
                return -1
        
        return 0


class GeometryChecker(BaseChecker):
    """ジオメトリ関連の検証（N-gon、Loose Geometry、Small Faces）"""
    
    SMALL_FACE_THRESHOLD = 0.0001  # 面積の閾値
    
    def check(self, obj: bpy.types.Object) -> List[Issue]:
        issues = []
        mesh = obj.data
        
        if len(mesh.polygons) == 0:
            return issues
        
        try:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.faces.ensure_lookup_table()
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            
            # W005: N-gons
            ngon_indices = [f.index for f in bm.faces if len(f.verts) > 4]
            if ngon_indices:
                issues.append(Issue(
                    id=IssueID.NGONS,
                    severity=Severity.WARNING,
                    category="N-gons",
                    object_name=obj.name,
                    message=f"{len(ngon_indices)} faces",
                    hint="Ctrl+T to triangulate",
                    can_select=True,
                    select_data={"type": "faces", "indices": ngon_indices}
                ))
            
            # W006: Loose Geometry
            loose_verts = [v.index for v in bm.verts if not v.link_edges]
            loose_edges = [e.index for e in bm.edges if not e.link_faces]
            
            if loose_verts or loose_edges:
                parts = []
                if loose_verts:
                    parts.append(f"{len(loose_verts)} verts")
                if loose_edges:
                    parts.append(f"{len(loose_edges)} edges")
                
                issues.append(Issue(
                    id=IssueID.LOOSE_GEOMETRY,
                    severity=Severity.WARNING,
                    category="Loose Geometry",
                    object_name=obj.name,
                    message=", ".join(parts),
                    hint="Mesh > Clean Up > Delete Loose",
                    can_select=True,
                    select_data={
                        "type": "loose",
                        "verts": loose_verts,
                        "edges": loose_edges
                    }
                ))
            
            # I003: Small Faces
            small_indices = [
                f.index for f in bm.faces 
                if f.calc_area() < self.SMALL_FACE_THRESHOLD
            ]
            if small_indices:
                issues.append(Issue(
                    id=IssueID.SMALL_FACES,
                    severity=Severity.INFO,
                    category="Small Faces",
                    object_name=obj.name,
                    message=f"{len(small_indices)} faces",
                    hint="Mesh > Clean Up > Merge by Distance",
                    can_select=True,
                    select_data={"type": "faces", "indices": small_indices}
                ))
            
            bm.free()
        
        except Exception as e:
            print(f"[Validator] GeometryChecker error for {obj.name}: {e}")
        
        return issues


class AutoSmoothChecker(BaseChecker):
    """Auto Smooth関連の検証（Blenderバージョン対応）"""
    
    def check(self, obj: bpy.types.Object) -> List[Issue]:
        issues = []
        
        # Blender 4.1以降はAuto Smoothが廃止
        if bpy.app.version >= (4, 1, 0):
            # Smooth by Angle Modifierの有無をチェック
            has_smooth_modifier = any(
                mod.type == 'NODES' and 'Smooth by Angle' in mod.name
                for mod in obj.modifiers
            )
            # 4.1以降では、Modifierがない場合はInfoとして報告しない
            # （新しい仕様では標準的な状態のため）
            return issues
        
        # Blender 3.6 - 4.0
        mesh = obj.data
        if hasattr(mesh, 'use_auto_smooth') and not mesh.use_auto_smooth:
            # スムーズシェーディングが有効な面があるかチェック
            has_smooth_faces = any(not p.use_smooth for p in mesh.polygons)
            
            if not has_smooth_faces:
                issues.append(Issue(
                    id=IssueID.AUTO_SMOOTH_OFF,
                    severity=Severity.INFO,
                    category="Auto Smooth OFF",
                    object_name=obj.name,
                    message="Auto Smooth is disabled",
                    hint="Object Data > Normals > Auto Smooth",
                    can_select=False,
                    select_data=None
                ))
        
        return issues


class NamingChecker(BaseChecker):
    """命名規則の検証"""
    
    # 問題のあるパターン
    DEFAULT_NAME_PATTERN = re.compile(r'^(Cube|Sphere|Cylinder|Plane|Cone|Torus|Suzanne|Circle|Grid|Monkey)\.\d+$')
    JAPANESE_PATTERN = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]')
    SPECIAL_CHARS_PATTERN = re.compile(r'[/\\:*?"<>|]')
    
    def check(self, obj: bpy.types.Object) -> List[Issue]:
        issues = []
        name = obj.name
        problems = []
        
        # 空白を含む
        if ' ' in name:
            problems.append("Contains spaces")
        
        # 日本語を含む
        if self.JAPANESE_PATTERN.search(name):
            problems.append("Contains Japanese characters")
        
        # 特殊文字を含む
        if self.SPECIAL_CHARS_PATTERN.search(name):
            problems.append("Contains special characters")
        
        # デフォルト名（Cube.001等）
        if self.DEFAULT_NAME_PATTERN.match(name):
            problems.append("Default name")
        
        # 先頭が数字
        if name and name[0].isdigit():
            problems.append("Starts with number")
        
        # I002: Naming Issues
        if problems:
            issues.append(Issue(
                id=IssueID.NAMING_ISSUES,
                severity=Severity.INFO,
                category="Naming Issues",
                object_name=obj.name,
                message=", ".join(problems),
                hint="Rename in Outliner (F2)",
                can_select=False,
                select_data=None
            ))
        
        return issues


# チェッカーのリストを取得
def get_all_checkers() -> List[BaseChecker]:
    """全チェッカーのインスタンスを返す"""
    return [
        MaterialChecker(),
        UVChecker(),
        TransformChecker(),
        FaceOrientationChecker(),
        GeometryChecker(),
        AutoSmoothChecker(),
        NamingChecker(),
    ]
