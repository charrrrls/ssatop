from PyQt6.QtGui import QColor
from Models.Config import Config

class ThemeManager:
    """主题管理器，用于管理应用程序的主题颜色设置"""
    
    # 单例模式
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化主题管理器"""
        self.config = Config()
        
        # 默认主题
        self.current_theme = "light"
        
        # 预定义主题
        self.themes = {
            "light": {
                "app_background": "#F5F5F5",
                "content_background": "#FFFFFF",
                "sidebar_background": "#2D3142",
                "sidebar_active": "#4A5072",
                "sidebar_hover": "#3D4256",
                "sidebar_text": "#F0F0F0",
                "primary_button": "#1E88E5",
                "primary_button_hover": "#1976D2",
                "secondary_button": "#9E9E9E",
                "secondary_button_hover": "#757575",
                "accent_button": "#FF9800",
                "accent_button_hover": "#F57C00",
                "success_button": "#4CAF50",
                "success_button_hover": "#388E3C",
                "text_primary": "#333333",
                "text_secondary": "#757575",
                "border": "#DDDDDD",
                "chart_background": "#FFFFFF",
                "chart_grid": "#EEEEEE",
                "chart_line": "#1E88E5",
                "chart_accent": "#FF9800",
                "chart_highlight": "#F44336",
            },
            "dark": {
                "app_background": "#121212",
                "content_background": "#1E1E1E",
                "sidebar_background": "#1A1A1A",
                "sidebar_active": "#333333",
                "sidebar_hover": "#2A2A2A",
                "sidebar_text": "#E0E0E0",
                "primary_button": "#2196F3",
                "primary_button_hover": "#1976D2",
                "secondary_button": "#616161",
                "secondary_button_hover": "#757575",
                "accent_button": "#FF9800",
                "accent_button_hover": "#F57C00",
                "success_button": "#4CAF50",
                "success_button_hover": "#388E3C",
                "text_primary": "#E0E0E0",
                "text_secondary": "#AAAAAA",
                "border": "#333333",
                "chart_background": "#1E1E1E",
                "chart_grid": "#333333",
                "chart_line": "#2196F3",
                "chart_accent": "#FF9800",
                "chart_highlight": "#F44336",
            },
            "high_contrast": {
                "app_background": "#000000",
                "content_background": "#121212",
                "sidebar_background": "#000000",
                "sidebar_active": "#1E88E5",
                "sidebar_hover": "#0D47A1",
                "sidebar_text": "#FFFFFF",
                "primary_button": "#1E88E5",
                "primary_button_hover": "#0D47A1",
                "secondary_button": "#757575",
                "secondary_button_hover": "#424242",
                "accent_button": "#FF9800",
                "accent_button_hover": "#E65100",
                "success_button": "#4CAF50",
                "success_button_hover": "#2E7D32",
                "text_primary": "#FFFFFF",
                "text_secondary": "#CCCCCC",
                "border": "#FFFFFF",
                "chart_background": "#000000",
                "chart_grid": "#424242",
                "chart_line": "#2196F3",
                "chart_accent": "#FF9800",
                "chart_highlight": "#F44336",
            },
            "blue_accent": {
                "app_background": "#E3F2FD",
                "content_background": "#FFFFFF",
                "sidebar_background": "#0D47A1",
                "sidebar_active": "#1976D2",
                "sidebar_hover": "#1565C0",
                "sidebar_text": "#FFFFFF",
                "primary_button": "#1E88E5",
                "primary_button_hover": "#1976D2",
                "secondary_button": "#90CAF9",
                "secondary_button_hover": "#64B5F6",
                "accent_button": "#FF9800",
                "accent_button_hover": "#F57C00",
                "success_button": "#4CAF50",
                "success_button_hover": "#388E3C",
                "text_primary": "#0D47A1",
                "text_secondary": "#1976D2",
                "border": "#BBDEFB",
                "chart_background": "#FFFFFF",
                "chart_grid": "#E3F2FD",
                "chart_line": "#1E88E5",
                "chart_accent": "#FF9800",
                "chart_highlight": "#F44336",
            },
            "dark_green": {
                "app_background": "#E8F5E9",
                "content_background": "#FFFFFF",
                "sidebar_background": "#1B5E20",
                "sidebar_active": "#2E7D32",
                "sidebar_hover": "#388E3C",
                "sidebar_text": "#FFFFFF",
                "primary_button": "#43A047",
                "primary_button_hover": "#388E3C",
                "secondary_button": "#A5D6A7",
                "secondary_button_hover": "#81C784",
                "accent_button": "#FF9800",
                "accent_button_hover": "#F57C00",
                "success_button": "#4CAF50",
                "success_button_hover": "#388E3C",
                "text_primary": "#1B5E20",
                "text_secondary": "#388E3C",
                "border": "#C8E6C9",
                "chart_background": "#FFFFFF",
                "chart_grid": "#E8F5E9",
                "chart_line": "#43A047",
                "chart_accent": "#FF9800",
                "chart_highlight": "#F44336",
            }
        }
        
        # 从配置中加载当前主题
        saved_theme = self.config.get("Theme", "current_theme")
        if saved_theme and saved_theme in self.themes:
            self.current_theme = saved_theme
            
        # 从配置中加载自定义主题
        custom_theme = self.config.get("Theme", "custom_theme")
        if custom_theme:
            try:
                import json
                custom_colors = json.loads(custom_theme)
                if isinstance(custom_colors, dict):
                    self.themes["custom"] = custom_colors
            except:
                pass
    
    def get_theme_names(self):
        """获取所有可用主题名称"""
        return list(self.themes.keys())
    
    def get_current_theme(self):
        """获取当前主题名称"""
        return self.current_theme
    
    def set_theme(self, theme_name):
        """设置当前主题"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            self.config.set("Theme", "current_theme", theme_name)
            return True
        return False
    
    def get_color(self, color_key):
        """获取指定颜色键的颜色值"""
        theme = self.themes.get(self.current_theme, self.themes["light"])
        return theme.get(color_key, "#000000")
    
    def get_stylesheet(self):
        """获取当前主题的样式表"""
        theme = self.themes.get(self.current_theme, self.themes["light"])
        
        return f"""
            QWidget {{
                font-family: Arial;
                background-color: {theme["app_background"]};
                color: {theme["text_primary"]};
            }}
            QMainWindow {{
                background-color: {theme["app_background"]};
            }}
            QGroupBox {{
                border: 1px solid {theme["border"]};
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                background-color: {theme["content_background"]};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {theme["text_primary"]};
            }}
            QPushButton {{
                background-color: {theme["primary_button"]};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme["primary_button_hover"]};
            }}
            QPushButton:pressed {{
                background-color: {theme["primary_button_hover"]};
            }}
            QPushButton[class="secondary"] {{
                background-color: {theme["secondary_button"]};
            }}
            QPushButton[class="secondary"]:hover {{
                background-color: {theme["secondary_button_hover"]};
            }}
            QPushButton[class="accent"] {{
                background-color: {theme["accent_button"]};
            }}
            QPushButton[class="accent"]:hover {{
                background-color: {theme["accent_button_hover"]};
            }}
            QPushButton[class="success"] {{
                background-color: {theme["success_button"]};
            }}
            QPushButton[class="success"]:hover {{
                background-color: {theme["success_button_hover"]};
            }}
            QLineEdit, QTextEdit, QPlainTextEdit {{
                border: 1px solid {theme["border"]};
                border-radius: 4px;
                padding: 8px;
                background-color: {theme["content_background"]};
                color: {theme["text_primary"]};
                selection-background-color: {theme["primary_button"]};
                selection-color: white;
            }}
            QLabel {{
                color: {theme["text_primary"]};
            }}
            QComboBox {{
                border: 1px solid {theme["border"]};
                border-radius: 4px;
                padding: 5px;
                background-color: {theme["content_background"]};
                color: {theme["text_primary"]};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: {theme["border"]};
                border-left-style: solid;
            }}
            QTabWidget::pane {{
                border: 1px solid {theme["border"]};
                border-radius: 4px;
                background-color: {theme["content_background"]};
            }}
            QTabBar::tab {{
                background-color: {theme["app_background"]};
                border: 1px solid {theme["border"]};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 12px;
                margin-right: 2px;
                color: {theme["text_primary"]};
            }}
            QTabBar::tab:selected {{
                background-color: {theme["content_background"]};
                border-bottom: 1px solid {theme["content_background"]};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {theme["app_background"]};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme["secondary_button"]};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme["secondary_button_hover"]};
            }}
            QScrollBar:horizontal {{
                border: none;
                background: {theme["app_background"]};
                height: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {theme["secondary_button"]};
                min-width: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {theme["secondary_button_hover"]};
            }}
            QMenuBar {{
                background-color: {theme["sidebar_background"]};
                color: {theme["sidebar_text"]};
            }}
            QMenuBar::item {{
                background-color: transparent;
            }}
            QMenuBar::item:selected {{
                background-color: {theme["sidebar_active"]};
            }}
            QMenu {{
                background-color: {theme["content_background"]};
                border: 1px solid {theme["border"]};
            }}
            QMenu::item {{
                padding: 5px 30px 5px 30px;
                color: {theme["text_primary"]};
            }}
            QMenu::item:selected {{
                background-color: {theme["primary_button"]};
                color: white;
            }}
            QProgressBar {{
                border: 1px solid {theme["border"]};
                border-radius: 4px;
                text-align: center;
                background-color: {theme["content_background"]};
                color: {theme["text_primary"]};
            }}
            QProgressBar::chunk {{
                background-color: {theme["success_button"]};
            }}
            QCheckBox {{
                color: {theme["text_primary"]};
            }}
            QRadioButton {{
                color: {theme["text_primary"]};
            }}
            QSpinBox, QDoubleSpinBox {{
                border: 1px solid {theme["border"]};
                border-radius: 4px;
                padding: 5px;
                background-color: {theme["content_background"]};
                color: {theme["text_primary"]};
            }}
            QWidget#titleBar {{
                background-color: {theme["content_background"]};
                border-bottom: 1px solid {theme["border"]};
            }}
            QLabel#pageTitle {{
                color: {theme["text_primary"]};
                font-weight: bold;
            }}
            QPushButton#refreshButton {{
                background-color: {theme["secondary_button"]};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton#refreshButton:hover {{
                background-color: {theme["secondary_button_hover"]};
            }}
            QWidget#mainContainer {{
                background-color: {theme["app_background"]};
            }}
            QStackedWidget#contentStack {{
                background-color: {theme["app_background"]};
            }}
        """
    
    def get_sidebar_stylesheet(self):
        """获取侧边栏的样式表"""
        theme = self.themes.get(self.current_theme, self.themes["light"])
        
        return f"""
            QWidget {{
                background-color: {theme["sidebar_background"]};
            }}
            QLabel {{
                color: {theme["sidebar_text"]};
            }}
            QPushButton {{
                color: {theme["sidebar_text"]};
                background-color: {theme["sidebar_background"]};
                border: none;
                text-align: left;
                padding: 10px 15px 10px 35px;
                font-size: 14px;
                font-weight: 500;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                background-color: {theme["sidebar_hover"]};
            }}
            QPushButton:checked {{
                background-color: {theme["sidebar_active"]};
                border-left: 4px solid {theme["primary_button"]};
                color: white;
            }}
            QWidget#header {{
                background-color: {theme["sidebar_background"]};
                border-bottom: 1px solid {theme["border"]};
            }}
            QWidget#footer {{
                background-color: {theme["sidebar_background"]};
                border-top: 1px solid {theme["border"]};
            }}
            QLabel#sidebarLabel {{
                color: {theme["sidebar_text"]};
                padding: 10px;
                font-size: 12px;
                opacity: 0.7;
            }}
            QLabel#versionLabel {{
                color: {theme["sidebar_text"]};
                font-size: 12px;
                opacity: 0.7;
            }}
        """
    
    def save_custom_theme(self, colors):
        """保存自定义主题"""
        if isinstance(colors, dict):
            self.themes["custom"] = colors
            import json
            self.config.set("Theme", "custom_theme", json.dumps(colors))
            return True
        return False 