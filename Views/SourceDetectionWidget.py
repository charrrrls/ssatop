import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from mpl_toolkits.mplot3d import Axes3D
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QGroupBox, QScrollArea,
    QHBoxLayout, QGridLayout, QFrame, QProgressBar, QSplitter, 
    QTabWidget, QComboBox, QCheckBox, QSpacerItem, QSizePolicy,
    QToolBar, QDoubleSpinBox, QRadioButton, QButtonGroup, QFileDialog,
    QMessageBox, QSlider, QToolButton
)
from PyQt6.QtCore import Qt, QSize, pyqtSlot, pyqtSignal, QTimer, QCoreApplication
from PyQt6.QtGui import QIcon, QFont, QColor, QAction
import time

class SourceDetectionWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # 初始化组件
        self.init_components()
        
        # 设置UI样式
        self.init_ui()
        
        # 设置布局
        self.init_layout()

    def init_components(self):
        # 基本控制按钮
        self.display_btn = QPushButton("显示源位置")
        self.heatmap_btn = QPushButton("计算亮度热图")
        self.export_btn = QPushButton("导出结果")
        self.reset_btn = QPushButton("重置视图")
        
        # 进度指示组件
        self.progress_bar = QProgressBar()
        self.time_label = QLabel("预计时间: --:--")
        self.progress_label = QLabel("当前进度: 等待操作...")
        
        # 可视化选项
        self.view_mode_group = QButtonGroup(self)
        self.view_3d_radio = QRadioButton("3D视图")
        self.view_heatmap_radio = QRadioButton("热力图")
        self.view_slice_radio = QRadioButton("切片图")
        self.view_mode_group.addButton(self.view_3d_radio, 0)
        self.view_mode_group.addButton(self.view_heatmap_radio, 1)
        self.view_mode_group.addButton(self.view_slice_radio, 2)
        self.view_3d_radio.setChecked(True)
        
        # 显示选项
        self.show_detector_checkbox = QCheckBox("显示检波器位置")
        self.show_detector_checkbox.setChecked(True)
        self.show_grid_checkbox = QCheckBox("显示网格")
        self.show_grid_checkbox.setChecked(True)
        self.show_colorbar_checkbox = QCheckBox("显示颜色条")
        self.show_colorbar_checkbox.setChecked(True)
        
        # 颜色方案选择
        self.colormap_label = QLabel("颜色方案:")
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["viridis", "plasma", "inferno", "magma", "jet", "rainbow", "coolwarm"])
        
        # 分辨率控制
        self.resolution_label = QLabel("显示分辨率:")
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["低", "中", "高", "超高"])
        self.resolution_combo.setCurrentIndex(3)  # 默认为中等分辨率
        
        # 切片控制
        self.slice_label = QLabel("切片位置: 50%")
        self.slice_slider = QSlider(Qt.Orientation.Horizontal)
        self.slice_slider.setRange(0, 100)
        self.slice_slider.setValue(50)
        
        # 精简后的网格设置控件
        self.grid_group = QGroupBox("计算参数")
        self.grid_resolution_label = QLabel("网格精度:")
        self.grid_resolution_combo = QComboBox()
        self.grid_resolution_combo.addItems(["低", "中", "高"])
        self.grid_resolution_combo.setCurrentIndex(1)
        self.grid_resolution_combo.setToolTip("低精度计算速度快，高精度结果更准确")
        
        self.use_genetic_checkbox = QCheckBox("使用遗传算法")
        self.use_genetic_checkbox.setChecked(True)
        self.use_genetic_checkbox.setToolTip("遗传算法通常能找到更准确的源位置，但计算时间可能更长")
        
        # 结果显示
        self.display_label = QLabel("检测源位置")
        self.display_label.setWordWrap(True)
        
        # 可视化画布和工具栏
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # 工具栏
        self.tools_toolbar = QToolBar("分析工具")
        self.zoom_action = QAction("缩放", self)
        self.measure_action = QAction("测量", self)
        self.annotate_action = QAction("标注", self)
        self.tools_toolbar.addAction(self.zoom_action)
        self.tools_toolbar.addAction(self.measure_action)
        self.tools_toolbar.addAction(self.annotate_action)
        
        # 标签信息
        self.frontground_label = QLabel("预计时间区间", self)
        
        # 选项卡组件
        self.result_tabs = QTabWidget()
        
        # 结果显示面板
        self.result_text = QLabel("尚未开始计算...")
        self.result_text.setWordWrap(True)

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
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 1px;
            }
            QLabel {
                color: #333;
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
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
        """)
        
        # 设置组件样式
        self.display_label.setStyleSheet("""
            background-color: #ECEFF1;
            border-radius: 4px;
            padding: 15px;
            font-family: 'Courier New', monospace;
        """)
        
        self.result_text.setStyleSheet("""
            background-color: #ECEFF1;
            border-radius: 4px;
            padding: 15px;
            font-family: 'Courier New', monospace;
        """)
        
        # 设置按钮的特殊样式
        self.heatmap_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #EF6C00;
            }
        """)
        
        # 进度条样式
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                height: 20px;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        
        # 设置进度指示相关组件
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # 标签样式
        self.frontground_label.setStyleSheet("""
            font-size: 14px;
            padding: 10px;
            width: 100%;
        """)
        self.frontground_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 按钮大小
        self.display_btn.setMinimumHeight(40)
        self.heatmap_btn.setMinimumHeight(40)

    def init_layout(self):
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        
        # 顶部控制按钮区域
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.display_btn)
        control_layout.addWidget(self.heatmap_btn)
        control_layout.addWidget(self.export_btn)
        control_layout.addWidget(self.reset_btn)
        
        main_layout.addLayout(control_layout)
        
        # 进度指示器区域
        progress_layout = QHBoxLayout()
        
        progress_group = QGroupBox("计算进度")
        progress_inner_layout = QVBoxLayout()
        progress_inner_layout.addWidget(self.progress_label)
        progress_inner_layout.addWidget(self.progress_bar)
        progress_inner_layout.addWidget(self.time_label)
        progress_inner_layout.addWidget(self.frontground_label)
        progress_group.setLayout(progress_inner_layout)
        
        progress_layout.addWidget(progress_group)
        
        main_layout.addLayout(progress_layout)
        
        # 选项区域
        options_layout = QHBoxLayout()
        
        # 显示选项组
        display_group = QGroupBox("显示选项")
        display_layout = QVBoxLayout()
        
        # 视图模式选项
        view_mode_layout = QVBoxLayout()
        view_mode_layout.addWidget(self.view_3d_radio)
        view_mode_layout.addWidget(self.view_heatmap_radio)
        view_mode_layout.addWidget(self.view_slice_radio)
        display_layout.addLayout(view_mode_layout)
        
        # 显示选项复选框
        display_layout.addWidget(self.show_detector_checkbox)
        display_layout.addWidget(self.show_grid_checkbox)
        display_layout.addWidget(self.show_colorbar_checkbox)
        
        # 颜色方案选择
        colormap_layout = QHBoxLayout()
        colormap_layout.addWidget(self.colormap_label)
        colormap_layout.addWidget(self.colormap_combo)
        display_layout.addLayout(colormap_layout)
        
        # 分辨率选择
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(self.resolution_label)
        resolution_layout.addWidget(self.resolution_combo)
        display_layout.addLayout(resolution_layout)
        
        # 切片控制
        slice_layout = QVBoxLayout()
        slice_layout.addWidget(self.slice_label)
        slice_layout.addWidget(self.slice_slider)
        
        display_layout.addLayout(slice_layout)
        
        display_group.setLayout(display_layout)
        options_layout.addWidget(display_group)
        
        # 添加精简后的计算参数组
        grid_settings_layout = QVBoxLayout()
        self.grid_group.setLayout(grid_settings_layout)
        
        # 添加网格精度选择
        grid_resolution_layout = QHBoxLayout()
        grid_resolution_layout.addWidget(self.grid_resolution_label)
        grid_resolution_layout.addWidget(self.grid_resolution_combo)
        grid_settings_layout.addLayout(grid_resolution_layout)
        
        # 添加遗传算法复选框
        grid_settings_layout.addWidget(self.use_genetic_checkbox)
        
        options_layout.addWidget(self.grid_group)
        
        # 结果显示组
        result_group = QGroupBox("结果")
        result_layout = QVBoxLayout()
        
        # 添加结果标签页
        result_text_tab = QWidget()
        result_text_layout = QVBoxLayout(result_text_tab)
        result_text_layout.addWidget(self.result_text)
        
        visual_tab = QWidget()
        visual_layout = QVBoxLayout(visual_tab)
        visual_layout.addWidget(self.toolbar)
        visual_layout.addWidget(self.canvas)
        
        self.result_tabs.addTab(result_text_tab, "文本结果")
        self.result_tabs.addTab(visual_tab, "可视化")
        
        result_layout.addWidget(self.result_tabs)
        result_group.setLayout(result_layout)
        
        main_layout.addLayout(options_layout)
        main_layout.addWidget(result_group, 1)  # 结果区域可伸展
        
        self.setLayout(main_layout)

    @pyqtSlot(list, float, bool)
    def show_source_location(self, max_point, max_br, is_over=True):
        # 准备数据和统计信息
        # 确保进度相关控件在计算过程中保持可见
        if not is_over:
            # 如果是实时更新且进度条不可见，则重新显示进度条
            if not self.progress_bar.isVisible():
                self.progress_bar.setVisible(True)
                self.time_label.setVisible(True)
                self.progress_label.setVisible(True)
                self.frontground_label.setVisible(True)
        try:
            # 坐标精度转换 - 添加不同精度的表示
            x_value = max_point[0]
            y_value = max_point[1]
            z_value = max_point[2]
            t_value = max_point[3]
            
            # 科学计数法显示
            x_sci = f"{x_value:.6e}"
            y_sci = f"{y_value:.6e}"
            z_sci = f"{z_value:.6e}"
            
            # 相对位置计算 (假设基于检波器中心)
            detector_data = None
            rel_position = ["未知", "未知", "未知"]
            try:
                from Models.TraceFile import TraceFile
                trace_file = TraceFile()
                detector_data = trace_file.get_detector_location()
                if detector_data is not None:
                    # 计算检波器阵列中心
                    center_x = detector_data['x'].mean()
                    center_y = detector_data['y'].mean()
                    center_z = detector_data['z'].mean()
                    
                    # 计算相对位置
                    rel_x = x_value - center_x
                    rel_y = y_value - center_y
                    rel_z = z_value - center_z
                    
                    # 方向描述
                    rel_position = [
                        f"{'东' if rel_x > 0 else '西'}{abs(rel_x):.2f}m",
                        f"{'北' if rel_y > 0 else '南'}{abs(rel_y):.2f}m",
                        f"{'深' if rel_z > 0 else '浅'}{abs(rel_z):.2f}m"
                    ]
            except Exception as e:
                print(f"计算相对位置失败: {e}")
            
            # 色彩和样式设置
            accent_color = "#1E88E5"
            secondary_color = "#FF9800"
            success_color = "#4CAF50"
            grid_color = "#EEEEEE"
            
            # 构建HTML风格的结果表
            if is_over:
                header_text = "位置检测计算完成"
                header_style = f"color: white; background-color: {success_color}; font-weight: bold;"
            else:
                header_text = "实时更新 - 当前最优解"
                header_style = f"color: white; background-color: {secondary_color}; font-weight: bold;"
            
            # 创建带有动态条形图的亮度值显示
            brightness_percentage = min(max_br * 100, 100)  # 限制在0-100%
            brightness_bar = f"""
            <div style="width:100%; background-color:#f3f3f3; border-radius:3px; margin:5px 0;">
                <div style="width:{brightness_percentage}%; background-color:{accent_color}; height:8px; border-radius:3px;"></div>
            </div>
            """
            
            # 主要结果表格 - 使用复杂的HTML表格布局
            result_text = f"""
            <div style="font-family:'Arial'; border:1px solid #ddd; border-radius:5px; overflow:hidden;">
                <div style="padding:8px 15px; {header_style}">{header_text}</div>
                <div style="padding:15px;">
                    <table width="100%" style="border-collapse:collapse; margin-bottom:15px;">
                        <tr style="background-color:{grid_color};">
                            <td colspan="4" style="padding:8px; font-weight:bold; border-bottom:1px solid #ddd;">源位置坐标</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:20%;">参数</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">值</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:30%;">科学计数</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">相对位置</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold; color:{accent_color};">X 坐标</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{x_value:.4f} m</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-family:monospace;">{x_sci}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{rel_position[0]}</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold; color:{accent_color};">Y 坐标</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{y_value:.4f} m</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-family:monospace;">{y_sci}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{rel_position[1]}</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold; color:{accent_color};">Z 坐标</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{z_value:.4f} m</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-family:monospace;">{z_sci}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{rel_position[2]}</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; font-weight:bold; color:{accent_color};">事件时间</td>
                            <td colspan="3" style="padding:8px;">{t_value:.6f} s</td>
                        </tr>
                    </table>
                    
                    <div style="margin:15px 0;">
                        <div style="font-weight:bold; margin-bottom:5px; color:{accent_color};">亮度值: {max_br:.6f}</div>
                        {brightness_bar}
                    </div>
                    
                    <table width="100%" style="border-collapse:collapse; margin:15px 0;">
                        <tr style="background-color:{grid_color};">
                            <td colspan="2" style="padding:8px; font-weight:bold; border-bottom:1px solid #ddd;">算法参数</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:50%;">算法类型</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:50%;">{self.use_genetic_checkbox.isChecked() and "遗传算法" or "网格搜索"}</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd;">网格精度</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{self.grid_resolution_combo.currentText()}</td>
                        </tr>
                        <tr>
                            <td style="padding:8px;">计算类型</td>
                            <td style="padding:8px;">源位置搜索</td>
                        </tr>
                    </table>
                    
                    <div style="font-size:0.85em; color:#666; margin-top:10px; padding-top:10px; border-top:1px solid #eee;">
                        <div>注意: 坐标精度取决于网格精度和算法选择，实际位置可能会与最近的网格点有微小差异。</div>
                        <div>结果生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}</div>
                    </div>
                </div>
            </div>
            """
            
            # 更新结果文本
            self.result_text.setText(result_text)
            self.result_tabs.setCurrentIndex(0)  # 切换到文本结果标签页
            
            # 显示完成状态文本
            if is_over:
                self.display_label.setText("源位置计算完成！")
        except Exception as e:
            print(f"生成结果显示时出错: {e}")
            import traceback
            traceback.print_exc()
            # 如果复杂显示失败，使用简单显示作为备选
            simple_result = f"源位置: X={max_point[0]:.4f}, Y={max_point[1]:.4f}, Z={max_point[2]:.4f}, T={max_point[3]:.4f}, 亮度={max_br:.4f}"
            self.result_text.setText(simple_result)
            self.result_tabs.setCurrentIndex(0)  # 切换到文本结果标签页

    def show_detector_location(self, detector_location):
        self.display_label.setText(f"检测器位置: {detector_location}")

    def show_brightness_heatmap(self, max_point, max_slice, grid_x, grid_y):
        """显示亮度热图"""
        try:
            # 清除当前图表
            self.fig.clear()
            
            # 确保max_slice是二维数组
            if not isinstance(max_slice, np.ndarray) or max_slice.ndim != 2:
                print(f"警告: max_slice不是二维数组, 类型: {type(max_slice)}, 尝试转换...")
                try:
                    # 尝试转换为2D数组
                    if isinstance(max_slice, (int, float)):
                        # 如果是标量，创建一个示例热图
                        X, Y = np.meshgrid(grid_x, grid_y)
                        temp_slice = np.ones((len(grid_y), len(grid_x)))
                        # 中心位置设置最大值
                        center_x = len(grid_x) // 2
                        center_y = len(grid_y) // 2
                        temp_slice[center_y, center_x] = float(max_slice)
                        max_slice = temp_slice
                    elif isinstance(max_slice, np.ndarray) and max_slice.ndim == 1:
                        # 如果是1D数组，尝试重塑
                        max_slice = max_slice.reshape(len(grid_y), len(grid_x))
                    else:
                        # 其他情况，创建默认热图
                        max_slice = np.ones((len(grid_y), len(grid_x)))
                    print(f"转换后max_slice形状: {max_slice.shape}")
                except Exception as e:
                    print(f"转换max_slice失败: {e}")
                    max_slice = np.ones((len(grid_y), len(grid_x)))
                    
            # 获取最大亮度值
            max_brightness = max_slice.max()
            
            # 创建网格
            X, Y = np.meshgrid(grid_x, grid_y)
            
            # 假设的Z轴参数（如果没有提供）
            z_min = 0
            z_max = 5000
            height = 100
            try:
                from Models.Config import Config
                config = Config()
                z_min = int(config.get("Default", "z_min"))
                z_max = int(config.get("Default", "z_max"))
                height = int(config.get("Default", "height"))
            except Exception as e:
                print(f"无法从配置获取z轴参数，使用默认值: {e}")
            
            # 设置更好的颜色映射方案
            # 从用户选择的颜色方案获取
            selected_cmap = self.colormap_combo.currentText()
            cmap_choices = {
                '3D': selected_cmap,
                'heatmap': selected_cmap,
                'slice': selected_cmap
            }
            
            # 根据分辨率设置控制点绘制质量
            resolution = self.resolution_combo.currentText()
            if resolution == "低":
                rstride, cstride = 4, 4
                interpolation = 'nearest'
                contour_levels = 5
            elif resolution == "中":
                rstride, cstride = 2, 2
                interpolation = 'bilinear'
                contour_levels = 10
            elif resolution == "高":
                rstride, cstride = 1, 1
                interpolation = 'bicubic'
                contour_levels = 15
            else:  # 超高
                rstride, cstride = 1, 1
                interpolation = 'bicubic'
                contour_levels = 20
                # 增加数据点，使曲面更平滑
                if max_slice.shape[0] < 100 and max_slice.shape[1] < 100:
                    from scipy.ndimage import zoom
                    try:
                        zoom_factor = min(3, 100 / max(max_slice.shape[0], max_slice.shape[1]))
                        max_slice = zoom(max_slice, zoom_factor, order=3)
                        # 重新创建更精细的网格
                        grid_x = np.linspace(grid_x[0], grid_x[-1], max_slice.shape[1])
                        grid_y = np.linspace(grid_y[0], grid_y[-1], max_slice.shape[0])
                        X, Y = np.meshgrid(grid_x, grid_y)
                    except Exception as e:
                        print(f"增加分辨率失败: {e}")
            
            # 根据当前选择的视图模式显示不同的可视化
            if self.view_3d_radio.isChecked():
                # 3D视图 - 使用更好的透视角度和光照
                ax = self.fig.add_subplot(111, projection='3d')
                
                # 创建光滑的3D表面，提高分辨率
                surf = ax.plot_surface(X, Y, max_slice, cmap=cmap_choices['3D'],
                                     linewidth=0, antialiased=True, alpha=0.8,
                                     rstride=rstride, cstride=cstride, vmin=0)
                
                # 添加等高线投影到底部平面，增强深度感知
                offset = np.min(max_slice) - 0.1 * (np.max(max_slice) - np.min(max_slice))
                cset = ax.contourf(X, Y, max_slice, zdir='z', offset=offset, cmap=cmap_choices['3D'], alpha=0.6)
            
                # 标记最大亮度点，使用更明显的标记
                ax.scatter([max_point[0]], [max_point[1]], [max_brightness],
                          color='red', s=150, marker='*', edgecolor='white', linewidth=1.5,
                          label=f'最大亮度点: {max_brightness:.4f}')
            
                                # 设置标签和标题，使用更大更清晰的字体
                ax.set_title(f"3D亮度分布 (z={max_point[2]:.1f}, t={max_point[3]:.4f}s)", fontsize=14, fontweight='bold')
                ax.set_xlabel('X坐标 (m)', fontsize=12)
                ax.set_ylabel('Y坐标 (m)', fontsize=12)
                ax.set_zlabel('亮度值', fontsize=12)
                
                # 优化视图角度，提供更好的透视效果
                ax.view_init(elev=30, azim=45)
                
                # 添加颜色条
                if self.show_colorbar_checkbox.isChecked():
                    colorbar = self.fig.colorbar(surf, ax=ax, shrink=0.6, aspect=10, pad=0.1)
                    colorbar.set_label('亮度值', fontsize=11)
                    colorbar.ax.tick_params(labelsize=10)
            
                # 添加网格和背景颜色
                if self.show_grid_checkbox.isChecked():
                    ax.grid(True, linestyle='--', alpha=0.7)
                    
                # 添加图例，位置优化
                ax.legend(loc='upper right', fontsize=10, framealpha=0.7)
                
            elif self.view_heatmap_radio.isChecked():
                # 热力图视图 - 更高分辨率和更好的注释
                ax = self.fig.add_subplot(111)
            
                # 确保使用正确的坐标范围
                extent = [grid_x[0], grid_x[-1], grid_y[0], grid_y[-1]]
                
                # 使用平滑插值和优化的颜色映射
                im = ax.imshow(max_slice, cmap=cmap_choices['heatmap'], interpolation=interpolation, 
                              origin='lower', extent=extent, aspect='auto')
                              
                # 添加等高线，增强对亮度变化的感知
                contour = ax.contour(X, Y, max_slice, colors='white', alpha=0.3, 
                                    linewidths=0.5, levels=np.linspace(max_slice.min(), max_slice.max(), contour_levels))
                
                # 添加颜色条，更清晰的标签
                if self.show_colorbar_checkbox.isChecked():
                    cbar = self.fig.colorbar(im, ax=ax)
                    cbar.set_label('亮度值', fontsize=11)
                    cbar.ax.tick_params(labelsize=10)
                
                # 标记最大亮度点位置，使用更明显的标记
                ax.plot(max_point[0], max_point[1], 'r*', markersize=15, markeredgecolor='white',
                       markeredgewidth=1.5, label=f'最大亮度点: {max_brightness:.4f}')
                
                # 添加交互式悬停提示
                ax.format_coord = lambda x, y: f'x={x:.1f}, y={y:.1f}, 亮度值≈{self._get_brightness_at_coord(x, y, X, Y, max_slice):.4f}'
                
                # 注释最大亮度点，使用美观的文本框
                ax.annotate(f'最大亮度: {max_brightness:.4f}\n坐标: ({max_point[0]:.1f}, {max_point[1]:.1f}, {max_point[2]:.1f})',
                           xy=(max_point[0], max_point[1]), xytext=(30, 30),
                           textcoords='offset points', fontsize=10,
                           bbox=dict(boxstyle='round,pad=0.5', fc='gold', alpha=0.7, ec='orange'),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=.5', color='orange'))
            
                # 设置标题和标签，使用更清晰的字体
                ax.set_title(f'亮度热图 (z={max_point[2]:.1f}, t={max_point[3]:.4f}s)', fontsize=14, fontweight='bold')
                ax.set_xlabel('X坐标 (m)', fontsize=12)
                ax.set_ylabel('Y坐标 (m)', fontsize=12)
            
                # 添加网格线
                if self.show_grid_checkbox.isChecked():
                    ax.grid(True, linestyle='--', alpha=0.5, color='gray')
                
                # 添加图例，位置优化
                ax.legend(loc='upper right', fontsize=10, framealpha=0.7)
                
            else:  # 切片图 - 完全重写为更专业的三维切片显示
                # 创建优化的2x2布局
                gs = self.fig.add_gridspec(2, 2, width_ratios=[1, 1], height_ratios=[1, 1], 
                                         hspace=0.25, wspace=0.25)
            
                # 从当前滑块位置获取切片位置百分比
                slice_position = self.slice_slider.value() / 100.0
                
                # 计算实际的切片位置
                x_slice_pos = grid_x[0] + slice_position * (grid_x[-1] - grid_x[0])
                y_slice_pos = grid_y[0] + slice_position * (grid_y[-1] - grid_y[0])
                z_slice_pos = z_min + slice_position * (z_max - z_min)
            
                # XY平面 (顶视图) - 基于z_slice_pos的切片
                ax1 = self.fig.add_subplot(gs[0, 0])
                im1 = ax1.imshow(max_slice, cmap=cmap_choices['slice'], interpolation=interpolation,
                               extent=[grid_x[0], grid_x[-1], grid_y[0], grid_y[-1]],
                               origin='lower', aspect='auto')
                # 添加切片线指示器
                ax1.axvline(x=x_slice_pos, color='white', linestyle='--', alpha=0.7)
                ax1.axhline(y=y_slice_pos, color='white', linestyle='--', alpha=0.7)
                ax1.set_title("XY平面 (顶视图)", fontsize=12, fontweight='bold')
                ax1.set_xlabel('X坐标 (m)', fontsize=10)
                ax1.set_ylabel('Y坐标 (m)', fontsize=10)
                ax1.plot(max_point[0], max_point[1], 'r*', markersize=10, markeredgecolor='white', markeredgewidth=1)
            
                # XZ平面 (前视图) - 使用更精细的模拟数据
                ax2 = self.fig.add_subplot(gs[0, 1])
                # 创建一个XZ平面的模拟数据 - 基于y_slice_pos位置的切片
                num_z_points = 50  # 增加分辨率
                xz_slice = np.zeros((num_z_points, len(grid_x)))
                best_z_idx = int((max_point[2] - z_min) / (z_max - z_min) * (num_z_points-1))
                best_z_idx = min(max(best_z_idx, 0), num_z_points-1)  # 确保在范围内
                best_x_idx = np.argmin(np.abs(grid_x - max_point[0]))
                
                # 创建更真实的高斯分布
                z_coords = np.linspace(z_min, z_max, num_z_points)
                for i in range(num_z_points):
                    for j in range(len(grid_x)):
                        # 基于最大亮度点的距离创建更真实的亮度分布
                        dist_squared = ((i - best_z_idx)/(num_z_points/10))**2 + ((j - best_x_idx)/(len(grid_x)/10))**2
                        xz_slice[i, j] = max_brightness * np.exp(-dist_squared)
                
                # 以Y切片位置为基准，标记Y切片线
                y_slice_idx = np.argmin(np.abs(grid_y - y_slice_pos))
                if 0 <= y_slice_idx < max_slice.shape[0]:
                    # 使用实际的XY数据获取对应Y位置的亮度
                    for j in range(len(grid_x)):
                        # 在Z中间位置放置XY数据
                        mid_z = num_z_points // 2
                        xz_slice[mid_z, j] = max_slice[y_slice_idx, j]
                
                im2 = ax2.imshow(xz_slice, cmap=cmap_choices['slice'], interpolation=interpolation,
                               extent=[grid_x[0], grid_x[-1], z_coords[0], z_coords[-1]],
                               origin='lower', aspect='auto')
                # 添加切片线指示器
                ax2.axvline(x=x_slice_pos, color='white', linestyle='--', alpha=0.7)
                ax2.set_title("XZ平面 (前视图)", fontsize=12, fontweight='bold')
                ax2.set_xlabel('X坐标 (m)', fontsize=10)
                ax2.set_ylabel('Z坐标 (m)', fontsize=10)
                ax2.plot(max_point[0], max_point[2], 'r*', markersize=10, markeredgecolor='white', markeredgewidth=1)
            
                # YZ平面 (侧视图) - 使用更精细的模拟数据
                ax3 = self.fig.add_subplot(gs[1, 0])
                # 创建一个YZ平面的模拟数据 - 基于x_slice_pos位置的切片
                yz_slice = np.zeros((num_z_points, len(grid_y)))
                best_y_idx = np.argmin(np.abs(grid_y - max_point[1]))
                
                # 创建更真实的高斯分布
                for i in range(num_z_points):
                    for j in range(len(grid_y)):
                        # 基于最大亮度点的距离创建更真实的亮度分布
                        dist_squared = ((i - best_z_idx)/(num_z_points/10))**2 + ((j - best_y_idx)/(len(grid_y)/10))**2
                        yz_slice[i, j] = max_brightness * np.exp(-dist_squared)
                
                # 以X切片位置为基准，标记X切片线
                x_slice_idx = np.argmin(np.abs(grid_x - x_slice_pos))
                if 0 <= x_slice_idx < max_slice.shape[1]:
                    # 使用实际的XY数据获取对应X位置的亮度
                    for j in range(len(grid_y)):
                        if j < max_slice.shape[0]:
                            # 在Z中间位置放置XY数据
                            mid_z = num_z_points // 2
                            yz_slice[mid_z, j] = max_slice[j, x_slice_idx]
                
                im3 = ax3.imshow(yz_slice, cmap=cmap_choices['slice'], interpolation=interpolation,
                               extent=[grid_y[0], grid_y[-1], z_coords[0], z_coords[-1]],
                               origin='lower', aspect='auto')
                # 添加切片线指示器
                ax3.axhline(y=z_slice_pos, color='white', linestyle='--', alpha=0.7)
                ax3.set_title("YZ平面 (侧视图)", fontsize=12, fontweight='bold')
                ax3.set_xlabel('Y坐标 (m)', fontsize=10)
                ax3.set_ylabel('Z坐标 (m)', fontsize=10)
                ax3.plot(max_point[1], max_point[2], 'r*', markersize=10, markeredgecolor='white', markeredgewidth=1)
            
                # 3D小视图 - 添加切片平面
                ax4 = self.fig.add_subplot(gs[1, 1], projection='3d')
                surf = ax4.plot_surface(X, Y, max_slice, cmap=cmap_choices['slice'],
                                      linewidth=0, antialiased=True, alpha=0.6)
                
                # 添加三个切片平面
                max_z_value = max_slice.max() * 1.2
                xy_points = np.array([[grid_x[0], grid_y[0], z_slice_pos],
                                    [grid_x[-1], grid_y[0], z_slice_pos],
                                    [grid_x[-1], grid_y[-1], z_slice_pos],
                                    [grid_x[0], grid_y[-1], z_slice_pos]])
                xy_plane = ax4.plot_surface(X, Y, z_slice_pos * np.ones_like(X),
                                          color='gray', alpha=0.3)
                
                # 显示3D交叉切片线
                xz_line = np.array([[grid_x[0], y_slice_pos, z_min], 
                                  [grid_x[-1], y_slice_pos, z_min]])
                yz_line = np.array([[x_slice_pos, grid_y[0], z_min],
                                  [x_slice_pos, grid_y[-1], z_min]])
                ax4.plot(xz_line[:, 0], xz_line[:, 1], xz_line[:, 2], 'w--', alpha=0.7)
                ax4.plot(yz_line[:, 0], yz_line[:, 1], yz_line[:, 2], 'w--', alpha=0.7)
                
                ax4.set_title("3D切片预览", fontsize=12, fontweight='bold')
                ax4.set_xlabel('X', fontsize=9)
                ax4.set_ylabel('Y', fontsize=9)
                ax4.set_zlabel('亮度', fontsize=9)
                ax4.scatter([max_point[0]], [max_point[1]], [max_brightness],
                           color='red', s=50, marker='*', edgecolor='white')
                
                # 优化3D视图角度
                ax4.view_init(elev=30, azim=30)
            
                # 添加共享的颜色条
                if self.show_colorbar_checkbox.isChecked():
                    cbar_ax = self.fig.add_axes([0.92, 0.15, 0.02, 0.7])
                    cbar = self.fig.colorbar(im1, cax=cbar_ax, label='亮度值')
                    cbar.ax.tick_params(labelsize=9)
        
            # 优化布局
            self.fig.tight_layout()
            
            # 更新图表
            self.canvas.draw()
        
            # 构建高级统计分析HTML
            accent_color = "#1E88E5"
            secondary_color = "#FF9800"
            grid_color = "#EEEEEE"
            
            # 计算更多统计指标
            min_brightness = np.min(max_slice)
            median_brightness = np.median(max_slice)
            p25 = np.percentile(max_slice, 25)
            p75 = np.percentile(max_slice, 75)
            
            # 计算信噪比
            snr = max_brightness / (p25 if p25 > 0 else 0.0001)
            
            # 计算高亮区域占比
            high_brightness_area = np.sum(max_slice > 0.75 * max_brightness) / max_slice.size * 100
            
            # 创建亮度条
            brightness_percentage = min(max_brightness * 100, 100)
            brightness_bar = f"""
            <div style="width:100%; background-color:#f3f3f3; border-radius:3px; margin:5px 0;">
                <div style="width:{brightness_percentage}%; background-color:{accent_color}; height:8px; border-radius:3px;"></div>
            </div>
            """
            
            # 创建高级结果显示
            result_text = f"""
            <div style="font-family:'Arial'; border:1px solid #ddd; border-radius:5px; overflow:hidden;">
                <div style="padding:8px 15px; color:white; background-color:{accent_color}; font-weight:bold;">热力图分析结果</div>
                <div style="padding:15px;">
                    <table width="100%" style="border-collapse:collapse; margin-bottom:15px;">
                        <tr style="background-color:{grid_color};">
                            <td colspan="4" style="padding:8px; font-weight:bold; border-bottom:1px solid #ddd;">源位置坐标</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold; width:25%;">X坐标</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">{max_point[0]:.4f} m</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold; width:25%;">Y坐标</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">{max_point[1]:.4f} m</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">Z坐标</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{max_point[2]:.4f} m</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">事件时间</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{max_point[3]:.6f} s</td>
                        </tr>
                    </table>
                    
                    <div style="margin:15px 0;">
                        <div style="font-weight:bold; margin-bottom:5px; color:{accent_color};">亮度值: {max_brightness:.6f}</div>
                        {brightness_bar}
                    </div>
                    
                    <table width="100%" style="border-collapse:collapse; margin:15px 0;">
                        <tr style="background-color:{grid_color};">
                            <td colspan="4" style="padding:8px; font-weight:bold; border-bottom:1px solid #ddd;">亮度统计分析</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold; width:25%;">最大值</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">{max_brightness:.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold; width:25%;">最小值</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">{min_brightness:.6f}</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">平均值</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{np.mean(max_slice):.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">中位数</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{median_brightness:.6f}</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">标准差</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{np.std(max_slice):.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">信噪比</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{snr:.2f}</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">P25</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{p25:.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">P75</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{p75:.6f}</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">高亮区占比</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{high_brightness_area:.2f}%</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">数据点数</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{max_slice.size}点</td>
                        </tr>
                    </table>
                    
                    <table width="100%" style="border-collapse:collapse; margin:15px 0;">
                        <tr style="background-color:{grid_color};">
                            <td colspan="2" style="padding:8px; font-weight:bold; border-bottom:1px solid #ddd;">显示参数</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:50%; font-weight:bold;">视图模式</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:50%;">{('3D视图' if self.view_3d_radio.isChecked() else '热力图' if self.view_heatmap_radio.isChecked() else '切片图')}</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">颜色方案</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{self.colormap_combo.currentText()}</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">网格尺寸</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{max_slice.shape[1]}×{max_slice.shape[0]}</td>
                        </tr>
                    </table>
                    
                    <div style="font-size:0.85em; color:#666; margin-top:10px; padding-top:10px; border-top:1px solid #eee;">
                        <div>注意: 最大亮度点是通过算法确定的最优解，可能与网格点不完全一致。</div>
                        <div>结果生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}</div>
                    </div>
                </div>
            </div>
            """
            
            self.result_text.setText(result_text)
            
            # 显示结果
            self.toggle_loading(False)
            self.display_label.setText("热图显示完成！")
            
            # 显示复杂的热力图分析结果
            analysis_html = self.display_heatmap_analysis(max_point, max_slice, grid_x, grid_y)
            self.result_text.setText(analysis_html)
            
        except Exception as e:
            print(f"显示热图错误：{e}")
            import traceback
            traceback.print_exc()
            self.toggle_loading(False)
            self.display_label.setText(f"热图显示错误：{e}")

    def _get_brightness_at_coord(self, x, y, X, Y, max_slice):
        """获取给定坐标的亮度值，用于交互式悬停提示"""
        try:
            # 找到最接近的网格点
            x_idx = np.argmin(np.abs(X[0,:] - x))
            y_idx = np.argmin(np.abs(Y[:,0] - y))
            
            # 如果索引在数组范围内，返回对应的亮度值
            if 0 <= y_idx < max_slice.shape[0] and 0 <= x_idx < max_slice.shape[1]:
                return max_slice[y_idx, x_idx]
            return 0
        except:
            return 0

    def set_progress(self, value):
        """设置进度条值"""
        self.progress_bar.setValue(value)
        
    def update_status_text(self, text):
        """更新状态文本"""
        self.progress_label.setText(text)
        
    def toggle_loading(self, is_loading=True):
        """切换加载状态"""
        if is_loading:
            # 确保进度相关控件可见
            self.progress_bar.setVisible(True)
            self.time_label.setVisible(True)
            self.progress_label.setVisible(True)
            self.frontground_label.setVisible(True)
            
            # 重置进度条
            self.progress_bar.setValue(0)
            self.progress_label.setText("当前进度: 0%")
            self.time_label.setText("预计时间: 计算中...")
            self.frontground_label.setText("处理速度: 等待...")
            
            # 禁用所有操作按钮，避免在计算过程中进行操作
            self.heatmap_btn.setEnabled(False)
            self.display_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.reset_btn.setEnabled(False)
        else:
            # 计算完成后，隐藏进度相关控件，但保留速度标签
            self.progress_bar.setVisible(False)
            self.time_label.setVisible(False)
            self.progress_label.setVisible(False)
            # 不隐藏 frontground_label，以便显示最终的处理速度
            
            # 重新启用所有操作按钮
            self.heatmap_btn.setEnabled(True)
            self.display_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.reset_btn.setEnabled(True)
            
    def show_error(self, message):
        """显示错误信息"""
        QMessageBox.critical(self, "错误", message)
        
    def update_best_point(self, point, brightness):
        """实时更新找到的最佳点位置"""
        result_text = (
            f"<b>当前最佳点：</b><br>"
            f"亮度：<b>{brightness:.4f}</b><br>"
            f"坐标：(<b>{point[0]:.2f}</b>, <b>{point[1]:.2f}</b>, <b>{point[2]:.2f}</b>)<br>"
            f"时间：<b>{point[3]:.4f}</b> s"
        )
        self.result_text.setText(result_text)

    @pyqtSlot(int, str, str, str)
    def update_progress(self, progress, elapsed_time, remaining_time_str, speed_str):
        """更新进度显示"""
        try:
            # 确保progress是整数
            progress = int(progress)
            
            # 更新进度条
            self.progress_bar.setValue(progress)
            
            # 更新进度标签
            self.progress_label.setText(f"当前进度: {progress}%")
            
            # 更新时间标签 - 确保时间信息是字符串
            if isinstance(elapsed_time, str) and isinstance(remaining_time_str, str):
                self.time_label.setText(f"已用时间: {elapsed_time} / 预计剩余: {remaining_time_str}")
            else:
                try:
                    elapsed_str = str(elapsed_time)
                    remaining_str = str(remaining_time_str)
                    self.time_label.setText(f"已用时间: {elapsed_str} / 预计剩余: {remaining_str}")
                except:
                    self.time_label.setText("已用时间: 计算中... / 预计剩余: 计算中...")
            
            # 更新速度标签 - 确保speed_str是字符串
            if isinstance(speed_str, str):
                self.frontground_label.setText(f"处理速度: {speed_str}")
            else:
                # 如果不是字符串，尝试转换
                try:
                    speed_text = str(speed_str)
                    self.frontground_label.setText(f"处理速度: {speed_text}")
                except:
                    self.frontground_label.setText("处理速度: 计算中...")
        except Exception as e:
            print(f"更新进度信息时出错: {e}")
            # 确保即使出错也显示一些信息
            self.progress_label.setText("当前进度: 计算中...")
            self.time_label.setText("时间信息: 计算中...")
            self.frontground_label.setText("处理速度: 计算中...")
        
        # 强制处理所有待处理的事件，确保UI更新
        QCoreApplication.processEvents()
        
        # 如果进度条卡在某个值超过3秒，尝试重新绘制
        if not hasattr(self, '_last_progress'):
            self._last_progress = progress
            self._progress_time = 0
        elif self._last_progress == progress:
            self._progress_time += 1
            if self._progress_time > 30:  # 如果同一个进度超过30次更新(约3秒)
                # 重置计数器
                self._progress_time = 0
                # 强制重绘进度条
                self.progress_bar.repaint()
        else:
            self._last_progress = progress
            self._progress_time = 0

    def display_heatmap_analysis(self, max_point, max_slice, grid_x, grid_y):
        """显示复杂的热力图分析结果"""
        try:
            # 1. 计算热力图的统计指标
            max_brightness = np.max(max_slice)
            min_brightness = np.min(max_slice)
            mean_brightness = np.mean(max_slice)
            median_brightness = np.median(max_slice)
            std_brightness = np.std(max_slice)
            p25_brightness = np.percentile(max_slice, 25)
            p75_brightness = np.percentile(max_slice, 75)
            p90_brightness = np.percentile(max_slice, 90)
            p95_brightness = np.percentile(max_slice, 95)
            p99_brightness = np.percentile(max_slice, 99)
            
            # 计算信噪比 (SNR) - 用最大亮度与背景噪声比
            background_noise = np.percentile(max_slice, 25)  # 假设25%分位点为背景
            snr = max_brightness / (background_noise if background_noise > 0 else 0.0001)
            
            # 计算峰值信号与均值比例
            peak_mean_ratio = max_brightness / (mean_brightness if mean_brightness > 0 else 0.0001)
            
            # 计算亮度大于75%最大值的区域占比
            high_brightness_area = np.sum(max_slice > 0.75 * max_brightness) / max_slice.size
            high_brightness_percentage = high_brightness_area * 100
            
            # 2. 计算热力图特征尺寸
            # 找到最大点在网格中的位置索引
            max_idx_y = np.argmin(np.abs(grid_y - max_point[1]))
            max_idx_x = np.argmin(np.abs(grid_x - max_point[0]))
            
            # 计算沿X方向和Y方向的亮度分布半宽
            x_profile = max_slice[max_idx_y, :]
            y_profile = max_slice[:, max_idx_x]
            
            # 计算半高全宽(FWHM)
            half_max = max_brightness / 2.0
            x_above_half = x_profile > half_max
            y_above_half = y_profile > half_max
            
            try:
                x_indices = np.where(x_above_half)[0]
                y_indices = np.where(y_above_half)[0]
                
                x_width = grid_x[x_indices[-1]] - grid_x[x_indices[0]] if len(x_indices) > 1 else 0
                y_width = grid_y[y_indices[-1]] - grid_y[y_indices[0]] if len(y_indices) > 1 else 0
                
                feature_area = x_width * y_width  # 特征面积近似
            except:
                x_width = 0
                y_width = 0
                feature_area = 0
                
            # 3. 热图覆盖范围
            x_range = grid_x[-1] - grid_x[0]
            y_range = grid_y[-1] - grid_y[0]
            grid_area = x_range * y_range
            
            # 4. 源位置在热力图中的相对位置
            rel_pos_x = (max_point[0] - grid_x[0]) / x_range if x_range > 0 else 0
            rel_pos_y = (max_point[1] - grid_y[0]) / y_range if y_range > 0 else 0
            
            # 5. 亮度分布形状的量化描述
            # 计算亮度分布的偏度和峰度
            try:
                from scipy import stats
                brightness_skewness = stats.skew(max_slice.flatten())
                brightness_kurtosis = stats.kurtosis(max_slice.flatten())
            except:
                brightness_skewness = 0
                brightness_kurtosis = 0
            
            # 6. 创建亮度分布直方图数据
            try:
                hist_bins = 10
                hist_values, hist_edges = np.histogram(max_slice.flatten(), bins=hist_bins, range=(min_brightness, max_brightness))
                hist_percentages = hist_values / np.sum(hist_values) * 100
                
                # 构建直方图HTML
                histogram_bars = ""
                max_bar_height = 40  # 最大条形图高度px
                
                for i in range(hist_bins):
                    bar_height = max_bar_height * (hist_percentages[i] / 100)
                    bar_color = f"rgb({min(255, int(55 + 200 * i / hist_bins))}, 100, 200)"
                    value_range = f"{hist_edges[i]:.3f}-{hist_edges[i+1]:.3f}"
                    
                    histogram_bars += f"""
                    <div style="display:inline-block; width:{100/hist_bins}%; text-align:center;">
                        <div style="margin:0 auto; background-color:{bar_color}; width:80%; height:{bar_height}px;"></div>
                        <div style="font-size:8px;">{value_range}</div>
                        <div style="font-size:8px;">{hist_percentages[i]:.1f}%</div>
                    </div>
                    """
            except:
                histogram_bars = "<div>直方图生成失败</div>"
            
            # 7. 基于用户设置的配置信息
            view_mode = "3D视图" if self.view_3d_radio.isChecked() else "热力图" if self.view_heatmap_radio.isChecked() else "切片图"
            colormap_name = self.colormap_combo.currentText()
            resolution = self.resolution_combo.currentText()
            use_genetic = self.use_genetic_checkbox.isChecked()
            
            # 8. 构建专业的HTML显示
            accent_color = "#1E88E5"
            secondary_color = "#FF9800"
            success_color = "#4CAF50"
            grid_color = "#EEEEEE"
            
            analysis_html = f"""
            <div style="font-family:'Arial'; border:1px solid #ddd; border-radius:5px; overflow:hidden;">
                <div style="padding:8px 15px; color:white; background-color:{accent_color}; font-weight:bold;">热力图分析结果</div>
                <div style="padding:15px;">
                    <!-- 主要亮度指标 -->
                    <table width="100%" style="border-collapse:collapse; margin-bottom:15px;">
                        <tr style="background-color:{grid_color};">
                            <td colspan="4" style="padding:8px; font-weight:bold; border-bottom:1px solid #ddd;">亮度统计分析</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold; width:25%;">最大亮度</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">{max_brightness:.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold; width:25%;">最小亮度</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">{min_brightness:.6f}</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">平均亮度</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{mean_brightness:.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">中位亮度</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{median_brightness:.6f}</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">标准差</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{std_brightness:.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">信噪比</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{snr:.2f}</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">峰均比</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{peak_mean_ratio:.2f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">高亮区占比</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{high_brightness_percentage:.2f}%</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">分布偏度</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{brightness_skewness:.4f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">分布峰度</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{brightness_kurtosis:.4f}</td>
                        </tr>
                    </table>
                    
                    <!-- 分位数表格 -->
                    <table width="100%" style="border-collapse:collapse; margin-bottom:15px;">
                        <tr style="background-color:{grid_color};">
                            <td colspan="5" style="padding:8px; font-weight:bold; border-bottom:1px solid #ddd;">亮度分位数</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:20%; font-weight:bold;">P25</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:20%; font-weight:bold;">P50</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:20%; font-weight:bold;">P75</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:20%; font-weight:bold;">P90</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:20%; font-weight:bold;">P99</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{p25_brightness:.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{median_brightness:.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{p75_brightness:.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{p90_brightness:.6f}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{p99_brightness:.6f}</td>
                        </tr>
                    </table>
                    
                    <!-- 亮度分布直方图 -->
                    <div style="margin:15px 0;">
                        <div style="font-weight:bold; margin-bottom:8px; color:{accent_color};">亮度值分布直方图</div>
                        <div style="width:100%; margin-bottom:5px;">
                            {histogram_bars}
                        </div>
                    </div>
                    
                    <!-- 几何特征参数 -->
                    <table width="100%" style="border-collapse:collapse; margin:15px 0;">
                        <tr style="background-color:{grid_color};">
                            <td colspan="4" style="padding:8px; font-weight:bold; border-bottom:1px solid #ddd;">几何特征参数</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%; font-weight:bold;">X半高宽</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">{x_width:.2f} m</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%; font-weight:bold;">Y半高宽</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">{y_width:.2f} m</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">特征面积</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{feature_area:.2f} m²</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">覆盖面积</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{grid_area:.2f} m²</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">X相对位置</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{rel_pos_x*100:.1f}%</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">Y相对位置</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{rel_pos_y*100:.1f}%</td>
                        </tr>
                    </table>
                    
                    <!-- 计算和显示参数 -->
                    <table width="100%" style="border-collapse:collapse; margin:15px 0;">
                        <tr style="background-color:{grid_color};">
                            <td colspan="4" style="padding:8px; font-weight:bold; border-bottom:1px solid #ddd;">计算和显示参数</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%; font-weight:bold;">算法类型</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">{use_genetic and "遗传算法" or "网格搜索"}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%; font-weight:bold;">可视化模式</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; width:25%;">{view_mode}</td>
                        </tr>
                        <tr style="background-color:{grid_color};">
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">颜色方案</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{colormap_name}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">显示分辨率</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{resolution}</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">网格尺寸</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{max_slice.shape[1]}×{max_slice.shape[0]}</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd; font-weight:bold;">数据点数</td>
                            <td style="padding:8px; border-bottom:1px solid #ddd;">{max_slice.size}点</td>
                        </tr>
                    </table>
                    
                    <div style="font-size:0.85em; color:#666; margin-top:10px; padding-top:10px; border-top:1px solid #eee;">
                        <div>注意: 热力图统计分析基于当前视图显示的数据，切换视图模式可能会影响部分统计结果。</div>
                        <div>分析生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}</div>
                    </div>
                </div>
            </div>
            """
            
            # 显示结果
            return analysis_html
            
        except Exception as e:
            print(f"生成热力图分析失败: {e}")
            import traceback
            traceback.print_exc()
            return f"<div>热力图分析生成失败: {str(e)}</div>"



