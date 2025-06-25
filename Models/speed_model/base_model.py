"""
速度模型基础抽象类模块

定义了所有速度模型必须实现的接口和通用行为，
为不同类型的速度模型提供统一的调用规范。

功能包括：
🔧 抽象基类定义
📋 通用接口规范
🛡️ 异常处理基类
📊 调试信息管理

作者: ssatop项目组
创建时间: 2025
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Union
import traceback


class VelocityModelError(Exception):
    """速度模型相关异常的基类"""
    
    def __init__(self, message: str, model_name: str = None):
        """
        初始化速度模型异常
        
        参数:
            message (str): 错误信息
            model_name (str): 发生错误的模型名称
        """
        self.model_name = model_name
        super().__init__(message)
    
    def __str__(self):
        if self.model_name:
            return f"[{self.model_name}] {super().__str__()}"
        return super().__str__()


class ModelInitializationError(VelocityModelError):
    """模型初始化失败异常"""
    pass


class CalculationError(VelocityModelError):
    """计算过程异常"""
    pass


class BaseVelocityModel(ABC):
    """
    速度模型抽象基类
    
    定义了所有速度模型必须实现的接口，包括：
    - 时间延迟计算
    - 调试信息管理
    - 模型验证
    
    所有具体的速度模型类都应该继承此基类并实现抽象方法。
    """
    
    def __init__(self, model_name: str):
        """
        初始化基础速度模型
        
        参数:
            model_name (str): 模型名称
        """
        self.model_name = model_name
        self.debug_info = []
        self._is_initialized = False
    
    @abstractmethod
    def calculate_time_delay(self, 
                           source_pos: Tuple[float, float, float], 
                           receiver_pos: Tuple[float, float, float],
                           fixed_speed: Optional[float] = None, 
                           phase: str = "P") -> float:
        """
        计算从震源到检波器的传播时间（抽象方法）
        
        参数:
            source_pos (tuple): (x, y, z) 震源位置，单位米
            receiver_pos (tuple): (x, y, z) 检波器位置，单位米
            fixed_speed (float, optional): 固定速度值，单位m/s
            phase (str): 波相（"P" 或 "S"），默认为P波
        
        返回:
            float: 传播时间，单位秒
            
        异常:
            CalculationError: 计算失败时抛出
        """
        pass
    
    def add_debug_info(self, info: str):
        """
        添加调试信息
        
        参数:
            info (str): 调试信息字符串
        """
        self.debug_info.append(f"[{self.model_name}] {info}")
        # 限制调试信息数量，避免内存泄漏
        if len(self.debug_info) > 100:
            self.debug_info = self.debug_info[-100:]
    
    def get_debug_info(self) -> List[str]:
        """
        获取调试信息列表
        
        返回:
            List[str]: 调试信息列表
        """
        return self.debug_info.copy()
    
    def clear_debug_info(self):
        """清空调试信息"""
        self.debug_info.clear()
    
    def is_initialized(self) -> bool:
        """
        检查模型是否已正确初始化
        
        返回:
            bool: 是否已初始化
        """
        return self._is_initialized
    
    def validate_positions(self, 
                          source_pos: Tuple[float, float, float], 
                          receiver_pos: Tuple[float, float, float]) -> bool:
        """
        验证震源和检波器位置的有效性
        
        参数:
            source_pos (tuple): 震源位置
            receiver_pos (tuple): 检波器位置
        
        返回:
            bool: 位置是否有效
        """
        try:
            # 检查是否为3元组
            if (not isinstance(source_pos, (tuple, list)) or len(source_pos) != 3 or
                not isinstance(receiver_pos, (tuple, list)) or len(receiver_pos) != 3):
                return False
            
            # 检查是否为数值
            for pos in [source_pos, receiver_pos]:
                for coord in pos:
                    if not isinstance(coord, (int, float)):
                        return False
                    # 检查是否为有限值
                    if abs(coord) > 1e10:  # 防止过大的坐标值
                        return False
            
            return True
        except Exception as e:
            self.add_debug_info(f"位置验证失败: {e}")
            return False
    
    def validate_parameters(self, fixed_speed: Optional[float], phase: str) -> bool:
        """
        验证计算参数的有效性
        
        参数:
            fixed_speed (float, optional): 固定速度值
            phase (str): 波相
        
        返回:
            bool: 参数是否有效
        """
        try:
            # 验证固定速度
            if fixed_speed is not None:
                if not isinstance(fixed_speed, (int, float)) or fixed_speed <= 0:
                    return False
                # 合理的速度范围检查（1-20 km/s）
                if fixed_speed < 1000 or fixed_speed > 20000:
                    self.add_debug_info(f"警告：速度值 {fixed_speed} m/s 超出常见范围")
            
            # 验证波相
            if not isinstance(phase, str) or phase.upper() not in ["P", "S"]:
                return False
            
            return True
        except Exception as e:
            self.add_debug_info(f"参数验证失败: {e}")
            return False
    
    def safe_calculate_time_delay(self, 
                                source_pos: Tuple[float, float, float], 
                                receiver_pos: Tuple[float, float, float],
                                fixed_speed: Optional[float] = None, 
                                phase: str = "P") -> float:
        """
        安全的时间延迟计算，包含完整的验证和异常处理
        
        参数:
            source_pos (tuple): 震源位置
            receiver_pos (tuple): 检波器位置  
            fixed_speed (float, optional): 固定速度值
            phase (str): 波相
        
        返回:
            float: 传播时间，失败时返回默认值
        """
        try:
            # 验证输入参数
            if not self.validate_positions(source_pos, receiver_pos):
                raise CalculationError("位置参数无效", self.model_name)
            
            if not self.validate_parameters(fixed_speed, phase):
                raise CalculationError("计算参数无效", self.model_name)
            
            # 调用具体实现
            return self.calculate_time_delay(source_pos, receiver_pos, fixed_speed, phase)
        
        except Exception as e:
            self.add_debug_info(f"计算失败: {e}")
            print(f"❌ {self.model_name} 计算时间延迟失败: {e}")
            print(traceback.format_exc())
            
            # 返回备用计算结果
            return self._fallback_calculation(source_pos, receiver_pos, fixed_speed, phase)
    
    def _fallback_calculation(self, 
                            source_pos: Tuple[float, float, float], 
                            receiver_pos: Tuple[float, float, float],
                            fixed_speed: Optional[float] = None, 
                            phase: str = "P") -> float:
        """
        备用计算方法，使用简单的距离/速度公式
        
        参数:
            source_pos (tuple): 震源位置
            receiver_pos (tuple): 检波器位置
            fixed_speed (float, optional): 固定速度值
            phase (str): 波相
        
        返回:
            float: 传播时间
        """
        try:
            # 计算直线距离
            from .utils import calculate_distance_3d, get_default_velocities
            
            distance = calculate_distance_3d(source_pos, receiver_pos)
            
            # 确定速度
            if fixed_speed is not None:
                velocity = fixed_speed
            else:
                defaults = get_default_velocities()
                velocity = defaults['p_velocity'] if phase.upper() == "P" else defaults['s_velocity']
            
            delay = distance / velocity
            self.add_debug_info(f"使用备用计算: 距离={distance:.2f}m, 速度={velocity:.2f}m/s, 延迟={delay:.4f}s")
            return delay
        
        except Exception as e:
            self.add_debug_info(f"备用计算也失败: {e}")
            # 最终回退值
            return 0.01
    
    def __str__(self) -> str:
        """返回模型的字符串表示"""
        status = "已初始化" if self._is_initialized else "未初始化"
        return f"{self.model_name} 速度模型 ({status})"
    
    def __repr__(self) -> str:
        """返回模型的详细表示"""
        return f"{self.__class__.__name__}(model_name='{self.model_name}', initialized={self._is_initialized})" 