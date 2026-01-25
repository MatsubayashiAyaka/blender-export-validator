# export_validator/panels/validator_panel.py
"""
N-Panel UI for the Export Validator.
"""

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Panel, PropertyGroup

from ..core.engine import get_validation_result
from ..core.issues import Severity


def get_object_filter_items(self, context):
    """オブジェクトフィルターの選択肢を動的に生成"""
    items = [('ALL', 'All Objects', 'Show all objects', 'NONE', 0)]
    
    result = get_validation_result()
    if result and result.objects:
        for idx, obj_name in enumerate(sorted(set(result.objects))):
            # オブジェクトごとの問題数をカウント
            obj_issues = result.filter_by_object(obj_name)
            error_count = sum(1 for i in obj_issues if i.severity == Severity.ERROR)
            warning_count = sum(1 for i in obj_issues if i.severity == Severity.WARNING)
            info_count = sum(1 for i in obj_issues if i.severity == Severity.INFO)
            
            # ラベルに問題数を含める
            label = f"{obj_name}"
            if error_count or warning_count or info_count:
                counts = []
                if error_count:
                    counts.append(f"Errors {error_count}")
                if warning_count:
                    counts.append(f"Warnings {warning_count}")
                if info_count:
                    counts.append(f"Information {info_count}")
                label += f" ({', '.join(counts)})"
            
            items.append((obj_name, label, f"Show issues for {obj_name}", 'OBJECT_DATA', idx + 1))
    
    return items


class ValidatorProperties(PropertyGroup):
    """Validator の設定を保持するPropertyGroup"""
    
    filter_mode: EnumProperty(
        name="Filter",
        description="Filter issues by severity",
        items=[
            ('ALL', 'All', 'Show all issues', 'NONE', 0),
            ('ERROR', 'Errors', 'Show errors only', 'CANCEL', 1),
            ('WARNING', 'Warnings', 'Show warnings only', 'ERROR', 2),
            ('INFO', 'Information', 'Show information only', 'INFO', 3),
        ],
        default='ALL'
    )
    
    object_filter: EnumProperty(
        name="Object",
        description="Filter issues by object",
        items=get_object_filter_items,
    )


class VALIDATOR_PT_main(Panel):
    """メインパネル"""
    bl_label = "Export Validator"
    bl_idname = "VALIDATOR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.validator_props
        
        # メッシュオブジェクトをフィルタ
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        # 選択なしの場合
        if not mesh_objects:
            box = layout.box()
            box.label(text="No mesh object selected", icon='INFO')
            return
        
        # v1.0.0仕様: 自動再検証は行わない（手動 Rescan のみ）
        result = get_validation_result()
        
        # ヘッダー：選択オブジェクト数
        header_box = layout.box()
        header_box.label(text=f"Selected: {len(mesh_objects)} object(s)", icon='OBJECT_DATA')
        
        # オブジェクトフィルター（常に表示）
        # 複数選択時はもちろん、単体選択でも「All/対象オブジェクト」を明示することで
        # ユーザーが状況を把握しやすくする。
        obj_row = header_box.row()
        obj_row.prop(props, "object_filter", text="")
        
        # 検証未実行の場合
        if not result or result.total_count is None:
            layout.separator()
            box = layout.box()
            box.label(text="Press 'Rescan' to run validation", icon='INFO')
            layout.separator()
            layout.operator("validator.rescan", icon='FILE_REFRESH')
            return

        # サマリーボックス
        summary_box = layout.box()
        summary_row = summary_box.row(align=True)
        
        # オブジェクトフィルターを適用した結果を取得
        filtered_result = self._get_filtered_result(result, props.object_filter)
        
        # エラー数（赤）
        error_col = summary_row.column()
        error_col.alert = filtered_result['error_count'] > 0
        error_col.label(text=f"Errors: {filtered_result['error_count']}", icon='CANCEL')
        
        # 警告数（黄）
        warning_col = summary_row.column()
        warning_col.label(text=f"Warnings: {filtered_result['warning_count']}", icon='ERROR')
        
        # Info数（青）
        info_col = summary_row.column()
        info_col.label(text=f"Information: {filtered_result['info_count']}", icon='INFO')
        
        # Severityフィルター
        layout.separator()
        filter_row = layout.row(align=True)
        filter_row.prop(props, "filter_mode", expand=True)
        
        # Rescanボタン
        layout.separator()
        layout.operator("validator.rescan", icon='FILE_REFRESH')
        
        # 問題がない場合
        if filtered_result['total_count'] == 0:
            layout.separator()
            box = layout.box()
            box.label(text="No issues found!", icon='CHECKMARK')
            return
        
        # 問題リストを描画
        layout.separator()
        self._draw_issues(layout, result, props.filter_mode, props.object_filter)
    
    def _get_filtered_result(self, result, object_filter):
        """オブジェクトフィルターを適用した結果を取得"""
        if object_filter == 'ALL':
            return {
                'error_count': result.error_count,
                'warning_count': result.warning_count,
                'info_count': result.info_count,
                'total_count': result.total_count,
            }
        else:
            issues = result.filter_by_object(object_filter)
            return {
                'error_count': sum(1 for i in issues if i.severity == Severity.ERROR),
                'warning_count': sum(1 for i in issues if i.severity == Severity.WARNING),
                'info_count': sum(1 for i in issues if i.severity == Severity.INFO),
                'total_count': len(issues),
            }
    
    def _draw_issues(self, layout, result, filter_mode, object_filter):
        """問題をSeverityとカテゴリごとに描画"""
        
        # Severityの順序
        severity_order = [Severity.ERROR, Severity.WARNING, Severity.INFO]
        severity_labels = {
            Severity.ERROR: "ERRORS",
            Severity.WARNING: "WARNINGS",
            Severity.INFO: "INFORMATION",
        }
        severity_icons = {
            Severity.ERROR: 'CANCEL',
            Severity.WARNING: 'ERROR',
            Severity.INFO: 'INFO',
        }
        
        # オブジェクトフィルターを適用
        if object_filter == 'ALL':
            issues = result.issues
        else:
            issues = result.filter_by_object(object_filter)
        
        # カテゴリでグループ化
        grouped = {}
        for issue in issues:
            if issue.category not in grouped:
                grouped[issue.category] = []
            grouped[issue.category].append(issue)
        
        for severity in severity_order:
            # Severityフィルターチェック
            if filter_mode != 'ALL' and filter_mode != severity:
                continue
            
            # このSeverityに該当するカテゴリを収集
            severity_categories = {}
            for category, cat_issues in grouped.items():
                category_issues = [i for i in cat_issues if i.severity == severity]
                if category_issues:
                    severity_categories[category] = category_issues
            
            if not severity_categories:
                continue
            
            # Severityヘッダー
            header_box = layout.box()
            header_row = header_box.row()
            header_row.alert = (severity == Severity.ERROR)
            header_row.label(
                text=f"{severity_labels[severity]}",
                icon=severity_icons[severity]
            )
            
            # カテゴリごとのボックス
            for category, cat_issues in severity_categories.items():
                self._draw_category_box(layout, category, cat_issues)
    
    def _draw_category_box(self, layout, category, issues):
        """カテゴリボックスを描画"""
        box = layout.box()
        
        # カテゴリ名
        box.label(text=category, icon='DOT')
        
        # セパレータ
        box.separator(factor=0.5)
        
        # 各Issue
        for issue in issues:
            # オブジェクト行
            row = box.row()
            row.label(text=f"● {issue.object_name}")
            
            # メッセージ行
            msg_row = box.row()
            msg_row.label(text=f"    {issue.message}")
            
            # Check Facesボタン（該当する場合）
            if issue.can_select:
                btn_row = box.row()
                btn_row.scale_y = 0.9
                op = btn_row.operator(
                    "validator.check_faces",
                    text="Check Faces",
                    icon='RESTRICT_SELECT_OFF'
                )
                op.object_name = issue.object_name
                op.issue_id = issue.id
                op.category = issue.category
        
        # ヒント
        box.separator(factor=0.5)
        hint_row = box.row()
        hint_row.scale_y = 0.8
        hint_row.label(text=f"💡 {issues[0].hint}")


# 登録するクラスのリスト
classes = [
    ValidatorProperties,
    VALIDATOR_PT_main,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # シーンにプロパティを追加
    bpy.types.Scene.validator_props = bpy.props.PointerProperty(type=ValidatorProperties)


def unregister():
    # プロパティを削除
    del bpy.types.Scene.validator_props
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
