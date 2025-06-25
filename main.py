import sys
import os
from Models.TraceFile import TraceFile
from Models.Config import Config
from Models.ThemeManager import ThemeManager
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QTabWidget, QMessageBox,
    QHBoxLayout, QSplitter, QFrame, QLabel, QStackedWidget, QPushButton,
    QScrollArea, QSizePolicy, QToolBar, QToolButton, QMenu, QStatusBar,
    QProgressBar, QSpacerItem
)
from PyQt6.QtCore import Qt, QSize, QRect, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont, QColor, QPixmap, QAction
from Views.FileUploadWidget import FileUploadWidget
from Views.WaveDisplayWidget import WaveDisplayWidget
from Views.SourceDetectionWidget import SourceDetectionWidget
from Views.SettingsWidget import SettingsWidget
from Views.ModelSettingWidget import ModelSettingWidget
from Views.ThemeSettingsWidget import ThemeSettingsWidget
from Views.BatchProcessingWidget import BatchProcessingWidget
from Controllers.FileUploadWidgetController import FileUploadWidgetController
from Controllers.WaveDisplayWidgetController import WaveDisplayWidgetController
from Controllers.SourceDetectionWidgetController import SourceDetectionWidgetController
from Controllers.SettingsWidgetController import SettingsWidgetController
from Controllers.ModelSettingWidgetController import ModelSettingWidgetController
from Controllers.ThemeSettingsWidgetController import ThemeSettingsWidgetController
from Controllers.BatchProcessingWidgetController import BatchProcessingWidgetController
import traceback
import threading

class NavigationButton(QPushButton):
    """现代化导航按钮"""
    def __init__(self, text, icon_path=None, parent=None):
        super(NavigationButton, self).__init__(text, parent)
        self.setFixedHeight(48)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # 设置图标（如果有）
        if icon_path:
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(20, 20))
        
        # 不在这里设置样式，样式会由主题管理器控制

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("波数据分析系统")
        self.setMinimumSize(1280, 800)
        
        # 跟踪窗口是否最大化
        self.is_maximized = False
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager()

        # 创建视图
        self.file_upload_widget = FileUploadWidget()
        self.wave_display_widget = WaveDisplayWidget()
        self.source_detection_widget = SourceDetectionWidget()
        self.settings_widget = SettingsWidget()
        self.model_setting_widget = ModelSettingWidget()
        self.theme_settings_controller = ThemeSettingsWidgetController()
        self.batch_processing_widget = BatchProcessingWidget()

        # 创建控制器
        self.file_upload_controller = FileUploadWidgetController(self.file_upload_widget)
        self.wave_display_controller = WaveDisplayWidgetController(self.wave_display_widget)
        self.source_detection_controller = SourceDetectionWidgetController(self.source_detection_widget)
        self.settings_controller = SettingsWidgetController(self.settings_widget)
        self.model_setting_controller = ModelSettingWidgetController(self.model_setting_widget)
        self.batch_processing_controller = BatchProcessingWidgetController(self.batch_processing_widget)
        
        # 连接主题变更信号
        self.theme_settings_controller.themeChanged.connect(self.apply_theme)
        
        # 设置布局
        self.init_ui()
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 添加状态栏信息
        self.status_message = QLabel("系统就绪")
        self.status_bar.addWidget(self.status_message)
        
        # 添加进度条到状态栏（平时隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # 添加状态指示灯
        self.status_indicator = QLabel()
        self.status_indicator.setPixmap(QPixmap(16, 16))
        self.status_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 8px;")
        self.status_indicator.setFixedSize(16, 16)
        self.status_bar.addPermanentWidget(self.status_indicator)

    def init_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建侧边栏
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet(self.theme_manager.get_sidebar_stylesheet())
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # 侧边栏头部
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(80)
        header_layout = QHBoxLayout(header)
        
        # 应用标题和图标
        app_title = QLabel("波数据分析系统")
        app_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(app_title)
        
        sidebar_layout.addWidget(header)
        
        # 侧边栏主要导航按钮
        navigation_label = QLabel("主要功能")
        navigation_label.setObjectName("sidebarLabel")
        sidebar_layout.addWidget(navigation_label)
        
        self.btn_wave_display = NavigationButton("波数据展示")
        self.btn_source_detection = NavigationButton("源位置检测")
        self.btn_batch_processing = NavigationButton("批量处理")
        self.btn_velocity_model = NavigationButton("速度模型")
        
        # 添加导航按钮到侧边栏
        sidebar_layout.addWidget(self.btn_wave_display)
        sidebar_layout.addWidget(self.btn_source_detection)
        sidebar_layout.addWidget(self.btn_batch_processing)
        sidebar_layout.addWidget(self.btn_velocity_model)
        
        # 系统管理部分
        system_label = QLabel("系统管理")
        system_label.setObjectName("sidebarLabel")
        sidebar_layout.addWidget(system_label)
        
        self.btn_file_upload = NavigationButton("文件管理")
        self.btn_settings = NavigationButton("系统设置")
        self.btn_theme_settings = NavigationButton("主题设置")
        
        sidebar_layout.addWidget(self.btn_file_upload)
        sidebar_layout.addWidget(self.btn_settings)
        sidebar_layout.addWidget(self.btn_theme_settings)
        sidebar_layout.addStretch(1)
        
        # 侧边栏底部 - 版本信息
        footer = QWidget()
        footer.setObjectName("footer")
        footer.setFixedHeight(40)
        footer_layout = QHBoxLayout(footer)
        
        version_label = QLabel("版本 1.0.0")
        version_label.setObjectName("versionLabel")
        footer_layout.addWidget(version_label)
        
        sidebar_layout.addWidget(footer)
        
        # 创建主内容区
        main_container = QWidget()
        main_container.setObjectName("mainContainer")
        main_container_layout = QVBoxLayout(main_container)
        main_container_layout.setContentsMargins(0, 0, 0, 0)
        main_container_layout.setSpacing(0)
        
        # 标题栏
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(60)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(20, 0, 20, 0)
        
        self.page_title = QLabel("波数据展示")
        self.page_title.setObjectName("pageTitle")
        self.page_title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_bar_layout.addWidget(self.page_title)
        
        # 添加右侧控制按钮
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        title_bar_layout.addItem(spacer)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setObjectName("refreshButton")
        self.refresh_btn.setFixedSize(QSize(80, 36))
        title_bar_layout.addWidget(self.refresh_btn)
        
        main_container_layout.addWidget(title_bar)
        
        # 内容区域
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")
        
        # 将各个页面添加到堆叠窗口中
        def add_page_to_stack(widget):
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(20, 20, 20, 20)
            
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(widget)
            scroll_area.setStyleSheet("border: none;")
            layout.addWidget(scroll_area)
            
            return container
            
        # 添加页面到堆叠窗口
        self.content_stack.addWidget(add_page_to_stack(self.wave_display_widget))
        self.content_stack.addWidget(add_page_to_stack(self.source_detection_widget))
        self.content_stack.addWidget(add_page_to_stack(self.batch_processing_widget))
        self.content_stack.addWidget(add_page_to_stack(self.model_setting_widget))
        self.content_stack.addWidget(add_page_to_stack(self.file_upload_widget))
        self.content_stack.addWidget(add_page_to_stack(self.settings_widget))
        self.content_stack.addWidget(add_page_to_stack(self.theme_settings_controller.get_view()))
        
        main_container_layout.addWidget(self.content_stack)
        
        # 将侧边栏和内容区域添加到主布局
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(main_container, 1)
        
        # 连接按钮信号
        self.btn_wave_display.clicked.connect(lambda: self.switch_page(0, "波数据展示"))
        self.btn_source_detection.clicked.connect(lambda: self.switch_page(1, "源位置检测"))
        self.btn_batch_processing.clicked.connect(lambda: self.switch_page(2, "批量处理"))
        self.btn_velocity_model.clicked.connect(lambda: self.switch_page(3, "速度模型"))
        self.btn_file_upload.clicked.connect(lambda: self.switch_page(4, "文件管理"))
        self.btn_settings.clicked.connect(lambda: self.switch_page(5, "系统设置"))
        self.btn_theme_settings.clicked.connect(lambda: self.switch_page(6, "主题设置"))
        
        # 添加刷新事件
        self.refresh_btn.clicked.connect(self.refresh_current_page)
        
        # 默认选中第一个按钮
        self.btn_wave_display.setChecked(True)
        
        self.setCentralWidget(central_widget)

    def switch_page(self, index, title):
        # 更新页面标题
        self.page_title.setText(title)
        
        # 切换页面
        self.content_stack.setCurrentIndex(index)
        
        # 取消所有按钮的选中状态
        for btn in [self.btn_wave_display, self.btn_source_detection, self.btn_batch_processing,
                   self.btn_velocity_model, self.btn_file_upload, self.btn_settings, 
                   self.btn_theme_settings]:
            btn.setChecked(False)
        
        # 根据索引选中对应的按钮
        if index == 0:
            self.btn_wave_display.setChecked(True)
        elif index == 1:
            self.btn_source_detection.setChecked(True)
        elif index == 2:
            self.btn_batch_processing.setChecked(True)
        elif index == 3:
            self.btn_velocity_model.setChecked(True)
        elif index == 4:
            self.btn_file_upload.setChecked(True)
        elif index == 5:
            self.btn_settings.setChecked(True)
        elif index == 6:
            self.btn_theme_settings.setChecked(True)

    def refresh_current_page(self):
        # 获取当前页面索引
        current_index = self.content_stack.currentIndex()
        
        # 基于索引刷新不同页面
        if current_index == 0:  # 波数据展示
            QMessageBox.information(self, "刷新", "波数据展示页面已刷新")
        elif current_index == 1:  # 源位置检测
            QMessageBox.information(self, "刷新", "源位置检测页面已刷新")
        elif current_index == 2:  # 速度模型
            QMessageBox.information(self, "刷新", "速度模型页面已刷新")
        elif current_index == 3:  # 文件管理
            QMessageBox.information(self, "刷新", "文件管理页面已刷新")
        elif current_index == 4:  # 系统设置
            QMessageBox.information(self, "刷新", "系统设置页面已刷新")
        elif current_index == 5:  # 主题设置
            QMessageBox.information(self, "刷新", "主题设置页面已刷新")

    def update_status(self, message, progress=-1):
        """更新状态栏信息"""
        # 确保UI更新在主线程执行
        if threading.current_thread() is not threading.main_thread():
            return
        
        self.status_message.setText(message)
        
        if progress >= 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(progress)
            
            # 根据进度更改指示灯颜色
            if progress < 30:
                self.status_indicator.setStyleSheet("background-color: #F44336; border-radius: 8px;")
            elif progress < 70:
                self.status_indicator.setStyleSheet("background-color: #FFC107; border-radius: 8px;")
            else:
                self.status_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 8px;")
        else:
            self.progress_bar.setVisible(False)
            self.status_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 8px;")

    def apply_theme(self):
        """应用当前主题到整个应用程序"""
        # 获取当前主题样式表
        stylesheet = self.theme_manager.get_stylesheet()
        
        # 更新侧边栏样式
        self.sidebar.setStyleSheet(self.theme_manager.get_sidebar_stylesheet())
        
        # 更新所有界面组件的样式
        self.file_upload_widget.setStyleSheet(stylesheet)
        self.wave_display_widget.setStyleSheet(stylesheet)
        self.source_detection_widget.setStyleSheet(stylesheet)
        self.settings_widget.setStyleSheet(stylesheet)
        self.model_setting_widget.setStyleSheet(stylesheet)
        
        # 重新应用全局样式表
        QApplication.instance().setStyleSheet(stylesheet)
        
        # 更新状态栏
        self.status_bar.setStyleSheet(stylesheet)
        
        # 更新状态信息
        self.update_status("主题已更新")
        
        # 刷新当前页面
        current_index = self.content_stack.currentIndex()
        self.switch_page(current_index, self.page_title.text())

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        
        # 设置应用样式
        app.setStyle("Fusion")
        
        # 初始化配置系统
        try:
            config = Config()
            print("配置系统初始化成功")
        except Exception as e:
            print(f"配置系统初始化失败: {e}")
            print(traceback.format_exc())
            QMessageBox.warning(None, "警告", f"配置系统初始化失败: {e}")
        
        # 初始化主题管理器
        theme_manager = ThemeManager()
        app.setStyleSheet(theme_manager.get_stylesheet())
            
        # 创建主窗口
        window = MainWindow()

        # 加载测试用的默认数据
        try:
            trace_file = TraceFile()
            
            # 尝试加载默认的波形数据
            default_sgy_path = config.get("Default", "default_sgy_path")
            if default_sgy_path and os.path.exists(default_sgy_path):
                trace_file.load_wave_data(default_sgy_path)
                window.file_upload_widget.show_file_info(trace_file.get_wave_file_info())
                window.update_status(f"已加载默认波形数据: {default_sgy_path}")
                print(f"已加载默认波形数据: {default_sgy_path}")
            else:
                # 尝试加载当前目录中的.sgy文件
                for file in os.listdir('.'):
                    if file.endswith('.sgy'):
                        try:
                            trace_file.load_wave_data(file)
                            window.file_upload_widget.show_file_info(trace_file.get_wave_file_info())
                            window.update_status(f"已加载本地波形数据: {file}")
                            print(f"已加载本地波形数据: {file}")
                            break
                        except:
                            continue
            
            # 尝试加载默认的检波器位置数据
            default_xlsx_path = config.get("Default", "default_xlsx_path")
            if default_xlsx_path and os.path.exists(default_xlsx_path):
                trace_file.load_location_data(default_xlsx_path)
                window.file_upload_widget.show_location_info(trace_file.get_detector_location())
                window.update_status(f"已加载默认检波器位置: {default_xlsx_path}")
                print(f"已加载默认检波器位置: {default_xlsx_path}")
            else:
                # 尝试加载当前目录中的xlsx文件
                for file in os.listdir('.'):
                    if file.endswith('.xlsx'):
                        try:
                            trace_file.load_location_data(file)
                            window.file_upload_widget.show_location_info(trace_file.get_detector_location())
                            window.update_status(f"已加载本地检波器位置数据: {file}")
                            print(f"已加载本地检波器位置数据: {file}")
                            break
                        except:
                            continue
        except Exception as e:
            print(f"加载默认数据失败: {e}")
            print(traceback.format_exc())
            window.update_status(f"加载默认数据失败: {str(e)}")
        
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"程序启动失败: {e}")
        print(traceback.format_exc())
