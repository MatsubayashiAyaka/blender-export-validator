# export_validator/core/issues.py
"""
Issue and ValidationResult data classes for the Export Validator.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class Issue:
    """
    検証で検出された問題を表すデータクラス
    
    Attributes:
        id: 問題ID（例: "W004"）
        severity: 重要度（"ERROR", "WARNING", "INFO"）
        category: カテゴリ名（例: "Flipped Faces"）
        object_name: 対象オブジェクト名
        message: 詳細メッセージ
        hint: 修正ヒント
        can_select: Select Faces が可能か
        select_data: 選択用データ（面インデックス等）
    """
    id: str
    severity: str
    category: str
    object_name: str
    message: str
    hint: str
    can_select: bool = False
    select_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """バリデーション"""
        valid_severities = ("ERROR", "WARNING", "INFO")
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity: {self.severity}. Must be one of {valid_severities}")


@dataclass
class ValidationResult:
    """
    検証結果を保持するデータクラス
    
    Attributes:
        timestamp: 検証実行時刻
        objects: 検証対象オブジェクト名のリスト
        issues: 検出された問題のリスト
    """
    timestamp: float = field(default_factory=time.time)
    objects: List[str] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        """Errorの数を返す"""
        return sum(1 for issue in self.issues if issue.severity == "ERROR")
    
    @property
    def warning_count(self) -> int:
        """Warningの数を返す"""
        return sum(1 for issue in self.issues if issue.severity == "WARNING")
    
    @property
    def info_count(self) -> int:
        """Infoの数を返す"""
        return sum(1 for issue in self.issues if issue.severity == "INFO")
    
    @property
    def total_count(self) -> int:
        """全問題の数を返す"""
        return len(self.issues)
    
    @property
    def has_errors(self) -> bool:
        """Errorがあるかどうか"""
        return self.error_count > 0
    
    def filter_by_severity(self, severity: str) -> List[Issue]:
        """
        指定したSeverityの問題のみを返す
        
        Args:
            severity: フィルタするSeverity（"ERROR", "WARNING", "INFO"）
            
        Returns:
            該当するIssueのリスト
        """
        return [issue for issue in self.issues if issue.severity == severity]
    
    def filter_by_object(self, object_name: str) -> List[Issue]:
        """
        指定したオブジェクトの問題のみを返す
        
        Args:
            object_name: オブジェクト名
            
        Returns:
            該当するIssueのリスト
        """
        return [issue for issue in self.issues if issue.object_name == object_name]
    
    def group_by_category(self) -> Dict[str, List[Issue]]:
        """
        カテゴリごとにグループ化して返す
        
        Returns:
            カテゴリ名をキー、Issueリストを値とする辞書
        """
        grouped: Dict[str, List[Issue]] = {}
        for issue in self.issues:
            if issue.category not in grouped:
                grouped[issue.category] = []
            grouped[issue.category].append(issue)
        return grouped
    
    def group_by_severity(self) -> Dict[str, List[Issue]]:
        """
        Severityごとにグループ化して返す
        
        Returns:
            Severityをキー、Issueリストを値とする辞書
        """
        return {
            "ERROR": self.filter_by_severity("ERROR"),
            "WARNING": self.filter_by_severity("WARNING"),
            "INFO": self.filter_by_severity("INFO"),
        }
    
    def find_issue(self, object_name: str, issue_id: str) -> Optional[Issue]:
        """
        オブジェクト名とIDで特定のIssueを検索
        
        Args:
            object_name: オブジェクト名
            issue_id: Issue ID
            
        Returns:
            見つかったIssue、なければNone
        """
        for issue in self.issues:
            if issue.object_name == object_name and issue.id == issue_id:
                return issue
        return None


# Severity定数
class Severity:
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


# Issue ID定数
class IssueID:
    # Errors
    NO_MATERIALS = "E001"
    MISSING_UV = "E002"
    
    # Warnings
    UNAPPLIED_SCALE = "W001"
    UNAPPLIED_ROTATION = "W002"
    NEGATIVE_SCALE = "W003"
    FLIPPED_FACES = "W004"
    NGONS = "W005"
    LOOSE_GEOMETRY = "W006"
    EMPTY_MATERIAL_SLOTS = "W007"
    
    # Info
    AUTO_SMOOTH_OFF = "I001"
    NAMING_ISSUES = "I002"
    SMALL_FACES = "I003"
