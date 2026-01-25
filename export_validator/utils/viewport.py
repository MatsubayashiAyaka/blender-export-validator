# export_validator/utils/viewport.py
"""
Viewport utility functions for element selection and focus.
"""

from typing import Dict, Any, List, Optional
import bpy
import bmesh


# -----------------------------------------------------------------------------
# Operator context helpers
# -----------------------------------------------------------------------------
# Some bpy.ops (notably mesh selection mode) depend on a VIEW_3D context.
# When Shader Editor is open/active, running these ops without overriding can
# fail or trigger unrelated poll evaluations.

def _view3d_override():
    """Return an override dict for a VIEW_3D window region, or None."""
    ctx = bpy.context
    screen = getattr(ctx, 'screen', None)
    if not screen:
        return None
    for area in screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for region in area.regions:
            if region.type == 'WINDOW':
                ov = ctx.copy()
                ov['area'] = area
                ov['region'] = region
                return ov
    return None

def _ops_view3d(op_callable, **kwargs):
    """Run a bpy.ops callable in VIEW_3D context when possible."""
    ov = _view3d_override()
    if ov:
        with bpy.context.temp_override(**ov):
            return op_callable(**kwargs)
    return op_callable(**kwargs)


def select_faces_by_indices(obj: bpy.types.Object, indices: List[int]) -> bool:
    """
    指定したインデックスの面を選択
    
    Args:
        obj: 対象オブジェクト
        indices: 選択する面のインデックスリスト
        
    Returns:
        成功したらTrue
    """
    if obj.type != 'MESH':
        return False
    
    mesh = obj.data
    
    # Object Modeで操作
    current_mode = obj.mode
    if current_mode != 'OBJECT':
        _ops_view3d(bpy.ops.object.mode_set, mode='OBJECT')
    
    # 全選択解除
    for poly in mesh.polygons:
        poly.select = False
    for edge in mesh.edges:
        edge.select = False
    for vert in mesh.vertices:
        vert.select = False
    
    # 指定した面を選択
    for idx in indices:
        if 0 <= idx < len(mesh.polygons):
            mesh.polygons[idx].select = True
    
    # Edit Modeに戻す
    _ops_view3d(bpy.ops.object.mode_set, mode='EDIT')
    
    # Face選択モードに設定
    _ops_view3d(bpy.ops.mesh.select_mode, type='FACE')
    
    return True


def select_single_face(obj: bpy.types.Object, face_index: int) -> bool:
    """
    単一の面を選択してフォーカス用に準備
    
    Args:
        obj: 対象オブジェクト
        face_index: 選択する面のインデックス
        
    Returns:
        成功したらTrue
    """
    if obj.type != 'MESH':
        return False
    
    mesh = obj.data
    
    if face_index < 0 or face_index >= len(mesh.polygons):
        return False
    
    # Object Modeで操作
    if obj.mode != 'OBJECT':
        _ops_view3d(bpy.ops.object.mode_set, mode='OBJECT')
    
    # 全選択解除
    for poly in mesh.polygons:
        poly.select = False
    for edge in mesh.edges:
        edge.select = False
    for vert in mesh.vertices:
        vert.select = False
    
    # 指定した面を選択
    mesh.polygons[face_index].select = True
    
    # Edit Modeに切り替え
    _ops_view3d(bpy.ops.object.mode_set, mode='EDIT')
    
    # Face選択モードに設定
    _ops_view3d(bpy.ops.mesh.select_mode, type='FACE')
    
    return True


def select_verts_by_indices(obj: bpy.types.Object, indices: List[int]) -> bool:
    """
    指定したインデックスの頂点を選択
    
    Args:
        obj: 対象オブジェクト
        indices: 選択する頂点のインデックスリスト
        
    Returns:
        成功したらTrue
    """
    if obj.type != 'MESH':
        return False
    
    mesh = obj.data
    
    # Object Modeで操作
    current_mode = obj.mode
    if current_mode != 'OBJECT':
        _ops_view3d(bpy.ops.object.mode_set, mode='OBJECT')
    
    # 全選択解除
    for poly in mesh.polygons:
        poly.select = False
    for edge in mesh.edges:
        edge.select = False
    for vert in mesh.vertices:
        vert.select = False
    
    # 指定した頂点を選択
    for idx in indices:
        if 0 <= idx < len(mesh.vertices):
            mesh.vertices[idx].select = True
    
    # Edit Modeに戻す
    _ops_view3d(bpy.ops.object.mode_set, mode='EDIT')
    
    # Vertex選択モードに設定
    _ops_view3d(bpy.ops.mesh.select_mode, type='VERT')
    
    return True


def select_edges_by_indices(obj: bpy.types.Object, indices: List[int]) -> bool:
    """
    指定したインデックスの辺を選択
    
    Args:
        obj: 対象オブジェクト
        indices: 選択する辺のインデックスリスト
        
    Returns:
        成功したらTrue
    """
    if obj.type != 'MESH':
        return False
    
    mesh = obj.data
    
    # Object Modeで操作
    current_mode = obj.mode
    if current_mode != 'OBJECT':
        _ops_view3d(bpy.ops.object.mode_set, mode='OBJECT')
    
    # 全選択解除
    for poly in mesh.polygons:
        poly.select = False
    for edge in mesh.edges:
        edge.select = False
    for vert in mesh.vertices:
        vert.select = False
    
    # 指定した辺を選択
    for idx in indices:
        if 0 <= idx < len(mesh.edges):
            mesh.edges[idx].select = True
    
    # Edit Modeに戻す
    _ops_view3d(bpy.ops.object.mode_set, mode='EDIT')
    
    # Edge選択モードに設定
    _ops_view3d(bpy.ops.mesh.select_mode, type='EDGE')
    
    return True


def select_elements(obj: bpy.types.Object, select_data: Dict[str, Any]) -> bool:
    """
    select_dataに基づいて要素を選択
    
    Args:
        obj: 対象オブジェクト
        select_data: 選択データ
            - type: "faces", "verts", "edges", "loose"
            - indices: インデックスリスト（faces/verts/edges）
            - verts/edges: インデックスリスト（looseの場合）
            
    Returns:
        成功したらTrue
    """
    if not select_data:
        return False
    
    element_type = select_data.get("type")
    
    if element_type == "faces":
        indices = select_data.get("indices", [])
        return select_faces_by_indices(obj, indices)
    
    elif element_type == "verts":
        indices = select_data.get("indices", [])
        return select_verts_by_indices(obj, indices)
    
    elif element_type == "edges":
        indices = select_data.get("indices", [])
        return select_edges_by_indices(obj, indices)
    
    elif element_type == "loose":
        # Loose geometry: 頂点と辺の両方を選択
        verts = select_data.get("verts", [])
        edges = select_data.get("edges", [])
        
        if obj.type != 'MESH':
            return False
        
        mesh = obj.data
        
        # Object Modeで操作
        if obj.mode != 'OBJECT':
            _ops_view3d(bpy.ops.object.mode_set, mode='OBJECT')
        
        # 全選択解除
        for poly in mesh.polygons:
            poly.select = False
        for edge in mesh.edges:
            edge.select = False
        for vert in mesh.vertices:
            vert.select = False
        
        # 頂点を選択
        for idx in verts:
            if 0 <= idx < len(mesh.vertices):
                mesh.vertices[idx].select = True
        
        # 辺を選択
        for idx in edges:
            if 0 <= idx < len(mesh.edges):
                mesh.edges[idx].select = True
        
        # Edit Modeに戻す
        _ops_view3d(bpy.ops.object.mode_set, mode='EDIT')
        
        # Vertex選択モードに設定（looseは頂点が主）
        _ops_view3d(bpy.ops.mesh.select_mode, type='VERT')
        
        return True
    
    return False


def focus_on_selection(context: bpy.types.Context) -> bool:
    """
    現在の選択にビューをフォーカス
    
    Args:
        context: Blenderコンテキスト
        
    Returns:
        成功したらTrue
    """
    try:
        # 選択した要素にビューをフォーカス
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        override = context.copy()
                        override['area'] = area
                        override['region'] = region
                        with context.temp_override(**override):
                            bpy.ops.view3d.view_selected()
                        return True
        return False
    except Exception as e:
        print(f"[Validator] Focus error: {e}")
        return False


def ensure_object_active(context: bpy.types.Context, obj: bpy.types.Object) -> None:
    """
    オブジェクトをアクティブにして選択
    
    Args:
        context: Blenderコンテキスト
        obj: アクティブにするオブジェクト
    """
    # 現在の選択を解除
    for o in context.selected_objects:
        o.select_set(False)
    
    # オブジェクトを選択してアクティブに
    obj.select_set(True)
    context.view_layer.objects.active = obj


def ensure_edit_mode(context: bpy.types.Context) -> None:
    """
    Edit Modeに切り替え
    
    Args:
        context: Blenderコンテキスト
    """
    if context.object and context.object.mode != 'EDIT':
        _ops_view3d(bpy.ops.object.mode_set, mode='EDIT')


def ensure_object_mode(context: bpy.types.Context) -> None:
    """
    Object Modeに切り替え
    
    Args:
        context: Blenderコンテキスト
    """
    if context.object and context.object.mode != 'OBJECT':
        _ops_view3d(bpy.ops.object.mode_set, mode='OBJECT')
