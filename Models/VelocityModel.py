from obspy.taup import TauPyModel
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import sys
import traceback
import platform
from PyQt6.QtCore import QObject
import math

# 设置matplotlib中文字体支持
# 根据系统选择合适的字体
system = platform.system()
if system == 'Darwin':  # macOS
    font_list = ['Arial Unicode MS', 'STHeiti', 'Heiti SC', 'PingFang SC']
elif system == 'Windows':
    font_list = ['Microsoft YaHei', 'SimHei']
else:  # Linux和其他系统
    font_list = ['DejaVu Sans']

# 尝试设置字体
for font in font_list:
    try:
        matplotlib.rcParams['font.family'] = font
        print(f"设置字体: {font}")
        break
    except:
        continue

matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 简单的恒定速度模型
class SimpleVelocityModel:
    """简单的速度模型，使用固定的P波和S波速度"""
    
    def __init__(self, model_name="simple", vp=5.5, vs=3.0):
        """
        初始化简单速度模型
        
        参数:
        model_name: 模型名称
        vp: P波速度(km/s)
        vs: S波速度(km/s)
        """
        self.model_name = model_name
        self.vp = vp  # P波速度(km/s)
        self.vs = vs  # S波速度(km/s)
        
        # 基本参数
        self.parameters = {
            "earth_radius": 6371.0,  # 地球半径(km)
            "moho_depth": 35.0,      # 莫霍面深度(km)
            "cmb_depth": 2891.0,     # 核幔边界深度(km)
            "icb_depth": 5150.0      # 内外核边界深度(km)
        }
        
        # 层数据
        self.layers = []
    
    def to_json(self):
        """
        将模型转换为JSON格式的数据
        
        返回:
        dict: 表示模型的字典，可以被json.dumps()序列化
        """
        # 构建参数字典
        params = {}
        for param_name, value in self.parameters.items():
            params[param_name] = {
                "value": value,
                "unit": "km" if "depth" in param_name or param_name == "earth_radius" else ""
            }
        
        # 如果没有层数据，创建一个简单的单层模型
        if not self.layers:
            self.layers = [
                {"depth": 0, "vp": self.vp, "vs": self.vs, "density": 2.7},
                {"depth": 35, "vp": 6.5, "vs": 3.7, "density": 2.9},
                {"depth": 100, "vp": 8.1, "vs": 4.5, "density": 3.3},
                {"depth": 300, "vp": 8.3, "vs": 4.7, "density": 3.5}
            ]
        
        # 构建完整的模型数据
        model_data = {
            "name": self.model_name,
            "description": f"简单速度模型 (P波: {self.vp} km/s, S波: {self.vs} km/s)",
            "source": "用户自定义",
            "parameters": params,
            "layers": self.layers
        }
        
        return model_data
    
    def load_from_json(self, data):
        """
        从JSON数据加载模型参数
        
        参数:
        data: JSON数据(字典格式)
        """
        if not data:
            return
            
        # 加载基本属性
        self.model_name = data.get("name", self.model_name)
        
        # 加载基本参数
        if "parameters" in data:
            for param_name, param_data in data["parameters"].items():
                if isinstance(param_data, dict) and "value" in param_data:
                    value = param_data["value"]
                else:
                    value = param_data  # 简单格式，直接使用值
                self.parameters[param_name] = value if isinstance(value, dict) else {"value": value}
        
        # 加载层数据
        if "layers" in data:
            self.layers = []
            for layer_data in data["layers"]:
                # 确保所有必需字段都存在
                layer = {
                    "depth": layer_data.get("depth", 0),
                    "vp": layer_data.get("vp", 0),
                    "vs": layer_data.get("vs", 0),
                    "density": layer_data.get("density", 0)
                }
                
                # 如果有描述字段，也加载
                if "description" in layer_data:
                    layer["description"] = layer_data["description"]
                
                self.layers.append(layer)
            
            # 按深度排序
            self.layers.sort(key=lambda x: x["depth"])
        
        # 更新基本P波和S波速度 (取第一层或平均值)
        if self.layers:
            # 取第一层的速度值作为基本速度
            self.vp = self.layers[0].get("vp", self.vp)
            self.vs = self.layers[0].get("vs", self.vs)
        
        return self
    
    def calculate_time_delay(self, source_pos, receiver_pos, fixed_speed=None, phase="P"):
        """
        计算从震源到接收器的时间延迟
        
        参数:
        source_pos: 震源位置(x, y, z)，单位为米
        receiver_pos: 接收器位置(x, y, z)，单位为米
        fixed_speed: 固定速度值，单位为km/s，如果提供则使用此速度
        phase: 波相位，"P"或"S"
        
        返回:
        时间延迟(秒)
        """
        try:
            # 计算震源和接收器之间的距离(米)
            distance = ((source_pos[0] - receiver_pos[0])**2 + 
                      (source_pos[1] - receiver_pos[1])**2 + 
                      (source_pos[2] - receiver_pos[2])**2)**0.5
            
            # 转换为km
            distance_km = distance / 1000.0
            
            # 根据波相选择速度(km/s)
            if fixed_speed is not None:
                velocity = fixed_speed
            elif phase.upper() == "P":
                velocity = self.vp
            elif phase.upper() == "S":
                velocity = self.vs
            else:
                print(f"未知波相: {phase}，使用P波速度")
                velocity = self.vp
            
            # 计算时间(s)
            time_delay = distance_km / velocity
            
            return time_delay
            
        except Exception as e:
            print(f"计算时间延迟时出错: {e}")
            return 0.0

# ObsPy的地球模型包装类
class ObsPyVelocityModel:
    def __init__(self, model_name="iasp91"):
        """
        初始化ObsPy速度模型
        
        参数:
        model_name: 模型名称，支持'iasp91'、'ak135'、'prem'等
        """
        self.model_name = model_name
        self._model = None
        self._initialize_model()
        
    def _initialize_model(self):
        """初始化ObsPy模型"""
        try:
            # 尝试导入ObsPy
            try:
                from obspy.taup import TauPyModel
            except ImportError:
                raise ImportError("未安装ObsPy或无法导入TauPyModel，请确保环境中安装了ObsPy库")
            
            # 初始化选定的模型
            self._model = TauPyModel(model=self.model_name)
            
            # 验证模型是否可用
            test = self._model.get_travel_times(source_depth_in_km=10, 
                                              distance_in_degree=10, 
                                              phase_list=["P"])
            if not test:
                raise ValueError(f"模型 {self.model_name} 初始化成功但未能计算测试路径")
                
            print(f"ObsPy {self.model_name} 模型初始化成功")
            
        except Exception as e:
            self._model = None
            print(f"初始化ObsPy模型 {self.model_name} 失败: {e}")
            print(traceback.format_exc())
            raise e

    def _cartesian_to_spherical(self, source_pos, receiver_pos):
        """
        将笛卡尔坐标转换为球坐标（距离和深度）
        
        参数:
        source_pos: (x, y, z) 震源位置，z为深度(m)
        receiver_pos: (x, y, z) 检波器位置，z为深度(m)
        
        返回:
        (distance_in_degree, source_depth_in_km)
        """
        try:
            # 计算水平距离（单位：米）
            dx = source_pos[0] - receiver_pos[0]
            dy = source_pos[1] - receiver_pos[1]
            horizontal_distance = math.sqrt(dx**2 + dy**2)
            
            # 将水平距离转换为角度（近似）
            # 地球半径约6371km，周长约40030km
            # 1度≈111.2km≈111200m
            distance_in_degree = horizontal_distance / 111200
            
            # 深度转换为km
            source_depth_in_km = source_pos[2] / 1000  # 假设z轴正向下为正
            
            return distance_in_degree, source_depth_in_km
        except Exception as e:
            print(f"坐标转换失败: {e}")
            print(traceback.format_exc())
            # 返回安全值
            return 0.1, 10  # 默认0.1度距离，10km深度

    def calculate_time_delay(self, source_pos, receiver_pos, fixed_speed=None, phase="P"):
        """
        使用ObsPy计算从震源到检波器的传播时间
        
        参数:
        source_pos: (x, y, z) 震源位置，z为深度(m)
        receiver_pos: (x, y, z) 检波器位置，z为深度(m)
        fixed_speed: 如果提供，将使用此速度而非模型速度
        phase: 选择波相（"P" 或 "S"），默认为P波
        
        返回:
        传播时间(秒)
        """
        # 如果提供了固定速度，使用简单模型计算
        if fixed_speed is not None:
            simple_model = SimpleVelocityModel()
            return simple_model.calculate_time_delay(source_pos, receiver_pos, fixed_speed, phase)
        
        try:
            # 确保模型已初始化
            if self._model is None:
                print("模型未初始化，尝试重新初始化")
                self._initialize_model()
                if self._model is None:
                    raise ValueError("模型初始化失败，无法计算时间延迟")
            
            # 将笛卡尔坐标转换为球坐标
            distance_in_degree, source_depth_in_km = self._cartesian_to_spherical(source_pos, receiver_pos)
            
            # 确保最小距离和深度
            distance_in_degree = max(0.1, distance_in_degree)  # 至少0.1度
            source_depth_in_km = max(0.1, source_depth_in_km)  # 至少0.1km深
            
            # 计算传播时间
            phase_to_use = phase.upper()
            arrivals = self._model.get_travel_times(
                source_depth_in_km=source_depth_in_km,
                distance_in_degree=distance_in_degree,
                phase_list=[phase_to_use]
            )
            
            # 检查是否有结果
            if not arrivals:
                print(f"未找到指定波相 {phase_to_use} 的到时，尝试使用任意首波")
                # 尝试使用任意波相
                arrivals = self._model.get_travel_times(
                    source_depth_in_km=source_depth_in_km,
                    distance_in_degree=distance_in_degree
                )
                
                if not arrivals:
                    # 仍然没有结果，回退到简单模型
                    print("ObsPy模型未返回结果，回退到简单模型计算")
                    simple_model = SimpleVelocityModel()
                    return simple_model.calculate_time_delay(source_pos, receiver_pos, None, phase)
            
            # 返回第一个到达的时间
            return arrivals[0].time
            
        except Exception as e:
            print(f"ObsPy模型计算时间延迟失败: {e}")
            print(traceback.format_exc())
            
            # 发生错误时回退到简单模型
            try:
                print("回退到简单模型计算")
                simple_model = SimpleVelocityModel()
                return simple_model.calculate_time_delay(source_pos, receiver_pos, None, phase)
            except Exception as nested_e:
                print(f"简单模型也失败了: {nested_e}")
                # 保底返回一个合理的值
                return 0.0

class VelocityModel(QObject):
    """封装ObsPy的TauPy功能，提供地震波速度模型和到达时间计算"""
    
    def __init__(self, model_name="iasp91"):
        """
        初始化速度模型
        
        参数:
        model_name: 模型名称，可选值包括: iasp91, ak135, prem等，默认使用iasp91
                   设置为"simple"时使用简单恒定速度模型
        """
        super().__init__()
        self.model_name = model_name
        self.is_simple_model = (model_name.lower() == "simple")
        self.debug_info = []  # 用于存储调试信息
        self.model = None
        
        if not self.is_simple_model:
            try:
                # 使用安全模式尝试加载ObsPy模型
                self._safely_load_model(model_name)
            except Exception as e:
                error_info = f"加载ObsPy速度模型失败: {e}, 回退到简单速度模型"
                print(error_info)
                print(traceback.format_exc())
                self.add_debug_info(error_info)
                self.is_simple_model = True
        else:
            self.add_debug_info("使用简单恒定速度模型")
    
    def _safely_load_model(self, model_name):
        """安全地加载ObsPy模型，避免程序崩溃"""
        try:
            # 尝试导入并创建模型
            self.model = TauPyModel(model=model_name)
            success_msg = f"成功加载ObsPy速度模型: {model_name}"
            print(success_msg)
            self.add_debug_info(success_msg)
        except ImportError:
            # ObsPy库可能没有正确安装
            error_msg = "未能导入ObsPy库，请确保正确安装：pip install obspy"
            print(error_msg)
            self.add_debug_info(error_msg)
            self.is_simple_model = True
        except Exception as e:
            # 其他可能的错误
            error_msg = f"加载ObsPy模型时出错: {e}"
            print(error_msg)
            print(traceback.format_exc())
            self.add_debug_info(error_msg)
            self.is_simple_model = True
    
    def add_debug_info(self, info):
        """添加调试信息"""
        self.debug_info.append(info)
        if len(self.debug_info) > 100:  # 限制调试信息数量
            self.debug_info = self.debug_info[-100:]
    
    def get_debug_info(self):
        """获取调试信息"""
        return self.debug_info
    
    def get_travel_time(self, source_depth, receiver_distance, phase_list=None):
        """
        计算给定震源深度和接收器距离的理论到达时间
        
        参数:
        source_depth: 震源深度，单位km
        receiver_distance: 接收器与震源的距离，单位度
        phase_list: 要计算的相位列表，如["P", "S"]
        
        返回:
        到达时间列表
        """
        if self.is_simple_model or self.model is None:
            self.add_debug_info(f"简单模型不支持获取到达时间")
            return []  # 简单模型不支持此功能
        
        try:
            arrivals = self.model.get_travel_times(
                source_depth_in_km=source_depth,
                distance_in_degree=receiver_distance,
                phase_list=phase_list
            )
            self.add_debug_info(f"计算到达时间：深度={source_depth}km, 距离={receiver_distance}度, 找到{len(arrivals)}个到达")
            return arrivals
        except Exception as e:
            self.add_debug_info(f"计算到达时间失败: {e}")
            return []
    
    def get_ray_paths(self, source_depth, receiver_distance, phase_list=None):
        """
        计算给定震源深度和接收器距离的射线路径
        
        参数:
        source_depth: 震源深度，单位km
        receiver_distance: 接收器与震源的距离，单位度
        phase_list: 要计算的相位列表，如["P", "S"]
        
        返回:
        射线路径列表
        """
        if self.is_simple_model or self.model is None:
            self.add_debug_info(f"简单模型不支持获取射线路径")
            return []  # 简单模型不支持此功能
        
        try:
            paths = self.model.get_ray_paths(
                source_depth_in_km=source_depth,
                distance_in_degree=receiver_distance,
                phase_list=phase_list
            )
            self.add_debug_info(f"计算射线路径：深度={source_depth}km, 距离={receiver_distance}度, 找到{len(paths)}条路径")
            return paths
        except Exception as e:
            self.add_debug_info(f"计算射线路径失败: {e}")
            return []
    
    def calculate_time_delay(self, source_pos, receiver_pos, fixed_speed=None, phase="P"):
        """
        计算从震源到接收器的时间延迟
        
        参数:
        source_pos: 震源位置(x, y, z)，单位为米
        receiver_pos: 接收器位置(x, y, z)，单位为米
        fixed_speed: 固定速度值，单位为km/s，如果提供则使用此速度
        phase: 波相位，"P"或"S"
        
        返回:
        时间延迟(秒)
        """
        try:
            # 计算震源和接收器之间的距离(米)
            distance = ((source_pos[0] - receiver_pos[0])**2 + 
                      (source_pos[1] - receiver_pos[1])**2 + 
                      (source_pos[2] - receiver_pos[2])**2)**0.5
            
            # 转换为km
            distance_km = distance / 1000.0
            
            # 根据波相选择速度(km/s)
            if fixed_speed is not None:
                velocity = fixed_speed
            elif phase.upper() == "P":
                velocity = self.vp
            elif phase.upper() == "S":
                velocity = self.vs
            else:
                print(f"未知波相: {phase}，使用P波速度")
                velocity = self.vp
            
            # 计算时间(s)
            time_delay = distance_km / velocity
            
            return time_delay
            
        except Exception as e:
            print(f"计算时间延迟时出错: {e}")
            return 0.0
    
    def plot_velocity_profile(self, max_depth=700):
        """
        绘制速度模型的速度-深度剖面图
        
        参数:
        max_depth: 最大深度(km)
        
        返回:
        matplotlib图表对象
        """
        try:
            if self.is_simple_model or self.model is None:
                # 简单模型绘制恒定速度
                depths = np.linspace(0, max_depth, 100)
                p_velocities = np.ones_like(depths) * 5.5  # 5.5 km/s
                s_velocities = np.ones_like(depths) * 3.2  # 3.2 km/s
            else:
                try:
                    # 使用ObsPy模型数据
                    model_data = self.model.model
                    depths = []
                    p_velocities = []
                    s_velocities = []
                    
                    # 提取模型数据
                    for i in range(len(model_data.s_mod.v_mod.layers)):
                        layer = model_data.s_mod.v_mod.layers[i]
                        if layer.depth <= max_depth:
                            depths.append(layer.depth)
                            p_velocities.append(layer.v_p)
                            s_velocities.append(layer.v_s)
                except Exception as e:
                    error_msg = f"获取模型数据失败: {e}, 使用简单模型数据"
                    print(error_msg)
                    self.add_debug_info(error_msg)
                    
                    # 回退到简单模型
                    depths = np.linspace(0, max_depth, 100)
                    p_velocities = np.ones_like(depths) * 5.5
                    s_velocities = np.ones_like(depths) * 3.2
            
            # 创建图表
            fig, ax = plt.subplots(figsize=(8, 10))
            ax.plot(p_velocities, depths, 'r-', label='P波速度')
            ax.plot(s_velocities, depths, 'b-', label='S波速度')
            
            # 设置轴标签和标题
            ax.set_xlabel('速度 (km/s)')
            ax.set_ylabel('深度 (km)')
            ax.set_title(f'速度模型: {self.model_name}')
            
            # 反转Y轴使深度向下增加
            ax.invert_yaxis()
            
            # 添加图例
            ax.legend()
            ax.grid(True)
            
            return fig
        except Exception as e:
            self.add_debug_info(f"绘制速度剖面图时出错: {e}")
            return None


if __name__ == "__main__":
    # 简单测试代码
    model = VelocityModel("iasp91")
    
    # 测试获取到达时间
    arrivals = model.get_travel_time(source_depth=10, receiver_distance=30, phase_list=["P", "S"])
    print("到达时间:")
    for arr in arrivals:
        print(f"  {arr.name} 波相位，到达时间: {arr.time:.3f} 秒")
    
    # 测试时间延迟计算
    source = (0, 0, 10000)  # 10km深度
    receiver = (50000, 0, 0)  # 地表50km处
    delay = model.calculate_time_delay(source, receiver)
    print(f"从震源到接收器的时间延迟: {delay:.3f} 秒")
    
    # 绘制速度剖面图
    fig = model.plot_velocity_profile()
    plt.show() 