"""
Модальные диалоги для приложения
"""

from .custom_confirm_dialog import CustomConfirmDialog, show_delete_confirmation
from .move_accounts_dialog import MoveAccountsDialog, show_move_accounts_dialog
from .bot_token_dialog import show_bot_tokens_dialog, BotTokensDialog
from .main_admins_dialog import show_main_admins_dialog, MainAdminsDialog

__all__ = [
    'CustomConfirmDialog',
    'show_delete_confirmation',
    'MoveAccountsDialog',
    'show_move_accounts_dialog',
    "show_main_admins_dialog",
    "show_bot_tokens_dialog",
    "BotTokensDialog",
    "MainAdminsDialog"
]