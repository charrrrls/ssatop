from Models.Config import Config
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from Views.ModelSettingWidget import ModelSettingWidget
from Controllers.ModelSettingWidgetController import ModelSettingWidgetController

class SettingsWidgetController:
    def __init__(self, settings_widget):
        self.settings_widget = settings_widget
        
        # 加载配置
        self.load_config()
        
        # 连接按钮信号
        self.settings_widget.save_button.clicked.connect(self.save_config)
        self.settings_widget.reset_button.clicked.connect(self.reset_config)
        self.settings_widget.model_setting_button.clicked.connect(self.open_model_settings)
        
        # 连接浏览按钮
        self.settings_widget.browse_sgy_button.clicked.connect(lambda: self.browse_file("sgy"))
        self.settings_widget.browse_xlsx_button.clicked.connect(lambda: self.browse_file("xlsx"))
        
        # 保存对话框实例
        self.model_setting_widget = None
        self.model_controller = None

    def load_config(self):
        """从配置文件中加载配置项并将其设置到视图中"""
        config = Config()
        try:
            # 从配置文件中加载每个配置项
            default_sgy_path = config.get("Default", "default_sgy_path")
            default_xlsx_path = config.get("Default", "default_xlsx_path")
            speed = str(config.get("Default", "speed"))
            length = str(config.get("Default", "length"))
            height = str(config.get("Default", "height"))
            time_slice = str(config.get("Default", "time_slice"))
            z_min = str(config.get("Default", "z_min"))
            z_max = str(config.get("Default", "z_max"))
            
            # 加载高级设置（如果存在）
            try:
                use_gpu = config.get("Advanced", "use_gpu") == "True"
                self.settings_widget.use_gpu_checkbox.setChecked(use_gpu)
                
                auto_load = config.get("Advanced", "auto_load") == "True"
                self.settings_widget.auto_load_checkbox.setChecked(auto_load)
                
                theme = config.get("Advanced", "theme")
                theme_index = {"light": 0, "dark": 1, "system": 2}.get(theme, 2)
                self.settings_widget.theme_selector.setCurrentIndex(theme_index)
            except:
                # 如果高级设置不存在，使用默认值
                pass
                
        except Exception as e:
            QMessageBox.warning(self.settings_widget, "警告", f"加载配置失败: {e}")
            return

        # 将加载的配置项设置到 SettingsWidget 视图的输入框中
        self.settings_widget.config_sgy_path.setText(default_sgy_path)
        self.settings_widget.config_xlsx_path.setText(default_xlsx_path)
        self.settings_widget.config_speed.setText(speed)
        self.settings_widget.config_length.setText(length)
        self.settings_widget.config_height.setText(height)
        self.settings_widget.config_time_slice.setText(time_slice)
        self.settings_widget.config_z_min.setText(z_min)
        self.settings_widget.config_z_max.setText(z_max)

    def save_config(self):
        """从视图中获取配置项并保存到配置文件"""
        param_sgy_path = self.settings_widget.config_sgy_path.text()
        param_xlsx_path = self.settings_widget.config_xlsx_path.text()
        param_speed = self.settings_widget.config_speed.text()
        param_length = self.settings_widget.config_length.text()
        param_height = self.settings_widget.config_height.text()
        param_time_slice = self.settings_widget.config_time_slice.text()
        param_z_min = self.settings_widget.config_z_min.text()
        param_z_max = self.settings_widget.config_z_max.text()

        # 获取高级设置
        use_gpu = self.settings_widget.use_gpu_checkbox.isChecked()
        auto_load = self.settings_widget.auto_load_checkbox.isChecked()
        theme_index = self.settings_widget.theme_selector.currentIndex()
        theme = ["light", "dark", "system"][theme_index]

        # 保存配置到配置文件
        config = Config()
        
        try:
            # 保存基本设置
            config.set("Default", "default_sgy_path", param_sgy_path)
            config.set("Default", "default_xlsx_path", param_xlsx_path)
            config.set("Default", "speed", param_speed)
            config.set("Default", "length", param_length)
            config.set("Default", "height", param_height)
            config.set("Default", "time_slice", param_time_slice)
            config.set("Default", "z_min", param_z_min)
            config.set("Default", "z_max", param_z_max)
            
            # 保存高级设置
            config.set("Advanced", "use_gpu", str(use_gpu))
            config.set("Advanced", "auto_load", str(auto_load))
            config.set("Advanced", "theme", theme)
            
            QMessageBox.information(self.settings_widget, "提示", "配置已保存！")
        except Exception as e:
            QMessageBox.warning(self.settings_widget, "警告", f"保存配置失败: {e}")
            return

    def reset_config(self):
        """重置配置为默认值"""
        try:
            # 检查是否真的要重置
            reply = QMessageBox.question(
                self.settings_widget,
                "确认重置",
                "确定要将所有设置重置为默认值吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 设置默认值
                self.settings_widget.config_sgy_path.setText("")
                self.settings_widget.config_xlsx_path.setText("")
                self.settings_widget.config_speed.setText("3000")
                self.settings_widget.config_length.setText("1000")
                self.settings_widget.config_height.setText("500")
                self.settings_widget.config_time_slice.setText("0.01")
                self.settings_widget.config_z_min.setText("0")
                self.settings_widget.config_z_max.setText("6000")
                
                # 重置高级设置
                self.settings_widget.use_gpu_checkbox.setChecked(False)
                self.settings_widget.auto_load_checkbox.setChecked(True)
                self.settings_widget.theme_selector.setCurrentIndex(2)  # 系统默认
                
                QMessageBox.information(self.settings_widget, "提示", "已重置为默认值")
        except Exception as e:
            QMessageBox.warning(self.settings_widget, "警告", f"重置配置失败: {e}")

    def browse_file(self, file_type):
        """打开文件选择对话框"""
        options = QFileDialog.Options()
        
        if file_type == "sgy":
            file_path, _ = QFileDialog.getOpenFileName(
                self.settings_widget, 
                "选择SGY文件", 
                "", 
                "SGY文件 (*.sgy *.segy);;所有文件 (*)",
                options=options
            )
            if file_path:
                self.settings_widget.config_sgy_path.setText(file_path)
                
        elif file_type == "xlsx":
            file_path, _ = QFileDialog.getOpenFileName(
                self.settings_widget, 
                "选择XLSX文件", 
                "", 
                "XLSX文件 (*.xlsx);;所有文件 (*)",
                options=options
            )
            if file_path:
                self.settings_widget.config_xlsx_path.setText(file_path)

    def open_model_settings(self):
        """打开速度模型设置对话框"""
        try:
            # 如果对话框不存在则创建
            if not self.model_setting_widget:
                self.model_setting_widget = ModelSettingWidget()
                self.model_controller = ModelSettingWidgetController(self.model_setting_widget)
            
            # 显示对话框
            self.model_setting_widget.show()
            self.model_setting_widget.raise_()  # 确保对话框在前面
        except Exception as e:
            QMessageBox.warning(
                self.settings_widget, 
                "打开模型设置失败", 
                f"无法打开速度模型设置: {str(e)}"
            )
