from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QComboBox, QColorDialog, QGroupBox,
                           QScrollArea, QFormLayout, QMessageBox, QGridLayout)
from PyQt6.QtGui import QColor, QPixmap, QPainter
from PyQt6.QtCore import Qt, pyqtSignal
from Models.ThemeManager import ThemeManager

class ColorPreview(QWidget):
    """颜色预览控件"""
    colorChanged = pyqtSignal(str, str)
    
    def __init__(self, color_key, color_value, parent=None):
        super().__init__(parent)
        self.color_key = color_key
        self.color_value = color_value
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(self.color_value))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 5, 5)
        
    def mousePressEvent(self, event):
        color = QColorDialog.getColor(QColor(self.color_value), self, "选择颜色")
        if color.isValid():
            self.color_value = color.name()
            self.update()
            self.colorChanged.emit(self.color_key, self.color_value)

class ThemeSettingsWidget(QWidget):
    """主题设置界面"""
    themeChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self.custom_colors = {}
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 主题选择区域
        theme_group = QGroupBox("主题选择")
        theme_layout = QVBoxLayout(theme_group)
        
        theme_selector_layout = QHBoxLayout()
        theme_selector_layout.addWidget(QLabel("选择主题:"))
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.theme_manager.get_theme_names())
        self.theme_combo.setCurrentText(self.theme_manager.get_current_theme())
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_selector_layout.addWidget(self.theme_combo)
        
        self.apply_btn = QPushButton("应用主题")
        self.apply_btn.clicked.connect(self.apply_theme)
        theme_selector_layout.addWidget(self.apply_btn)
        
        theme_layout.addLayout(theme_selector_layout)
        
        # 主题预览
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("预览:"))
        
        self.preview_widget = QWidget()
        self.preview_widget.setFixedHeight(100)
        preview_layout.addWidget(self.preview_widget)
        
        theme_layout.addLayout(preview_layout)
        layout.addWidget(theme_group)
        
        # 自定义主题区域
        custom_group = QGroupBox("自定义主题")
        custom_layout = QVBoxLayout(custom_group)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.color_layout = QFormLayout(scroll_content)
        
        # 添加颜色选择控件
        self.color_widgets = {}
        self.load_theme_colors()
        
        scroll.setWidget(scroll_content)
        custom_layout.addWidget(scroll)
        
        # 保存自定义主题按钮
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.save_btn = QPushButton("保存为自定义主题")
        self.save_btn.clicked.connect(self.save_custom_theme)
        save_layout.addWidget(self.save_btn)
        
        custom_layout.addLayout(save_layout)
        layout.addWidget(custom_group)
        
        # 更新预览
        self.update_preview()
        
    def load_theme_colors(self):
        """加载当前主题的颜色"""
        # 清除现有控件
        while self.color_layout.rowCount() > 0:
            self.color_layout.removeRow(0)
        
        self.color_widgets = {}
        
        # 获取当前主题的颜色
        theme_name = self.theme_combo.currentText()
        if theme_name in self.theme_manager.themes:
            colors = self.theme_manager.themes[theme_name]
            
            # 按类别组织颜色
            color_categories = {
                "背景颜色": ["app_background", "content_background", "sidebar_background", 
                         "sidebar_active", "sidebar_hover"],
                "文本颜色": ["text_primary", "text_secondary", "sidebar_text"],
                "按钮颜色": ["primary_button", "primary_button_hover", "secondary_button", 
                         "secondary_button_hover", "accent_button", "accent_button_hover",
                         "success_button", "success_button_hover"],
                "图表颜色": ["chart_background", "chart_grid", "chart_line", "chart_accent", 
                         "chart_highlight"],
                "其他": ["border"]
            }
            
            # 创建颜色名称映射
            color_names = {
                "app_background": "应用背景",
                "content_background": "内容背景",
                "sidebar_background": "侧边栏背景",
                "sidebar_active": "侧边栏激活",
                "sidebar_hover": "侧边栏悬停",
                "sidebar_text": "侧边栏文本",
                "primary_button": "主要按钮",
                "primary_button_hover": "主要按钮悬停",
                "secondary_button": "次要按钮",
                "secondary_button_hover": "次要按钮悬停",
                "accent_button": "强调按钮",
                "accent_button_hover": "强调按钮悬停",
                "success_button": "成功按钮",
                "success_button_hover": "成功按钮悬停",
                "text_primary": "主要文本",
                "text_secondary": "次要文本",
                "border": "边框",
                "chart_background": "图表背景",
                "chart_grid": "图表网格",
                "chart_line": "图表线条",
                "chart_accent": "图表强调",
                "chart_highlight": "图表高亮"
            }
            
            # 复制当前主题的颜色到自定义颜色
            self.custom_colors = colors.copy()
            
            # 按类别添加颜色选择控件
            for category, color_keys in color_categories.items():
                # 添加类别标签
                category_label = QLabel(f"<b>{category}</b>")
                self.color_layout.addRow(category_label)
                
                # 为每个颜色创建一个选择控件
                for color_key in color_keys:
                    if color_key in colors:
                        color_value = colors[color_key]
                        color_name = color_names.get(color_key, color_key)
                        
                        # 创建水平布局
                        color_widget = QWidget()
                        color_hbox = QHBoxLayout(color_widget)
                        color_hbox.setContentsMargins(0, 0, 0, 0)
                        
                        # 添加颜色预览控件
                        preview = ColorPreview(color_key, color_value)
                        preview.colorChanged.connect(self.on_color_changed)
                        color_hbox.addWidget(preview)
                        
                        # 添加颜色代码标签
                        color_code = QLabel(color_value)
                        color_hbox.addWidget(color_code)
                        
                        # 保存引用
                        self.color_widgets[color_key] = {
                            "preview": preview,
                            "code": color_code
                        }
                        
                        self.color_layout.addRow(color_name, color_widget)
    
    def on_color_changed(self, color_key, color_value):
        """当颜色改变时更新预览"""
        self.custom_colors[color_key] = color_value
        self.color_widgets[color_key]["code"].setText(color_value)
        self.update_preview()
    
    def on_theme_changed(self, theme_name):
        """当主题选择改变时更新颜色选择器"""
        self.load_theme_colors()
        self.update_preview()
    
    def update_preview(self):
        """更新主题预览"""
        # 创建一个简单的预览
        preview_layout = QVBoxLayout()
        if self.preview_widget.layout():
            # 清除旧的布局
            QWidget().setLayout(self.preview_widget.layout())
        
        self.preview_widget.setLayout(preview_layout)
        
        # 设置预览窗口的背景色
        self.preview_widget.setStyleSheet(f"""
            background-color: {self.custom_colors.get('app_background', '#FFFFFF')};
            border-radius: 5px;
            border: 1px solid {self.custom_colors.get('border', '#DDDDDD')};
        """)
        
        # 创建预览元素
        header = QWidget()
        header.setFixedHeight(30)
        header.setStyleSheet(f"""
            background-color: {self.custom_colors.get('sidebar_background', '#2D3142')};
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        """)
        preview_layout.addWidget(header)
        
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 侧边栏预览
        sidebar = QWidget()
        sidebar.setFixedWidth(80)
        sidebar.setStyleSheet(f"""
            background-color: {self.custom_colors.get('sidebar_background', '#2D3142')};
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        
        # 添加一些侧边栏按钮预览
        for i in range(3):
            btn = QPushButton(f"按钮 {i+1}")
            if i == 1:
                btn.setStyleSheet(f"""
                    background-color: {self.custom_colors.get('sidebar_active', '#4A5072')};
                    color: {self.custom_colors.get('sidebar_text', '#F0F0F0')};
                    border-left: 4px solid {self.custom_colors.get('primary_button', '#1E88E5')};
                    text-align: center;
                    border-radius: 0;
                """)
            else:
                btn.setStyleSheet(f"""
                    background-color: {self.custom_colors.get('sidebar_background', '#2D3142')};
                    color: {self.custom_colors.get('sidebar_text', '#F0F0F0')};
                    text-align: center;
                    border-radius: 0;
                """)
            sidebar_layout.addWidget(btn)
        
        content_layout.addWidget(sidebar)
        
        # 主内容区预览
        main_content = QWidget()
        main_content.setStyleSheet(f"""
            background-color: {self.custom_colors.get('content_background', '#FFFFFF')};
        """)
        main_layout = QVBoxLayout(main_content)
        
        # 添加标题
        title = QLabel("主题预览")
        title.setStyleSheet(f"""
            color: {self.custom_colors.get('text_primary', '#333333')};
            font-weight: bold;
            font-size: 14px;
        """)
        main_layout.addWidget(title)
        
        # 添加文本
        text = QLabel("这是一段示例文本，用于预览主题效果。")
        text.setStyleSheet(f"""
            color: {self.custom_colors.get('text_secondary', '#757575')};
        """)
        main_layout.addWidget(text)
        
        # 添加按钮
        buttons_layout = QHBoxLayout()
        
        primary_btn = QPushButton("主要")
        primary_btn.setStyleSheet(f"""
            background-color: {self.custom_colors.get('primary_button', '#1E88E5')};
            color: white;
            border-radius: 4px;
            padding: 5px;
        """)
        buttons_layout.addWidget(primary_btn)
        
        secondary_btn = QPushButton("次要")
        secondary_btn.setStyleSheet(f"""
            background-color: {self.custom_colors.get('secondary_button', '#9E9E9E')};
            color: white;
            border-radius: 4px;
            padding: 5px;
        """)
        buttons_layout.addWidget(secondary_btn)
        
        accent_btn = QPushButton("强调")
        accent_btn.setStyleSheet(f"""
            background-color: {self.custom_colors.get('accent_button', '#FF9800')};
            color: white;
            border-radius: 4px;
            padding: 5px;
        """)
        buttons_layout.addWidget(accent_btn)
        
        main_layout.addLayout(buttons_layout)
        content_layout.addWidget(main_content)
        
        preview_layout.addWidget(content)
    
    def apply_theme(self):
        """应用选中的主题"""
        theme_name = self.theme_combo.currentText()
        if self.theme_manager.set_theme(theme_name):
            self.themeChanged.emit()
    
    def save_custom_theme(self):
        """保存自定义主题"""
        if self.theme_manager.save_custom_theme(self.custom_colors):
            # 如果自定义主题不在下拉列表中，添加它
            if "custom" not in [self.theme_combo.itemText(i) for i in range(self.theme_combo.count())]:
                self.theme_combo.addItem("custom")
            
            # 选择自定义主题
            self.theme_combo.setCurrentText("custom")
            
            # 应用主题
            self.theme_manager.set_theme("custom")
            self.themeChanged.emit()
            
            QMessageBox.information(self, "保存成功", "自定义主题已保存并应用。")
        else:
            QMessageBox.warning(self, "保存失败", "保存自定义主题时出错。") 