# TeleCRM/gui/components/__init__.py
"""
Компоненты GUI для TeleCRM
"""

from .account_stats import AccountStatsWidget
from .account_table import AccountTableWidget
from .loading_animation import LoadingAnimationWidget
from .traffic_accounts import TrafficAccountsTab
from .sales_accounts import SalesAccountsTab

__all__ = [
    'AccountStatsWidget',
    'AccountTableWidget',
    'LoadingAnimationWidget',
    'TrafficAccountsTab',
    'SalesAccountsTab'
]