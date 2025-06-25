from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox, QComboBox,
    QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QIcon, QFont, QColor

class BatchProcessingWidget(QWidget):
    """批量处理文件的界面"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化组件
        self.init_components()
        
        # 设置UI样式
        self.init_ui()
        
        # 设置布局
        self.init_layout()
        
    def init_components(self):
        """初始化界面组件"""
        # 文件操作按钮
        self.add_files_btn = QPushButton("添加文件")
        self.remove_files_btn = QPushButton("移除选中")
        self.clear_files_btn = QPushButton("清空列表")
        
        # 文件列表表格
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(["波形文件", "检波器文件", "状态", "进度"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # 处理参数设置
        self.param_group = QGroupBox("处理参数")
        
        # 网格精度选择
        self.grid_precision_label = QLabel("网格精度:")
        self.grid_precision_combo = QComboBox()
        self.grid_precision_combo.addItems(["低", "中", "高"])
        self.grid_precision_combo.setCurrentIndex(1)  # 默认中等精度
        
        # 算法参数设置
        self.population_label = QLabel("种群大小:")
        self.population_combo = QComboBox()
        self.population_combo.addItems(["100", "200", "300", "500"])
        self.population_combo.setCurrentIndex(2)  # 默认300
        
        self.iterations_label = QLabel("迭代次数:")
        self.iterations_combo = QComboBox()
        self.iterations_combo.addItems(["10", "20", "50", "100"])
        self.iterations_combo.setCurrentIndex(1)  # 默认20
        
        self.mutation_label = QLabel("变异率:")
        self.mutation_combo = QComboBox()
        self.mutation_combo.addItems(["0.1", "0.2", "0.3", "0.5"])
        self.mutation_combo.setCurrentIndex(1)  # 默认0.2
        
        # 批量处理按钮
        self.start_batch_btn = QPushButton("开始批量处理")
        self.stop_batch_btn = QPushButton("停止处理")
        self.stop_batch_btn.setEnabled(False)
        
        # 总体进度
        self.overall_progress_label = QLabel("总体进度:")
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setRange(0, 100)
        self.overall_progress_bar.setValue(0)
        
        # 状态信息标签
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setBold(True)
        self.status_label.setFont(font)
        
        # 处理结果
        self.result_group = QGroupBox("处理结果")
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["文件名", "X坐标", "Y坐标", "Z坐标", "亮度"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # 导出按钮
        self.export_results_btn = QPushButton("导出结果")
        self.export_results_btn.setEnabled(False)
    
    def init_ui(self):
        """设置UI样式"""
        # 设置按钮样式
        button_style = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        
        self.add_files_btn.setStyleSheet(button_style)
        self.remove_files_btn.setStyleSheet(button_style)
        self.clear_files_btn.setStyleSheet(button_style)
        self.start_batch_btn.setStyleSheet(button_style)
        self.export_results_btn.setStyleSheet(button_style)
        
        self.stop_batch_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        # 设置表格样式
        table_style = """
            QTableWidget {
                border: 1px solid #ddd;
                gridline-color: #ddd;
                background-color: white;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #f2f2f2;
                padding: 6px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """
        
        self.files_table.setStyleSheet(table_style)
        self.result_table.setStyleSheet(table_style)
        
        # 设置进度条样式
        self.overall_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        
        # 设置分组框样式
        group_style = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        
        self.param_group.setStyleSheet(group_style)
        self.result_group.setStyleSheet(group_style)
    
    def init_layout(self):
        """设置布局"""
        main_layout = QVBoxLayout()
        
        # 文件操作区域
        file_ops_layout = QHBoxLayout()
        file_ops_layout.addWidget(self.add_files_btn)
        file_ops_layout.addWidget(self.remove_files_btn)
        file_ops_layout.addWidget(self.clear_files_btn)
        file_ops_layout.addStretch()
        
        main_layout.addLayout(file_ops_layout)
        main_layout.addWidget(self.files_table)
        
        # 参数设置区域
        param_layout = QVBoxLayout()
        
        grid_layout = QHBoxLayout()
        grid_layout.addWidget(self.grid_precision_label)
        grid_layout.addWidget(self.grid_precision_combo)
        grid_layout.addStretch()
        
        algo_layout = QHBoxLayout()
        algo_layout.addWidget(self.population_label)
        algo_layout.addWidget(self.population_combo)
        algo_layout.addWidget(self.iterations_label)
        algo_layout.addWidget(self.iterations_combo)
        algo_layout.addWidget(self.mutation_label)
        algo_layout.addWidget(self.mutation_combo)
        algo_layout.addStretch()
        
        param_layout.addLayout(grid_layout)
        param_layout.addLayout(algo_layout)
        
        self.param_group.setLayout(param_layout)
        main_layout.addWidget(self.param_group)
        
        # 处理控制区域
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.start_batch_btn)
        control_layout.addWidget(self.stop_batch_btn)
        control_layout.addStretch()
        
        main_layout.addLayout(control_layout)
        
        # 进度显示区域
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.overall_progress_label)
        progress_layout.addWidget(self.overall_progress_bar)
        
        main_layout.addLayout(progress_layout)
        
        # 添加状态信息标签
        main_layout.addWidget(self.status_label)
        
        # 结果区域
        result_layout = QVBoxLayout()
        result_layout.addWidget(self.result_table)
        
        result_btn_layout = QHBoxLayout()
        result_btn_layout.addStretch()
        result_btn_layout.addWidget(self.export_results_btn)
        
        result_layout.addLayout(result_btn_layout)
        
        self.result_group.setLayout(result_layout)
        main_layout.addWidget(self.result_group)
        
        self.setLayout(main_layout)
    
    @pyqtSlot(str, str)
    def add_file_pair(self, wave_file, location_file):
        """添加文件对到表格中"""
        row_position = self.files_table.rowCount()
        self.files_table.insertRow(row_position)
        
        self.files_table.setItem(row_position, 0, QTableWidgetItem(wave_file))
        self.files_table.setItem(row_position, 1, QTableWidgetItem(location_file))
        self.files_table.setItem(row_position, 2, QTableWidgetItem("等待处理"))
        
        # 添加进度条
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        
        self.files_table.setCellWidget(row_position, 3, progress_bar)
    
    @pyqtSlot(int, str)
    def update_file_status(self, row, status):
        """更新文件状态"""
        if 0 <= row < self.files_table.rowCount():
            self.files_table.setItem(row, 2, QTableWidgetItem(status))
    
    @pyqtSlot(int, int)
    def update_file_progress(self, row, progress):
        """更新文件处理进度"""
        if 0 <= row < self.files_table.rowCount():
            progress_bar = self.files_table.cellWidget(row, 3)
            if progress_bar:
                progress_bar.setValue(progress)
    
    @pyqtSlot(str, float, float, float, float)
    def add_result(self, filename, x, y, z, brightness):
        """添加处理结果到结果表格"""
        row_position = self.result_table.rowCount()
        self.result_table.insertRow(row_position)
        
        self.result_table.setItem(row_position, 0, QTableWidgetItem(filename))
        self.result_table.setItem(row_position, 1, QTableWidgetItem(str(round(x, 2))))
        self.result_table.setItem(row_position, 2, QTableWidgetItem(str(round(y, 2))))
        self.result_table.setItem(row_position, 3, QTableWidgetItem(str(round(z, 2))))
        self.result_table.setItem(row_position, 4, QTableWidgetItem(str(round(brightness, 4))))
    
    @pyqtSlot()
    def clear_results(self):
        """清空结果表格"""
        self.result_table.setRowCount(0)
    
    @pyqtSlot(int)
    def update_overall_progress(self, progress):
        """更新总体进度"""
        self.overall_progress_bar.setValue(progress)
    
    @pyqtSlot(str)
    def update_status_text(self, text):
        """更新状态文本"""
        self.status_label.setText(text) 