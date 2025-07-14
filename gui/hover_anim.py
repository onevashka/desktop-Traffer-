# TeleCRM/gui/hover_anim.py
from PySide6.QtCore import QObject, Property, QEvent, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PySide6.QtGui import QEnterEvent


class HoverAnimator(QObject):
    def __init__(self, widget: QWidget, start_scale=1.0, end_scale=1.05, duration=150):
        super().__init__(widget)
        self.widget = widget
        self._scale = start_scale
        self._opacity = 1.0
        self.start_scale = start_scale
        self.end_scale = end_scale

        # Группа анимаций
        self.anim_group = QParallelAnimationGroup()

        # Анимация масштабирования
        self.scale_anim = QPropertyAnimation(self, b"scale")
        self.scale_anim.setDuration(duration)
        self.scale_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Анимация прозрачности
        self.opacity_anim = QPropertyAnimation(self, b"opacity")
        self.opacity_anim.setDuration(duration)
        self.opacity_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.anim_group.addAnimation(self.scale_anim)
        self.anim_group.addAnimation(self.opacity_anim)

        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.widget:
            if isinstance(event, QEnterEvent):
                self._animate_enter()
            elif event.type() == QEvent.Leave:
                self._animate_leave()
        return super().eventFilter(obj, event)

    def _animate_enter(self):
        self.anim_group.stop()
        self.scale_anim.setStartValue(self._scale)
        self.scale_anim.setEndValue(self.end_scale)
        self.opacity_anim.setStartValue(self._opacity)
        self.opacity_anim.setEndValue(0.9)
        self.anim_group.start()

    def _animate_leave(self):
        self.anim_group.stop()
        self.scale_anim.setStartValue(self._scale)
        self.scale_anim.setEndValue(self.start_scale)
        self.opacity_anim.setStartValue(self._opacity)
        self.opacity_anim.setEndValue(1.0)
        self.anim_group.start()

    def getScale(self):
        return self._scale

    def setScale(self, value):
        self._scale = value
        self.widget.setStyleSheet(self.widget.styleSheet() + f"""
            transform: scale({value});
        """)

    def getOpacity(self):
        return self._opacity

    def setOpacity(self, value):
        self._opacity = value
        if not self.widget.graphicsEffect():
            effect = QGraphicsOpacityEffect()
            self.widget.setGraphicsEffect(effect)
        self.widget.graphicsEffect().setOpacity(value)

    scale = Property(float, getScale, setScale)
    opacity = Property(float, getOpacity, setOpacity)