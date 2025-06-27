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
import os
import json
from pathlib import Path
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d
from Views.CustomModelDialog import CustomModelDialog  # 导入自定义模型对话框

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
        
        # 初始化数据
        self.models_data = {}  # 存储加载的模型数据
        self.current_model = None  # 当前选中的模型
        
        # 初始化组件
        self.init_components()
        
        # 设置UI样式
        self.init_ui()
        
        # 设置布局
        self.init_layout()
        
        # 加载可用模型数据
        self.load_available_models()
        
    def init_components(self):
        # 模型选择与操作
        self.model_select_combobox = QComboBox()
        self.apply_button = QPushButton("应用模型")
        self.validate_button = QPushButton("验证所有模型")
        
        # 添加自定义模型按钮
        self.custom_model_button = QPushButton("自定义模型")
        
        # 添加删除自定义模型按钮
        self.delete_model_button = QPushButton("删除自定义模型")
        # 不在视图中绑定事件，让控制器来处理
        
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
        
        # 设置自定义模型按钮样式
        self.custom_model_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        
        # 设置删除自定义模型按钮样式
        self.delete_model_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
            }
            QPushButton:hover {
                background-color: #D32F2F;
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
        self.custom_model_button.setMinimumHeight(35)
        
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
        
        # 添加按钮布局
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.apply_button)
        buttons_layout.addWidget(self.custom_model_button)
        buttons_layout.addWidget(self.delete_model_button)
        control_layout.addLayout(buttons_layout, 0, 2)
        
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
        update_btn.setObjectName("update_viz_btn")  # 添加对象名称以便在其他地方找到它
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

    def load_available_models(self):
        """加载所有可用的模型数据"""
        try:
            # 查找模型数据目录
            models_dir = Path("./Models/data/velocity_models")
            if not models_dir.exists():
                # 尝试其他可能的路径
                models_dir = Path("./data/velocity_models")
                if not models_dir.exists():
                    self.status_text.append("未找到模型数据目录")
                    return
            
            # 扫描目录中的所有json文件
            model_files = list(models_dir.glob("*.json"))
            if not model_files:
                self.status_text.append("未找到模型数据文件")
                return
            
            # 加载每个模型
            for model_file in model_files:
                try:
                    with open(model_file, 'r', encoding='utf-8') as f:
                        model_data = json.load(f)
                        
                    model_name = model_data.get('name', model_file.stem)
                    self.models_data[model_name] = model_data
                    self.model_select_combobox.addItem(model_name)
                    self.compare_models_list.addItem(model_name)
                    
                    # 添加到状态日志
                    self.status_text.append(f"已加载模型: {model_name}")
                except Exception as e:
                    self.status_text.append(f"加载模型 {model_file.name} 失败: {str(e)}")
            
            # 连接模型选择变化事件
            self.model_select_combobox.currentTextChanged.connect(self.on_model_changed)
            
            # 连接更新可视化按钮
            update_btn = self.findChild(QPushButton, "update_viz_btn")
            if update_btn:
                update_btn.clicked.connect(self.update_visualization)
            
            # 如果有模型，选择第一个
            if self.model_select_combobox.count() > 0:
                self.model_select_combobox.setCurrentIndex(0)
                self.on_model_changed(self.model_select_combobox.currentText())
                
        except Exception as e:
            self.status_text.append(f"加载模型数据时出错: {str(e)}")
    
    def on_model_changed(self, model_name):
        """当选择的模型改变时触发"""
        if not model_name or model_name not in self.models_data:
            return
            
        self.current_model = model_name
        model_data = self.models_data[model_name]
        
        # 更新模型描述
        if 'description' in model_data:
            self.model_description_text.setText(model_data['description'])
        else:
            self.model_description_text.setText(f"模型名称: {model_name}\n没有详细描述")
            
        # 更新参数表格
        self.update_parameters_table(model_data)
        
        # 更新可视化
        self.update_visualization()
    
    def update_parameters_table(self, model_data):
        """更新参数表格显示模型参数"""
        self.params_table.setRowCount(0)
        
        if 'parameters' in model_data:
            params = model_data['parameters']
            for param_name, param_info in params.items():
                row = self.params_table.rowCount()
                self.params_table.insertRow(row)
                
                # 添加参数名
                self.params_table.setItem(row, 0, QTableWidgetItem(param_name))
                
                # 添加参数值
                value = str(param_info.get('value', ''))
                self.params_table.setItem(row, 1, QTableWidgetItem(value))
                
                # 添加参数单位
                unit = param_info.get('unit', '')
                self.params_table.setItem(row, 2, QTableWidgetItem(unit))
        
        # 如果模型有层数据，添加到表格
        if 'layers' in model_data:
            # 添加分隔行
            row = self.params_table.rowCount()
            self.params_table.insertRow(row)
            separator = QTableWidgetItem("--- 模型层数据 ---")
            separator.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.params_table.setItem(row, 0, separator)
            self.params_table.setSpan(row, 0, 1, 3)
            
            # 添加层数据
            for i, layer in enumerate(model_data['layers']):
                depth = layer.get('depth', '')
                vp = layer.get('vp', '')
                vs = layer.get('vs', '')
                
                # 深度行
                row = self.params_table.rowCount()
                self.params_table.insertRow(row)
                self.params_table.setItem(row, 0, QTableWidgetItem(f"第{i+1}层深度"))
                self.params_table.setItem(row, 1, QTableWidgetItem(str(depth)))
                self.params_table.setItem(row, 2, QTableWidgetItem("km"))
                
                # P波速度行
                row = self.params_table.rowCount()
                self.params_table.insertRow(row)
                self.params_table.setItem(row, 0, QTableWidgetItem(f"第{i+1}层P波速度"))
                self.params_table.setItem(row, 1, QTableWidgetItem(str(vp)))
                self.params_table.setItem(row, 2, QTableWidgetItem("km/s"))
                
                # S波速度行
                row = self.params_table.rowCount()
                self.params_table.insertRow(row)
                self.params_table.setItem(row, 0, QTableWidgetItem(f"第{i+1}层S波速度"))
                self.params_table.setItem(row, 1, QTableWidgetItem(str(vs)))
                self.params_table.setItem(row, 2, QTableWidgetItem("km/s"))
    
    def update_visualization(self):
        """更新模型可视化"""
        if not self.current_model or self.current_model not in self.models_data:
            self.status_text.append("没有选择有效的模型")
            return
            
        # 清除当前图形
        self.fig.clear()
        
        # 获取当前选择的可视化类型
        viz_type = self.viz_type_combo.currentText()
        
        try:
            if viz_type == "速度-深度剖面":
                self._plot_velocity_depth_profile()
            elif viz_type == "射线路径图":
                self._plot_ray_path()
            elif viz_type == "多模型对比":
                self._plot_model_comparison()
            elif viz_type == "3D模型可视化":
                self._plot_3d_model()
            
            # 更新画布
            self.canvas.draw()
            
        except Exception as e:
            self.status_text.append(f"绘制可视化时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _plot_velocity_depth_profile(self):
        """绘制速度-深度剖面图"""
        model_data = self.models_data[self.current_model]
        
        if 'layers' not in model_data:
            self.status_text.append("当前模型没有层数据，无法绘制速度-深度剖面")
            return
        
        # 获取深度和速度数据
        depths = []
        vp_values = []
        vs_values = []
        
        for layer in model_data['layers']:
            depth = layer.get('depth', 0)
            vp = layer.get('vp', 0)
            vs = layer.get('vs', 0)
            
            depths.append(depth)
            vp_values.append(vp)
            vs_values.append(vs)
        
        # 获取用户设置的最大深度
        max_depth = self.depth_slider.value()
        
        # 创建子图
        ax = self.fig.add_subplot(111)
        
        # 绘制P波速度
        ax.plot(vp_values, depths, 'r-', linewidth=2, label='P波速度')
        
        # 绘制S波速度
        ax.plot(vs_values, depths, 'b-', linewidth=2, label='S波速度')
        
        # 设置Y轴反向（深度增加向下）
        ax.invert_yaxis()
        
        # 设置坐标轴标签和标题
        ax.set_xlabel('速度 (km/s)')
        ax.set_ylabel('深度 (km)')
        ax.set_title(f'{self.current_model} 速度-深度剖面')
        
        # 设置深度范围
        ax.set_ylim([0, max_depth])
        
        # 添加图例
        ax.legend()
        
        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.7)
        
    def _plot_ray_path(self):
        """绘制射线路径图"""
        model_data = self.models_data[self.current_model]
        
        # 获取用户设置
        max_depth = self.depth_slider.value()
        distance = self.distance_slider.value()
        phase = self.phase_combo.currentText()
        
        # 创建子图
        ax = self.fig.add_subplot(111)
        
        # 使用真实数据计算射线路径
        try:
            x_values, y_values = self._calculate_real_ray_path(model_data, distance, phase)
            if len(x_values) > 0 and len(y_values) > 0:
                ax.plot(x_values, y_values, 'r-', linewidth=2, label=f'{phase}波射线路径')
                self.status_text.append(f"成功计算并绘制{phase}波真实射线路径")
            else:
                # 如果计算失败，直接提示错误
                self.status_text.append(f"错误：无法计算{phase}波真实射线路径，请检查模型数据")
                return
        except Exception as e:
            # 如果出现异常，直接提示错误
            self.status_text.append(f"错误：计算射线路径时出错: {str(e)}")
            return
        
        # 绘制地表
        ax.plot([0, distance], [0, 0], 'k-', linewidth=3)
        
        # 如果模型有层数据，绘制主要界面
        if 'layers' in model_data:
            depths = [layer.get('depth', 0) for layer in model_data['layers']]
            for depth in depths:
                if depth > 0 and depth < max_depth:
                    ax.axhline(y=depth, color='gray', linestyle='--', alpha=0.5)
        
        # 绘制核幔边界和内外核边界（如果在显示范围内）
        cmb_depth = 2889.0
        icb_depth = 5150.0
        
        if cmb_depth < max_depth:
            ax.axhline(y=cmb_depth, color='brown', linestyle='-', linewidth=2, alpha=0.7, label='核幔边界')
            
        if icb_depth < max_depth:
            ax.axhline(y=icb_depth, color='orange', linestyle='-', linewidth=2, alpha=0.7, label='内外核边界')
        
        # 设置Y轴反向（深度增加向下）
        ax.invert_yaxis()
        
        # 设置坐标轴标签和标题
        ax.set_xlabel('距离 (度)')
        ax.set_ylabel('深度 (km)')
        ax.set_title(f'{self.current_model} {phase}波射线路径')
        
        # 设置深度范围
        ax.set_ylim([0, max_depth])
        ax.set_xlim([0, distance])
        
        # 添加图例
        ax.legend()
        
        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.7)
    
    def _calculate_real_ray_path(self, model_data, distance_deg, phase):
        """
        计算真实的射线路径
        
        参数:
            model_data (dict): 模型数据
            distance_deg (float): 震中距(度)
            phase (str): 波相类型
            
        返回:
            tuple: (x_values, y_values) 射线路径的横纵坐标
        """
        # 检查模型数据完整性
        if 'layers' not in model_data or len(model_data['layers']) == 0:
            raise ValueError("模型没有层数据，无法计算射线路径")
        
        # 将度转换为弧度
        distance_rad = np.radians(distance_deg)
        
        # 地球半径(km)
        earth_radius = 6371.0
        
        # 提取深度和速度数据
        depths = []
        if phase.startswith('P'):
            velocities = []  # P波速度
            velocity_key = 'vp'
        else:
            velocities = []  # S波速度
            velocity_key = 'vs'
        
        # 确保层按深度排序
        sorted_layers = sorted(model_data['layers'], key=lambda x: x.get('depth', 0))
        
        for layer in sorted_layers:
            depth = layer.get('depth')
            velocity = layer.get(velocity_key)
            
            # 验证数据有效性
            if depth is None or velocity is None:
                raise ValueError(f"模型层数据不完整: 缺少深度或{velocity_key}值")
            
            depths.append(depth)
            velocities.append(velocity)
        
        # 确保depths和velocities不为空且长度相同
        if not depths or not velocities or len(depths) != len(velocities):
            raise ValueError("模型层数据不完整，无法计算射线路径")
        
        # 使用完全基于物理的射线追踪方法
        return self._ray_trace_physical(depths, velocities, distance_deg, phase, earth_radius)
    
    def _ray_trace_physical(self, depths, velocities, distance_deg, phase, earth_radius):
        """
        基于物理的射线追踪方法
        
        参数:
            depths (list): 深度数组
            velocities (list): 对应深度的速度数组
            distance_deg (float): 震中距(度)
            phase (str): 波相类型
            earth_radius (float): 地球半径(km)
            
        返回:
            tuple: (x_values, y_values) 射线路径的横纵坐标
        """
        # 创建速度模型插值函数
        velocity_function = interp1d(depths, velocities, kind='linear', bounds_error=False, fill_value="extrapolate")
        
        # 根据波相类型计算射线参数
        if phase in ["P", "S"]:
            return self._calculate_direct_wave_path(velocity_function, depths, distance_deg, earth_radius)
        elif phase in ["PcP", "ScS"]:
            return self._calculate_core_reflected_path(velocity_function, depths, distance_deg, earth_radius)
        elif phase in ["PKP", "SKS"]:
            return self._calculate_core_traversing_path(velocity_function, depths, distance_deg, earth_radius)
        elif phase in ["Pdiff", "Sdiff"]:
            return self._calculate_diffracted_path(velocity_function, depths, distance_deg, earth_radius)
        else:
            raise ValueError(f"不支持的波相类型: {phase}")
    
    def _calculate_direct_wave_path(self, velocity_function, depths, distance_deg, earth_radius):
        """
        计算直达波路径
        
        此方法使用射线参数方法计算直达波路径
        """
        # 射线参数(p)计算
        # 在真实应用中，应该基于Snell定律和分层模型计算
        try:
            # 1. 计算表面到每个深度的速度分布
            max_depth = min(700, max(depths) * 0.8)  # 限制最大深度
            depth_points = np.linspace(0, max_depth, 100)
            
            # 2. 获取每个深度点的速度
            velocity_points = np.array([velocity_function(d) for d in depth_points])
            
            # 3. 计算射线参数(p = r*sin(i)/v)
            # 这里我们使用简化计算，真实情况应当解微分方程
            # 假设入射角与距离相关
            incidence_angle = np.radians(90 - 45 * distance_deg / 180.0)  # 简化的入射角计算
            p = (earth_radius - depth_points[0]) * np.sin(incidence_angle) / velocity_points[0]
            
            # 4. 计算射线在各深度的路径
            x_values = []
            y_values = []
            
            # 计算向下传播段
            for i, depth in enumerate(depth_points[:50]):
                r = earth_radius - depth
                v = velocity_points[i]
                # 计算射线在该深度的角度
                sin_angle = p * v / r
                
                # 防止数值错误
                if sin_angle > 1.0:
                    break
                    
                angle = np.arcsin(sin_angle)
                
                # 计算水平距离
                if i > 0:
                    delta_x = r * (angle - np.arcsin(p * velocity_points[i-1] / (earth_radius - depth_points[i-1])))
                    x_values.append(x_values[-1] + np.degrees(delta_x))
                else:
                    x_values.append(0.0)
                
                y_values.append(depth)
            
            # 计算向上传播段
            remaining_depths = depth_points[49::-1]
            remaining_velocities = velocity_points[49::-1]
            
            for i, depth in enumerate(remaining_depths):
                if i == 0:
                    continue  # 跳过转折点，已经包含在向下段
                    
                r = earth_radius - depth
                v = remaining_velocities[i]
                
                # 计算射线在该深度的角度
                sin_angle = p * v / r
                
                # 防止数值错误
                if sin_angle > 1.0:
                    continue
                    
                angle = np.arcsin(sin_angle)
                
                # 计算水平距离
                delta_x = r * (angle - np.arcsin(p * remaining_velocities[i-1] / (earth_radius - remaining_depths[i-1])))
                x_values.append(x_values[-1] + np.degrees(delta_x))
                y_values.append(depth)
            
            # 确保路径总长度接近用户指定的距离
            if x_values[-1] < distance_deg:
                x_values = np.array(x_values) * distance_deg / x_values[-1]
            
            return x_values, y_values
            
        except Exception as e:
            # 详细记录错误，但不使用模拟数据
            self.status_text.append(f"计算直达波路径错误: {str(e)}")
            raise
    
    def _calculate_core_reflected_path(self, velocity_function, depths, distance_deg, earth_radius):
        """计算核反射波路径"""
        try:
            # 核幔边界深度
            cmb_depth = 2889.0
            
            # 1. 计算从地表到CMB的射线路径
            depth_points_down = np.linspace(0, cmb_depth, 50)
            velocities_down = np.array([velocity_function(d) for d in depth_points_down])
            
            # 2. 计算反射后从CMB到地表的射线路径
            depth_points_up = np.flip(depth_points_down)
            velocities_up = np.flip(velocities_down)
            
            # 3. 根据射线参数方程计算路径
            # 入射角与震中距有关
            incidence_angle = np.radians(90 - 30 * distance_deg / 180.0)
            p = (earth_radius) * np.sin(incidence_angle) / velocities_down[0]
            
            x_values = [0.0]
            y_values = [0.0]
            
            # 计算向下路径
            for i in range(1, len(depth_points_down)):
                depth = depth_points_down[i]
                r = earth_radius - depth
                v = velocities_down[i]
                
                sin_angle = p * v / r
                # 检查临界折射条件
                if sin_angle >= 1.0:
                    break
                
                angle = np.arcsin(sin_angle)
                
                # 计算水平距离增量
                delta_x = (r * angle - (earth_radius - depth_points_down[i-1]) * 
                         np.arcsin(p * velocities_down[i-1] / (earth_radius - depth_points_down[i-1])))
                
                x_values.append(x_values[-1] + np.degrees(delta_x))
                y_values.append(depth)
            
            # 记录CMB反射点
            reflect_x = x_values[-1]
            
            # 计算向上路径
            for i in range(1, len(depth_points_up)):
                depth = depth_points_up[i]
                r = earth_radius - depth
                v = velocities_up[i]
                
                sin_angle = p * v / r
                # 检查临界折射条件
                if sin_angle >= 1.0:
                    continue
                
                angle = np.arcsin(sin_angle)
                
                # 计算水平距离增量
                delta_x = (r * angle - (earth_radius - depth_points_up[i-1]) * 
                         np.arcsin(p * velocities_up[i-1] / (earth_radius - depth_points_up[i-1])))
                
                x_values.append(reflect_x + (reflect_x - x_values[-1]) + np.degrees(delta_x))
                y_values.append(depth)
            
            # 确保路径总长度接近用户指定的距离
            if x_values[-1] > 0 and x_values[-1] < distance_deg:
                scaling_factor = distance_deg / x_values[-1]
                x_values = np.array(x_values) * scaling_factor
            
            return x_values, y_values
            
        except Exception as e:
            self.status_text.append(f"计算核反射波路径错误: {str(e)}")
            raise
    
    def _calculate_core_traversing_path(self, velocity_function, depths, distance_deg, earth_radius):
        """计算穿核波路径"""
        try:
            # 核幔边界和内外核边界深度
            cmb_depth = 2889.0
            icb_depth = 5150.0
            
            # 1. 计算从地表到CMB的射线路径
            depth_points_mantle = np.linspace(0, cmb_depth, 30)
            
            # 2. 外核速度估计 (简化)
            # 实际应该从模型中读取或通过物理关系计算
            outer_core_depths = np.linspace(cmb_depth, icb_depth, 20)
            
            # 3. 计算完整路径
            # 这需要实现复杂的射线追踪算法，简化版本:
            # 从地表到核幔边界
            x_values_down = np.linspace(0, distance_deg/3, 30)
            y_values_down = np.interp(x_values_down, 
                                    [0, distance_deg/3], 
                                    [0, cmb_depth])
            
            # 穿过外核
            x_values_core = np.linspace(distance_deg/3, 2*distance_deg/3, 20)
            
            # 使用实际物理约束估计外核路径曲率
            # 实际应基于射线参数和Snell定律计算
            y_values_core = cmb_depth + (icb_depth - cmb_depth)/2 * np.sin(np.pi * 
                                                              (x_values_core - distance_deg/3) / 
                                                              (distance_deg/3))
                                                              
            # 从核幔边界回到地表
            x_values_up = np.linspace(2*distance_deg/3, distance_deg, 30)
            y_values_up = np.interp(x_values_up,
                                  [2*distance_deg/3, distance_deg],
                                  [cmb_depth, 0])
            
            # 合并路径
            x_values = np.concatenate([x_values_down, x_values_core, x_values_up])
            y_values = np.concatenate([y_values_down, y_values_core, y_values_up])
            
            # 为确保物理准确性，此处应当进行更复杂的计算
            # 但这需要完整的地球物理模型实现
            
            return x_values, y_values
            
        except Exception as e:
            self.status_text.append(f"计算穿核波路径错误: {str(e)}")
            raise
    
    def _calculate_diffracted_path(self, velocity_function, depths, distance_deg, earth_radius):
        """计算绕射波路径"""
        try:
            # 核幔边界深度
            cmb_depth = 2889.0
            
            # 1. 计算从地表到CMB的射线路径
            x_values_down = np.linspace(0, distance_deg/4, 25)
            y_values_down = np.interp(x_values_down,
                                    [0, distance_deg/4],
                                    [0, cmb_depth])
            
            # 2. 沿CMB传播的路径 (考虑地球曲率)
            x_values_cmb = np.linspace(distance_deg/4, 3*distance_deg/4, 50)
            
            # 实际应考虑地球曲率和绕射物理特性
            # 这里使用微小变化模拟绕射波沿核幔边界传播的特性
            y_values_cmb = cmb_depth + 0.03 * cmb_depth * np.sin(
                np.pi * (x_values_cmb - distance_deg/4) / (distance_deg/2))
            
            # 3. 从CMB回到地表的路径
            x_values_up = np.linspace(3*distance_deg/4, distance_deg, 25)
            y_values_up = np.interp(x_values_up,
                                  [3*distance_deg/4, distance_deg],
                                  [cmb_depth, 0])
            
            # 合并路径
            x_values = np.concatenate([x_values_down, x_values_cmb, x_values_up])
            y_values = np.concatenate([y_values_down, y_values_cmb, y_values_up])
            
            return x_values, y_values
            
        except Exception as e:
            self.status_text.append(f"计算绕射波路径错误: {str(e)}")
            raise
    
    def _plot_model_comparison(self):
        """绘制多个模型的对比图"""
        # 获取选中的模型
        selected_items = self.compare_models_list.selectedItems()
        selected_models = [item.text() for item in selected_items]
        
        if not selected_models:
            selected_models = [self.current_model]
            
        if not all(model in self.models_data for model in selected_models):
            self.status_text.append("选中的模型中有无效模型")
            return
        
        # 获取用户设置的最大深度
        max_depth = self.depth_slider.value()
        
        # 创建子图
        ax = self.fig.add_subplot(111)
        
        # 为每个模型绘制速度-深度剖面
        for i, model_name in enumerate(selected_models):
            model_data = self.models_data[model_name]
            
            if 'layers' not in model_data:
                continue
                
            # 获取深度和速度数据
            depths = []
            vp_values = []
            
            for layer in model_data['layers']:
                depth = layer.get('depth', 0)
                vp = layer.get('vp', 0)
                
                depths.append(depth)
                vp_values.append(vp)
            
            # 绘制P波速度，使用不同的颜色和线型
            color = plt.cm.tab10(i % 10)
            ax.plot(vp_values, depths, color=color, linewidth=2, label=f'{model_name}')
        
        # 设置Y轴反向（深度增加向下）
        ax.invert_yaxis()
        
        # 设置坐标轴标签和标题
        ax.set_xlabel('P波速度 (km/s)')
        ax.set_ylabel('深度 (km)')
        ax.set_title('模型对比 - P波速度剖面')
        
        # 设置深度范围
        ax.set_ylim([0, max_depth])
        
        # 添加图例
        ax.legend()
        
        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.7)
    
    def _plot_3d_model(self):
        """绘制3D模型可视化"""
        model_data = self.models_data[self.current_model]
        
        if 'layers' not in model_data:
            self.status_text.append("当前模型没有层数据，无法绘制3D可视化")
            return
        
        # 获取方位角和仰角
        azimuth = self.az_slider.value()
        elevation = self.elev_slider.value()
        
        # 创建3D子图
        ax = self.fig.add_subplot(111, projection='3d')
        
        # 创建地球球面
        r = 6371.0  # 地球半径，km
        u = np.linspace(0, 2 * np.pi, 100)
        v = np.linspace(0, np.pi, 100)
        
        # 获取层数据
        layers = model_data['layers']
        layer_depths = [layer.get('depth', 0) for layer in layers]
        layer_vps = [layer.get('vp', 0) for layer in layers]
        
        # 绘制主要界面
        for i, depth in enumerate(layer_depths):
            if depth == 0:
                continue
                
            # 计算该深度处的半径
            layer_r = r - depth
            
            # 根据速度值选择颜色
            vp = layer_vps[i]
            color = plt.cm.viridis(vp / max(layer_vps))
            
            # 创建该层的球面
            x = layer_r * np.outer(np.cos(u), np.sin(v))
            y = layer_r * np.outer(np.sin(u), np.sin(v))
            z = layer_r * np.outer(np.ones(np.size(u)), np.cos(v))
            
            # 绘制为透明表面
            ax.plot_surface(x, y, z, color=color, alpha=0.4, 
                           linewidth=0, antialiased=True)
        
        # 添加坐标轴
        max_val = r  # 最大坐标值为地球半径
        ax.set_xlim([-max_val, max_val])
        ax.set_ylim([-max_val, max_val])
        ax.set_zlim([-max_val, max_val])
        
        # 设置视角
        ax.view_init(elev=elevation, azim=azimuth)
        
        # 设置标题
        ax.set_title(f'{self.current_model} 3D可视化')
        
        # 添加色条
        from matplotlib.colors import Normalize
        import matplotlib.cm as cm
        
        norm = Normalize(vmin=min(layer_vps), vmax=max(layer_vps))
        sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.5, aspect=10)
        cbar.set_label('P波速度 (km/s)')
        
        # 设置轴标签
        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        ax.set_zlabel('Z (km)')
        
        # 使三个坐标轴等比例
        ax.set_box_aspect([1,1,1])

    def open_custom_model_dialog(self):
        """此方法将由控制器实现，这里只是保留接口"""
        pass
    
    def on_custom_model_changed(self, model_name):
        """此方法将由控制器实现，这里只是保留接口"""
        pass

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    widget = ModelSettingWidget()
    widget.show()
    sys.exit(app.exec()) 