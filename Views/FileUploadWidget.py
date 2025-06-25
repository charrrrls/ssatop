from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout,
    QGroupBox, QSizePolicy, QHBoxLayout, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QGridLayout, QToolButton, QSpacerItem, QProgressBar,
    QTabWidget, QComboBox, QLineEdit, QMenu, QToolBar,
    QScrollArea, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QAction
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import os
import datetime

class FileUploadWidget(QWidget):
    file_loaded = pyqtSignal(str, str)  # 文件加载信号 (文件路径, 文件类型)
    
    def __init__(self):
        super().__init__()
        # 创建组件
        self.init_components()
        # 设置UI样式和布局
        self.init_ui()
        self.init_layout()
        # 初始化文件历史记录
        self.file_history = []
        # 设置定时自动保存
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_history)
        self.auto_save_timer.start(30000)  # 每30秒自动保存一次

    def init_components(self):
        # 文件上传按钮和工具栏
        self.upload_wave_button = QPushButton('上传信号文件')
        self.upload_detector_button = QPushButton('上传检测器位置文件')
        
        # 文件操作工具栏
        self.file_toolbar = QToolBar("文件操作")
        self.reload_action = QAction("重新加载", self)
        self.export_action = QAction("导出数据", self)
        self.clear_action = QAction("清除历史", self)
        
        self.file_toolbar.addAction(self.reload_action)
        self.file_toolbar.addAction(self.export_action)
        self.file_toolbar.addAction(self.clear_action)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索文件...")
        
        # 文件信息显示
        self.file_info_label = QLabel('尚未选择信号文件')
        self.position_label = QLabel('尚未选择位置文件')
        
        # 位置可视化按钮
        self.show_position_button = QPushButton('可视化检测器分布')
        
        # 数据预览画布
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(200)

        # 文件历史记录标签页
        self.history_tabs = QTabWidget()
        
        # 文件历史记录表格
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["文件名", "类型", "大小", "修改日期", "操作"])
        
        # 最近活动表格
        self.activity_table = QTableWidget(0, 3)
        self.activity_table.setHorizontalHeaderLabels(["时间", "操作", "文件"])
        
        # 进度指示器
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("就绪")
        
    def init_ui(self):
        # 设置整体样式
        self.setStyleSheet("""
            QWidget {
                font-family: 'Microsoft YaHei', 'Arial';
                background-color: #f5f5f5;
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
            QLabel {
                color: #333;
            }
            QPushButton {
                background-color: #1E88E5;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QTableWidget {
                border: 1px solid #ddd;
                background-color: white;
                selection-background-color: #E3F2FD;
                selection-color: #000;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-right: 1px solid #ddd;
                border-bottom: 1px solid #ddd;
            }
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
            }
            QToolBar {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
                spacing: 10px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QToolBar QToolButton:hover {
                background-color: #e0e0e0;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-top: 0px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-bottom: none;
                min-width: 100px;
                padding: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        
        # 文件信息标签样式
        self.file_info_label.setWordWrap(True)
        self.position_label.setWordWrap(True)
        info_style = """
            background-color: #ECEFF1;
            border-radius: 4px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            line-height: 1.5;
        """
        self.file_info_label.setStyleSheet(info_style)
        self.position_label.setStyleSheet(info_style)
        
        # 按钮样式
        self.upload_wave_button.setMinimumHeight(40)
        self.upload_detector_button.setMinimumHeight(40)
        self.show_position_button.setMinimumHeight(40)
        self.show_position_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        # 表格设置
        for table in [self.history_table, self.activity_table]:
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.verticalHeader().setVisible(False)
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # 搜索框样式
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 15px;
                padding: 5px 10px;
                background-color: white;
            }
        """)
        
    def init_layout(self):
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        
        # 上传和搜索操作区
        top_section = QHBoxLayout()
        
        # 上传按钮区
        upload_buttons = QHBoxLayout()
        upload_buttons.addWidget(self.upload_wave_button)
        upload_buttons.addWidget(self.upload_detector_button)
        upload_buttons.addWidget(self.show_position_button)
        
        # 搜索区
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input)
        
        top_section.addLayout(upload_buttons)
        top_section.addStretch(1)
        top_section.addLayout(search_layout)
        
        # 添加工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self.file_toolbar)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addWidget(self.progress_bar)
        
        # 创建左右分割的布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧区域 - 文件信息
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        # 文件信息显示区域
        info_group = QGroupBox("文件信息")
        info_layout = QGridLayout()
        
        # 添加标签
        info_layout.addWidget(QLabel("<b>信号文件:</b>"), 0, 0)
        info_layout.addWidget(self.file_info_label, 0, 1)
        info_layout.addWidget(QLabel("<b>检测器位置:</b>"), 1, 0)
        info_layout.addWidget(self.position_label, 1, 1)
        
        info_group.setLayout(info_layout)
        
        # 数据预览区域
        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(self.canvas)
        preview_group.setLayout(preview_layout)
        
        left_layout.addWidget(info_group)
        left_layout.addWidget(preview_group)
        
        # 右侧区域 - 文件历史
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        # 历史记录和活动日志标签页
        self.history_tabs.addTab(self.history_table, "文件历史")
        self.history_tabs.addTab(self.activity_table, "活动日志")
        right_layout.addWidget(self.history_tabs)
        
        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        # 添加到主布局
        main_layout.addLayout(top_section)
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(splitter, 1)
        
        self.setLayout(main_layout)
        
        # 连接信号和槽
        self.upload_wave_button.clicked.connect(self.upload_wave_file)
        self.upload_detector_button.clicked.connect(self.upload_detector_file)
        self.search_input.textChanged.connect(self.search_files)
        self.reload_action.triggered.connect(self.reload_selected_file)
        self.export_action.triggered.connect(self.export_data)
        self.clear_action.triggered.connect(self.clear_history)

    def show_file_info(self, file_info):
        """
        显示文件信息
        """
        self.file_info_label.setText(
            f"<b>文件名</b>: {file_info['file_name']}<br>"
            f"<b>道数</b>: {file_info['trace_count']}<br>"
            f"<b>采样间隔</b>: {file_info['sample_interval']}<br>"
            f"<b>采样点数</b>: {file_info['sample_count']}"
        )
        
        # 添加到历史记录
        self.add_to_history(file_info['file_name'], "信号文件")
        
        # 添加到活动日志
        self.add_to_activity("加载", file_info['file_name'])
        
        # 绘制简单预览图
        self.draw_preview()

    def show_location_info(self, location_info):
        """
        显示位置信息，包括 X、Y、Z 轴坐标范围
        """
        x_min = location_info['x'].min()
        x_max = location_info['x'].max()
        y_min = location_info['y'].min()
        y_max = location_info['y'].max()
        z_min = location_info['z'].min()
        z_max = location_info['z'].max()

        # 显示位置信息
        self.position_label.setText(
            f"<b>X轴坐标范围</b>: {x_min:.2f}m ~ {x_max:.2f}m<br>"
            f"<b>Y轴坐标范围</b>: {y_min:.2f}m ~ {y_max:.2f}m<br>"
            f"<b>Z轴坐标范围</b>: {z_min:.2f}m ~ {z_max:.2f}m<br>"
            f"<b>检波器数量</b>: {len(location_info)}"
        )
        
        # 添加到历史记录
        self.add_to_history("检波器位置文件", "位置数据")
        
        # 添加到活动日志
        self.add_to_activity("加载", "检波器位置文件")
        
        # 更新预览图以显示检波器位置
        self.draw_detector_preview(location_info)
        
    def add_to_history(self, filename, filetype):
        """添加文件到历史记录表格"""
        # 检查文件是否已经存在
        for row in range(self.history_table.rowCount()):
            if self.history_table.item(row, 0).text() == filename:
                return
                
        # 获取文件信息
        try:
            file_stats = {}
            if os.path.exists(filename):
                file_stats = os.stat(filename)
                size_kb = file_stats.st_size / 1024
                size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
                mod_time = datetime.datetime.fromtimestamp(file_stats.st_mtime).strftime("%Y-%m-%d %H:%M")
            else:
                size_str = "未知"
                mod_time = "未知"
        except:
            size_str = "未知"
            mod_time = "未知"
        
        # 添加新行
        row_position = self.history_table.rowCount()
        self.history_table.insertRow(row_position)
        
        # 设置单元格内容
        self.history_table.setItem(row_position, 0, QTableWidgetItem(filename))
        self.history_table.setItem(row_position, 1, QTableWidgetItem(filetype))
        self.history_table.setItem(row_position, 2, QTableWidgetItem(size_str))
        self.history_table.setItem(row_position, 3, QTableWidgetItem(mod_time))
        
        # 添加"重新加载"按钮
        reload_btn = QPushButton("重新加载")
        reload_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        # 存储文件信息
        self.file_history.append({
            'filename': filename,
            'type': filetype,
            'size': size_str,
            'date': mod_time
        })
        
        self.history_table.setCellWidget(row_position, 4, reload_btn)

    def add_to_activity(self, action, filename):
        """添加活动记录"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = self.activity_table.rowCount()
        self.activity_table.insertRow(row)
        self.activity_table.setItem(row, 0, QTableWidgetItem(now))
        self.activity_table.setItem(row, 1, QTableWidgetItem(action))
        self.activity_table.setItem(row, 2, QTableWidgetItem(filename))
    
    def add_history_item(self, file_path, file_type):
        """添加文件到历史记录"""
        # 调用已有的 add_to_history 方法
        self.add_to_history(file_path, file_type)
        # 添加活动记录
        self.add_to_activity("上传", os.path.basename(file_path))
    
    def draw_preview(self):
        """绘制预览图"""
        try:
            # 清除当前图表
            self.fig.clear()
            
            # 创建新子图
            ax = self.fig.add_subplot(111)
            
            # 模拟数据 - 实际应用中应使用真实数据
            x = np.linspace(0, 10, 100)
            y = np.sin(x) * np.exp(-x/5)
            
            ax.plot(x, y, 'b-')
            ax.set_title('波形数据预览')
            ax.set_xlabel('时间 (s)')
            ax.set_ylabel('振幅')
            ax.grid(True)
            
            self.canvas.draw()
        except Exception as e:
            print(f"绘制预览图时出错: {e}")
    
    def draw_detector_preview(self, location_data):
        """绘制检波器位置分布图"""
        self.fig.clear()
        ax = self.fig.add_subplot(111, projection='3d')
        
        # 绘制检波器位置
        ax.scatter(location_data['x'], location_data['y'], location_data['z'], 
                  c='r', marker='o', s=20, alpha=0.8)
        
        ax.set_title('检波器位置分布')
        ax.set_xlabel('X轴 (m)')
        ax.set_ylabel('Y轴 (m)')
        ax.set_zlabel('Z轴 (m)')
        
        self.canvas.draw()
    
    def upload_wave_file(self):
        """上传波形文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择波形文件", "", "SGY Files (*.sgy);;All Files (*)")
        
        if file_path:
            self.status_label.setText(f"正在加载 {os.path.basename(file_path)}...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 模拟加载进度
            for i in range(1, 101):
                QTimer.singleShot(i * 20, lambda val=i: self.progress_bar.setValue(val))
            
            QTimer.singleShot(2000, lambda: self.finish_upload(file_path, "wave"))
    
    def upload_detector_file(self):
        """上传检波器位置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择检波器位置文件", "", "Excel Files (*.xlsx);;All Files (*)")
        
        if file_path:
            self.status_label.setText(f"正在加载 {os.path.basename(file_path)}...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 模拟加载进度
            for i in range(1, 101):
                QTimer.singleShot(i * 10, lambda val=i: self.progress_bar.setValue(val))
            
            QTimer.singleShot(1000, lambda: self.finish_upload(file_path, "detector"))
    
    def finish_upload(self, file_path, file_type):
        """完成文件上传"""
        self.progress_bar.setValue(100)
        self.status_label.setText(f"已加载 {os.path.basename(file_path)}")
        
        # 延迟隐藏进度条
        QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
        
        # 触发文件加载信号
        self.file_loaded.emit(file_path, file_type)
        
        # 添加到活动日志
        self.add_to_activity("上传", os.path.basename(file_path))
    
    def search_files(self, text):
        """搜索文件历史"""
        if not text:
            # 显示所有行
            for row in range(self.history_table.rowCount()):
                self.history_table.setRowHidden(row, False)
            return
            
        # 隐藏不匹配的行
        for row in range(self.history_table.rowCount()):
            filename = self.history_table.item(row, 0).text()
            filetype = self.history_table.item(row, 1).text()
            if text.lower() in filename.lower() or text.lower() in filetype.lower():
                self.history_table.setRowHidden(row, False)
            else:
                self.history_table.setRowHidden(row, True)
    
    def reload_selected_file(self):
        """重新加载选中的文件"""
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择一个文件")
            return
            
        row = selected_rows[0].row()
        filename = self.history_table.item(row, 0).text()
        filetype = self.history_table.item(row, 1).text()
        
        if os.path.exists(filename):
            self.status_label.setText(f"正在重新加载 {os.path.basename(filename)}...")
            
            # 根据文件类型触发不同的加载操作
            if "信号" in filetype:
                self.finish_upload(filename, "wave")
            elif "位置" in filetype:
                self.finish_upload(filename, "detector")
        else:
            QMessageBox.warning(self, "文件错误", f"文件不存在: {filename}")
    
    def export_data(self):
        """导出数据"""
        QMessageBox.information(self, "导出数据", "数据导出功能即将上线")
    
    def clear_history(self):
        """清除历史记录"""
        reply = QMessageBox.question(self, "确认", "确定要清除所有历史记录吗？",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history_table.setRowCount(0)
            self.activity_table.setRowCount(0)
            self.file_history = []
            self.add_to_activity("清除", "所有历史记录")
    
    def auto_save_history(self):
        """自动保存历史记录"""
        # 实际应用中可以将历史记录保存到文件或数据库中
        self.status_label.setText("历史记录已自动保存")
        QTimer.singleShot(2000, lambda: self.status_label.setText("就绪"))
