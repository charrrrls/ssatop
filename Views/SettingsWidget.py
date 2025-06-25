from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel,
    QGroupBox, QHBoxLayout, QGridLayout, QTabWidget, QComboBox,
    QCheckBox, QSpacerItem, QSizePolicy, QFileDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QColor
from Models.Config import Config

class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统设置")

        # 初始化组件
        self.init_components()
        
        # 设置UI样式
        self.init_ui()
        
        # 设置布局
        self.init_layout()

    def init_components(self):
        # 文件路径设置
        self.config_sgy_path = QLineEdit()
        self.config_xlsx_path = QLineEdit()
        self.browse_sgy_button = QPushButton("浏览...")
        self.browse_xlsx_button = QPushButton("浏览...")
        
        # 计算参数设置
        self.config_speed = QLineEdit()
        self.config_length = QLineEdit()
        self.config_height = QLineEdit()
        self.config_time_slice = QLineEdit()
        self.config_z_min = QLineEdit()
        self.config_z_max = QLineEdit()
        
        # 高级选项
        self.use_gpu_checkbox = QCheckBox("使用GPU加速计算")
        self.auto_load_checkbox = QCheckBox("启动时自动加载上次文件")
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["浅色主题", "深色主题", "系统默认"])
        
        # 操作按钮
        self.save_button = QPushButton("保存配置")
        self.reset_button = QPushButton("重置默认值")
        self.model_setting_button = QPushButton("速度模型设置")
        
        # 标签页
        self.settings_tabs = QTabWidget()
    
    def init_ui(self):
        # 设置整体样式
        self.setStyleSheet("""
            QWidget {
                font-family: 'Microsoft YaHei', 'Arial';
                background-color: #F5F5F5;
            }
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #1E88E5;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
            }
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 5px 10px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
        """)
        
        # 设置特殊按钮样式
        self.model_setting_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 15px;
                font-size: 14px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        
        # 设置控件大小
        self.browse_sgy_button.setFixedWidth(80)
        self.browse_xlsx_button.setFixedWidth(80)
        
        # 设置输入框提示
        self.config_sgy_path.setPlaceholderText("请选择SGY文件路径")
        self.config_xlsx_path.setPlaceholderText("请选择XLSX文件路径")
        self.config_speed.setPlaceholderText("例如：3000")
        self.config_length.setPlaceholderText("例如：1000")
        self.config_height.setPlaceholderText("例如：500")

    def init_layout(self):
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        
        # 创建标签页
        self.settings_tabs.addTab(self.create_file_tab(), "文件设置")
        self.settings_tabs.addTab(self.create_calculation_tab(), "计算参数")
        self.settings_tabs.addTab(self.create_advanced_tab(), "高级选项")
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.model_setting_button)
        
        # 添加主要组件到布局中
        main_layout.addWidget(self.settings_tabs, 1)  # 使标签页可以伸展
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)

    def create_file_tab(self):
        """创建文件设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 文件路径组
        file_group = QGroupBox("默认文件路径")
        file_layout = QGridLayout()
        
        # SGY文件路径
        file_layout.addWidget(QLabel("SGY 文件路径:"), 0, 0)
        file_layout.addWidget(self.config_sgy_path, 0, 1)
        file_layout.addWidget(self.browse_sgy_button, 0, 2)
        
        # XLSX文件路径
        file_layout.addWidget(QLabel("检波器位置文件路径:"), 1, 0)
        file_layout.addWidget(self.config_xlsx_path, 1, 1)
        file_layout.addWidget(self.browse_xlsx_button, 1, 2)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 文件加载策略
        load_group = QGroupBox("文件加载策略")
        load_layout = QVBoxLayout()
        
        load_layout.addWidget(self.auto_load_checkbox)
        load_layout.addWidget(QLabel("首选文件格式："))
        
        format_combo = QComboBox()
        format_combo.addItems(["SGY", "SEGY", "SEG-Y", "自动检测"])
        load_layout.addWidget(format_combo)
        
        load_group.setLayout(load_layout)
        layout.addWidget(load_group)
        
        layout.addStretch(1)
        tab.setLayout(layout)
        return tab
        
    def create_calculation_tab(self):
        """创建计算参数标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 基本参数组
        basic_group = QGroupBox("基本参数")
        basic_layout = QFormLayout()
        
        basic_layout.addRow(QLabel("速度 (m/s):"), self.config_speed)
        basic_layout.addRow(QLabel("长度 (m):"), self.config_length)
        basic_layout.addRow(QLabel("高度 (m):"), self.config_height)
        basic_layout.addRow(QLabel("时间切片 (s):"), self.config_time_slice)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Z轴范围组
        z_group = QGroupBox("Z轴范围")
        z_layout = QFormLayout()
        
        z_layout.addRow(QLabel("Z 最小值:"), self.config_z_min)
        z_layout.addRow(QLabel("Z 最大值:"), self.config_z_max)
        
        z_group.setLayout(z_layout)
        layout.addWidget(z_group)
        
        # 说明
        velocity_note = QLabel("可以在速度模型设置中选择更精确的地球速度模型")
        velocity_note.setStyleSheet("color: #1976D2; font-style: italic;")
        layout.addWidget(velocity_note)
        
        layout.addStretch(1)
        tab.setLayout(layout)
        return tab
        
    def create_advanced_tab(self):
        """创建高级选项标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 性能组
        perf_group = QGroupBox("性能设置")
        perf_layout = QVBoxLayout()
        
        perf_layout.addWidget(self.use_gpu_checkbox)
        
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(QLabel("计算线程数:"))
        thread_combo = QComboBox()
        thread_combo.addItems(["1", "2", "4", "8", "自动"])
        thread_layout.addWidget(thread_combo)
        thread_layout.addStretch(1)
        
        perf_layout.addLayout(thread_layout)
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        # 界面组
        ui_group = QGroupBox("界面设置")
        ui_layout = QVBoxLayout()
        
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("主题:"))
        theme_layout.addWidget(self.theme_selector)
        theme_layout.addStretch(1)
        
        ui_layout.addLayout(theme_layout)
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        layout.addStretch(1)
        tab.setLayout(layout)
        return tab

