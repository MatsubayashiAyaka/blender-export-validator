# export_validator/core/__init__.py
"""
Core validation module.
"""

from .issues import (
    Issue,
    ValidationResult,
    Severity,
    IssueID,
)

from .checkers import (
    BaseChecker,
    MaterialChecker,
    UVChecker,
    TransformChecker,
    FaceOrientationChecker,
    GeometryChecker,
    AutoSmoothChecker,
    NamingChecker,
    get_all_checkers,
)

from .engine import (
    ValidationEngine,
    get_validation_result,
    store_validation_result,
    clear_validation_result,
    run_validation,
    should_revalidate,
)

__all__ = [
    # Issues
    'Issue',
    'ValidationResult',
    'Severity',
    'IssueID',
    # Checkers
    'BaseChecker',
    'MaterialChecker',
    'UVChecker',
    'TransformChecker',
    'FaceOrientationChecker',
    'GeometryChecker',
    'AutoSmoothChecker',
    'NamingChecker',
    'get_all_checkers',
    # Engine
    'ValidationEngine',
    'get_validation_result',
    'store_validation_result',
    'clear_validation_result',
    'run_validation',
    'should_revalidate',
]
