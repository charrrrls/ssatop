from PyQt6.QtCore import QObject
from Models.VelocityModel import SimpleVelocityModel, ObsPyVelocityModel
from Models.Config import Config
import traceback
import os
import json

class ModelManager(QObject):
    """模型管理器，用于管理和选择不同的速度模型"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化模型管理器"""
        if self._initialized:
            return
            
        super().__init__()
        self._initialized = True
        self.config = Config()
        self._models = {}
        self._current_model_name = None
        
        # 添加模型数据目录路径
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                     "Models", "data", "velocity_models")
        # 检查目录是否存在，不存在则创建
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir, exist_ok=True)
            
        self._model_descriptions = {
            "simple": "简单恒定速度模型：使用固定的P波和S波速度，不考虑地球内部结构变化。适合局部小尺度的地震研究。",
            "iasp91": "IASPEI 1991参考地球模型：由国际地震和地球内部物理协会开发的标准地球参考模型。用于全球尺度地震定位。",
            "ak135": "AK135模型：由Kennett等人于1995年发表的地震学参考地球模型，是对iasp91的改进版本。更适用于远震定位。",
            "prem": "PREM模型(Preliminary Reference Earth Model)：由Dziewonski和Anderson于1981年提出的初步参考地球模型，考虑了地球旋转和各向异性影响。",
            "jb": "Jeffreys-Bullen模型：经典的地球速度模型，由Jeffreys和Bullen在1940年代开发，常用于震相走时计算。",
            "sp6": "SP6模型：现代的地球速度模型，提供高精度的地球内部结构参数，适合全球地震定位。",
            "1066a": "1066a模型：早期的地球参考模型，考虑了球状地球的分层结构，用于震相走时计算。",
            "ak135f": "AK135f模型：AK135的改进版本，包含更新的地球物理参数，用于更精确的地震定位。",
            "herrin": "Herrin模型：由Herrin等人于1968年提出的地球速度模型，曾广泛用于地震定位。"
        }
        self._initialize_models()
    
    def _check_model_file_exists(self, model_name):
        """检查ObsPy模型文件是否存在"""
        try:
            # 尝试导入ObsPy
            from obspy.taup import TauPyModel
            
            # 导入成功后，检查模型文件是否存在
            import os
            import obspy
            
            # 获取ObsPy安装路径
            obspy_path = os.path.dirname(obspy.__file__)
            model_path = os.path.join(obspy_path, "taup", "data", f"{model_name}.npz")
            
            # 检查文件是否存在
            exists = os.path.exists(model_path)
            print(f"模型 {model_name} 文件{'' if exists else '不'}存在")
            return exists
        except ImportError:
            print(f"ObsPy未能导入，无法检查模型 {model_name}")
            return False
        except Exception as e:
            print(f"检查模型文件时出错: {e}")
            return False
    
    def _initialize_models(self):
        """初始化所有可用的速度模型"""
        try:
            # 初始化简单模型
            self._models["simple"] = SimpleVelocityModel()
            
            # 尝试初始化ObsPy模型
            try:
                # 先检查ObsPy能否正常导入
                import obspy
                from obspy.taup import TauPyModel
                
                # ObsPy标准模型列表
                standard_models = ["iasp91", "ak135", "prem"]
                # 添加更多可选模型
                additional_models = ["jb", "sp6", "1066a", "ak135f", "herrin"]
                
                all_models = standard_models + additional_models
                
                print("正在初始化ObsPy模型...")
                
                # 初始化标准模型和附加模型
                for model_name in all_models:
                    try:
                        # 检查模型文件是否存在
                        if self._check_model_file_exists(model_name):
                            # 创建测试模型实例，检查是否能成功加载
                            test_model = TauPyModel(model=model_name)
                            # 测试一个简单的路径计算
                            test = test_model.get_travel_times(source_depth_in_km=10, 
                                                             distance_in_degree=10, 
                                                             phase_list=["P"])
                            if test:
                                self._models[model_name] = ObsPyVelocityModel(model_name)
                                print(f"ObsPy模型 {model_name} 初始化成功")
                            else:
                                print(f"ObsPy模型 {model_name} 初始化失败：未能计算测试路径")
                        else:
                            print(f"ObsPy模型 {model_name} 文件不存在，跳过加载")
                    except Exception as e:
                        print(f"ObsPy模型 {model_name} 初始化失败: {e}")
                        traceback.print_exc()
                
                # 检查是否成功加载了至少一个ObsPy模型
                if len(self._models) <= 1:  # 只有simple模型
                    print("未能成功加载任何ObsPy模型，将只使用简单模型")
                else:
                    print(f"成功加载了 {len(self._models) - 1} 个ObsPy模型")
                
            except ImportError as e:
                print(f"ObsPy未安装或导入失败: {e}，将只使用简单模型")
            
            # 加载自定义模型
            self._load_custom_models()
            
            # 设置默认模型
            model_name = self.config.get_velocity_model() or "simple"
            self.set_current_model(model_name)
            
        except Exception as e:
            print(f"初始化模型管理器失败: {e}")
            traceback.print_exc()
            # 确保至少有简单模型可用
            self._models["simple"] = SimpleVelocityModel()
            self.set_current_model("simple")
    
    def _load_custom_models(self):
        """加载所有自定义模型"""
        try:
            # 确保模型目录存在
            if not os.path.exists(self.models_dir):
                os.makedirs(self.models_dir, exist_ok=True)
                print(f"创建模型目录: {self.models_dir}")
                return
            
            # 加载所有JSON模型文件
            model_files = [f for f in os.listdir(self.models_dir) if f.endswith('.json')]
            print(f"发现 {len(model_files)} 个自定义模型文件")
            
            for model_file in model_files:
                try:
                    file_path = os.path.join(self.models_dir, model_file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        model_data = json.load(f)
                    
                    # 获取模型名称
                    model_name = model_data.get('name')
                    if not model_name:
                        print(f"模型文件 {model_file} 没有名称，跳过加载")
                        continue
                    
                    # 创建自定义模型实例
                    custom_model = SimpleVelocityModel(model_name=model_name)
                    custom_model.load_from_json(model_data)
                    
                    # 添加到模型字典
                    self._models[model_name] = custom_model
                    
                    # 添加模型描述
                    if model_name not in self._model_descriptions:
                        description = model_data.get('description', f"自定义模型: {model_name}")
                        self._model_descriptions[model_name] = description
                    
                    print(f"成功加载自定义模型: {model_name}")
                    
                except Exception as e:
                    print(f"加载自定义模型 {model_file} 失败: {e}")
                    traceback.print_exc()
        
        except Exception as e:
            print(f"加载自定义模型失败: {e}")
            traceback.print_exc()
    
    def get_model(self, model_name):
        """获取指定名称的速度模型"""
        if model_name in self._models:
            return self._models[model_name]
        
        # 如果请求的模型不存在，返回简单模型
        print(f"请求的模型 '{model_name}' 不存在，返回简单模型")
        return self._models["simple"]
    
    def get_current_model(self):
        """获取当前使用的速度模型"""
        # 如果当前没有设置模型或者设置的模型不可用，则尝试加载配置文件中指定的模型
        if not self._current_model_name or self._current_model_name not in self._models:
            model_name = self.config.get_velocity_model() or "simple"
            self.set_current_model(model_name)
        
        # 返回当前模型
        return self._models[self._current_model_name]
    
    def set_current_model(self, model_name):
        """设置当前使用的速度模型"""
        # 如果请求的模型存在，则设置为当前模型
        if model_name in self._models:
            try:
                # 检查模型是否可用
                model = self._models[model_name]
                
                # 执行一个简单计算来验证模型可用性
                test_result = model.calculate_time_delay(
                    source_pos=(0, 0, 1000),
                    receiver_pos=(1000, 0, 0),
                    phase="P"
                )
                
                # 设置为当前模型
                self._current_model_name = model_name
                self.config.set_velocity_model(model_name)
                print(f"成功设置当前速度模型为: {model_name}, 测试结果: {test_result}")
                return True
            except Exception as e:
                print(f"模型 '{model_name}' 不可用: {e}")
                traceback.print_exc()
        
        # 如果请求的模型不存在或不可用，尝试使用简单模型
        if "simple" in self._models:
            self._current_model_name = "simple"
            self.config.set_velocity_model("simple")
            print(f"模型 '{model_name}' 不可用，回退到简单模型")
            return True
            
        # 如果简单模型也不可用，返回失败
        print("无法设置任何速度模型")
        return False
    
    def get_available_models(self):
        """
        获取所有可用模型的名称列表
        
        返回:
        list: 模型名称列表
        """
        # 确保模型已初始化
        if not self._initialized:
            self._initialize_models()
            
        # 返回所有模型名称
        return list(self._models.keys())
    
    def get_model_description(self, model_name):
        """获取模型描述信息"""
        return self._model_descriptions.get(model_name, f"未知模型: {model_name}")
    
    def validate_all_models(self):
        """验证所有模型是否可用"""
        results = {}
        
        for model_name, model in self._models.items():
            try:
                # 执行一个简单计算来验证模型可用性
                test_result = model.calculate_time_delay(
                    source_pos=(0, 0, 1000),
                    receiver_pos=(1000, 0, 0),
                    phase="P"
                )
                results[model_name] = {
                    "status": "可用",
                    "test_result": test_result,
                    "description": self.get_model_description(model_name)
                }
            except Exception as e:
                results[model_name] = {
                    "status": "不可用",
                    "error": str(e),
                    "description": self.get_model_description(model_name)
                }
        
        return results
    
    def calculate_time_delay(self, source_pos, receiver_pos, fixed_speed=None, phase="P"):
        """
        计算从震源到接收器的时间延迟(代理到当前模型)
        
        参数:
        source_pos: 震源位置(x, y, z)
        receiver_pos: 接收器位置(x, y, z)
        fixed_speed: 固定速度值
        phase: 波相位
        
        返回:
        时间延迟(秒)
        """
        try:
            model = self.get_current_model()
            if model:
                return model.calculate_time_delay(source_pos, receiver_pos, fixed_speed, phase)
            else:
                # 尝试使用回退模型
                if "simple" in self._models:
                    print("当前模型不可用，使用回退模型计算")
                    return self._models["simple"].calculate_time_delay(source_pos, receiver_pos, fixed_speed, phase)
                else:
                    # 最后回退到简单计算
                    distance = ((source_pos[0] - receiver_pos[0])**2 + 
                              (source_pos[1] - receiver_pos[1])**2 + 
                              (source_pos[2] - receiver_pos[2])**2)**0.5
                    return distance / (fixed_speed or 5500.0)  # 默认P波速度
        except Exception as e:
            print(f"计算时间延迟时出错: {e}")
            print(traceback.format_exc())
            
            # 错误时使用简单计算
            try:
                distance = ((source_pos[0] - receiver_pos[0])**2 + 
                          (source_pos[1] - receiver_pos[1])**2 + 
                          (source_pos[2] - receiver_pos[2])**2)**0.5
                return distance / (fixed_speed or 5500.0)  # 默认P波速度
            except:
                # 最终回退，确保不会崩溃
                return 0.01  # 返回一个合理的非零值

    def get_model_data(self, model_name):
        """
        获取指定模型的原始数据
        
        参数:
        model_name: 模型名称
        
        返回:
        dict: 模型数据字典
        """
        # 检查是否是自定义JSON模型
        json_path = os.path.join(self.models_dir, f"{model_name}.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"读取模型文件失败: {e}")
                return None
        
        # 如果不是JSON文件，尝试从内置模型获取数据
        if model_name in self._models:
            model = self._models[model_name]
            # 尝试获取模型的JSON表示
            if hasattr(model, 'to_json'):
                return model.to_json()
            elif hasattr(model, 'to_dict'):
                return model.to_dict()
            else:
                # 构造基本模型数据
                data = {
                    "name": model_name,
                    "description": self._model_descriptions.get(model_name, ""),
                    "source": "内置模型",
                    "parameters": {},
                    "layers": []
                }
                return data
        
        return None
            
    def refresh_models(self):
        """
        刷新可用模型列表
        
        当添加新模型或修改现有模型时调用此方法
        """
        try:
            # 清空现有模型中的自定义模型
            # 注意：只清除自定义模型，保留内置模型
            custom_models = []
            for model_name in list(self._models.keys()):
                if os.path.exists(os.path.join(self.models_dir, f"{model_name}.json")):
                    custom_models.append(model_name)
            
            # 从模型列表中移除旧的自定义模型
            for model_name in custom_models:
                if model_name in self._models:
                    del self._models[model_name]
            
            # 加载所有JSON模型文件
            if os.path.exists(self.models_dir):
                for file_name in os.listdir(self.models_dir):
                    if file_name.endswith('.json'):
                        try:
                            # 读取模型数据
                            file_path = os.path.join(self.models_dir, file_name)
                            with open(file_path, 'r', encoding='utf-8') as f:
                                model_data = json.load(f)
                            
                            # 获取模型名称
                            model_name = model_data.get('name')
                            if not model_name:
                                print(f"模型文件 {file_name} 没有名称，跳过加载")
                                continue
                            
                            # 创建自定义模型实例
                            custom_model = SimpleVelocityModel(model_name=model_name)
                            custom_model.load_from_json(model_data)
                            
                            # 添加到模型字典
                            self._models[model_name] = custom_model
                            
                            # 更新模型描述
                            if "description" in model_data:
                                self._model_descriptions[model_name] = model_data["description"]
                            else:
                                self._model_descriptions[model_name] = f"自定义模型: {model_name}"
                                
                            print(f"成功加载自定义模型: {model_name}")
                                
                        except Exception as e:
                            print(f"加载模型文件 {file_name} 失败: {e}")
                            traceback.print_exc()
            
            print(f"刷新模型完成，当前可用模型: {list(self._models.keys())}")
            
        except Exception as e:
            print(f"刷新模型列表失败: {e}")
            import traceback
            traceback.print_exc()

    def delete_model(self, model_name):
        """
        删除指定名称的模型
        
        参数:
        model_name: 要删除的模型名称
        
        返回:
        bool: 是否成功删除
        """
        try:
            # 内置模型列表
            built_in_models = ["AK135", "IASP91", "PREM", "JB", "SP6", "1066A", "Herrin", "AK135F", "999"]
            
            # 检查是否为内置模型 (不区分大小写)
            if model_name.upper() in [m.upper() for m in built_in_models]:
                raise ValueError(f"{model_name} 是内置模型，不能删除")
            
            # 检查模型是否存在
            if model_name not in self._models:
                raise ValueError(f"模型 {model_name} 不存在")
            
            # 检查对应的JSON文件是否存在
            json_file = os.path.join(self.models_dir, f"{model_name}.json")
            if not os.path.exists(json_file):
                raise ValueError(f"模型文件 {json_file} 不存在")
            
            # 从内存中删除模型
            if model_name in self._models:
                del self._models[model_name]
            
            # 删除文件
            os.remove(json_file)
            
            # 如果当前模型被删除，切换到默认模型
            if self._current_model_name == model_name:
                self._current_model_name = self.config.get_velocity_model() or "simple"
            
            return True
        except Exception as e:
            print(f"删除模型失败: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    # 简单测试
    manager = ModelManager()
    print(f"当前模型: {manager.get_current_model().model_name}")
    
    # 测试获取所有可用模型
    available_models = manager.get_available_models()
    print(f"可用模型: {available_models}")
    
    # 获取模型描述
    for model in available_models:
        print(f"{model}: {manager.get_model_description(model)}")
    
    # 切换模型
    if "ak135" in available_models and manager.set_current_model("ak135"):
        print(f"切换到模型: {manager.get_current_model().model_name}")
    
    # 测试时间延迟计算
    source = (0, 0, 10000)  # 10km深度
    receiver = (50000, 0, 0)  # 地表50km处
    delay = manager.calculate_time_delay(source, receiver)
    print(f"从震源到接收器的时间延迟: {delay:.3f} 秒") 