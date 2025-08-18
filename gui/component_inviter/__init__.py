# gui/component_inviter/__init__.py
"""
Компоненты GUI для инвайтера
"""

from .inviter_stats import InviterStatsWidget
from .inviter_table_old import InviterTableWidget, InviterProfileRow

__all__ = [
    'InviterStatsWidget',
    'InviterTableWidget',
    'InviterProfileRow'
]