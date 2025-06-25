from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, 
    QLabel, QGroupBox, QFormLayout, QScrollArea, QMessageBox,
    QTextEdit, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSplitter, QGridLayout, QLineEdit, QCheckBox, QSpacerItem,
    QSizePolicy, QProgressBar, QDoubleSpinBox, QSlider, QListWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib
import numpy as np
import platform

# 设置matplotlib中文字体支持
system = platform.system()
if system == 'Darwin':  # macOS
    matplotlib.rcParams['font.family'] = 'Arial Unicode MS'
elif system == 'Windows':
    matplotlib.rcParams['font.family'] = 'Microsoft YaHei'
else:
    matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

class ModelSettingWidget(QWidget):
    """速度模型设置界面"""

    def __init__(self):
        super().__init__()
        
        # 初始化组件
        self.init_components()
        
        # 设置UI样式
        self.init_ui()
        
        # 设置布局
        self.init_layout()
        
    def init_components(self):
        # 模型选择与操作
        self.model_select_combobox = QComboBox()
        self.apply_button = QPushButton("应用模型")
        self.validate_button = QPushButton("验证所有模型")
        
        # 模型描述
        self.model_description_text = QTextEdit()
        self.model_description_text.setReadOnly(True)
        
        # 模型可视化
        self.fig = plt.figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # 可视化控制组件
        self.viz_type_combo = QComboBox()
        self.viz_type_combo.addItems(["速度-深度剖面", "射线路径图", "多模型对比", "3D模型可视化"])
        
        self.depth_slider = QSlider(Qt.Orientation.Horizontal)
        self.depth_slider.setRange(10, 700)
        self.depth_slider.setValue(100)
        self.depth_label = QLabel("最大深度: 100 km")
        
        self.distance_slider = QSlider(Qt.Orientation.Horizontal)
        self.distance_slider.setRange(10, 180)
        self.distance_slider.setValue(30)
        self.distance_label = QLabel("震中距: 30°")
        
        self.phase_combo = QComboBox()
        self.phase_combo.addItems(["P", "S", "PcP", "ScS", "PKP", "SKS", "Pdiff", "Sdiff"])
        
        # 使用QListWidget替代QComboBox以支持多选
        self.compare_models_list = QListWidget()
        self.compare_models_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        
        # 3D可视化控制
        self.az_slider = QSlider(Qt.Orientation.Horizontal)
        self.az_slider.setRange(0, 360)
        self.az_slider.setValue(30)
        self.az_label = QLabel("方位角: 30°")
        
        self.elev_slider = QSlider(Qt.Orientation.Horizontal)
        self.elev_slider.setRange(-90, 90)
        self.elev_slider.setValue(30)
        self.elev_label = QLabel("仰角: 30°")
        
        # 模型状态与日志
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        
        # 模型参数表格
        self.params_table = QTableWidget(0, 3)
        self.params_table.setHorizontalHeaderLabels(["参数", "值", "单位"])
        
        # 模型切换标签页
        self.model_tabs = QTabWidget()
        
    def init_ui(self):
        """初始化界面样式"""
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
            QLineEdit, QTextEdit {
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
            QTableWidget {
                border: 1px solid #ddd;
                background-color: white;
                selection-background-color: #E3F2FD;
                selection-color: #000;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                font-weight: bold;
                border: none;
                border-right: 1px solid #ddd;
                border-bottom: 1px solid #ddd;
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
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1E88E5;
                border: 1px solid #777;
                width: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
        """)
        
        # 设置按钮样式
        self.validate_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        # 设置文本框样式
        self.model_description_text.setStyleSheet("""
            background-color: #ECEFF1;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Courier New', monospace;
        """)
        
        self.status_text.setStyleSheet("""
            background-color: #ECEFF1;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Courier New', monospace;
        """)
        
        # 设置表格样式
        self.params_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.params_table.setAlternatingRowColors(True)
        
        # 设置按钮大小
        self.apply_button.setMinimumHeight(35)
        self.validate_button.setMinimumHeight(35)
        
        # 设置滑块事件连接
        self.depth_slider.valueChanged.connect(self._update_depth_label)
        self.distance_slider.valueChanged.connect(self._update_distance_label)
        self.az_slider.valueChanged.connect(self._update_az_label)
        self.elev_slider.valueChanged.connect(self._update_elev_label)
        
    def _update_depth_label(self, value):
        self.depth_label.setText(f"最大深度: {value} km")
        
    def _update_distance_label(self, value):
        self.distance_label.setText(f"震中距: {value}°")
        
    def _update_az_label(self, value):
        self.az_label.setText(f"方位角: {value}°")
        
    def _update_elev_label(self, value):
        self.elev_label.setText(f"仰角: {value}°")
        
    def init_layout(self):
        """初始化界面布局"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        
        # 顶部控制区域
        control_group = QGroupBox("模型选择")
        control_layout = QGridLayout()
        
        # 第一行：模型选择
        control_layout.addWidget(QLabel("选择模型:"), 0, 0)
        control_layout.addWidget(self.model_select_combobox, 0, 1)
        control_layout.addWidget(self.apply_button, 0, 2)
        
        # 第二行：模型描述
        control_layout.addWidget(QLabel("模型描述:"), 1, 0)
        control_layout.addWidget(self.model_description_text, 1, 1, 1, 2)
        
        control_group.setLayout(control_layout)
        
        # 中部内容区域 - 使用标签页组织内容
        self.model_tabs.addTab(self.create_visualization_tab(), "模型可视化")
        self.model_tabs.addTab(self.create_parameters_tab(), "模型参数")
        
        # 底部操作区域
        action_group = QGroupBox("操作与状态")
        action_layout = QVBoxLayout()
        
        # 添加操作按钮
        action_buttons = QHBoxLayout()
        action_buttons.addWidget(self.validate_button)
        action_buttons.addStretch(1)
        action_layout.addLayout(action_buttons)
        
        # 添加状态显示
        action_layout.addWidget(QLabel("模型状态:"))
        action_layout.addWidget(self.status_text)
        
        action_group.setLayout(action_layout)
        
        # 添加到主布局
        main_layout.addWidget(control_group)
        main_layout.addWidget(self.model_tabs, 1)  # 中部内容区域可扩展
        main_layout.addWidget(action_group)
        
        self.setLayout(main_layout)
    
    def create_visualization_tab(self):
        """创建模型可视化标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 可视化控制面板
        control_panel = QGroupBox("可视化控制")
        control_layout = QGridLayout()
        
        # 可视化类型选择
        control_layout.addWidget(QLabel("可视化类型:"), 0, 0)
        control_layout.addWidget(self.viz_type_combo, 0, 1)
        
        # 深度和距离控制
        control_layout.addWidget(QLabel("深度范围:"), 1, 0)
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(self.depth_slider)
        depth_layout.addWidget(self.depth_label)
        control_layout.addLayout(depth_layout, 1, 1)
        
        control_layout.addWidget(QLabel("震中距离:"), 2, 0)
        distance_layout = QHBoxLayout()
        distance_layout.addWidget(self.distance_slider)
        distance_layout.addWidget(self.distance_label)
        control_layout.addLayout(distance_layout, 2, 1)
        
        # 波相选择
        control_layout.addWidget(QLabel("波相选择:"), 3, 0)
        control_layout.addWidget(self.phase_combo, 3, 1)
        
        # 多模型对比
        control_layout.addWidget(QLabel("对比模型:"), 4, 0)
        control_layout.addWidget(self.compare_models_list, 4, 1)
        
        # 3D视图控制 (方位角和仰角)
        control_layout.addWidget(QLabel("3D方位角:"), 5, 0)
        az_layout = QHBoxLayout()
        az_layout.addWidget(self.az_slider)
        az_layout.addWidget(self.az_label)
        control_layout.addLayout(az_layout, 5, 1)
        
        control_layout.addWidget(QLabel("3D仰角:"), 6, 0)
        elev_layout = QHBoxLayout()
        elev_layout.addWidget(self.elev_slider)
        elev_layout.addWidget(self.elev_label)
        control_layout.addLayout(elev_layout, 6, 1)
        
        # 更新按钮
        update_btn = QPushButton("更新可视化")
        update_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        control_layout.addWidget(update_btn, 7, 0, 1, 2)
        
        control_panel.setLayout(control_layout)
        
        # 可视化区域
        viz_panel = QGroupBox("可视化结果")
        viz_layout = QVBoxLayout()
        
        # 添加工具栏和画布
        viz_layout.addWidget(self.toolbar)
        viz_layout.addWidget(self.canvas)
        
        viz_panel.setLayout(viz_layout)
        
        # 添加控制面板和可视化面板到主布局
        # 使用拆分窗口进行布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        control_widget = QWidget()
        control_widget.setLayout(QVBoxLayout())
        control_widget.layout().addWidget(control_panel)
        control_widget.layout().addStretch(1)
        
        viz_widget = QWidget()
        viz_widget.setLayout(QVBoxLayout())
        viz_widget.layout().addWidget(viz_panel)
        
        splitter.addWidget(control_widget)
        splitter.addWidget(viz_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)
        
        tab.setLayout(layout)
        return tab
        
    def create_parameters_tab(self):
        """创建模型参数标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 添加表格和说明
        layout.addWidget(QLabel("模型参数:"))
        layout.addWidget(self.params_table)
        
        # 添加编辑控制
        edit_controls = QHBoxLayout()
        edit_button = QPushButton("编辑参数")
        edit_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        reset_button = QPushButton("重置参数")
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        
        edit_controls.addWidget(edit_button)
        edit_controls.addWidget(reset_button)
        edit_controls.addStretch(1)
        
        layout.addLayout(edit_controls)
        
        tab.setLayout(layout)
        return tab

    def update_compare_models_combo(self, available_models):
        """更新用于比较的模型列表"""
        self.compare_models_list.clear()
        for model in available_models:
            self.compare_models_list.addItem(model)

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    widget = ModelSettingWidget()
    widget.show()
    sys.exit(app.exec()) 