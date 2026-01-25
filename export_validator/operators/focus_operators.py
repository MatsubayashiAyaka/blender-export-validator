# export_validator/operators/focus_operators.py
"""
Operators for the Export Validator.
"""

import bpy
from bpy.props import StringProperty, IntProperty

from ..core.engine import (
    get_validation_result,
    run_validation,
)
from ..core.issues import Severity
from ..utils.viewport import (
    select_elements,
    focus_on_selection,
    ensure_object_active,
    ensure_object_mode,
    select_single_face,
)


class VALIDATOR_OT_rescan(bpy.types.Operator):
    """選択オブジェクトを再検証"""
    bl_idname = "validator.rescan"
    bl_label = "Rescan"
    bl_description = "Re-validate selected objects"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        # Object Modeに切り替え（Edit Mode中は正確な検証ができない）
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # 検証実行
        result = run_validation(context)
        
        # 結果をレポート
        self.report(
            {'INFO'},
            f"Validation complete: {result.error_count} errors, "
            f"{result.warning_count} warnings, {result.info_count} info"
        )
        
        # UI更新
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}


class VALIDATOR_OT_check_faces(bpy.types.Operator):
    """問題のある要素を選択してフォーカス"""
    bl_idname = "validator.check_faces"
    bl_label = "Check Faces"
    bl_description = "Select problematic elements and focus view"
    bl_options = {'REGISTER', 'UNDO'}
    
    object_name: StringProperty(
        name="Object Name",
        description="Name of the object to select elements from",
        default=""
    )
    
    issue_id: StringProperty(
        name="Issue ID",
        description="ID of the issue (e.g., W004)",
        default=""
    )
    
    category: StringProperty(
        name="Category",
        description="Category of the issue",
        default=""
    )
    
    def execute(self, context):
        # オブジェクトを取得
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            self.report({'ERROR'}, f"Object '{self.object_name}' not found")
            return {'CANCELLED'}
        
        if obj.type != 'MESH':
            self.report({'ERROR'}, f"Object '{self.object_name}' is not a mesh")
            return {'CANCELLED'}
        
        # 検証結果からIssueを検索
        result = get_validation_result()
        issue = result.find_issue(self.object_name, self.issue_id)
        
        if not issue:
            # カテゴリで再検索
            for i in result.issues:
                if i.object_name == self.object_name and i.category == self.category:
                    issue = i
                    break
        
        if not issue:
            self.report({'WARNING'}, f"Issue not found. Please rescan.")
            return {'CANCELLED'}
        
        if not issue.can_select or not issue.select_data:
            self.report({'WARNING'}, f"This issue does not support element selection")
            return {'CANCELLED'}
        
        # Object Modeに切り替え
        ensure_object_mode(context)
        
        # オブジェクトをアクティブに
        ensure_object_active(context, obj)
        
        # Face Orientationの場合は特別な処理
        if issue.category == "Face Orientation":
            success = self._handle_face_orientation(context, obj, issue, result)
        else:
            # 通常の要素選択
            # 仕様: フォーカスは「どれか1つ」に寄せたい。
            # view_selected は選択範囲全体にズームしてしまうため、faces については
            # 代表として先頭1面のみを選択してフォーカスする。
            select_data = issue.select_data or {}
            if select_data.get("type") == "faces":
                indices = select_data.get("indices", [])
                if indices:
                    focus_index = select_data.get("focus_index", -1)
                    pick = focus_index if (isinstance(focus_index, int) and focus_index in indices) else indices[0]
                    success = select_single_face(obj, pick)
                else:
                    success = False
            else:
                success = select_elements(obj, select_data)
        
        if not success:
            self.report({'ERROR'}, "Failed to select elements")
            return {'CANCELLED'}
        
        # ビューをフォーカス
        focus_on_selection(context)
        
        # 選択数をレポート
        select_data = issue.select_data or {}
        element_type = select_data.get("type", "")
        
        if element_type == "faces":
            count = len(select_data.get("indices", []))
            mesh_type = select_data.get("mesh_type", "")
            if mesh_type:
                self.report({'INFO'}, f"Selected {count} face(s) ({mesh_type} mesh)")
            else:
                self.report({'INFO'}, f"Selected {count} face(s)")
        elif element_type == "loose":
            verts = len(select_data.get("verts", []))
            edges = len(select_data.get("edges", []))
            self.report({'INFO'}, f"Selected {verts} vert(s), {edges} edge(s)")
        
        return {'FINISHED'}
    
    def _handle_face_orientation(self, context, obj, issue, result):
        """
        Face Orientationの特別な処理
        
        閉メッシュの反転面を優先してフォーカス
        同じ優先度の場合は最初に検出された面をフォーカス
        """
        select_data = issue.select_data
        indices = select_data.get("indices", [])
        
        if not indices:
            return False
        
        # 同じオブジェクトのFace Orientation問題をすべて取得
        face_orientation_issues = [
            i for i in result.issues 
            if i.object_name == obj.name and i.category == "Face Orientation"
        ]
        
        # 優先度でソート（低い数値 = 高優先度）
        # 閉メッシュ（WARNING）が開メッシュ（INFO）より優先
        face_orientation_issues.sort(
            key=lambda i: (
                i.select_data.get("priority", 99) if i.select_data else 99,
                0 if i.severity == Severity.WARNING else 1
            )
        )
        
        # 最も優先度の高い問題を選択
        if face_orientation_issues:
            priority_issue = face_orientation_issues[0]
            priority_data = priority_issue.select_data
            
            if priority_data:
                priority_indices = priority_data.get("indices", [])
                focus_index = priority_data.get("focus_index", -1)
                
                if priority_indices:
                    # 最初の1面のみを選択してフォーカス
                    pick = focus_index if (isinstance(focus_index, int) and focus_index in priority_indices) else priority_indices[0]
                    return select_single_face(obj, pick)
        
        # フォールバック: 元のindicesの最初の面を選択
        return select_single_face(obj, indices[0])


# 登録するクラスのリスト
classes = [
    VALIDATOR_OT_rescan,
    VALIDATOR_OT_check_faces,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
