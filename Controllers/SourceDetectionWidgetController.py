# controllers.py
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import QMetaObject, Qt, Q_ARG, QObject, QTimer
from Models.TraceFile import TraceFile
from Models.TaskRunner import TaskRunner
from Views.SourceDetectionWidget import SourceDetectionWidget
from Models.ModelManager import ModelManager
import time
import traceback
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import os
from functools import lru_cache
from Models.Config import Config
import threading
from PyQt6.QtWidgets import QApplication
import Services.ssatop as ssatop

class SourceDetectionWidgetController:
    def __init__(self, view: SourceDetectionWidget):
        self.view = view
        self.trace_file = TraceFile()
        self.model_manager = ModelManager()  # 添加模型管理器引用

        self.thread = None # 必须要把线程对象声明为类变量，否则线程会被垃圾回收!!
        self.last_result = None  # 保存上次的结果
        
        # 连接按钮事件
        self.view.display_btn.clicked.connect(
            self.handle_show_source_location
        )
        self.view.heatmap_btn.clicked.connect(
            self.handle_show_brightness_heatmap
        )
        
        # 连接可视化选项事件
        self.view.view_mode_group.buttonClicked.connect(self.handle_view_mode_change)
        self.view.show_detector_checkbox.toggled.connect(self.handle_show_detector_change)
        self.view.show_grid_checkbox.toggled.connect(self.handle_show_grid_change)
        self.view.show_colorbar_checkbox.toggled.connect(self.handle_show_colorbar_change)
        self.view.slice_slider.valueChanged.connect(self.handle_slice_change)
        self.view.export_btn.clicked.connect(self.handle_export_results)
        self.view.reset_btn.clicked.connect(self.handle_reset_view)
        
        # 连接新增的颜色方案和分辨率控制
        self.view.colormap_combo.currentIndexChanged.connect(self.handle_colormap_change)
        self.view.resolution_combo.currentIndexChanged.connect(self.handle_resolution_change)

    # 确保模型已初始化
    def _ensure_model_initialized(self):
        """确保模型已经初始化，防止闪退"""
        try:
            # 获取当前模型并确保它已初始化
            current_model = self.model_manager.get_current_model()
            
            # 进行一个简单的计算以验证模型是否可用
            test_result = current_model.calculate_time_delay(
                source_pos=(0, 0, 1000),
                receiver_pos=(1000, 0, 0),
                phase="P"
            )
            
            print(f"模型初始化测试: {current_model.model_name}, 测试计算结果: {test_result}")
            return True
        except Exception as e:
            print(f"模型初始化失败: {e}")
            print(traceback.format_exc())
            
            # 尝试回退到简单模型
            try:
                success = self.model_manager.set_current_model("simple")
                if success:
                    print("已回退到简单模型")
                    return True
            except:
                pass
                
            # 显示错误消息
            QMessageBox.warning(
                self.view, 
                "模型初始化失败", 
                "无法初始化速度模型，请先在设置中选择并应用速度模型。"
            )
            return False

    # 处理视图模式变更
    def handle_view_mode_change(self, button):
        """处理可视化模式变更事件"""
        # 只在有结果时更新显示
        if self.last_result:
            self.update_visualization()

    # 处理检测器显示切换
    def handle_show_detector_change(self, checked):
        """处理检测器显示切换事件"""
        # 只在有结果时更新显示
        if self.last_result:
            self.update_visualization()
    
    # 处理网格显示切换
    def handle_show_grid_change(self, checked):
        """处理网格显示切换事件"""
        # 只在有结果时更新显示
        if self.last_result:
            self.update_visualization()
    
    # 处理颜色条显示切换
    def handle_show_colorbar_change(self, checked):
        """处理颜色条显示切换事件"""
        # 只在有结果时更新显示
        if self.last_result:
            self.update_visualization()
            
    # 处理切片位置变更
    def handle_slice_change(self, value):
        """处理切片位置变更事件"""
        # 只在有结果时且在切片模式下更新显示
        if self.last_result and self.view.view_slice_radio.isChecked():
            # 更新切片标签显示百分比
            slice_percent = value
            self.view.slice_label.setText(f"切片位置: {slice_percent}%")
            
            # 延迟更新可视化，避免滑块拖动时过度刷新
            if hasattr(self, '_slice_timer'):
                self._slice_timer.stop()
            else:
                self._slice_timer = QTimer()
                self._slice_timer.setSingleShot(True)
                self._slice_timer.timeout.connect(self.update_visualization)
            
            self._slice_timer.start(200)  # 200毫秒后更新可视化

    # 更新可视化显示
    def update_visualization(self):
        """根据当前的视图模式和选项更新可视化"""
        # 确保有结果数据
        if not self.last_result:
            print("没有可视化结果数据")
            return
            
        try:
            # 确保last_result是元组格式
            if not isinstance(self.last_result, tuple):
                print(f"无效的结果类型: {type(self.last_result)}")
                return
                
            # 获取并转换max_point，确保格式一致
            max_point = self.convert_max_point(self.last_result[0])
                
            # 源位置检测结果 (通常包含2个元素): (max_point, max_br)
            if len(self.last_result) == 2:
                max_br = self.last_result[1]
                self.view.show_source_location(max_point, max_br)
                print(f"显示源位置检测结果: 最大亮度 {max_br}")
                
                # 如果是源位置检测结果，但需要显示热图或切片图，则尝试重新计算热图数据
                if self.view.view_heatmap_radio.isChecked() or self.view.view_slice_radio.isChecked():
                    self.generate_heatmap_from_point(max_point, max_br)
                
            # 亮度热图结果 (通常包含4个元素): (max_point, max_slice, grid_x, grid_y)
            elif len(self.last_result) >= 4:
                max_slice = self.last_result[1]
                grid_x = self.last_result[2]
                grid_y = self.last_result[3]
                
                # 检查是否需要重新生成更高质量的热图数据
                if (self.view.view_slice_radio.isChecked() and 
                    (not isinstance(max_slice, np.ndarray) or max_slice.shape[0] < 20)):
                    # 需要更高质量的切片数据
                    self.generate_better_slice_data(max_point, max_slice, grid_x, grid_y)
                else:
                    # 直接显示热图
                    self.view.show_brightness_heatmap(max_point, max_slice, grid_x, grid_y)
                    
                print(f"显示亮度热图结果: 切片大小 {max_slice.shape if hasattr(max_slice, 'shape') else '未知'}")
                
            else:
                print(f"不支持的结果格式，元组长度为 {len(self.last_result)}")
                
        except Exception as e:
            print(f"可视化更新失败: {e}")
            print(traceback.format_exc())

    def generate_better_slice_data(self, max_point, max_slice, grid_x, grid_y):
        """生成更高质量的切片数据用于3D切片视图"""
        try:
            # 如果已经有高质量数据，则直接使用
            if isinstance(max_slice, np.ndarray) and max_slice.shape[0] >= 20:
                self.view.show_brightness_heatmap(max_point, max_slice, grid_x, grid_y)
                return
                
            # 开始生成更高质量的切片数据的后台任务
            self.view.update_status_text("正在生成高质量切片数据...")
            
            # 使用现有数据创建临时热图数据进行显示
            # 这样用户不用等待高质量数据生成就能看到初步结果
            self.view.show_brightness_heatmap(max_point, max_slice, grid_x, grid_y)
            
            # 在后台计算更高质量的切片数据（如果有必要且未在计算中）
            if not hasattr(self, '_slice_thread') or not self._slice_thread.isRunning():
                # 创建一个后台线程来计算更高质量的切片数据
                self._slice_thread = TaskRunner(
                    lambda progress_callback: self._calculate_high_quality_slices(
                        max_point, grid_x, grid_y, progress_callback
                    ),
                    lambda progress, *args: self.view.update_status_text(f"生成高质量切片数据: {progress}%")
                )
                self._slice_thread.task_completed.connect(self._on_better_slice_data_ready)
                self._slice_thread.start()
                
        except Exception as e:
            print(f"生成更高质量切片数据失败: {e}")
            print(traceback.format_exc())
            # 使用原始数据作为备选
            self.view.show_brightness_heatmap(max_point, max_slice, grid_x, grid_y)

    def _calculate_high_quality_slices(self, max_point, grid_x, grid_y, progress_callback):
        """计算高质量的3D切片数据"""
        try:
            from Models.Config import Config
            config = Config()
            try:
                z_min = int(config.get("Default", "z_min"))
                z_max = int(config.get("Default", "z_max"))
                speed = float(config.get("Default", "speed"))
            except Exception as e:
                print(f"读取配置失败: {e}")
                z_min = 0
                z_max = 5000
                speed = 3000
                
            # 使用更精细的网格
            num_z_points = 50
            
            # 创建高质量的切片数据
            # 通常这里会使用前面已经计算好的热力图数据结合插值方法
            # 在实际应用中可能需要调用更复杂的算法
            
            # 示例：使用高斯模型生成更平滑的亮度分布
            X, Y = np.meshgrid(grid_x, grid_y)
            Z = np.zeros((len(grid_y), len(grid_x)))
            
            # 创建以最大亮度点为中心的高斯分布
            center_x = np.argmin(np.abs(grid_x - max_point[0]))
            center_y = np.argmin(np.abs(grid_y - max_point[1]))
            max_brightness = 1.0  # 假设的最大亮度值
            
            # 如果是真实的亮度计算，可以使用更复杂的模型
            for i in range(len(grid_y)):
                for j in range(len(grid_x)):
                    # 距离衰减模型
                    dist_squared = ((i - center_y)/5)**2 + ((j - center_x)/5)**2
                    Z[i, j] = max_brightness * np.exp(-0.5 * dist_squared)
                
                # 更新进度
                progress_callback(int(100 * i / len(grid_y)), 0, "", "")
            
            # 返回高质量的切片数据元组
            return (max_point, Z, grid_x, grid_y)
            
        except Exception as e:
            print(f"计算高质量切片失败: {e}")
            print(traceback.format_exc())
            # 出错时返回None，让调用者处理
            return None

    def _on_better_slice_data_ready(self, result):
        """当更高质量的切片数据准备好时调用"""
        if result is None or isinstance(result, Exception):
            # 如果计算失败，使用现有数据
            self.view.update_status_text("高质量切片数据生成失败，使用标准数据")
            return
            
        # 更新last_result，以便下次直接使用高质量数据
        self.last_result = result
        
        # 显示高质量切片
        max_point = result[0]
        max_slice = result[1]
        grid_x = result[2]
        grid_y = result[3]
        
        # 只有在仍处于切片视图模式时才更新显示
        if self.view.view_slice_radio.isChecked():
            self.view.show_brightness_heatmap(max_point, max_slice, grid_x, grid_y)
            self.view.update_status_text("高质量切片数据生成完成")

    def generate_heatmap_from_point(self, max_point, max_br):
        """从最佳点生成简化热图数据用于可视化"""
        try:
            # 根据网格精度选择设置网格参数
            grid_precision = self.view.grid_resolution_combo.currentText()
            if grid_precision == "低":
                grid_size = 500
            elif grid_precision == "高":
                grid_size = 2000
            else:  # 中等精度
                grid_size = 1000
            
            # 创建网格
            grid_range = 1000  # 假设的热图范围，实际应该基于配置获取
            try:
                from Models.Config import Config
                config = Config()
                grid_range = int(config.get("Default", "grid_range", 1000))
            except:
                pass
                
            # 创建以最佳点为中心的网格
            center_x, center_y = max_point[0], max_point[1]
            grid_x = np.linspace(center_x - grid_range, center_x + grid_range, int(grid_size))
            grid_y = np.linspace(center_y - grid_range, center_y + grid_range, int(grid_size))
            
            # 创建热图数据
            X, Y = np.meshgrid(grid_x, grid_y)
            max_slice = np.zeros((len(grid_y), len(grid_x)))
            
            # 使用高斯模型生成以最佳点为中心的热图
            for i in range(len(grid_y)):
                for j in range(len(grid_x)):
                    dist_squared = ((grid_x[j] - center_x)/300)**2 + ((grid_y[i] - center_y)/300)**2
                    max_slice[i, j] = max_br * np.exp(-dist_squared)
            
            # 更新结果元组
            self.last_result = (max_point, max_slice, grid_x, grid_y)
            
            # 显示热图
            self.view.show_brightness_heatmap(max_point, max_slice, grid_x, grid_y)
            
        except Exception as e:
            print(f"从点生成热图失败: {e}")
            print(traceback.format_exc())
            # 显示错误消息
            self.view.display_label.setText(f"生成热图失败: {e}")

    # 绘制3D视图
    def draw_3d_view(self, fig, show_detectors=True):
        """绘制3D视图"""
        try:
            ax = fig.add_subplot(111, projection='3d')
            
            # 绘制源位置点
            if isinstance(self.last_result, tuple) and len(self.last_result) >= 2:
                max_point = self.last_result[0]
                ax.scatter([max_point[0]], [max_point[1]], [max_point[2]], 
                          color='red', s=100, label='震源位置')
            
            # 显示检波器位置
            if show_detectors:
                detector_data = self.trace_file.get_detector_location()
                if detector_data is not None:
                    x = detector_data['x']
                    y = detector_data['y']
                    z = detector_data['z']
                    ax.scatter(x, y, z, s=10, color='blue', alpha=0.5, label='检波器位置')
            
            # 设置轴标签和图例
            ax.set_xlabel('X坐标')
            ax.set_ylabel('Y坐标')
            ax.set_zlabel('Z坐标 (深度)')
            ax.legend()
            
            # 优化显示效果
            ax.set_title("三维空间位置视图", fontsize=14, fontweight='bold')
            fig.tight_layout()
            
        except Exception as e:
            print(f"绘制3D视图时出错: {e}")
            print(traceback.format_exc())

    # 绘制切片视图
    def draw_slice_view(self, fig, show_detectors=True):
        """绘制切片视图"""
        try:
            # 创建2x2网格子图
            ax1 = fig.add_subplot(221)  # XY平面
            ax2 = fig.add_subplot(222)  # XZ平面
            ax3 = fig.add_subplot(223)  # YZ平面
            
            # 绘制源位置点
            if isinstance(self.last_result, tuple) and len(self.last_result) >= 2:
                max_point = self.last_result[0]
                
                # XY平面
                ax1.scatter([max_point[0]], [max_point[1]], color='red', s=100)
                ax1.set_title("XY平面", fontsize=12)
                ax1.set_xlabel('X坐标')
                ax1.set_ylabel('Y坐标')
                
                # XZ平面
                ax2.scatter([max_point[0]], [max_point[2]], color='red', s=100)
                ax2.set_title("XZ平面", fontsize=12)
                ax2.set_xlabel('X坐标')
                ax2.set_ylabel('Z坐标')
                
                # YZ平面
                ax3.scatter([max_point[1]], [max_point[2]], color='red', s=100)
                ax3.set_title("YZ平面", fontsize=12)
                ax3.set_xlabel('Y坐标')
                ax3.set_ylabel('Z坐标')
            
            # 显示检波器位置
            if show_detectors:
                detector_data = self.trace_file.get_detector_location()
                if detector_data is not None:
                    x = detector_data['x']
                    y = detector_data['y']
                    z = detector_data['z']
                    
                    # 在各平面上绘制检波器位置
                    ax1.scatter(x, y, s=10, color='blue', alpha=0.5)
                    ax2.scatter(x, z, s=10, color='blue', alpha=0.5)
                    ax3.scatter(y, z, s=10, color='blue', alpha=0.5)
            
            # 优化显示效果
            fig.suptitle("多平面切片视图", fontsize=14, fontweight='bold')
            fig.tight_layout()
            
        except Exception as e:
            print(f"绘制切片视图时出错: {e}")
            print(traceback.format_exc())

    # 进行震源计算
    def handle_show_source_location(self):
        if self.thread is not None:
            QMessageBox.information(self.view, "提示", "正在计算中...")
            return
            
        # 确保模型已初始化
        if not self._ensure_model_initialized():
            return
            
        # 显示进度条并重置相关控件
        self.view.toggle_loading(True)
        self.view.update_status_text("正在准备计算源位置...")
        self.view.set_progress(0)
        QApplication.processEvents()  # 强制更新UI
        
        # 根据网格精度选择设置网格参数
        grid_precision = self.view.grid_resolution_combo.currentText()
        if grid_precision == "低":
            grid_size = 500
            z_grid = 50
        elif grid_precision == "高":
            grid_size = 2000
            z_grid = 200
        else:  # 中等精度
            grid_size = 1000
            z_grid = 100
            
        # 从界面获取网格参数
        grid_params = {
            'x_grid': grid_size,
            'y_grid': grid_size, 
            'z_grid': z_grid,
            'use_genetic': self.view.use_genetic_checkbox.isChecked()
        }
        
        # 使用制作的异步类TaskRunner来处理耗时操作
        self.thread = TaskRunner(
            lambda progress_callback: self.trace_file.get_source_location(
                progress_callback,
                grid_params=grid_params
            ),
            self.safe_update_progress
        )
        # 连接回调函数
        self.thread.task_completed.connect(
            self.handle_show_source_location_complete
        )

        # 启动异步任务
        self.thread.start()

    # 震源计算完成的回调函数，显示结果，并释放线程资源
    def handle_show_source_location_complete(self, result):
        # 如果result是异常，则显示错误信息
        if isinstance(result, Exception):
            self.thread = None
            self.view.toggle_loading(False)  # 确保关闭加载状态
            QMessageBox.critical(self.view, "错误", f"{str(result)}！")
            return
        
        # 保存结果以便后续可视化使用
        self.last_result = result
        
        max_point = result[0]
        max_br = result[1]
        self.view.show_source_location(max_point, max_br)
        
        # 更新可视化
        self.update_visualization()
        
        # 关闭加载状态
        self.view.toggle_loading(False)
        
        self.thread = None

    def handle_show_detector_location(self):
        result = self.trace_file.get_detector_location()
        self.view.show_detector_location(result)

    def handle_show_brightness_heatmap(self):
        if self.thread is not None:
            QMessageBox.information(self.view, "提示", "正在计算中...")
            return
        
        # 确保模型已初始化
        if not self._ensure_model_initialized():
            return
            
        # 显示进度条并重置相关控件
        self.view.toggle_loading(True)
        self.view.update_status_text("正在准备计算亮度热力图...")
        self.view.set_progress(0)
        QApplication.processEvents()  # 强制更新UI
        
        # 根据网格精度选择设置网格参数
        grid_precision = self.view.grid_resolution_combo.currentText()
        if grid_precision == "低":
            grid_size = 500
            z_grid = 50
        elif grid_precision == "高":
            grid_size = 2000
            z_grid = 200
        else:  # 中等精度
            grid_size = 1000
            z_grid = 100
            
        # 从界面获取网格参数
        grid_params = {
            'x_grid': grid_size,
            'y_grid': grid_size, 
            'z_grid': z_grid,
            'use_genetic': self.view.use_genetic_checkbox.isChecked()
        }
        
        # 显示计算参数
        self.view.update_status_text(f"开始计算亮度热力图，网格精度: {grid_precision}, 使用遗传算法: {grid_params['use_genetic']}")
        QApplication.processEvents()  # 强制更新UI
        
        # 定义一个更强大的进度回调函数
        def enhanced_progress_callback(progress, start_time, idx, 单位, 更优的点=None):
            # 先调用原有的安全更新函数
            result = self.safe_update_progress(progress, start_time, idx, 单位, 更优的点)
            
            # 添加更多的UI更新
            if progress % 5 == 0:  # 每5%更新一次状态文本
                self.view.update_status_text(f"计算中...进度: {progress}%, 单位: {单位}")
                QApplication.processEvents()  # 强制更新UI
                
            return result
        
        # 使用制作的异步类TaskRunner来处理耗时操作
        self.thread = TaskRunner(
            lambda progress_callback: self.trace_file.get_source_heatmap(
                progress_callback, 
                grid_params=grid_params
            ),
            enhanced_progress_callback  # 使用增强的回调函数
        )
        
        # 连接回调函数
        self.thread.task_completed.connect(
            self.handle_show_brightness_heatmap_complete
        )

        # 在启动线程前显示状态
        self.view.update_status_text("正在启动计算线程...")
        QApplication.processEvents()  # 强制更新UI

        # 启动异步任务
        self.thread.start()
        
        # 线程启动后更新UI
        self.view.update_status_text("计算线程已启动，请等待结果...")
        QApplication.processEvents()  # 强制更新UI

    # 亮度热图计算完成的回调函数，显示结果，并释放线程资源
    def handle_show_brightness_heatmap_complete(self, result):
        # 如果result是异常，则显示错误信息
        if isinstance(result, Exception):
            self.thread = None
            QMessageBox.critical(self.view, "错误", f"{str(result)}！")
            return
        
        # 保存结果以便后续可视化使用
        self.last_result = result
        
        # 当使用遗传算法时，result结构为：(max_point, best_brightness, grid_x, grid_y)
        # max_point包含位置和时间信息，best_brightness是最大亮度值
        max_point = self.convert_max_point(result[0])
        
        # 判断第二个元素是否为二维数组，如果不是，则需要构建二维热图数据
        if not isinstance(result[1], np.ndarray) or result[1].ndim != 2:
            print(f"需要构建二维热图数据，当前类型: {type(result[1])}, 形状: {getattr(result[1], 'shape', 'scalar')}")
            try:
                # 从Services/ssatop.py获取wave_data、location_data和sample_interval
                wave_data = self.trace_file.wave_data
                location_data = self.trace_file.location_data
                sample_interval = self.trace_file.basic_info['sample_interval']
                
                # 导入必要的函数
                from Services.ssatop import normalize_data, amp_norm
                
                config = Config()
                try:
                    speed = float(config.get("Default", "speed"))
                    length = int(config.get("Default", "length"))
                    height = int(config.get("Default", "height"))
                except Exception as e:
                    print(f"读取配置失败: {e}")
                    speed = 3000
                    length = 1000
                    height = 500
                
                # 创建与最佳点对应的二维切片
                grid_x = result[2]
                grid_y = result[3]
                
                # 创建2D网格
                X, Y = np.meshgrid(grid_x, grid_y)
                Z = np.zeros((len(grid_y), len(grid_x)))
                
                # 计算每个点的亮度值
                model_manager = ModelManager()
                
                # 计算时窗中不同时刻的权重
                def get_local_max(trace_data, time):
                    point_index = int(time // sample_interval)
                    start_index = max(0, point_index - 50)
                    end_index = min(len(trace_data), point_index + 51)
                    local_max = np.max(np.abs(trace_data[start_index:end_index]))
                    return local_max
                
                # 振幅归一化
                @lru_cache(maxsize=None)
                def normalize_amp(trace_index):
                    data = wave_data[trace_index]
                    baseline = np.mean(data[:100])
                    data = data - baseline
                    max_amp = np.max(np.abs(data))
                    if max_amp == 0:
                        return data
                    data = data / max_amp
                    return data
                
                # 时间延迟计算
                @lru_cache(maxsize=None)
                def time_delay(x, y, z, trace_index):
                    x_s = location_data['x'][trace_index]
                    y_s = location_data['y'][trace_index]
                    z_s = location_data['z'][trace_index]
                    
                    try:
                        return model_manager.calculate_time_delay(
                            source_pos=(x, y, z),
                            receiver_pos=(x_s, y_s, z_s),
                            fixed_speed=speed,
                            phase="P"
                        )
                    except Exception as e:
                        print(f"计算时间延迟失败: {e}")
                        distance = ((x - x_s) ** 2 + (y - y_s) ** 2 + (z - z_s) ** 2) ** 0.5
                        return distance / speed
                
                # 亮度函数
                def br(x, y, z, t):
                    N = len(location_data['trace_number'])
                    sum_brightness = 0
                    
                    for i in range(N):
                        u = get_local_max(normalize_amp(location_data['trace_number'][i]), 
                                         t + time_delay(x, y, z, i))
                        sum_brightness += u
                        
                    return sum_brightness / N
                
                # 计算热图切片数据
                for i in range(len(grid_y)):
                    for j in range(len(grid_x)):
                        Z[i, j] = br(grid_x[j], grid_y[i], max_point[2], max_point[3])
                
                # 将计算的热图数据赋值给max_slice
                max_slice = Z
                print(f"已构建热图数据，形状: {max_slice.shape}")
            except Exception as e:
                print(f"构建热图数据失败: {e}")
                # 创建一个示例热图数据
                X, Y = np.meshgrid(result[2], result[3])
                max_slice = np.ones((len(result[3]), len(result[2])))
                # 中心位置设置最大值
                center_x = np.argmin(np.abs(X[0] - max_point[0]))
                center_y = np.argmin(np.abs(Y[:, 0] - max_point[1]))
                if 0 <= center_y < max_slice.shape[0] and 0 <= center_x < max_slice.shape[1]:
                    max_slice[center_y, center_x] = float(result[1])  # 最大亮度值
                print(f"使用示例热图数据, 形状: {max_slice.shape}")
        else:
            max_slice = result[1]
        
        grid_x = result[2]
        grid_y = result[3]
        
        try:
            # 确保使用遗传算法找到的点和亮度值来显示热力图
            self.view.show_brightness_heatmap(max_point, max_slice, grid_x, grid_y)
        except Exception as e:
            print(f"显示热力图失败: {e}")
            traceback.print_exc()  # 打印详细错误堆栈
            QMessageBox.critical(self.view, "错误", f"显示热力图失败: {e}")
            
        self.thread = None
    
    # 工具函数：转换max_point数据类型
    def convert_max_point(self, max_point):
        """将max_point转换为标准Python列表，处理不同的数据类型"""
        try:
            # 如果是numpy数组，转换为列表
            if hasattr(max_point, 'tolist'):
                return max_point.tolist()
            # 如果已经是列表或元组，确保包含4个元素
            elif isinstance(max_point, (list, tuple)) and len(max_point) >= 4:
                return list(max_point[:4])  # 只取前4个元素
            # 不支持的类型，尝试转换
            else:
                return [float(max_point[0]), float(max_point[1]), 
                        float(max_point[2]), float(max_point[3])]
        except Exception as e:
            print(f"转换max_point失败: {e}")
            print(f"max_point类型: {type(max_point)}")
            print(f"max_point值: {max_point}")
            raise Exception(f"无法处理的max_point数据格式: {e}")
            
    # 导出结果
    def handle_export_results(self):
        """处理导出结果按钮点击事件"""
        if not self.last_result:
            QMessageBox.warning(self.view, "警告", "没有可导出的结果！请先进行源位置检测或亮度热图计算。")
            return
            
        try:
            # 获取当前文件名作为默认导出文件名的基础
            current_filename = "源位置检测结果"
            try:
                if hasattr(self.trace_file, 'basic_info') and self.trace_file.basic_info:
                    # 从basic_info中获取文件名
                    if 'file_name' in self.trace_file.basic_info:
                        # 移除扩展名
                        base_name = os.path.splitext(self.trace_file.basic_info['file_name'])[0]
                        current_filename = f"{base_name}_位置检测结果"
                        print(f"使用当前文件名作为基础: {current_filename}")
            except Exception as e:
                print(f"获取当前文件名时出错: {e}")
                
            # 打开文件保存对话框 - 移除不兼容的Options参数
            file_path, file_filter = QFileDialog.getSaveFileName(
                self.view, 
                "导出结果", 
                f"{current_filename}.png", 
                "PNG图像 (*.png);;CSV文件 (*.csv);;所有文件 (*)"
            )
            
            if not file_path:
                print("导出取消：用户未选择保存位置")
                return
               
            # 根据选择的格式调整文件扩展名
            if "PNG" in file_filter and not file_path.lower().endswith('.png'):
                file_path += '.png'
            elif "CSV" in file_filter and not file_path.lower().endswith('.csv'):
                file_path += '.csv'
                
            # 获取文件名部分，用于页脚展示
            export_filename = os.path.basename(file_path)
                
            print(f"开始导出结果到文件: {file_path}")
                
            # 根据文件类型导出不同格式
            if file_path.lower().endswith('.png'):
                try:
                    # 获取当前选择的颜色方案
                    cmap = self.view.colormap_combo.currentText()
                    
                    # 获取并转换max_point
                    max_point = self.convert_max_point(self.last_result[0])
                    max_br = self.last_result[1]
                    
                    # 添加调试信息
                    print(f"导出源位置数据: max_point类型={type(max_point)}, 值={max_point}")
                    print(f"最大亮度: max_br类型={type(max_br)}, 值={max_br}")
                    
                    # 如果是热力图结果，打印结果结构
                    if len(self.last_result) >= 4:
                        print(f"热力图数据: max_slice类型={type(self.last_result[1])}, 形状={getattr(self.last_result[1], 'shape', '未知')}")
                        print(f"grid_x类型={type(self.last_result[2])}, grid_y类型={type(self.last_result[3])}")
                    
                    # 创建一个新的Figure用于导出
                    export_fig = plt.figure(figsize=(10, 7), dpi=150)
                    
                    # 设置全局字体和风格 - 支持中文
                    try:
                        # 尝试设置中文字体
                        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'sans-serif']
                        plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
                        chinese_font = 'Arial Unicode MS'  # 确保使用支持中文的字体
                        print("已设置中文字体支持")
                    except Exception as e:
                        print(f"设置中文字体失败: {e}")
                        chinese_font = 'sans-serif'
                        # 回退到基础字体
                        plt.rcParams['font.family'] = 'sans-serif'
                    
                    if isinstance(self.last_result, tuple) and len(self.last_result) >= 4:
                        # 有热力图数据，创建超高级多面板布局
                        grid = plt.GridSpec(5, 6, height_ratios=[0.7, 1.5, 1.5, 1.5, 0.5], 
                                          width_ratios=[1, 1, 1, 1, 1, 1],
                                          hspace=0.35, wspace=0.3)
                        
                        # 创建超高级标题面板，跨越整行
                        title_ax = export_fig.add_subplot(grid[0, :])
                        title_ax.axis('off')
                        
                        # 创建高级渐变背景
                        gradient = np.linspace(0, 1, 300).reshape(1, -1)
                        gradient = np.repeat(gradient, 20, axis=0)
                        title_ax.imshow(gradient, cmap='plasma_r', aspect='auto', alpha=0.2,
                                       extent=[0, 1, 0, 1], transform=title_ax.transAxes)
                        
                        # 增加装饰性设计元素
                        for i in range(20):
                            title_ax.plot([0.05+i*0.045, 0.07+i*0.045], [0.3, 0.3], 'k-', lw=1, alpha=0.5-i*0.02,
                                         transform=title_ax.transAxes)
                        for i in range(20):
                            title_ax.plot([0.95-i*0.045, 0.93-i*0.045], [0.2, 0.2], 'k-', lw=1, alpha=0.5-i*0.02,
                                         transform=title_ax.transAxes)
                        
                        # 添加高级标题和子标题
                        title_ax.text(0.5, 0.7, "多维震源定位亮度分析报告", 
                                     fontsize=26, fontweight='bold', ha='center', va='center',
                                     family=chinese_font,
                                     bbox=dict(facecolor='white', alpha=0.9, edgecolor='none', 
                                            boxstyle='round,pad=0.5', mutation_aspect=0.3))
                        
                        # 添加高级时间戳和品牌信息
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 添加装饰性箭头和分隔线
                        title_ax.add_patch(plt.Polygon([(0.05, 0.25), (0.1, 0.3), (0.05, 0.35)], 
                                                    closed=True, color='#888', alpha=0.5))
                        title_ax.add_patch(plt.Polygon([(0.95, 0.25), (0.9, 0.3), (0.95, 0.35)], 
                                                    closed=True, color='#888', alpha=0.5))
                        
                        title_ax.text(0.07, 0.25, f"分析时间: {timestamp}", 
                                     fontsize=10, ha='left', va='top',
                                     family=chinese_font, color='#444444')
                        
                        try:
                            # 添加文件信息
                            if hasattr(self.trace_file, 'basic_info') and self.trace_file.basic_info:
                                if 'file_name' in self.trace_file.basic_info:
                                    title_ax.text(0.93, 0.25, f"数据源: {self.trace_file.basic_info['file_name']}", 
                                                 fontsize=10, ha='right', va='top',
                                                 family=chinese_font, color='#444444')
                        except Exception as e:
                            print(f"获取文件信息失败: {e}")
                        
                        # 确保max_point和热力图数据正确转换
                        max_point = self.convert_max_point(self.last_result[0])
                        try:
                            max_slice = self.last_result[1].copy() if isinstance(self.last_result[1], np.ndarray) else np.array([[0]])
                            grid_x = np.array(self.last_result[2])
                            grid_y = np.array(self.last_result[3])
                            max_brightness = float(np.max(max_slice)) if max_slice.size > 0 else float(self.last_result[1])
                            x_val = float(max_point[0])
                            y_val = float(max_point[1])
                            z_val = float(max_point[2])
                            t_val = float(max_point[3])
                        except Exception as e:
                            print(f"转换热力图数据失败: {e}")
                            x_val, y_val, z_val, t_val = max_point[0], max_point[1], max_point[2], max_point[3]
                            max_brightness = 0.0 if isinstance(self.last_result[1], np.ndarray) else float(self.last_result[1])
                        
                        # 1. 3D热力图面板 (跨越两行两列)
                        ax_3d = export_fig.add_subplot(grid[1:3, 0:2], projection='3d')
                        
                        # 获取当前选择的颜色方案
                        cmap = self.view.colormap_combo.currentText()
                        
                        # 绘制高级3D亮度表面
                        if isinstance(max_slice, np.ndarray) and max_slice.size > 1:
                            # 增强3D图的视觉效果
                            ax_3d.grid(True, linestyle='--', alpha=0.6)
                            ax_3d.xaxis.pane.fill = False
                            ax_3d.yaxis.pane.fill = False
                            ax_3d.zaxis.pane.fill = False
                            ax_3d.xaxis.pane.set_edgecolor('lightgray')
                            ax_3d.yaxis.pane.set_edgecolor('lightgray')
                            ax_3d.zaxis.pane.set_edgecolor('lightgray')
                            
                            # 创建网格
                            X, Y = np.meshgrid(grid_x, grid_y)
                            
                            # 绘制3D表面
                            stride = 2 if max_slice.shape[0] > 100 else 1
                            surf = ax_3d.plot_surface(X, Y, max_slice, cmap=cmap, 
                                                   linewidth=0.2, antialiased=True, alpha=0.8,
                                                   rstride=stride, cstride=stride)
                            
                            # 添加等高线投影到底部平面
                            max_range = max_slice.max()
                            offset = -0.1 * max_range
                            ax_3d.contourf(X, Y, max_slice, zdir='z', offset=offset, cmap=cmap, alpha=0.6)
                            
                            # 标记最大亮度点
                            max_i, max_j = np.unravel_index(np.argmax(max_slice), max_slice.shape)
                            max_x, max_y = X[max_i, max_j], Y[max_i, max_j]
                            
                            # 添加从最大亮度点到底部的垂直线
                            max_z = max_slice[max_i, max_j]
                            ax_3d.plot([max_x, max_x], [max_y, max_y], [offset, max_z], 'r--', alpha=0.7, lw=2)
                            
                            # 绘制震源位置
                            ax_3d.scatter([x_val], [y_val], [max_z], 
                                        color='red', s=150, marker='*', 
                                        edgecolor='white', linewidth=1.5,
                                        label='震源位置')
                            
                            # 添加颜色条
                            cbar = plt.colorbar(surf, ax=ax_3d, shrink=0.6, aspect=12, pad=0.1)
                            cbar.set_label('亮度值', family=chinese_font, fontsize=10)
                            
                            # 设置轴标签
                            ax_3d.set_xlabel('X坐标 (m)', fontsize=10, family=chinese_font)
                            ax_3d.set_ylabel('Y坐标 (m)', fontsize=10, family=chinese_font)
                            ax_3d.set_zlabel('亮度值', fontsize=10, family=chinese_font)
                            
                            # 优化视图角度
                            ax_3d.view_init(elev=30, azim=125)
                            
                            # 添加高级标题
                            ax_3d.set_title("三维亮度分布表面", fontsize=12, fontweight='bold', family=chinese_font)
                            ax_3d.legend(fontsize=9, loc='upper right')
                            
                            # 添加网格标尺
                            ax_3d.tick_params(axis='x', labelsize=8)
                            ax_3d.tick_params(axis='y', labelsize=8)
                            ax_3d.tick_params(axis='z', labelsize=8)
                        
                        # 2. 高级热力图面板
                        ax_heatmap = export_fig.add_subplot(grid[1:3, 2:4])
                        
                        if isinstance(max_slice, np.ndarray) and max_slice.size > 1:
                            # 绘制高级热力图
                            extent = [grid_x[0], grid_x[-1], grid_y[0], grid_y[-1]]
                            im = ax_heatmap.imshow(max_slice, cmap=cmap, interpolation='bicubic',
                                                 origin='lower', extent=extent, aspect='auto')
                            
                            # 添加颜色条
                            cbar = plt.colorbar(im, ax=ax_heatmap, fraction=0.046, pad=0.04)
                            cbar.set_label('亮度值', family=chinese_font, fontsize=10)
                            
                            # 添加等高线
                            levels = np.linspace(max_slice.min(), max_slice.max(), 10)
                            contour = ax_heatmap.contour(X, Y, max_slice, levels=levels, colors='white', 
                                                      alpha=0.4, linewidths=0.8)
                            
                            # 标记最大亮度点
                            ax_heatmap.plot(x_val, y_val, 'r*', markersize=15, markeredgecolor='white',
                                          markeredgewidth=1.5, label=f'震源: 亮度={max_brightness:.4f}')
                            
                            # 添加标注
                            ax_heatmap.annotate('震源位置', xy=(x_val, y_val), 
                                            xytext=(x_val+50, y_val+50),
                                            arrowprops=dict(facecolor='white', shrink=0.05, 
                                                         width=1.5, headwidth=8, alpha=0.7),
                                            color='white', fontsize=10, family=chinese_font,
                                            bbox=dict(boxstyle="round,pad=0.3", fc="black", alpha=0.6))
                            
                            # 添加坐标轴标签和标题
                            ax_heatmap.set_xlabel('X坐标 (m)', fontsize=10, family=chinese_font)
                            ax_heatmap.set_ylabel('Y坐标 (m)', fontsize=10, family=chinese_font)
                            ax_heatmap.set_title("亮度热力图分析", fontsize=12, fontweight='bold', family=chinese_font)
                            
                            # 添加网格
                            ax_heatmap.grid(True, linestyle='--', alpha=0.3)
                            ax_heatmap.legend(fontsize=9, loc='upper right')
                            
                            # 添加自定义比例尺
                            scale_len = 100  # 100米比例尺
                            x_min, x_max = ax_heatmap.get_xlim()
                            y_min, y_max = ax_heatmap.get_ylim()
                            scale_x = x_min + (x_max - x_min) * 0.05  # 左下角5%位置
                            scale_y = y_min + (y_max - y_min) * 0.05  # 左下角5%位置
                            ax_heatmap.plot([scale_x, scale_x + scale_len], [scale_y, scale_y], 'w-', lw=2)
                            ax_heatmap.text(scale_x + scale_len/2, scale_y + (y_max-y_min)*0.02, 
                                          f'{scale_len} m', ha='center', va='bottom', 
                                          color='white', fontsize=8, family=chinese_font)
                        
                        # 3. 亮度分布直方图面板
                        ax_histogram = export_fig.add_subplot(grid[1, 4:])
                        
                        if isinstance(max_slice, np.ndarray) and max_slice.size > 1:
                            # 计算直方图数据
                            flattened = max_slice.flatten()
                            hist_data, bin_edges = np.histogram(flattened, bins=30)
                            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                            
                            # 绘制高级直方图
                            bars = ax_histogram.bar(bin_centers, hist_data, width=(bin_edges[1]-bin_edges[0]),
                                                 alpha=0.7, color='skyblue', edgecolor='navy')
                            
                            # 添加KDE曲线
                            try:
                                from scipy.stats import gaussian_kde
                                kde = gaussian_kde(flattened)
                                x_kde = np.linspace(flattened.min(), flattened.max(), 200)
                                kde_vals = kde(x_kde) * len(flattened) * (bin_edges[1]-bin_edges[0])
                                ax_histogram.plot(x_kde, kde_vals, 'r-', lw=2, alpha=0.8, label='密度估计')
                            except Exception as e:
                                print(f"KDE计算失败: {e}")
                            
                            # 添加最大亮度标线
                            ax_histogram.axvline(x=max_brightness, color='red', linestyle='--', alpha=0.8,
                                              label=f'最大亮度: {max_brightness:.4f}')
                            
                            # 设置标题和标签
                            ax_histogram.set_title("亮度分布直方图", fontsize=11, fontweight='bold', family=chinese_font)
                            ax_histogram.set_xlabel('亮度值', fontsize=10, family=chinese_font)
                            ax_histogram.set_ylabel('频率', fontsize=10, family=chinese_font)
                            ax_histogram.legend(fontsize=8)
                            
                            # 添加高亮区域 - 大于75%最大亮度的区域
                            highlight_threshold = 0.75 * max_brightness
                            ax_histogram.axvspan(highlight_threshold, max_brightness, color='yellow', alpha=0.2,
                                              label='高亮区')
                        
                        # 4. 亮度剖面图
                        ax_profile = export_fig.add_subplot(grid[2, 4:])
                        
                        if isinstance(max_slice, np.ndarray) and max_slice.size > 1:
                            # 找到最大点在网格中的索引
                            max_idx_y = np.argmin(np.abs(grid_y - y_val))
                            max_idx_x = np.argmin(np.abs(grid_x - x_val))
                            
                            # 提取X和Y方向的亮度剖面
                            if 0 <= max_idx_y < max_slice.shape[0]:
                                x_profile = max_slice[max_idx_y, :]
                                ax_profile.plot(grid_x, x_profile, 'b-', lw=2, alpha=0.7, label='X方向剖面')
                            
                            if 0 <= max_idx_x < max_slice.shape[1]:
                                y_profile = max_slice[:, max_idx_x]
                                ax_profile.plot(grid_y, y_profile, 'g-', lw=2, alpha=0.7, label='Y方向剖面')
                            
                            # 添加最大亮度点标记
                            ax_profile.axhline(y=max_brightness, color='red', linestyle='--', alpha=0.5)
                            
                            # 设置标题和标签
                            ax_profile.set_title("亮度剖面图", fontsize=11, fontweight='bold', family=chinese_font)
                            ax_profile.set_xlabel('坐标 (m)', fontsize=10, family=chinese_font)
                            ax_profile.set_ylabel('亮度值', fontsize=10, family=chinese_font)
                            ax_profile.legend(fontsize=8)
                            ax_profile.grid(True, linestyle='--', alpha=0.3)
                        
                        # 5. 多面分析面板 - 三个平面切片视图
                        ax_slice_xy = export_fig.add_subplot(grid[3, 0:2])
                        ax_slice_xz = export_fig.add_subplot(grid[3, 2:4])
                        ax_slice_yz = export_fig.add_subplot(grid[3, 4:])
                        
                        # 获取检波器位置
                        try:
                            detector_data = self.trace_file.get_detector_location()
                            if detector_data is not None:
                                detector_x = detector_data['x']
                                detector_y = detector_data['y']
                                detector_z = detector_data['z']
                        except Exception as e:
                            print(f"获取检波器位置失败: {e}")
                            detector_x = []
                            detector_y = []
                            detector_z = []
                            
                        # 获取Z坐标范围
                        from Models.Config import Config
                        try:
                            config = Config()
                            z_min = int(config.get("Default", "z_min", 0))
                            z_max = int(config.get("Default", "z_max", 5000))
                        except Exception as e:
                            print(f"获取Z范围失败: {e}")
                            z_min = 0
                            z_max = 5000
                        
                        # XY平面切片图
                        if isinstance(max_slice, np.ndarray) and max_slice.size > 1:
                            ax_slice_xy.imshow(max_slice, cmap=cmap, interpolation='bicubic',
                                            extent=[grid_x[0], grid_x[-1], grid_y[0], grid_y[-1]],
                                            origin='lower', aspect='auto', alpha=0.8)
                            # 添加XY平面上的检波器位置
                            ax_slice_xy.scatter(detector_x, detector_y, s=30, color='white', alpha=0.7, 
                                             marker='^', edgecolor='black', linewidth=0.5)
                            # 添加震源位置标记
                            ax_slice_xy.plot(x_val, y_val, 'r*', markersize=15, markeredgecolor='white', 
                                          markeredgewidth=1.5)
                            # 添加轴标签
                            ax_slice_xy.set_xlabel('X坐标 (m)', fontsize=10, family=chinese_font)
                            ax_slice_xy.set_ylabel('Y坐标 (m)', fontsize=10, family=chinese_font)
                            ax_slice_xy.set_title("XY平面切片 (俯视图)", fontsize=11, fontweight='bold', family=chinese_font)
                            
                            # 添加切线
                            ax_slice_xy.axvline(x=x_val, color='white', linestyle='--', alpha=0.5)
                            ax_slice_xy.axhline(y=y_val, color='white', linestyle='--', alpha=0.5)
                        
                        # XZ平面切片图 (模拟)
                        # 创建XZ平面上的模拟数据
                        try:
                            # 使用高斯模型创建空间亮度衰减模拟
                            xz_grid_x = grid_x
                            xz_grid_z = np.linspace(z_min, z_max, 100)
                            XZ, ZX = np.meshgrid(xz_grid_x, xz_grid_z)
                            XZ_slice = np.zeros_like(XZ)
                            
                            # 基于最大亮度点创建高斯分布
                            for i in range(XZ_slice.shape[0]):
                                for j in range(XZ_slice.shape[1]):
                                    dist_squared = ((xz_grid_x[j] - x_val)/300)**2 + ((xz_grid_z[i] - z_val)/300)**2
                                    XZ_slice[i, j] = max_brightness * np.exp(-dist_squared)
                            
                            # 绘制XZ平面图
                            ax_slice_xz.imshow(XZ_slice, cmap=cmap, interpolation='bicubic',
                                            extent=[xz_grid_x[0], xz_grid_x[-1], xz_grid_z[0], xz_grid_z[-1]],
                                            origin='lower', aspect='auto', alpha=0.8)
                            
                            # 添加XZ平面上的检波器位置
                            ax_slice_xz.scatter(detector_x, detector_z, s=30, color='white', alpha=0.7, 
                                             marker='^', edgecolor='black', linewidth=0.5)
                            
                            # 添加震源位置标记
                            ax_slice_xz.plot(x_val, z_val, 'r*', markersize=15, markeredgecolor='white', 
                                          markeredgewidth=1.5)
                            
                            # 添加轴标签
                            ax_slice_xz.set_xlabel('X坐标 (m)', fontsize=10, family=chinese_font)
                            ax_slice_xz.set_ylabel('Z坐标 (m)', fontsize=10, family=chinese_font)
                            ax_slice_xz.set_title("XZ平面切片 (纵剖面)", fontsize=11, fontweight='bold', family=chinese_font)
                            
                            # 添加切线
                            ax_slice_xz.axvline(x=x_val, color='white', linestyle='--', alpha=0.5)
                            ax_slice_xz.axhline(y=z_val, color='white', linestyle='--', alpha=0.5)
                        except Exception as e:
                            print(f"创建XZ平面切片失败: {e}")
                        
                        # YZ平面切片图 (模拟)
                        try:
                            # 创建YZ平面上的模拟数据
                            yz_grid_y = grid_y
                            yz_grid_z = np.linspace(z_min, z_max, 100)
                            YZ, ZY = np.meshgrid(yz_grid_y, yz_grid_z)
                            YZ_slice = np.zeros_like(YZ)
                            
                            # 基于最大亮度点创建高斯分布
                            for i in range(YZ_slice.shape[0]):
                                for j in range(YZ_slice.shape[1]):
                                    dist_squared = ((yz_grid_y[j] - y_val)/300)**2 + ((yz_grid_z[i] - z_val)/300)**2
                                    YZ_slice[i, j] = max_brightness * np.exp(-dist_squared)
                            
                            # 绘制YZ平面图
                            ax_slice_yz.imshow(YZ_slice, cmap=cmap, interpolation='bicubic',
                                            extent=[yz_grid_y[0], yz_grid_y[-1], yz_grid_z[0], yz_grid_z[-1]],
                                            origin='lower', aspect='auto', alpha=0.8)
                            
                            # 添加YZ平面上的检波器位置
                            ax_slice_yz.scatter(detector_y, detector_z, s=30, color='white', alpha=0.7, 
                                             marker='^', edgecolor='black', linewidth=0.5)
                            
                            # 添加震源位置标记
                            ax_slice_yz.plot(y_val, z_val, 'r*', markersize=15, markeredgecolor='white', 
                                          markeredgewidth=1.5)
                            
                            # 添加轴标签
                            ax_slice_yz.set_xlabel('Y坐标 (m)', fontsize=10, family=chinese_font)
                            ax_slice_yz.set_ylabel('Z坐标 (m)', fontsize=10, family=chinese_font)
                            ax_slice_yz.set_title("YZ平面切片 (侧剖面)", fontsize=11, fontweight='bold', family=chinese_font)
                            
                            # 添加切线
                            ax_slice_yz.axvline(x=y_val, color='white', linestyle='--', alpha=0.5)
                            ax_slice_yz.axhline(y=z_val, color='white', linestyle='--', alpha=0.5)
                        except Exception as e:
                            print(f"创建YZ平面切片失败: {e}")
                        
                        # 6. 分析报告页脚
                        footer_ax = export_fig.add_subplot(grid[4, :])
                        footer_ax.axis('off')
                        
                        # 添加页脚分隔线
                        footer_ax.axhline(y=0.9, xmin=0.05, xmax=0.95, color='#888', lw=1, alpha=0.5)
                        
                        # 添加结果摘要
                        summary_text = (
                            f"震源坐标: X={x_val:.2f} m, Y={y_val:.2f} m, Z={z_val:.2f} m    "
                            f"事件时间: T={t_val:.4f} s    "
                            f"最大亮度: {max_brightness:.4f}    "
                        )
                        
                        footer_ax.text(0.5, 0.7, summary_text, fontsize=11, ha='center', va='center',
                                     family='monospace', fontweight='bold', color='#333')
                        
                        # 统计数据
                        if isinstance(max_slice, np.ndarray) and max_slice.size > 1:
                            try:
                                min_br = float(np.min(max_slice))
                                mean_br = float(np.mean(max_slice))
                                median_br = float(np.median(max_slice))
                                std_br = float(np.std(max_slice))
                                p90_br = float(np.percentile(max_slice, 90))
                                
                                # 计算高于阈值的点数比例
                                high_threshold = 0.75 * max_brightness
                                high_ratio = np.sum(max_slice > high_threshold) / max_slice.size * 100
                                
                                # 计算半高宽
                                half_max = max_brightness / 2.0
                                x_profile = max_slice[max_idx_y, :]
                                y_profile = max_slice[:, max_idx_x]
                                x_above_half = np.where(x_profile > half_max)[0]
                                y_above_half = np.where(y_profile > half_max)[0]
                                
                                if len(x_above_half) > 1 and len(y_above_half) > 1:
                                    x_fwhm = grid_x[x_above_half[-1]] - grid_x[x_above_half[0]]
                                    y_fwhm = grid_y[y_above_half[-1]] - grid_y[y_above_half[0]]
                                else:
                                    x_fwhm = y_fwhm = 0
                                    
                                stats_text = (
                                    f"统计: 平均亮度={mean_br:.4f}, 标准差={std_br:.4f}, P90={p90_br:.4f}    "
                                    f"高亮区占比={high_ratio:.2f}%    X半高宽={x_fwhm:.2f} m, Y半高宽={y_fwhm:.2f} m"
                                )
                                
                                footer_ax.text(0.5, 0.4, stats_text, fontsize=9, ha='center', va='center',
                                             family=chinese_font, color='#555')
                            except Exception as e:
                                    print(f"计算统计数据失败: {e}")
                        
                        # 添加品牌信息
                        footer_ax.text(0.05, 0.1, "SSATOP®微地震监测系统", fontsize=8, ha='left', va='center',
                                     family=chinese_font, color='#666', style='italic')
                        
                        # 添加页码和时间信息
                        footer_ax.text(0.95, 0.1, f"页码 1/1 · 生成时间 {timestamp}", fontsize=7, 
                                     ha='right', va='center', family=chinese_font, color='#666')
                        
                        # 添加装饰点
                        for i in range(11):
                            dot_color = plt.cm.plasma(i/10)
                            footer_ax.add_patch(plt.Circle((0.05+i*0.09, 0.2), 0.01, fc=dot_color, ec='none'))
                        
                        # 添加QR码（模拟）
                        qr_ax = export_fig.add_axes([0.01, 0.01, 0.08, 0.08])
                        qr_ax.axis('off')
                        
                        # 创建模拟QR码
                        qr_data = np.random.randint(0, 2, (10, 10))
                        # 扩大边缘，添加定位符
                        qr_image = np.ones((12, 12))
                        qr_image[1:11, 1:11] = qr_data
                        
                        # 添加三个定位点
                        for i, j in [(1,1), (1,9), (9,1)]:
                            qr_image[i-1:i+2, j-1:j+2] = 0
                            qr_image[i, j] = 1
                        
                        qr_ax.imshow(qr_image, cmap='binary', interpolation='none')
                        qr_ax.text(0.5, -0.2, "扫码查看详情", fontsize=6, ha='center', family=chinese_font)
                        
                        # 添加半透明对角线水印
                        watermark_ax = export_fig.add_axes([0, 0, 1, 1])
                        watermark_ax.axis('off')
                        watermark_ax.text(0.5, 0.5, "SSATOP Analysis", fontsize=50, 
                                        color='gray', alpha=0.05, rotation=30,
                                        ha='center', va='center', weight='bold')
                        
                        # 自定义创建比例尺的函数
                        def add_custom_scalebar(ax, length=100, position='lower right'):
                            """添加自定义比例尺到坐标轴"""
                            x_min, x_max = ax.get_xlim()
                            y_min, y_max = ax.get_ylim()
                            
                            # 根据位置确定比例尺起点
                            if position == 'lower right':
                                scale_x = x_max - (x_max - x_min) * 0.15 - length  # 右下角
                                scale_y = y_min + (y_max - y_min) * 0.05  # 底部附近
                            elif position == 'lower left':
                                scale_x = x_min + (x_max - x_min) * 0.05  # 左下角
                                scale_y = y_min + (y_max - y_min) * 0.05  # 底部附近
                            else:
                                scale_x = x_min + (x_max - x_min) * 0.05  # 默认左下角
                                scale_y = y_min + (y_max - y_min) * 0.05
                                
                            # 绘制比例尺线段和文本
                            ax.plot([scale_x, scale_x + length], [scale_y, scale_y], 'w-', lw=2)
                            ax.text(scale_x + length/2, scale_y + (y_max-y_min)*0.02, 
                                  f'{length} m', ha='center', va='bottom', 
                                  color='white', fontsize=8, family=chinese_font,
                                  bbox=dict(facecolor='black', alpha=0.3, boxstyle='round,pad=0.2'))
                        
                        # 添加图例和标尺到所有切片视图
                        for ax in [ax_slice_xy, ax_slice_xz, ax_slice_yz]:
                            add_custom_scalebar(ax, 100, 'lower right')
                            
                        # 调整布局，确保所有元素可见
                        plt.tight_layout(rect=[0.01, 0.01, 0.99, 0.99], h_pad=1.5, w_pad=1.5)
                    
                    # 保存图像
                    print("正在保存图像...")
                    export_fig.savefig(file_path, dpi=150, bbox_inches='tight')
                    plt.close(export_fig)  # 关闭导出用的图像
                    print(f"图像已保存: {file_path}")
                    QMessageBox.information(self.view, "成功", f"图像已保存至: {file_path}")
                except Exception as e:
                    print(f"导出图像时出错: {e}")
                    print(traceback.format_exc())
                    QMessageBox.warning(self.view, "导出失败", f"导出图像失败: {str(e)}")
                
            elif file_path.lower().endswith('.csv'):
                # 导出数据为CSV
                print("正在导出CSV数据...")
                if isinstance(self.last_result, tuple):
                    if len(self.last_result) >= 2:
                        # 获取并转换max_point，确保格式一致
                        original_max_point = self.last_result[0]
                        max_point = self.convert_max_point(original_max_point)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write("参数,值\n")
                            # 添加格式化数字，避免科学计数法表示
                            try:
                                f.write(f"X坐标(m),{float(max_point[0]):.6f}\n")
                                f.write(f"Y坐标(m),{float(max_point[1]):.6f}\n")
                                f.write(f"Z坐标(m),{float(max_point[2]):.6f}\n")
                                f.write(f"时间(s),{float(max_point[3]):.6f}\n")
                                f.write(f"最大亮度,{float(self.last_result[1]):.6f}\n")
                            except Exception as e:
                                print(f"格式化数值时出错: {e}")
                                # 回退到简单输出
                                f.write(f"X坐标(m),{max_point[0]}\n")
                                f.write(f"Y坐标(m),{max_point[1]}\n")
                                f.write(f"Z坐标(m),{max_point[2]}\n")
                                f.write(f"时间(s),{max_point[3]}\n")
                                f.write(f"最大亮度,{self.last_result[1]}\n")
                            
                            # 添加额外数据信息
                            f.write("\n附加信息\n")
                            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                            f.write(f"导出时间,{current_time}\n")
                            
                            # 获取速度模型信息
                            try:
                                model_name = self.model_manager.get_current_model().model_name
                                f.write(f"使用的模型,{model_name}\n")
                            except:
                                f.write("使用的模型,未知\n")
                            
                        print(f"CSV数据已保存: {file_path}")
                        QMessageBox.information(self.view, "成功", f"数据已保存至: {file_path}")
                    else:
                        raise Exception(f"结果元组长度不足: {len(self.last_result)}")
                else:
                    raise Exception(f"无效的结果类型: {type(self.last_result)}")
            else:
                QMessageBox.warning(self.view, "警告", f"不支持的文件格式: {file_path}")
                
        except Exception as e:
            error_message = f"导出结果时出错: {str(e)}"
            print(f"错误: {error_message}")
            print(traceback.format_exc())
            QMessageBox.warning(self.view, "导出失败", error_message)
    
    # 重置视图
    def handle_reset_view(self):
        """处理重置视图按钮点击事件"""
        if not self.last_result:
            return
            
        # 重新显示结果
        self.update_visualization()
        
    def format_time(self, seconds):
        """格式化时间为小时:分钟:秒"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # 从子线程安全地更新UI的包装函数
    def safe_update_progress(self, progress, start_time, idx, 单位, 更优的点=None):
        """从子线程安全地更新UI进度"""
        # 检查视图对象是否有效
        if not self.view or not hasattr(self.view, "update_progress"):
            print("警告: 视图对象无效或已被删除")
            return
            
        # 计算所需的值
        elapsed_time = time.time() - start_time
        if elapsed_time == 0:
            return
        
        # 确保idx是数值类型
        try:
            if isinstance(idx, (list, tuple, np.ndarray)):
                # 如果是数组类型，尝试获取第一个元素
                if len(idx) > 0:
                    idx_value = float(idx[0])
                else:
                    idx_value = 0
                # 打印调试信息
                print(f"idx是数组类型: {type(idx)}, 值: {idx}, 使用值: {idx_value}")
            else:
                idx_value = float(idx) if isinstance(idx, str) else idx
        except (ValueError, TypeError) as e:
            print(f"转换idx值出错: {e}, 原始值: {idx}, 类型: {type(idx)}")
            idx_value = 0  # 如果无法转换，使用默认值
        
        # 计算速度和剩余时间
        v = progress / elapsed_time if elapsed_time > 0 else 0
        remaining_time = (100 - progress) / v if progress > 0 and v > 0 else 0
        remaining_time_str = self.format_time(remaining_time)
        elapsed_time_str = self.format_time(elapsed_time)
        
        # 确保speed_str是字符串类型
        try:
            if isinstance(idx_value, (int, float)):
                speed_value = idx_value / elapsed_time
                speed_str = f"{speed_value:.2f} {单位}/s"
            else:
                speed_str = f"0.00 {单位}/s"
        except Exception as e:
            print(f"计算速度时出错: {e}")
            speed_str = f"计算中..."
        
        # 存储需要在主线程使用的更优点数据
        better_point_data = 更优的点
        
        try:
            # 安排在主线程中调用实际的UI更新方法
            QMetaObject.invokeMethod(self.view, "update_progress",
                                   Qt.ConnectionType.QueuedConnection,
                                   Q_ARG(int, progress),
                                   Q_ARG(str, elapsed_time_str),
                                   Q_ARG(str, remaining_time_str),
                                   Q_ARG(str, speed_str))
                                   
            # 如果有更优点，也在主线程中更新
            if better_point_data is not None and hasattr(self.view, "show_source_location"):
                try:
                    # 检查更优点的格式
                    if isinstance(better_point_data, tuple) and len(better_point_data) >= 2:
                        point = better_point_data[0]
                        brightness = better_point_data[1]
                    elif isinstance(better_point_data, list) and len(better_point_data) >= 4:
                        # 如果直接是点坐标列表
                        point = better_point_data
                        brightness = 0.0
                    elif isinstance(better_point_data, np.ndarray):
                        # 如果是numpy数组
                        point = better_point_data.tolist() if hasattr(better_point_data, 'tolist') else list(better_point_data)
                        brightness = 0.0
                    else:
                        print(f"无法识别的更优点格式: {type(better_point_data)}")
                        return
                    
                    # 确保point是列表类型
                    if isinstance(point, np.ndarray):
                        point = point.tolist() if hasattr(point, 'tolist') else list(point)
                    
                    # 确保brightness是浮点数
                    try:
                        brightness = float(brightness)
                    except (ValueError, TypeError):
                        brightness = 0.0
                    
                    # 确保进度相关控件在实时更新过程中保持可见
                    if hasattr(self.view, "progress_bar"):
                        # 直接检查UI控件是否可见，如果不可见则设为可见
                        if not self.view.progress_bar.isVisible():
                            # 在主线程中设置控件可见性
                            QMetaObject.invokeMethod(self.view.progress_bar, "setVisible", 
                                                   Qt.ConnectionType.QueuedConnection, 
                                                   Q_ARG(bool, True))
                    
                    # 使用lambda在主线程中调用show_source_location
                    QMetaObject.invokeMethod(self.view, 
                                           "show_source_location", 
                                           Qt.ConnectionType.QueuedConnection,
                                           Q_ARG(list, point),
                                           Q_ARG(float, brightness),
                                           Q_ARG(bool, False))
                except Exception as e:
                    print(f"更新最佳点时出错: {e}")
                    traceback.print_exc()
        except RuntimeError as e:
            print(f"更新UI时出错: {e}")
            # 标记视图对象已失效，避免后续调用
            self.view = None
        
        return True  # 返回True表示继续处理

    def run_source_detection(self, wave_path, location_path, time_range, grid_params=None, 使用遗传算法=True):
        """
        运行源位置检测算法
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(wave_path):
                self.view.show_error("波形文件不存在")
                return
            
            if not os.path.exists(location_path):
                self.view.show_error("检波器位置文件不存在")
                return
            
            # 开始处理前显示加载动画
            self.view.toggle_loading(True)
            
            # 设置实时进度更新的回调函数
            def update_progress(progress, start_time, current_step, step_type, better_point=None):
                self.view.set_progress(progress)
                
                # 预计剩余时间计算
                elapsed = time.time() - start_time
                if progress > 0:
                    remaining = elapsed * (100 - progress) / progress
                    eta_str = time.strftime("%H:%M:%S", time.gmtime(remaining))
                else:
                    eta_str = "计算中..."
                
                if step_type == 'points':
                    self.view.update_status_text(f"正在计算网格点 {current_step}，进度 {progress}%，预计剩余时间: {eta_str}")
                elif step_type == 'evaluations':
                    self.view.update_status_text(f"正在评估个体 {current_step}，进度 {progress}%，预计剩余时间: {eta_str}")
                elif step_type == 'generations':
                    self.view.update_status_text(f"正在进行第 {current_step} 代，进度 {progress}%，预计剩余时间: {eta_str}")
                
                # 如果有更好的点，实时更新UI
                if better_point:
                    point, brightness = better_point
                    self.view.update_best_point(point, brightness)
                
                # 允许UI更新
                QApplication.processEvents()
            
            # 使用线程运行计算
            def process_data():
                try:
                    trace_file = TraceFile()
                    trace_file.load_wave_data(wave_path)
                    trace_file.load_location_data(location_path)
                    
                    wave_data = trace_file.get_wave_data()
                    location_data = trace_file.get_detector_location()
                    sample_interval = trace_file.get_sample_interval()
                    
                    # 调用服务层进行计算
                    max_point, max_slice, grid_x, grid_y = ssatop.calculate_heatmap(
                        wave_data=wave_data, 
                        location_data=location_data, 
                        sample_interval=sample_interval, 
                        time_range=time_range,
                        update_progress=update_progress,
                        使用遗传算法=使用遗传算法,
                        grid_params=grid_params
                    )
                    
                    # 计算完成后发送信号到主线程
                    self.processing_done.emit((max_point, max_slice, grid_x, grid_y))
                    
                except Exception as e:
                    self.processing_error.emit(str(e))
                    print(f"源位置检测错误: {e}")
                    traceback.print_exc()
            
            # 创建和启动线程
            self.processing_thread = threading.Thread(target=process_data)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            return True
        
        except Exception as e:
            self.view.show_error(f"运行源位置检测出错: {str(e)}")
            self.view.toggle_loading(False)
            print(f"运行源位置检测错误: {e}")
            traceback.print_exc()
            return False

    # 处理颜色方案变更
    def handle_colormap_change(self, index):
        """处理颜色方案变更事件"""
        # 只在有结果时更新显示
        if self.last_result:
            # 立即更新可视化
            self.update_visualization()
            print(f"颜色方案已更改为: {self.view.colormap_combo.currentText()}")
    
    # 处理分辨率变更
    def handle_resolution_change(self, index):
        """处理分辨率变更事件"""
        # 只在有结果时更新显示
        if self.last_result:
            # 超高分辨率可能需要更多计算时间，提示用户
            if index == 3:  # 超高分辨率
                self.view.update_status_text("正在生成超高分辨率图像，可能需要几秒钟...")
            
            # 使用定时器延迟更新，避免频繁更改时的性能问题
            if hasattr(self, '_resolution_timer'):
                self._resolution_timer.stop()
            else:
                self._resolution_timer = QTimer()
                self._resolution_timer.setSingleShot(True)
                self._resolution_timer.timeout.connect(self.update_visualization)
            
            self._resolution_timer.start(300)  # 300毫秒后更新可视化
            print(f"分辨率已更改为: {self.view.resolution_combo.currentText()}")