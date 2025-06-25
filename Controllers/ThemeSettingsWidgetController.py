from PyQt6.QtCore import QObject, pyqtSignal
from Models.ThemeManager import ThemeManager
from Views.ThemeSettingsWidget import ThemeSettingsWidget

class ThemeSettingsWidgetController(QObject):
    """主题设置界面控制器"""
    themeChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self.view = ThemeSettingsWidget()
        
        # 连接信号
        self.view.themeChanged.connect(self.on_theme_changed)
    
    def get_view(self):
        """获取视图"""
        return self.view
    
    def on_theme_changed(self):
        """当主题改变时发出信号"""
        self.themeChanged.emit()
    
    def apply_theme_to_app(self, app):
        """应用当前主题到整个应用程序"""
        stylesheet = self.theme_manager.get_stylesheet()
        app.setStyleSheet(stylesheet) 