import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from mpl_toolkits.mplot3d import Axes3D  # 导入3D绘图工具
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QGroupBox,
    QHBoxLayout, QComboBox, QSlider, QSplitter, QFrame, QSizePolicy,
    QToolButton, QGridLayout, QSpacerItem, QTabWidget, QCheckBox,
    QToolBar, QMenu, QSpinBox, QDoubleSpinBox, QRadioButton,
    QButtonGroup, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QPixmap, QAction
from Services.ssatop import normalize_data
import scipy.signal as signal
import scipy.fft as fft
import logging
import traceback

# 配置日志
logger = logging.getLogger('WaveDisplayWidget')


class WaveDisplayWidget(QWidget):
    def __init__(self):
        super().__init__()
        logger.info("初始化WaveDisplayWidget")
        
        # 定义组件
        self.init_components()
        # 设置UI样式和布局
        self.init_ui()
        self.init_layout()
        # 初始化数据
        self.current_data = None
        self.normalized_data = None
        self.fft_data = None
        self.time_axis = None
        self.freq_axis = None

    def init_components(self):
        # 控制面板组件
        self.trace_input = QLineEdit()  # 输入框
        self.display_button = QPushButton("显示波数据")  # 主按钮
        self.display_label = QLabel("波数据显示")  # 显示标签
        
        # 绘图工具
        self.fig = Figure(figsize=(8, 5), dpi=100)  # 更大的画布
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(300)
        
        # 添加matplotlib导航工具栏
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # 波形控制组件
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_label = QLabel("缩放: 100%")
        
        # 显示类型选择
        self.display_type_group = QButtonGroup(self)
        self.raw_radio = QRadioButton("原始波形")
        self.normalized_radio = QRadioButton("归一化波形")
        self.fft_radio = QRadioButton("频谱分析")
        self.spectrogram_radio = QRadioButton("时频图")
        
        self.display_type_group.addButton(self.raw_radio, 0)
        self.display_type_group.addButton(self.normalized_radio, 1)
        self.display_type_group.addButton(self.fft_radio, 2)
        self.display_type_group.addButton(self.spectrogram_radio, 3)
        self.normalized_radio.setChecked(True)  # 默认选择归一化波形
        
        # 分析参数控制
        self.window_size_spin = QSpinBox()
        self.window_size_spin.setRange(64, 4096)
        self.window_size_spin.setValue(512)
        self.window_size_spin.setSingleStep(64)
        
        # 时间范围控制
        self.start_time_spin = QDoubleSpinBox()
        self.end_time_spin = QDoubleSpinBox()
        self.start_time_spin.setRange(0, 10)
        self.end_time_spin.setRange(0, 10)
        self.start_time_spin.setValue(0)
        self.end_time_spin.setValue(5)
        self.start_time_spin.setSingleStep(0.1)
        self.end_time_spin.setSingleStep(0.1)
        
        # 显示选项
        self.grid_checkbox = QCheckBox("显示网格")
        self.grid_checkbox.setChecked(True)
        self.legend_checkbox = QCheckBox("显示图例")
        self.legend_checkbox.setChecked(True)
        
        # 分析工具按钮
        self.analyze_button = QPushButton("分析波形")
        self.save_button = QPushButton("保存图像")
        self.reset_button = QPushButton("重置视图")
        
        # 标签页组件
        self.tabs = QTabWidget()
        
        # 工具栏
        self.tools_toolbar = QToolBar("波形工具")
        self.filter_action = QAction("滤波", self)
        self.detect_peaks_action = QAction("检测峰值", self)
        self.measure_action = QAction("测量", self)
        self.tools_toolbar.addAction(self.filter_action)
        self.tools_toolbar.addAction(self.detect_peaks_action)
        self.tools_toolbar.addAction(self.measure_action)
        
        # 频谱分析画布
        self.spectrum_fig = Figure(figsize=(8, 5), dpi=100)
        self.spectrum_canvas = FigureCanvas(self.spectrum_fig)
        self.spectrum_toolbar = NavigationToolbar(self.spectrum_canvas, self)
        
        # 高级分析画布
        self.tf_fig = Figure(figsize=(8, 5), dpi=100)
        self.tf_canvas = FigureCanvas(self.tf_fig)
        self.tf_toolbar = NavigationToolbar(self.tf_canvas, self)
        
        # 初始化窗口函数和频谱类型下拉框
        self.window_combo = QComboBox()
        self.window_combo.addItems(["矩形窗", "汉宁窗", "汉明窗", "布莱克曼窗", "平顶窗"])
        
        self.spectrum_combo = QComboBox()
        self.spectrum_combo.addItems(["幅度谱", "功率谱", "相位谱"])
        
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["线性", "对数"])
        
        # 滤波器相关控件
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["低通", "高通", "带通", "带阻", "中值滤波"])
        
        self.cutoff_spin = QDoubleSpinBox()
        self.cutoff_spin.setRange(0, 1000)
        self.cutoff_spin.setValue(50)
        
        self.apply_filter_btn = QPushButton("应用滤波")

    def init_ui(self):
        # 设置整体样式
        self.setStyleSheet("""
            QWidget {
                font-family: 'Arial', 'Arial Unicode MS';
                background-color: #F5F5F5;
                color: #333;
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
                selection-background-color: #E3F2FD;
            }
            QLabel {
                color: #333;
            }
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: #ccc;
                border-left-style: solid;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QSlider {
                height: 20px;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #ccc;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1E88E5;
                border: 1px solid #1976D2;
                width: 16px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #1E88E5;
                border-radius: 4px;
            }
            QFrame#line {
                background-color: #ddd;
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
                padding: 6px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
            QDoubleSpinBox, QSpinBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton {
                spacing: 5px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        # 设置滑块初始值和范围
        self.zoom_slider.setRange(10, 500)  # 10% 到 500%
        self.zoom_slider.setValue(100)  # 默认100%
        self.zoom_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zoom_slider.setTickInterval(50)
        
        # 设置分析按钮的样式
        self.apply_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #673AB7;
                color: white;
            }
            QPushButton:hover {
                background-color: #5E35B1;
            }
        """)
        
        # 设置工具栏样式
        self.tools_toolbar.setIconSize(QSize(24, 24))

    def init_layout(self):
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # 创建标签页
        self.tabs.addTab(self.create_display_tab(), "波形显示")
        self.tabs.addTab(self.create_analysis_tab(), "频谱分析")
        self.tabs.addTab(self.create_advanced_tab(), "高级分析")
        
        # 添加标签页到主布局
        main_layout.addWidget(self.tabs)
        
        self.setLayout(main_layout)

        # 连接信号和槽
        self.display_button.clicked.connect(self.on_display_button_clicked)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        self.grid_checkbox.stateChanged.connect(self.update_display_options)
        self.legend_checkbox.stateChanged.connect(self.update_display_options)
        self.display_type_group.buttonClicked.connect(self.update_display_type)
        self.save_button.clicked.connect(self.save_figure)
        self.reset_button.clicked.connect(self.reset_view)
        self.analyze_button.clicked.connect(self.analyze_waveform)
        
    def create_display_tab(self):
        """创建波形显示标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 上部控制面板
        control_group = QGroupBox("波形控制")
        control_layout = QGridLayout()
        
        # 第一行 - 输入和显示
        control_layout.addWidget(QLabel("波数据编号:"), 0, 0)
        control_layout.addWidget(self.trace_input, 0, 1, 1, 2)
        control_layout.addWidget(self.display_button, 0, 3)
        
        # 第二行 - 显示类型选择
        display_type_layout = QHBoxLayout()
        display_type_layout.addWidget(QLabel("显示类型:"))
        display_type_layout.addWidget(self.raw_radio)
        display_type_layout.addWidget(self.normalized_radio)
        display_type_layout.addWidget(self.fft_radio)
        display_type_layout.addWidget(self.spectrogram_radio)
        display_type_layout.addStretch(1)
        control_layout.addLayout(display_type_layout, 1, 0, 1, 4)
        
        # 第三行 - 缩放控制
        control_layout.addWidget(QLabel("缩放控制:"), 2, 0)
        control_layout.addWidget(self.zoom_slider, 2, 1, 1, 2)
        control_layout.addWidget(self.zoom_label, 2, 3)
        
        # 第四行 - 显示选项
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("显示选项:"))
        options_layout.addWidget(self.grid_checkbox)
        options_layout.addWidget(self.legend_checkbox)
        options_layout.addStretch(1)
        control_layout.addLayout(options_layout, 3, 0, 1, 4)
        
        # 设置布局
        control_group.setLayout(control_layout)
        
        # 中部显示区域
        display_group = QGroupBox("波形显示")
        display_layout = QVBoxLayout()
        
        # 分析面板布局
        tools_layout = QHBoxLayout()
        tools_layout.addWidget(self.tools_toolbar)
        tools_layout.addStretch(1)
        tools_layout.addWidget(self.analyze_button)
        tools_layout.addWidget(self.save_button)
        tools_layout.addWidget(self.reset_button)
        
        # 添加图表和工具栏
        display_layout.addLayout(tools_layout)
        display_layout.addWidget(self.toolbar)
        display_layout.addWidget(self.canvas)
        display_layout.addWidget(self.display_label)
        
        display_group.setLayout(display_layout)
        
        # 添加组件到标签页布局
        layout.addWidget(control_group)
        layout.addWidget(display_group, 1)  # 波形显示区域可以伸缩
        
        tab.setLayout(layout)
        return tab
        
    def create_analysis_tab(self):
        """创建频谱分析标签页"""
        logger.info("创建频谱分析标签页")
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 频谱分析控制
        fft_control_group = QGroupBox("频谱分析控制")
        fft_layout = QGridLayout()
        
        # 窗口大小
        fft_layout.addWidget(QLabel("窗口大小:"), 0, 0)
        fft_layout.addWidget(self.window_size_spin, 0, 1)
        
        # 窗口函数选择
        window_label = QLabel("窗口函数:")
        fft_layout.addWidget(window_label, 0, 2)
        fft_layout.addWidget(self.window_combo, 0, 3)
        
        # 频谱类型
        spectrum_label = QLabel("频谱类型:")
        fft_layout.addWidget(spectrum_label, 1, 0)
        fft_layout.addWidget(self.spectrum_combo, 1, 1)
        
        # 缩放类型
        scale_label = QLabel("缩放类型:")
        fft_layout.addWidget(scale_label, 1, 2)
        fft_layout.addWidget(self.scale_combo, 1, 3)
        
        # 添加应用按钮
        apply_btn = QPushButton("应用频谱设置")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
        """)
        fft_layout.addWidget(apply_btn, 2, 3)
        
        fft_control_group.setLayout(fft_layout)
        
        # 频谱图显示区域
        spectrum_group = QGroupBox("频谱图")
        spectrum_layout = QVBoxLayout()
        
        spectrum_layout.addWidget(self.spectrum_toolbar)
        spectrum_layout.addWidget(self.spectrum_canvas)
        
        spectrum_group.setLayout(spectrum_layout)
        
        # 添加到标签页
        layout.addWidget(fft_control_group)
        layout.addWidget(spectrum_group, 1)
        
        # 连接信号
        apply_btn.clicked.connect(self.update_spectrum_display)
        
        tab.setLayout(layout)
        return tab
        
    def create_advanced_tab(self):
        """创建高级分析标签页"""
        logger.info("创建高级分析标签页")
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 高级分析控制
        advanced_control_group = QGroupBox("高级分析控制")
        advanced_layout = QGridLayout()
        
        # 时间范围控制
        advanced_layout.addWidget(QLabel("起始时间 (s):"), 0, 0)
        advanced_layout.addWidget(self.start_time_spin, 0, 1)
        advanced_layout.addWidget(QLabel("结束时间 (s):"), 0, 2)
        advanced_layout.addWidget(self.end_time_spin, 0, 3)
        
        # 时间范围快捷按钮
        time_buttons_layout = QHBoxLayout()
        
        full_range_btn = QPushButton("全部")
        full_range_btn.setToolTip("显示全部时间范围")
        full_range_btn.clicked.connect(self.set_full_time_range)
        
        first_5s_btn = QPushButton("前5秒")
        first_5s_btn.setToolTip("显示前5秒")
        first_5s_btn.clicked.connect(lambda: self.set_time_range(0, 5))
        
        mid_5s_btn = QPushButton("中间5秒")
        mid_5s_btn.setToolTip("显示中间5秒")
        mid_5s_btn.clicked.connect(self.set_middle_time_range)
        
        last_5s_btn = QPushButton("后5秒")
        last_5s_btn.setToolTip("显示后5秒")
        last_5s_btn.clicked.connect(self.set_last_time_range)
        
        time_buttons_layout.addWidget(full_range_btn)
        time_buttons_layout.addWidget(first_5s_btn)
        time_buttons_layout.addWidget(mid_5s_btn)
        time_buttons_layout.addWidget(last_5s_btn)
        
        advanced_layout.addLayout(time_buttons_layout, 1, 0, 1, 4)
        
        # 滤波器设置
        filter_label = QLabel("滤波器类型:")
        advanced_layout.addWidget(filter_label, 2, 0)
        advanced_layout.addWidget(self.filter_combo, 2, 1)
        
        # 滤波器参数
        cutoff_label = QLabel("截止频率 (Hz):")
        advanced_layout.addWidget(cutoff_label, 2, 2)
        advanced_layout.addWidget(self.cutoff_spin, 2, 3)
        
        # 应用滤波按钮
        advanced_layout.addWidget(self.apply_filter_btn, 3, 3)
        
        advanced_control_group.setLayout(advanced_layout)
        
        # 时频分析区域
        tf_group = QGroupBox("时频分析")
        tf_layout = QVBoxLayout()
        
        tf_layout.addWidget(self.tf_toolbar)
        tf_layout.addWidget(self.tf_canvas)
        
        tf_group.setLayout(tf_layout)
        
        # 添加到标签页
        layout.addWidget(advanced_control_group)
        layout.addWidget(tf_group, 1)
        
        # 连接信号
        self.apply_filter_btn.clicked.connect(self.apply_filter)
        
        tab.setLayout(layout)
        return tab

    def show_wave_data(self, sample_count, sample_interval, trace_number, wave_data, time_data):
        """
        显示波数据及归一化后的波形图
        """
        # 保存数据
        self.current_data = wave_data
        self.normalized_data = normalize_data(wave_data)
        self.time_axis = np.arange(sample_count) * sample_interval
        
        # 计算频谱
        self.compute_fft()
        
        # 显示波数据详情
        self.display_label.setText(
            f"<b>波数据详情</b><br>"
            f"------------------------------------------------------------<br>"
            f"<b>波数据编号</b>: {trace_number}<br>"
            f"<b>数据点个数</b>: {len(wave_data)} <br>"
            f"<b>采样间隔</b>: {sample_interval:.6f} s<br>"
            f"<b>采样频率</b>: {1/sample_interval:.2f} Hz<br>"
            f"<b>波形总时长</b>: {sample_count * sample_interval:.3f} s<br>"
            f"<b>微地震预测发生区间</b>：{time_data['start']:.3f}s ~ {time_data['end']:.3f}s<br>"
            f"------------------------------------------------------------"
        )

        # 更新时间范围控件
        max_time = sample_count * sample_interval
        logger.info(f"更新时间范围: 0 - {max_time} s")
        
        # 设置起始和结束时间的范围
        self.start_time_spin.setRange(0, max_time)
        self.end_time_spin.setRange(0, max_time)
        
        # 设置默认值
        self.start_time_spin.setValue(0)
        self.end_time_spin.setValue(min(5, max_time))  # 默认显示前5秒或全部（如果小于5秒）
        
        # 更新步长为总时长的1%，方便微调
        step_size = max(0.01, max_time / 100)
        self.start_time_spin.setSingleStep(step_size)
        self.end_time_spin.setSingleStep(step_size)

        # 更新显示
        self.update_display_type()
        
    def compute_fft(self):
        """计算频谱"""
        if self.current_data is None:
            return
            
        # 计算FFT
        n = len(self.current_data)
        self.fft_data = np.abs(fft.fft(self.current_data))
        self.fft_data = self.fft_data[:n//2]  # 只取一半（实数信号的频谱是对称的）
        
        # 计算频率轴
        if self.time_axis is not None:
            sample_rate = 1 / (self.time_axis[1] - self.time_axis[0])
            self.freq_axis = np.linspace(0, sample_rate/2, n//2)
    
    def update_display_type(self):
        """根据选择的显示类型更新图表"""
        if self.current_data is None:
            return
            
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        
        # 根据选择的显示类型绘制不同的图
        if self.raw_radio.isChecked():
            # 原始波形
            ax.plot(self.time_axis, self.current_data, 'b-', label='原始波形')
            ax.set_title('原始波形数据')
            ax.set_xlabel('时间 (s)')
            ax.set_ylabel('振幅')
            
        elif self.normalized_radio.isChecked():
            # 归一化波形
            ax.plot(self.time_axis, self.normalized_data, 'g-', label='归一化波形')
            ax.set_title('归一化波形数据')
            ax.set_xlabel('时间 (s)')
            ax.set_ylabel('归一化振幅')
            
        elif self.fft_radio.isChecked():
            # 频谱分析
            if self.freq_axis is not None and self.fft_data is not None:
                ax.plot(self.freq_axis, self.fft_data, 'r-', label='频谱')
                ax.set_title('频谱分析')
                ax.set_xlabel('频率 (Hz)')
                ax.set_ylabel('幅度')
                ax.set_xlim(0, min(500, max(self.freq_axis)))  # 限制显示范围
                
        elif self.spectrogram_radio.isChecked():
            # 时频图
            if self.current_data is not None and self.time_axis is not None:
                # 计算并绘制时频图
                sample_rate = 1 / (self.time_axis[1] - self.time_axis[0])
                ax.specgram(self.current_data, NFFT=256, Fs=sample_rate, 
                           noverlap=128, cmap='viridis')
                ax.set_title('时频分析')
                ax.set_xlabel('时间 (s)')
                ax.set_ylabel('频率 (Hz)')
                self.fig.colorbar(ax.images[0], ax=ax, label='功率/频率 (dB/Hz)')
        
        # 更新显示选项
        self.update_display_options()
        
        # 绘制图表
        self.canvas.draw()
    
    def update_zoom(self, value):
        """更新缩放级别"""
        zoom_percent = value
        self.zoom_label.setText(f"缩放: {zoom_percent}%")
        
        # 实际缩放操作
        if hasattr(self, 'fig') and self.fig.axes:
            ax = self.fig.axes[0]

            # 计算新的y轴范围
            if self.normalized_data is not None:
                y_range = np.max(np.abs(self.normalized_data))
                y_scale = 100 / zoom_percent
                ax.set_ylim(-y_range * y_scale, y_range * y_scale)
                self.canvas.draw()
    
    def update_display_options(self):
        """更新显示选项"""
        if hasattr(self, 'fig') and self.fig.axes:
            ax = self.fig.axes[0]
            
            # 网格显示
            ax.grid(self.grid_checkbox.isChecked())
            
            # 图例显示
            if self.legend_checkbox.isChecked():
                ax.legend()
            else:
                if ax.get_legend():
                    ax.get_legend().remove()
            
            self.canvas.draw()
    
    def on_display_button_clicked(self):
        """显示按钮点击处理"""
        trace_number = self.trace_input.text()
        if not trace_number:
            return
            
        try:
            trace_number = int(trace_number)
            # 这里应该调用控制器来获取数据
            # 现在只是模拟一些数据
            sample_count = 1000
            sample_interval = 0.001
            wave_data = np.sin(2 * np.pi * 10 * np.arange(sample_count) * sample_interval) + \
                       0.5 * np.sin(2 * np.pi * 50 * np.arange(sample_count) * sample_interval) + \
                       0.3 * np.random.randn(sample_count)
            time_data = {'start': 0.2, 'end': 0.8}
            
            self.show_wave_data(sample_count, sample_interval, trace_number, wave_data, time_data)
        except ValueError:
            self.display_label.setText("请输入有效的波数据编号")
    
    def save_figure(self):
        """保存图像"""
        if not hasattr(self, 'fig'):
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "", "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)")
            
        if file_path:
            self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, "保存成功", f"图像已保存至: {file_path}")
    
    def reset_view(self):
        """重置视图"""
        if hasattr(self, 'fig') and self.fig.axes:
            ax = self.fig.axes[0]
            ax.relim()
            ax.autoscale()
            self.zoom_slider.setValue(100)
            self.canvas.draw()
    
    def analyze_waveform(self):
        """分析波形"""
        logger.info("执行analyze_waveform")
        if self.current_data is None:
            logger.warning("当前没有加载波数据")
            QMessageBox.warning(self, "警告", "请先加载波形数据！")
            return
            
        try:
            # 切换到频谱分析标签页
            logger.info("切换到频谱分析标签页")
            self.tabs.setCurrentIndex(1)
            
            # 计算频谱并显示
            logger.info("调用update_spectrum_display")
            self.update_spectrum_display()
        except Exception as e:
            # 显示详细错误
            error_msg = f"分析波形时出错: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", error_msg)
            
    def update_spectrum_display(self):
        """更新频谱显示"""
        logger.info("执行update_spectrum_display")
        if self.current_data is None:
            logger.warning("当前没有加载波数据")
            QMessageBox.warning(self, "警告", "请先加载波形数据！")
            return
            
        try:
            # 获取参数
            window_size = self.window_size_spin.value()
            window_type = self.window_combo.currentText()
            spectrum_type = self.spectrum_combo.currentText()
            scale_type = self.scale_combo.currentText()
            
            logger.info(f"频谱参数: 窗口大小={window_size}, 窗口类型={window_type}, " 
                       f"频谱类型={spectrum_type}, 缩放类型={scale_type}")
            
            # 清除现有图表
            self.spectrum_fig.clear()
            ax = self.spectrum_fig.add_subplot(111)
            
            # 应用窗口函数
            logger.info("应用窗口函数")
            window_dict = {
                "矩形窗": 'boxcar',
                "汉宁窗": 'hann',
                "汉明窗": 'hamming',
                "布莱克曼窗": 'blackman',
                "平顶窗": 'flattop'
            }
            window = signal.get_window(window_dict[window_type], min(window_size, len(self.current_data)))
            
            # 计算频谱
            if len(self.current_data) >= window_size:
                logger.info(f"计算频谱，数据长度={len(self.current_data)}")
                # 采样率
                sample_rate = 1 / (self.time_axis[1] - self.time_axis[0])
                logger.info(f"采样率: {sample_rate} Hz")
                
                # 计算频谱
                if spectrum_type == "幅度谱":
                    logger.info("计算幅度谱")
                    f, Pxx = signal.welch(self.current_data, fs=sample_rate, window=window,
                                         nperseg=window_size, scaling='spectrum')
                    Pxx = np.sqrt(Pxx)  # 取平方根得到幅度谱
                    ylabel = "幅度"
                elif spectrum_type == "功率谱":
                    logger.info("计算功率谱")
                    f, Pxx = signal.welch(self.current_data, fs=sample_rate, window=window,
                                         nperseg=window_size)
                    ylabel = "功率密度 (V²/Hz)"
                else:  # 相位谱
                    logger.info("计算相位谱")
                    f = np.fft.rfftfreq(window_size, d=1/sample_rate)
                    Pxx = np.angle(np.fft.rfft(self.current_data[:window_size] * window))
                    ylabel = "相位 (rad)"
                
                # 绘制频谱
                logger.info("绘制频谱")
                if scale_type == "线性":
                    ax.plot(f, Pxx, 'r-', linewidth=1.5)
                else:  # 对数
                    if spectrum_type != "相位谱":  # 相位谱不能取对数
                        ax.semilogy(f, Pxx, 'r-', linewidth=1.5)
                    else:
                        ax.plot(f, Pxx, 'r-', linewidth=1.5)
                
                ax.set_title(f'{spectrum_type} - {window_type}')
                ax.set_xlabel('频率 (Hz)')
                ax.set_ylabel(ylabel)
                ax.grid(True, linestyle='--', alpha=0.7)
                
                # 添加频谱特征信息
                max_idx = np.argmax(Pxx)
                peak_freq = f[max_idx]
                peak_value = Pxx[max_idx]
                
                logger.info(f"峰值频率: {peak_freq} Hz, 峰值: {peak_value}")
                
                if spectrum_type != "相位谱":
                    ax.axvline(x=peak_freq, color='g', linestyle='--', alpha=0.7)
                    ax.text(0.95, 0.95, f"峰值频率: {peak_freq:.2f} Hz\n峰值: {peak_value:.4f}",
                           verticalalignment='top', horizontalalignment='right',
                           transform=ax.transAxes, bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
                
                # 优化布局
                self.spectrum_fig.tight_layout()
                logger.info("更新canvas显示")
                self.spectrum_canvas.draw()
                
            else:
                error_msg = f"数据长度({len(self.current_data)})小于窗口大小({window_size})!"
                logger.warning(error_msg)
                QMessageBox.warning(self, "警告", error_msg)
                
        except Exception as e:
            error_msg = f"计算频谱时出错: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            QMessageBox.warning(self, "警告", error_msg)
    
    def apply_filter(self):
        """应用滤波器"""
        logger.info("执行apply_filter")
        if self.current_data is None:
            logger.warning("当前没有加载波数据")
            QMessageBox.warning(self, "警告", "请先加载波形数据！")
            return
            
        try:
            # 获取参数
            filter_type = self.filter_combo.currentText()
            cutoff = self.cutoff_spin.value()
            start_time = self.start_time_spin.value()
            end_time = self.end_time_spin.value()
            
            # 验证时间范围
            if start_time >= end_time:
                error_msg = "起始时间必须小于结束时间！"
                logger.warning(error_msg)
                QMessageBox.warning(self, "警告", error_msg)
                return
                
            max_time = len(self.current_data) * (self.time_axis[1] - self.time_axis[0])
            if end_time > max_time:
                end_time = max_time
                self.end_time_spin.setValue(end_time)
                logger.warning(f"结束时间超出范围，已调整为最大值: {max_time}s")
            
            logger.info(f"滤波参数: 滤波类型={filter_type}, 截止频率={cutoff} Hz, " 
                       f"时间范围={start_time}s - {end_time}s")
            
            # 计算起始和结束索引
            sample_interval = self.time_axis[1] - self.time_axis[0]
            start_idx = max(0, int(start_time / sample_interval))
            end_idx = min(len(self.current_data), int(end_time / sample_interval))
            
            # 确保有足够的数据点用于滤波
            if end_idx - start_idx < 10:
                error_msg = "选择的时间范围太小，请选择更大的时间范围！"
                logger.warning(error_msg)
                QMessageBox.warning(self, "警告", error_msg)
                return
            
            logger.info(f"数据范围索引: {start_idx} - {end_idx}, 数据长度: {end_idx - start_idx}")
            
            # 获取需要处理的数据段
            data_segment = self.current_data[start_idx:end_idx]
            time_segment = self.time_axis[start_idx:end_idx]
            
            # 采样率
            sample_rate = 1 / sample_interval
            logger.info(f"采样率: {sample_rate} Hz")
            
            # 应用滤波器
            filtered_data = None
            nyq = 0.5 * sample_rate  # 奈奎斯特频率
            
            if filter_type == "低通":
                logger.info(f"应用低通滤波器, 截止频率: {cutoff} Hz")
                b, a = signal.butter(4, cutoff/nyq, btype='low')
                filtered_data = signal.filtfilt(b, a, data_segment)
            elif filter_type == "高通":
                logger.info(f"应用高通滤波器, 截止频率: {cutoff} Hz")
                b, a = signal.butter(4, cutoff/nyq, btype='high')
                filtered_data = signal.filtfilt(b, a, data_segment)
            elif filter_type == "带通":
                # 带通需要两个截止频率，这里简化处理
                low_cutoff = max(1, cutoff - 10)
                high_cutoff = cutoff + 10
                logger.info(f"应用带通滤波器, 截止频率: {low_cutoff}-{high_cutoff} Hz")
                b, a = signal.butter(4, [low_cutoff/nyq, high_cutoff/nyq], btype='band')
                filtered_data = signal.filtfilt(b, a, data_segment)
            elif filter_type == "带阻":
                # 带阻需要两个截止频率，这里简化处理
                low_cutoff = max(1, cutoff - 10)
                high_cutoff = cutoff + 10
                logger.info(f"应用带阻滤波器, 截止频率: {low_cutoff}-{high_cutoff} Hz")
                b, a = signal.butter(4, [low_cutoff/nyq, high_cutoff/nyq], btype='bandstop')
                filtered_data = signal.filtfilt(b, a, data_segment)
            else:  # 中值滤波
                kernel_size = int(min(51, len(data_segment) / 10))
                # 确保kernel_size是奇数
                if kernel_size % 2 == 0:
                    kernel_size += 1
                logger.info(f"应用中值滤波, 核大小: {kernel_size}")
                filtered_data = signal.medfilt(data_segment, kernel_size)
            
            # 清除图表并绘制结果
            logger.info("清除图表并绘制结果")
            self.tf_fig.clear()
            
            # 创建2x1图表布局
            ax1 = self.tf_fig.add_subplot(211)
            ax2 = self.tf_fig.add_subplot(212)
            
            # 绘制原始数据
            logger.info("绘制原始数据")
            ax1.plot(time_segment, data_segment, 'b-', label='原始数据')
            ax1.set_title(f'原始数据 ({start_time:.2f}s - {end_time:.2f}s)')
            ax1.set_ylabel('振幅')
            ax1.grid(True, linestyle='--', alpha=0.7)
            ax1.legend()
            
            # 绘制滤波后的数据
            logger.info("绘制滤波后的数据")
            ax2.plot(time_segment, filtered_data, 'r-', label='滤波后数据')
            ax2.set_title(f'{filter_type} (截止频率: {cutoff} Hz)')
            ax2.set_xlabel('时间 (s)')
            ax2.set_ylabel('振幅')
            ax2.grid(True, linestyle='--', alpha=0.7)
            ax2.legend()
            
            # 优化布局
            self.tf_fig.tight_layout()
            logger.info("更新canvas显示")
            self.tf_canvas.draw()
            
        except Exception as e:
            error_msg = f"应用滤波器时出错: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            QMessageBox.warning(self, "警告", error_msg)

    def set_full_time_range(self):
        """设置为全部时间范围"""
        if self.time_axis is None:
            return
        
        max_time = len(self.current_data) * (self.time_axis[1] - self.time_axis[0])
        self.start_time_spin.setValue(0)
        self.end_time_spin.setValue(max_time)
        logger.info(f"设置时间范围: 0 - {max_time}s")
        
    def set_time_range(self, start, end):
        """设置指定的时间范围"""
        if self.time_axis is None:
            return
            
        max_time = len(self.current_data) * (self.time_axis[1] - self.time_axis[0])
        
        # 确保范围在有效范围内
        start = max(0, min(start, max_time))
        end = max(0, min(end, max_time))
        
        if start >= end:
            return
            
        self.start_time_spin.setValue(start)
        self.end_time_spin.setValue(end)
        logger.info(f"设置时间范围: {start} - {end}s")
        
    def set_middle_time_range(self):
        """设置为中间5秒"""
        if self.time_axis is None:
            return
            
        max_time = len(self.current_data) * (self.time_axis[1] - self.time_axis[0])
        
        if max_time <= 5:
            self.set_full_time_range()
            return
            
        mid_point = max_time / 2
        start = max(0, mid_point - 2.5)
        end = min(max_time, mid_point + 2.5)
        
        self.set_time_range(start, end)
        
    def set_last_time_range(self):
        """设置为最后5秒"""
        if self.time_axis is None:
            return
            
        max_time = len(self.current_data) * (self.time_axis[1] - self.time_axis[0])
        
        if max_time <= 5:
            self.set_full_time_range()
            return
            
        start = max(0, max_time - 5)
        
        self.set_time_range(start, max_time)
