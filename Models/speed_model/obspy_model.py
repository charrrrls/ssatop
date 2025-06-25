"""
ObsPy地球模型封装模块

提供基于ObsPy的专业地震学速度模型，
支持多种标准地球模型进行精确的地震波传播时间计算。

支持的模型：
🌍 iasp91 - IASPEI 1991参考地球模型
🌍 ak135 - AK135地震学参考模型
🌍 prem - 初步参考地球模型
🌍 其他ObsPy支持的模型

特点：
🎯 高精度计算
🌐 全球尺度适用
📊 考虑地球内部结构
🔬 专业地震学标准

作者: ssatop项目组
创建时间: 2024
"""

import traceback
from typing import Tuple, Optional, List
from .base_model import BaseVelocityModel, ModelInitializationError, CalculationError
from .utils import cartesian_to_spherical, calculate_distance_3d, get_default_velocities


class ObsPyVelocityModel(BaseVelocityModel):
    """
    ObsPy地球模型封装类
    
    封装ObsPy的TauPyModel功能，提供专业的地震学速度模型。
    支持多种标准地球模型，能够精确计算地震波在复杂地球结构中的传播时间。
    
    适用场景:
    - 全球地震定位
    - 远震研究
    - 精确走时计算
    - 专业地震学分析
    """
    
    def __init__(self, model_name: str = "iasp91"):
        """
        初始化ObsPy速度模型
        
        参数:
            model_name (str): 模型名称，支持'iasp91'、'ak135'、'prem'等
            
        异常:
            ModelInitializationError: 模型初始化失败时抛出
        """
        super().__init__(model_name)
        self._obspy_model = None
        
        # 尝试初始化ObsPy模型
        try:
            self._initialize_obspy_model()
            self._is_initialized = True
            self.add_debug_info(f"ObsPy {model_name} 模型初始化成功")
        except Exception as e:
            error_msg = f"ObsPy模型 {model_name} 初始化失败: {e}"
            self.add_debug_info(error_msg)
            raise ModelInitializationError(error_msg, model_name) from e
    
    def _initialize_obspy_model(self):
        """
        初始化ObsPy TauPy模型
        
        异常:
            ImportError: ObsPy库未安装或导入失败
            Exception: 模型初始化过程中的其他错误
        """
        try:
            # 尝试导入ObsPy
            from obspy.taup import TauPyModel
            self.add_debug_info("成功导入ObsPy TauPyModel")
        except ImportError as e:
            raise ImportError(
                "未安装ObsPy或无法导入TauPyModel。"
                "请使用以下命令安装: pip install obspy"
            ) from e
        
        try:
            # 创建模型实例
            self._obspy_model = TauPyModel(model=self.model_name)
            
            # 验证模型是否可用 - 执行测试计算
            test_arrivals = self._obspy_model.get_travel_times(
                source_depth_in_km=10, 
                distance_in_degree=10, 
                phase_list=["P"]
            )
            
            if not test_arrivals:
                raise ValueError(f"模型 {self.model_name} 初始化成功但未能计算测试路径")
            
            self.add_debug_info(f"模型验证成功，测试到达时间: {test_arrivals[0].time:.3f}s")
            
        except Exception as e:
            self._obspy_model = None
            raise Exception(f"创建TauPyModel实例失败: {e}") from e
    
    def calculate_time_delay(self, 
                           source_pos: Tuple[float, float, float], 
                           receiver_pos: Tuple[float, float, float],
                           fixed_speed: Optional[float] = None, 
                           phase: str = "P") -> float:
        """
        使用ObsPy计算从震源到检波器的传播时间
        
        参数:
            source_pos (tuple): (x, y, z) 震源位置，z为深度(m)
            receiver_pos (tuple): (x, y, z) 检波器位置，z为深度(m)
            fixed_speed (float, optional): 如果提供，将回退到简单计算
            phase (str): 选择波相（"P" 或 "S"），默认为P波
        
        返回:
            float: 传播时间(秒)
            
        异常:
            CalculationError: 计算失败时抛出
        """
        # 如果提供了固定速度，使用简单模型计算
        if fixed_speed is not None:
            self.add_debug_info(f"使用固定速度 {fixed_speed} m/s 进行简单计算")
            return self._simple_calculation(source_pos, receiver_pos, fixed_speed, phase)
        
        try:
            # 确保模型已初始化
            if not self._is_initialized or self._obspy_model is None:
                raise CalculationError("模型未正确初始化", self.model_name)
            
            # 将笛卡尔坐标转换为球坐标
            distance_in_degree, source_depth_in_km = cartesian_to_spherical(
                source_pos, receiver_pos
            )
            
            # 确保最小距离和深度，避免计算错误
            distance_in_degree = max(0.1, distance_in_degree)  # 至少0.1度
            source_depth_in_km = max(0.1, abs(source_depth_in_km))  # 至少0.1km深
            
            self.add_debug_info(
                f"坐标转换: 距离={distance_in_degree:.4f}度, 深度={source_depth_in_km:.2f}km"
            )
            
            # 计算传播时间
            phase_to_use = phase.upper()
            arrivals = self._obspy_model.get_travel_times(
                source_depth_in_km=source_depth_in_km,
                distance_in_degree=distance_in_degree,
                phase_list=[phase_to_use]
            )
            
            # 检查是否有结果
            if not arrivals:
                self.add_debug_info(f"未找到指定波相 {phase_to_use} 的到时，尝试使用任意首波")
                
                # 尝试使用任意波相
                arrivals = self._obspy_model.get_travel_times(
                    source_depth_in_km=source_depth_in_km,
                    distance_in_degree=distance_in_degree
                )
                
                if not arrivals:
                    # 仍然没有结果，回退到简单模型
                    self.add_debug_info("ObsPy模型未返回结果，回退到简单模型计算")
                    return self._simple_calculation(source_pos, receiver_pos, None, phase)
            
            # 返回第一个到达的时间
            travel_time = arrivals[0].time
            
            self.add_debug_info(
                f"ObsPy计算成功: 波相={arrivals[0].name}, 时间={travel_time:.4f}s"
            )
            
            return travel_time
            
        except Exception as e:
            error_msg = f"ObsPy模型计算失败: {e}"
            self.add_debug_info(error_msg)
            print(f"❌ {error_msg}")
            print(traceback.format_exc())
            
            # 发生错误时回退到简单模型
            try:
                self.add_debug_info("回退到简单模型计算")
                return self._simple_calculation(source_pos, receiver_pos, None, phase)
            except Exception as nested_e:
                self.add_debug_info(f"简单模型也失败了: {nested_e}")
                raise CalculationError(f"所有计算方法都失败: {e}", self.model_name) from e
    
    def _simple_calculation(self, 
                          source_pos: Tuple[float, float, float], 
                          receiver_pos: Tuple[float, float, float],
                          fixed_speed: Optional[float] = None, 
                          phase: str = "P") -> float:
        """
        简单距离/速度计算的回退方法
        
        参数:
            source_pos (tuple): 震源位置
            receiver_pos (tuple): 检波器位置  
            fixed_speed (float, optional): 固定速度值
            phase (str): 波相
        
        返回:
            float: 传播时间
        """
        try:
            distance = calculate_distance_3d(source_pos, receiver_pos)
            
            if fixed_speed is not None:
                velocity = fixed_speed
            else:
                defaults = get_default_velocities()
                velocity = defaults['p_velocity'] if phase.upper() == "P" else defaults['s_velocity']
            
            travel_time = distance / velocity
            self.add_debug_info(
                f"简单计算: 距离={distance:.2f}m, 速度={velocity:.2f}m/s, 时间={travel_time:.4f}s"
            )
            
            return travel_time
        except Exception as e:
            self.add_debug_info(f"简单计算失败: {e}")
            # 保底返回值
            return 0.01
    
    def get_travel_times(self, 
                        source_depth: float, 
                        receiver_distance: float,
                        phase_list: Optional[List[str]] = None) -> List:
        """
        获取给定震源深度和接收器距离的理论到达时间
        
        参数:
            source_depth (float): 震源深度，单位km
            receiver_distance (float): 接收器与震源的距离，单位度
            phase_list (List[str], optional): 要计算的相位列表，如["P", "S"]
        
        返回:
            List: 到达时间列表（ObsPy Arrival对象）
            
        异常:
            CalculationError: 计算失败时抛出
        """
        if not self._is_initialized or self._obspy_model is None:
            raise CalculationError("模型未正确初始化", self.model_name)
        
        try:
            arrivals = self._obspy_model.get_travel_times(
                source_depth_in_km=source_depth,
                distance_in_degree=receiver_distance,
                phase_list=phase_list
            )
            
            self.add_debug_info(
                f"获取到达时间: 深度={source_depth}km, 距离={receiver_distance}度, "
                f"找到{len(arrivals)}个到达"
            )
            
            return arrivals
        except Exception as e:
            error_msg = f"获取到达时间失败: {e}"
            self.add_debug_info(error_msg)
            raise CalculationError(error_msg, self.model_name) from e
    
    def get_ray_paths(self, 
                     source_depth: float, 
                     receiver_distance: float,
                     phase_list: Optional[List[str]] = None) -> List:
        """
        获取给定震源深度和接收器距离的射线路径
        
        参数:
            source_depth (float): 震源深度，单位km
            receiver_distance (float): 接收器与震源的距离，单位度
            phase_list (List[str], optional): 要计算的相位列表，如["P", "S"]
        
        返回:
            List: 射线路径列表（ObsPy RayPath对象）
            
        异常:
            CalculationError: 计算失败时抛出
        """
        if not self._is_initialized or self._obspy_model is None:
            raise CalculationError("模型未正确初始化", self.model_name)
        
        try:
            paths = self._obspy_model.get_ray_paths(
                source_depth_in_km=source_depth,
                distance_in_degree=receiver_distance,
                phase_list=phase_list
            )
            
            self.add_debug_info(
                f"获取射线路径: 深度={source_depth}km, 距离={receiver_distance}度, "
                f"找到{len(paths)}条路径"
            )
            
            return paths
        except Exception as e:
            error_msg = f"获取射线路径失败: {e}"
            self.add_debug_info(error_msg)
            raise CalculationError(error_msg, self.model_name) from e
    
    def get_model_info(self) -> dict:
        """
        获取模型的详细信息
        
        返回:
            dict: 包含模型信息的字典
        """
        info = {
            'model_name': self.model_name,
            'is_initialized': self._is_initialized,
            'obspy_available': self._obspy_model is not None,
        }
        
        if self._obspy_model is not None:
            try:
                model_data = self._obspy_model.model
                info.update({
                    'radius_of_planet': model_data.radius_of_planet,
                    'max_radius': model_data.max_radius,
                    'min_radius': model_data.min_radius,
                    'is_spherical': model_data.is_spherical
                })
            except Exception as e:
                info['model_info_error'] = str(e)
        
        return info
    
    def validate_model(self) -> bool:
        """
        验证模型是否可用
        
        返回:
            bool: 模型是否可用
        """
        try:
            if not self._is_initialized or self._obspy_model is None:
                return False
            
            # 执行简单的测试计算
            test_arrivals = self._obspy_model.get_travel_times(
                source_depth_in_km=10,
                distance_in_degree=30,
                phase_list=["P"]
            )
            
            return len(test_arrivals) > 0
        except Exception as e:
            self.add_debug_info(f"模型验证失败: {e}")
            return False
    
    def __str__(self) -> str:
        """返回模型的字符串表示"""
        status = "已初始化" if self._is_initialized else "未初始化"
        available = "可用" if self._obspy_model is not None else "不可用"
        return f"ObsPy {self.model_name} 模型 ({status}, {available})"


if __name__ == "__main__":
    # 简单测试代码
    print("🧪 测试ObsPy速度模型...")
    
    try:
        # 创建模型实例
        model = ObsPyVelocityModel("iasp91")
        print(f"📋 模型信息: {model}")
        
        # 获取模型详细信息
        info = model.get_model_info()
        print(f"🔍 模型详情: {info}")
        
        # 测试时间延迟计算
        source = (0, 0, 10000)      # 震源：(0, 0, 10km深)
        receiver = (50000, 0, 0)    # 检波器：(50km, 0, 地表)
        
        # P波计算
        p_delay = model.calculate_time_delay(source, receiver, phase="P")
        print(f"⏱️ P波传播时间: {p_delay:.3f} 秒")
        
        # S波计算
        s_delay = model.calculate_time_delay(source, receiver, phase="S")
        print(f"⏱️ S波传播时间: {s_delay:.3f} 秒")
        
        # 测试到达时间计算
        arrivals = model.get_travel_times(10, 0.45, ["P", "S"])  # 约50km对应0.45度
        print(f"📊 找到 {len(arrivals)} 个到达:")
        for arrival in arrivals[:3]:  # 只显示前3个
            print(f"  {arrival.name}: {arrival.time:.3f}s")
        
        # 验证模型
        is_valid = model.validate_model()
        print(f"✅ 模型验证: {'通过' if is_valid else '失败'}")
        
        # 显示调试信息
        print("\n🔍 调试信息:")
        for info in model.get_debug_info()[-5:]:  # 只显示最后5条
            print(f"  {info}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print(traceback.format_exc())
    
    print("✅ 测试完成!") 