import os
import yaml
import traceback
import threading
from PyQt6.QtCore import QObject

class Config(QObject):
    # 单例模式
    _instance = None
    _lock = threading.Lock()

    yaml_path = None
    config = None

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(Config, cls).__new__(cls)
                cls._instance._initialized = False  # 在这里初始化_initialized
        return cls._instance

    def __init__(self):
        # 先检查初始化状态
        if getattr(self, '_initialized', False):
            return
            
        # 调用父类初始化
        super().__init__()
        
        # 设置初始化标志
        self._initialized = True
        
        # 初始化配置路径和默认配置
        self.config_path = self._get_config_path()
        self.default_config = {
            "Default": {
                "velocity_model": "simple"  # 默认使用简单速度模型
            }
        }
        
        # 加载配置
        self.config_data = self._load_config()
        
        print("Config类初始化完成")

    def _get_config_path(self):
        """获取配置文件路径"""
        # 当前脚本所在目录
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(script_dir, "config.yaml")
        print(f"配置文件路径: {config_path}")
        return config_path
    
    def _load_config(self):
        """加载配置文件"""
        try:
            # 检查配置文件是否存在
            if not os.path.exists(self.config_path):
                print(f"配置文件不存在，创建默认配置: {self.config_path}")
                # 创建默认配置
                self._save_config(self.default_config)
                return self.default_config
            
            # 读取现有配置
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # 配置验证
            if not config_data:
                print("配置文件为空，使用默认配置")
                return self.default_config
                
            # 确保配置文件包含必要的部分
            if "Default" not in config_data:
                config_data["Default"] = self.default_config["Default"]
            if "velocity_model" not in config_data["Default"]:
                config_data["Default"]["velocity_model"] = self.default_config["Default"]["velocity_model"]
            
            print(f"成功加载配置: {config_data}")    
            return config_data
            
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            print(traceback.format_exc())
            return self.default_config
    
    def _save_config(self, config_data):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            print(f"配置已保存到: {self.config_path}")
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            print(traceback.format_exc())
            return False
    
    def get(self, section, key, default=None):
        """获取配置值"""
        try:
            return self.config_data.get(section, {}).get(key, default)
        except Exception as e:
            print(f"获取配置值失败: {e}")
            return default
    
    def set(self, section, key, value):
        """设置配置值"""
        try:
            # 确保section存在
            if section not in self.config_data:
                self.config_data[section] = {}
            
            # 设置值
            self.config_data[section][key] = value
            
            # 保存配置
            return self._save_config(self.config_data)
        except Exception as e:
            print(f"设置配置值失败: {e}")
            print(traceback.format_exc())
            return False
            
    def get_velocity_model(self):
        """获取当前使用的速度模型名称"""
        return self.get("Default", "velocity_model", "simple")
        
    def set_velocity_model(self, model_name):
        """设置当前使用的速度模型名称"""
        return self.set("Default", "velocity_model", model_name)

if __name__ == '__main__':
    config = Config()
    print(f"当前速度模型: {config.get_velocity_model()}")
    # 测试设置新的速度模型
    config.set_velocity_model("iasp91")
    print(f"更新后的速度模型: {config.get_velocity_model()}")