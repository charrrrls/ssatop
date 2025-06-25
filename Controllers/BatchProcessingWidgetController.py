from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, Qt, QMetaObject, Q_ARG
from Views.BatchProcessingWidget import BatchProcessingWidget
from Models.TraceFile import TraceFile
from Models.TaskRunner import TaskRunner
from Services.ssatop import calculate_source_location

import os
import time
import traceback
import numpy as np
from PyQt6.QtWidgets import QApplication
import datetime

class BatchProcessingWidgetController(QObject):
    """批量处理控制器"""
    
    # 信号定义
    processing_completed = pyqtSignal()  # 处理完成信号
    processing_stopped = pyqtSignal()    # 处理停止信号
    
    # 添加UI更新信号
    update_file_status_signal = pyqtSignal(int, str)
    update_file_progress_signal = pyqtSignal(int, int)
    add_result_signal = pyqtSignal(str, float, float, float, float)
    update_overall_progress_signal = pyqtSignal(int)
    update_status_text_signal = pyqtSignal(str)
    
    def __init__(self, view: BatchProcessingWidget):
        super().__init__()
        self.view = view
        self.file_pairs = []  # 存储文件对：[(波形文件, 检波器文件), ...]
        self.current_index = -1  # 当前处理的文件索引
        self.is_processing = False  # 是否正在处理
        self.should_stop = False   # 是否应该停止处理
        self.thread = None  # 处理线程
        self.results = []  # 处理结果
        self.processed_count = 0  # 已处理文件计数
        
        # 时间预测相关变量
        self.batch_start_time = 0  # 批处理开始时间
        self.file_start_time = 0   # 当前文件开始处理时间
        self.completed_files_time = []  # 已完成文件的处理时间列表
        
        # 连接信号到UI更新方法
        self.update_file_status_signal.connect(self.view.update_file_status)
        self.update_file_progress_signal.connect(self.view.update_file_progress)
        self.add_result_signal.connect(self.view.add_result)
        self.update_overall_progress_signal.connect(self.view.update_overall_progress)
        self.update_status_text_signal.connect(self.view.update_status_text)
        
        # 绑定事件
        self.connect_signals()
    
    def connect_signals(self):
        """连接信号与槽"""
        # 文件操作
        self.view.add_files_btn.clicked.connect(self.handle_add_files)
        self.view.remove_files_btn.clicked.connect(self.handle_remove_files)
        self.view.clear_files_btn.clicked.connect(self.handle_clear_files)
        
        # 处理控制
        self.view.start_batch_btn.clicked.connect(self.handle_start_batch)
        self.view.stop_batch_btn.clicked.connect(self.handle_stop_batch)
        
        # 结果导出
        self.view.export_results_btn.clicked.connect(self.handle_export_results)
    
    def handle_add_files(self):
        """处理添加文件按钮点击事件"""
        # 打开文件对话框选择波形文件
        wave_files, _ = QFileDialog.getOpenFileNames(
            self.view, "选择波形文件", "", "SGY文件 (*.sgy);;所有文件 (*.*)"
        )
        
        if not wave_files:
            return
        
        # 选择检波器位置文件
        location_file, _ = QFileDialog.getOpenFileName(
            self.view, "选择检波器位置文件", "", "Excel文件 (*.xlsx);;所有文件 (*.*)"
        )
        
        if not location_file:
            return
        
        # 添加文件对到列表
        for wave_file in wave_files:
            self.file_pairs.append((wave_file, location_file))
            self.view.add_file_pair(wave_file, location_file)
        
        # 启用开始处理按钮
        if self.file_pairs:
            self.view.start_batch_btn.setEnabled(True)
    
    def handle_remove_files(self):
        """处理移除文件按钮点击事件"""
        # 获取选中的行
        selected_rows = sorted(set(index.row() for index in self.view.files_table.selectedIndexes()), reverse=True)
        
        if not selected_rows:
            QMessageBox.information(self.view, "提示", "请先选择要移除的文件")
            return
        
        # 从后往前移除，避免索引变化
        for row in selected_rows:
            self.file_pairs.pop(row)
            self.view.files_table.removeRow(row)
        
        # 如果没有文件了，禁用开始处理按钮
        if not self.file_pairs:
            self.view.start_batch_btn.setEnabled(False)
    
    def handle_clear_files(self):
        """处理清空文件按钮点击事件"""
        self.file_pairs = []
        self.view.files_table.setRowCount(0)
        self.view.start_batch_btn.setEnabled(False)
    
    def handle_start_batch(self):
        """处理开始批量处理按钮点击事件"""
        if not self.file_pairs:
            QMessageBox.information(self.view, "提示", "请先添加文件")
            return
        
        # 重置状态
        self.current_index = -1
        self.is_processing = True
        self.should_stop = False
        self.results = []
        self.processed_count = 0
        
        # 重置时间预测相关变量
        self.batch_start_time = time.time()
        self.file_start_time = 0
        self.completed_files_time = []
        
        # 清空结果表格
        self.view.clear_results()
        
        # 更新UI状态
        self.view.start_batch_btn.setEnabled(False)
        self.view.stop_batch_btn.setEnabled(True)
        self.view.add_files_btn.setEnabled(False)
        self.view.remove_files_btn.setEnabled(False)
        self.view.clear_files_btn.setEnabled(False)
        self.view.export_results_btn.setEnabled(False)
        
        # 重置所有文件的状态和进度
        for i in range(self.view.files_table.rowCount()):
            self.view.update_file_status(i, "等待处理")
            self.view.update_file_progress(i, 0)
        
        # 重置总体进度
        self.view.update_overall_progress(0)
        
        # 开始处理第一个文件
        self.process_next_file()
    
    def handle_stop_batch(self):
        """处理停止批量处理按钮点击事件"""
        self.should_stop = True
        self.view.update_file_status(self.current_index, "已取消")
        
        # 更新UI状态
        self.view.start_batch_btn.setEnabled(True)
        self.view.stop_batch_btn.setEnabled(False)
        self.view.add_files_btn.setEnabled(True)
        self.view.remove_files_btn.setEnabled(True)
        self.view.clear_files_btn.setEnabled(True)
        
        # 如果有结果，启用导出按钮
        if self.results:
            self.view.export_results_btn.setEnabled(True)
        
        # 停止当前运行的线程（如果有）
        if hasattr(self, 'thread') and self.thread is not None:
            self.thread.should_stop = True
            self.thread.quit()
            self.thread.wait(1000)  # 等待最多1秒让线程结束
            
        # 发出处理停止信号
        self.processing_stopped.emit()
    
    def handle_export_results(self):
        """处理导出结果按钮点击事件"""
        if not self.results:
            QMessageBox.information(self.view, "提示", "没有可导出的结果")
            return
        
        # 打开文件对话框选择保存路径
        save_path, _ = QFileDialog.getSaveFileName(
            self.view, "导出结果", "", "CSV文件 (*.csv);;所有文件 (*.*)"
        )
        
        if not save_path:
            return
        
        try:
            # 创建DataFrame并保存为CSV
            import pandas as pd
            df = pd.DataFrame(self.results)
            df.to_csv(save_path, index=False)
            
            QMessageBox.information(self.view, "导出成功", f"结果已导出到 {save_path}")
        except Exception as e:
            QMessageBox.critical(self.view, "导出失败", f"导出结果时出错: {str(e)}")
    
    def format_time(self, seconds):
        """格式化时间为易读格式"""
        if seconds < 0 or seconds > 100000000:  # 避免异常值
            return "计算中..."
            
        # 处理非常大的时间值
        if seconds > 86400:  # 大于1天
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}天{hours}小时"
            
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}时{minutes}分{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分{seconds}秒"
        else:
            return f"{seconds}秒"
    
    def estimate_remaining_time(self, current_progress):
        """估算剩余时间"""
        if not self.completed_files_time or current_progress <= 0:
            return "计算中..."
        
        # 计算平均每个文件处理时间
        avg_file_time = sum(self.completed_files_time) / len(self.completed_files_time)
        
        # 计算剩余文件数
        remaining_files = len(self.file_pairs) - self.current_index
        
        # 如果当前有文件正在处理，考虑当前文件的已处理进度
        if self.file_start_time > 0 and current_progress > 0:
            elapsed_time = time.time() - self.file_start_time
            estimated_total_time = elapsed_time / (current_progress / 100)
            remaining_time = estimated_total_time - elapsed_time + avg_file_time * (remaining_files - 1)
        else:
            remaining_time = avg_file_time * remaining_files
        
        # 格式化剩余时间
        return self.format_time(remaining_time)
    
    def update_eta_display(self, file_progress):
        """更新预计完成时间显示"""
        # 确保file_progress是整数
        try:
            file_progress_value = int(file_progress)
        except (ValueError, TypeError):
            file_progress_value = 0
            
        # 计算总体进度
        if len(self.file_pairs) > 0:
            completed_percentage = (self.processed_count + file_progress_value / 100) / len(self.file_pairs) * 100
            overall_progress = int(completed_percentage)
            self.view.update_overall_progress(overall_progress)
        
        # 计算已用时间
        elapsed_time = time.time() - self.batch_start_time
        
        # 计算预计剩余时间
        eta = self.estimate_remaining_time(file_progress_value)
        
        # 计算处理速度 (文件/分钟)
        if self.processed_count > 0 and elapsed_time > 0:
            files_per_minute = (self.processed_count / elapsed_time) * 60
            speed_str = f"{files_per_minute:.2f} 文件/分钟"
        else:
            speed_str = "计算中..."
        
        # 格式化时间
        elapsed_str = self.format_time(elapsed_time)
        
        # 更新总体状态显示
        status_text = f"总进度: {overall_progress}% | 已用时间: {elapsed_str} | 预计剩余: {eta} | 处理速度: {speed_str}"
        self.view.update_status_text(status_text)
    
    def process_next_file(self):
        """处理下一个文件"""
        if self.should_stop:
            self.is_processing = False
            return
        
        self.current_index += 1
        
        # 检查是否处理完所有文件
        if self.current_index >= len(self.file_pairs):
            self.handle_processing_completed()
            return
        
        # 记录当前文件开始处理时间
        self.file_start_time = time.time()
        
        # 获取当前要处理的文件对
        wave_file, location_file = self.file_pairs[self.current_index]
        
        # 更新文件状态
        self.view.update_file_status(self.current_index, "处理中")
        
        # 更新总体进度和预计时间
        self.update_eta_display(0)
        
        try:
            # 创建TraceFile实例
            trace_file = TraceFile()
            
            # 重置TraceFile实例，确保每次处理都是新的数据
            trace_file.reset_instance()
            
            # 加载波形文件
            trace_file.load_wave_data(wave_file)
            
            # 加载检波器位置文件
            trace_file.load_location_data(location_file)
            
            # 获取处理参数
            grid_precision = self.view.grid_precision_combo.currentText()
            population_size = int(self.view.population_combo.currentText())
            iterations = int(self.view.iterations_combo.currentText())
            mutation_rate = float(self.view.mutation_combo.currentText())
            
            # 根据网格精度设置网格参数
            if grid_precision == "低":
                grid_size = 500
                z_grid = 50
            elif grid_precision == "高":
                grid_size = 2000
                z_grid = 200
            else:  # 中等精度
                grid_size = 1000
                z_grid = 100
            
            # 设置网格参数
            grid_params = {
                'x_grid': grid_size,
                'y_grid': grid_size,
                'z_grid': z_grid,
                'population_size': population_size,
                'generations': iterations,
                'mutation_rate': mutation_rate
            }
            
            # 创建任务运行器
            self.task_runner = TaskRunner()
            
            # 获取波形文件采样间隔
            sample_interval = trace_file.basic_info['sample_interval']
            
            # 获取预估微地震时间区间
            time_range = trace_file.get_estimate_earthquake_time()
            
            # 记录开始时间
            start_time = time.time()
            
            # 设置进度回调，确保UI更新
            def progress_callback(progress, start_time=0, idx=0, 单位='', 更优的点=None):
                if self.should_stop:
                    return False  # 返回False表示停止处理
                
                try:
                    # 确保progress是整数类型
                    try:
                        progress_value = int(progress)
                    except (ValueError, TypeError):
                        progress_value = 0
                    
                    # 在主线程中安全地更新UI - 使用信号和槽机制
                    self.update_file_progress_signal.emit(self.current_index, progress_value)
                    
                    # 更新总体进度和预计时间 - 使用信号和槽机制
                    if progress_value % 5 == 0:  # 每5%更新一次减少UI负担
                        # 计算总体进度
                        if len(self.file_pairs) > 0:
                            completed_percentage = (self.processed_count + progress_value / 100) / len(self.file_pairs) * 100
                            overall_progress = int(completed_percentage)
                            
                            # 更新总体进度条
                            self.update_overall_progress_signal.emit(overall_progress)
                            
                            # 计算和更新状态文本
                            elapsed_time = time.time() - self.batch_start_time
                            eta = self.estimate_remaining_time(progress_value)
                            elapsed_str = self.format_time(elapsed_time)
                            
                            # 计算处理速度
                            if self.processed_count > 0 and elapsed_time > 0:
                                files_per_minute = (self.processed_count / elapsed_time) * 60
                                speed_str = f"{files_per_minute:.2f} 文件/分钟"
                            else:
                                speed_str = "计算中..."
                            
                            # 构建状态文本并更新
                            status_text = f"总进度: {overall_progress}% | 已用时间: {elapsed_str} | 预计剩余: {eta} | 处理速度: {speed_str}"
                            self.update_status_text_signal.emit(status_text)
                        
                        # 强制处理事件队列，确保UI更新
                        QApplication.processEvents()
                    
                    return True
                except Exception as e:
                    print(f"更新进度时出错: {e}")
                    traceback.print_exc()
                    return True
            
            # 使用真正的线程运行任务，确保UI不卡顿
            try:
                self.thread = TaskRunner(
                    calculate_source_location,
                    trace_file.wave_data, trace_file.location_data, sample_interval, time_range, progress_callback, grid_params
                )
                self.thread.task_completed.connect(self.handle_file_processing_completed)
                self.thread.start()
                
                # 更新状态显示
                self.update_status_text_signal.emit(f"正在处理文件 {os.path.basename(wave_file)}...")
                self.update_file_status_signal.emit(self.current_index, "处理中")
                
                # 注意：这里不再等待结果，而是异步处理
                return
            except Exception as e:
                self.update_status_text_signal.emit(f"启动处理线程失败: {str(e)}")
                self.update_file_status_signal.emit(self.current_index, f"错误: {str(e)[:20]}...")
                print(f"启动处理线程失败: {e}")
                traceback.print_exc()
                
                # 处理下一个文件
                self.current_index += 1
                QTimer.singleShot(100, self.process_next_file)
            
        except Exception as e:
            # 处理异常
            error_msg = str(e)
            traceback.print_exc()
            
            # 更新文件状态
            self.view.update_file_status(self.current_index, f"错误: {error_msg[:20]}...")
            
            # 询问是否继续处理下一个文件
            reply = QMessageBox.question(
                self.view,
                "处理错误",
                f"处理文件 {os.path.basename(wave_file)} 时出错:\n{error_msg}\n\n是否继续处理下一个文件？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 处理下一个文件
                self.process_next_file()
            else:
                # 停止处理
                self.should_stop = True
                self.handle_processing_completed()
    
    def handle_file_processing_completed(self, result):
        """处理单个文件计算完成的回调"""
        try:
            # 获取当前处理的文件对
            wave_file, location_file = self.file_pairs[self.current_index]
            
            # 处理完成，记录处理时间
            file_processing_time = time.time() - self.file_start_time
            self.completed_files_time.append(file_processing_time)
            
            # 处理完成，更新状态
            if self.should_stop:
                self.update_file_status_signal.emit(self.current_index, "已取消")
            else:
                self.update_file_status_signal.emit(self.current_index, f"已完成 ({self.format_time(file_processing_time)})")
                self.update_file_progress_signal.emit(self.current_index, 100)
                self.processed_count += 1
                
                # 添加结果到结果表格
                if result and isinstance(result, tuple) and len(result) >= 2:
                    max_point, max_brightness = result
                    if isinstance(max_point, np.ndarray) and len(max_point) >= 3:
                        x, y, z = max_point[:3]
                        brightness = max_brightness
                        self.add_result_signal.emit(os.path.basename(wave_file), float(x), float(y), float(z), float(brightness))
            
            # 处理下一个文件
            self.process_next_file()
            
        except Exception as e:
            # 处理异常
            error_msg = str(e)
            traceback.print_exc()
            
            # 更新文件状态
            self.update_file_status_signal.emit(self.current_index, f"错误: {error_msg[:20]}...")
            
            # 在主线程中询问是否继续
            QTimer.singleShot(100, lambda: self.ask_continue_after_error(wave_file, error_msg))
    
    @pyqtSlot(str, str)
    def ask_continue_after_error(self, wave_file, error_msg):
        """询问是否在错误后继续处理"""
        # 询问是否继续处理下一个文件
        reply = QMessageBox.question(
            self.view,
            "处理错误",
            f"处理文件 {os.path.basename(wave_file)} 时出错:\n{error_msg}\n\n是否继续处理下一个文件？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 处理下一个文件
            self.process_next_file()
        else:
            # 停止处理
            self.should_stop = True
            self.handle_processing_completed()
    
    def handle_processing_completed(self):
        """处理完成处理"""
        self.is_processing = False
        
        # 清理线程资源
        if hasattr(self, 'thread') and self.thread is not None:
            self.thread.should_stop = True
            self.thread.quit()
            self.thread.wait(1000)  # 等待最多1秒让线程结束
            self.thread = None
        
        # 计算总处理时间
        total_time = time.time() - self.batch_start_time
        total_time_str = self.format_time(total_time)
        
        # 在主线程中安全地更新UI - 使用信号和槽
        self.view.start_batch_btn.setEnabled(True)
        self.view.stop_batch_btn.setEnabled(False)
        self.view.add_files_btn.setEnabled(True)
        self.view.remove_files_btn.setEnabled(True)
        self.view.clear_files_btn.setEnabled(True)
        
        # 如果有结果，启用导出按钮
        if self.results:
            self.view.export_results_btn.setEnabled(True)
        
        # 更新总体进度为100%
        self.update_overall_progress_signal.emit(100)
        
        # 更新状态文本，显示总处理时间
        self.update_status_text_signal.emit(f"处理完成 | 总用时: {total_time_str}")
        
        # 强制处理事件，确保UI更新
        QApplication.processEvents()
        
        # 显示处理完成消息 - 仅在主线程中调用
        if not self.should_stop:
            # 使用QTimer确保消息框在UI更新后显示
            QTimer.singleShot(100, lambda: QMessageBox.information(
                self.view, 
                "处理完成", 
                f"已成功处理 {self.processed_count} 个文件\n总用时: {total_time_str}"
            ))
        
        # 发出处理完成信号
        self.processing_completed.emit() 