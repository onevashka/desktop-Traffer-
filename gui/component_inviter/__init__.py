# gui/component_inviter/__init__.py
"""
Компоненты GUI для инвайтера
"""

from .inviter_stats import InviterStatsWidget
from .inviter_table import InviterTableWidget, InviterProfileRow

__all__ = [
    'InviterStatsWidget',
    'InviterTableWidget',
    'InviterProfileRow'
]