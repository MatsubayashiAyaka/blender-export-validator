# export_validator/__init__.py
"""
Export Validator - Blender Addon

A validation tool for checking mesh objects before exporting (FBX).
Detects common issues that can cause problems in game engines.

Author: Matsubayashi Ayaka
Version: 1.0.0
Blender: 3.6+
"""

bl_info = {
    "name": "Export Validator",
    "author": "Matsubayashi Ayaka",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Tool > Export Validator",
    "description": "Validate mesh objects before exporting (FBX)",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

import bpy


# -----------------------------------------------------------------------------
# Blender 4.2 compatibility: suppress Node Wrangler poll traceback
# -----------------------------------------------------------------------------
#
# When Shader Editor is open and Node Wrangler is enabled, Blender 4.2 can emit
# a repeating traceback from node_wrangler's poll() due to a format-string bug.
# This add-on must NOT spam the Info Log. We patch Node Wrangler *in-memory*
# (only for Blender 4.2.x) to safely catch the ValueError and return False.
#
# This does NOT change user files; it only wraps functions during this add-on's
# lifetime and restores originals on unregister.

_NW_PATCH_STATE = {
    "patched": False,
    "ops_orig": None,
    "utils_orig": None,
}


def _is_blender_42x():
    v = bpy.app.version
    return (v[0] == 4 and v[1] == 2)


def _patch_node_wrangler():
    if _NW_PATCH_STATE["patched"]:
        return
    if not _is_blender_42x():
        return

    # Only patch when Node Wrangler is enabled/loaded.
    try:
        import node_wrangler.operators as nw_ops
        import node_wrangler.utils.nodes as nw_nodes
    except Exception:
        return

    # Patch node_wrangler.operators.nw_check_selected (used directly in poll).
    if hasattr(nw_ops, "nw_check_selected"):
        orig = nw_ops.nw_check_selected

        def safe_nw_check_selected(*args, **kwargs):
            try:
                return orig(*args, **kwargs)
            except ValueError as e:
                # Blender 4.2 bug: "Unknown format code 's' for object of type 'int'"
                if "Unknown format code" in str(e):
                    return False
                raise

        _NW_PATCH_STATE["ops_orig"] = orig
        nw_ops.nw_check_selected = safe_nw_check_selected

    # Patch utils too (defensive; some versions reference it).
    if hasattr(nw_nodes, "nw_check_selected"):
        orig_u = nw_nodes.nw_check_selected

        def safe_nw_check_selected_u(*args, **kwargs):
            try:
                return orig_u(*args, **kwargs)
            except ValueError as e:
                if "Unknown format code" in str(e):
                    return False
                raise

        _NW_PATCH_STATE["utils_orig"] = orig_u
        nw_nodes.nw_check_selected = safe_nw_check_selected_u

    _NW_PATCH_STATE["patched"] = True


def _unpatch_node_wrangler():
    if not _NW_PATCH_STATE["patched"]:
        return
    try:
        import node_wrangler.operators as nw_ops
        import node_wrangler.utils.nodes as nw_nodes
    except Exception:
        _NW_PATCH_STATE["patched"] = False
        return

    if _NW_PATCH_STATE["ops_orig"] is not None and hasattr(nw_ops, "nw_check_selected"):
        nw_ops.nw_check_selected = _NW_PATCH_STATE["ops_orig"]

    if _NW_PATCH_STATE["utils_orig"] is not None and hasattr(nw_nodes, "nw_check_selected"):
        nw_nodes.nw_check_selected = _NW_PATCH_STATE["utils_orig"]

    _NW_PATCH_STATE["patched"] = False
    _NW_PATCH_STATE["ops_orig"] = None
    _NW_PATCH_STATE["utils_orig"] = None


# サブモジュールのインポート
from . import operators
from . import panels
from .core.engine import clear_validation_result


def register():
    """アドオン登録"""
    _patch_node_wrangler()
    # オペレーター登録
    operators.register()
    
    # パネル登録
    panels.register()
    
    # NOTE:
    # v1.0.0仕様: バックグラウンドの常時監視は行わない。
    # 自動再スキャン（depsgraph handler）を入れるとUIリドローが頻発し、
    # 他アドオンのpoll評価を巻き込んで予期せぬTracebackが増え続ける原因になる。
    # 検証はユーザー操作（Rescan / Export Gate）でのみ実行する。
    
    print(f"[Export Validator] Registered v{'.'.join(map(str, bl_info['version']))}")


def unregister():
    """アドオン登録解除"""
    _unpatch_node_wrangler()
    # ハンドラは登録しないため削除処理も不要
    
    # パネル登録解除
    panels.unregister()
    
    # オペレーター登録解除
    operators.unregister()
    
    # 検証結果クリア
    clear_validation_result()
    
    print("[Export Validator] Unregistered")


if __name__ == "__main__":
    register()
