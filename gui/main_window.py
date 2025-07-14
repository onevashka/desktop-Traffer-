# TeleCRM/gui/main_window.py
from PySide6.QtWidgets import QMainWindow, QTabWidget
from gui.account_manager import AccountManagerTab
from log_config import logger

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TeleCRM")
        self.resize(1400, 900)
        self.setMinimumSize(1200, 800)

        # Табы
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Склад аккаунтов
        self.account_tab = AccountManagerTab()
        self.tabs.addTab(self.account_tab, "Склад аккаунтов")


        logger.debug("MainWindow initialized")

