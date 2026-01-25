# export_validator/core/engine.py
"""
Validation engine that orchestrates all checkers.
"""

from typing import List, Optional
import time
import bpy

from .issues import ValidationResult, Issue
from .checkers import get_all_checkers, BaseChecker


class ValidationEngine:
    """
    検証処理を統括するエンジン
    
    使用例:
        engine = ValidationEngine()
        result = engine.validate(context.selected_objects)
        print(f"Found {result.error_count} errors")
    """
    
    def __init__(self):
        self._checkers: List[BaseChecker] = get_all_checkers()
    
    def validate(self, objects: List[bpy.types.Object]) -> ValidationResult:
        """
        指定オブジェクトを検証
        
        Args:
            objects: 検証対象のBlenderオブジェクトリスト
            
        Returns:
            ValidationResult: 検証結果
        """
        issues: List[Issue] = []
        mesh_objects = [obj for obj in objects if obj.type == 'MESH']
        
        for obj in mesh_objects:
            for checker in self._checkers:
                try:
                    checker_issues = checker.check(obj)
                    issues.extend(checker_issues)
                except Exception as e:
                    print(f"[Validator] Error in {checker.__class__.__name__} for {obj.name}: {e}")
        
        return ValidationResult(
            timestamp=time.time(),
            objects=[obj.name for obj in mesh_objects],
            issues=issues
        )
    
    def validate_single(self, obj: bpy.types.Object) -> ValidationResult:
        """
        単一オブジェクトを検証
        
        Args:
            obj: 検証対象のBlenderオブジェクト
            
        Returns:
            ValidationResult: 検証結果
        """
        return self.validate([obj])


# グローバル状態管理
_current_result: Optional[ValidationResult] = None
_last_selection_hash: Optional[int] = None


def get_validation_result() -> ValidationResult:
    """
    現在の検証結果を取得
    
    Returns:
        ValidationResult: 現在の検証結果（なければ空の結果）
    """
    global _current_result
    if _current_result is None:
        _current_result = ValidationResult()
    return _current_result


def store_validation_result(result: ValidationResult) -> None:
    """
    検証結果を保存
    
    Args:
        result: 保存する検証結果
    """
    global _current_result
    _current_result = result


def clear_validation_result() -> None:
    """検証結果をクリア"""
    global _current_result
    _current_result = None


def get_selection_hash(objects: List[bpy.types.Object]) -> int:
    """
    選択オブジェクトのハッシュを計算
    
    Args:
        objects: オブジェクトリスト
        
    Returns:
        ハッシュ値
    """
    return hash(frozenset(obj.name for obj in objects if obj.type == 'MESH'))


def should_revalidate(objects: List[bpy.types.Object]) -> bool:
    """
    再検証が必要かどうかを判定
    
    Args:
        objects: 現在の選択オブジェクト
        
    Returns:
        再検証が必要ならTrue
    """
    global _last_selection_hash
    current_hash = get_selection_hash(objects)
    
    if _last_selection_hash != current_hash:
        _last_selection_hash = current_hash
        return True
    return False


def run_validation(context: bpy.types.Context) -> ValidationResult:
    """
    コンテキストから選択オブジェクトを取得して検証を実行
    
    Args:
        context: Blenderコンテキスト
        
    Returns:
        ValidationResult: 検証結果
    """
    engine = ValidationEngine()
    objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
    result = engine.validate(objects)
    store_validation_result(result)
    return result
