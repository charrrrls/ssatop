# controllers.py
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import Qt
from Models.TraceFile import TraceFile
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from Services.ssatop import normalize_data
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wave_display_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('WaveDisplayController')

class WaveDisplayWidgetController:
    def __init__(self, wave_display_widget):
        logger.info("初始化WaveDisplayWidgetController")
        self.wave_display_widget = wave_display_widget
        self.trace_file = TraceFile()
        self.current_wave_data = None
        self.current_time = None
        self.current_trace_number = None
        self.current_sample_interval = None
        self.current_sample_count = None

        # 绑定界面事件
        logger.info("绑定界面事件")
        self.wave_display_widget.display_button.clicked.connect(self.handle_query_wave_data)
        self.wave_display_widget.analyze_button.clicked.connect(self.handle_analyze_wave)
        self.wave_display_widget.save_button.clicked.connect(self.handle_save_image)
        self.wave_display_widget.reset_button.clicked.connect(self.handle_reset_view)
        self.wave_display_widget.zoom_slider.valueChanged.connect(self.handle_zoom_change)
        self.wave_display_widget.display_type_group.buttonClicked.connect(self.handle_display_type_change)
        
    def handle_query_wave_data(self):
        """
        处理按钮点击事件，从输入框获取数据并查询波数据
        """
        logger.info("执行handle_query_wave_data")
        # 获取并检查输入框的值
        try:
            # 将输入的字符串转换为整数
            trace_number = int(self.wave_display_widget.trace_input.text())
            logger.info(f"查询波数据，编号: {trace_number}")
        except:
            logger.error("输入的不是有效数字")
            QMessageBox.warning(self.wave_display_widget, "错误", "请输入正确的数字！")
            return
        
        # 查询波数据并显示
        try:
            wave_info = self.trace_file.get_wave_file_info()
            wave_data = self.trace_file.get_wave_data_by_trace_number(trace_number)
            time_data = self.trace_file.get_estimate_earthquake_time()
            
            # 保存当前波形数据以供后续使用
            self.current_wave_data = wave_data
            self.current_time = np.arange(wave_info["sample_count"]) * wave_info["sample_interval"]
            self.current_trace_number = trace_number
            self.current_sample_interval = wave_info["sample_interval"]
            self.current_sample_count = wave_info["sample_count"]
            
            logger.info(f"获取到波数据，点数: {len(wave_data)}, 采样间隔: {wave_info['sample_interval']}")
            
            # 更新WaveDisplayWidget的波形数据
            self.wave_display_widget.show_wave_data(
                wave_info["sample_count"],
                wave_info["sample_interval"],
                trace_number,
                wave_data,
                time_data,
            )
        except Exception as e:
            logger.error(f"查询波数据失败: {str(e)}")
            logger.error(traceback.format_exc())
            QMessageBox.warning(self.wave_display_widget, "警告", str(e))
            
    def handle_analyze_wave(self):
        """处理分析波形按钮点击事件，显示高级波形分析"""
        logger.info("执行handle_analyze_wave")
        if self.current_wave_data is None:
            logger.warning("当前没有加载波数据")
            QMessageBox.warning(self.wave_display_widget, "警告", "请先加载波形数据！")
            return
            
        try:
            # 切换到频谱分析标签页
            logger.info("切换到频谱分析标签页")
            self.wave_display_widget.tabs.setCurrentIndex(1)
            
            # 使用WaveDisplayWidget的内置方法计算并显示频谱
            logger.info("调用update_spectrum_display")
            self.wave_display_widget.update_spectrum_display()
            
        except Exception as e:
            logger.error(f"分析波形时出错: {str(e)}")
            logger.error(traceback.format_exc())
            QMessageBox.warning(self.wave_display_widget, "警告", f"分析波形时出错: {str(e)}")

    def handle_save_image(self):
        """处理保存图像按钮点击事件"""
        logger.info("执行handle_save_image")
        if self.current_wave_data is None:
            logger.warning("当前没有加载波数据")
            QMessageBox.warning(self.wave_display_widget, "警告", "没有可保存的图像！")
            return
            
        try:
            # 打开文件保存对话框
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(
                self.wave_display_widget, 
                "保存图像", 
                f"波形_{self.current_trace_number}.png", 
                "PNG图像 (*.png);;JPG图像 (*.jpg);;所有文件 (*)", 
                options=options
            )
            
            if file_path:
                logger.info(f"保存图像到: {file_path}")
                # 保存图像
                self.wave_display_widget.fig.savefig(
                    file_path, 
                    dpi=300, 
                    bbox_inches='tight',
                    facecolor=self.wave_display_widget.fig.get_facecolor()
                )
                QMessageBox.information(self.wave_display_widget, "成功", f"图像已保存至: {file_path}")
        except Exception as e:
            logger.error(f"保存图像时出错: {str(e)}")
            logger.error(traceback.format_exc())
            QMessageBox.warning(self.wave_display_widget, "警告", f"保存图像时出错: {str(e)}")

    def handle_reset_view(self):
        """处理重置视图按钮点击事件"""
        logger.info("执行handle_reset_view")
        if self.current_wave_data is None:
            logger.warning("当前没有加载波数据")
            QMessageBox.warning(self.wave_display_widget, "警告", "没有可重置的视图！")
            return
            
        # 重置缩放滑块
        self.wave_display_widget.zoom_slider.setValue(100)
        
        # 重新绘制波形
        self.wave_display_widget.update_display_type()
            
    def handle_zoom_change(self, value):
        """处理缩放滑块值变化事件"""
        logger.debug(f"执行handle_zoom_change: {value}")
        # 更新缩放标签
        self.wave_display_widget.zoom_label.setText(f"缩放: {value}%")
        
        # 使用WaveDisplayWidget的内置方法
        self.wave_display_widget.update_zoom(value)
            
    def handle_display_type_change(self, button):
        """处理显示类型变更事件"""
        logger.info(f"执行handle_display_type_change: {button.text()}")
        if self.current_wave_data is None:
            logger.warning("当前没有加载波数据")
            return
            
        # 使用WaveDisplayWidget的内置方法
        self.wave_display_widget.update_display_type()
