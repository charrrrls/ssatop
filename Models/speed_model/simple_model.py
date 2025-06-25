"""
简单恒定速度模型模块

提供基于恒定速度的简单地震波传播时间计算，
适用于局部小尺度的地震研究和快速近似计算。

特点：
🚀 计算速度快
🔧 配置简单
📏 使用恒定P波和S波速度
🎯 适合局部研究

该模型假设地震波在均匀介质中以恒定速度传播，
不考虑地球内部结构的复杂性，使用直线距离和固定速度计算传播时间。

作者: ssatop项目组
创建时间: 2025
"""

import math
from typing import Tuple, Optional
from .base_model import BaseVelocityModel, CalculationError
from .utils import calculate_distance_3d, get_default_velocities


class SimpleVelocityModel(BaseVelocityModel):
    """
    简单恒定速度模型
    
    使用固定的P波和S波速度进行地震波传播时间计算。
    计算公式: 时间 = 直线距离 / 波速
    
    适用场景:
    - 局部小尺度地震研究
    - 快速近似计算
    - 初步结果估算
    - 其他模型的备用方案
    """
    
    def __init__(self, p_velocity: float = None, s_velocity: float = None):
        """
        初始化简单速度模型
        
        参数:
            p_velocity (float, optional): P波速度 (m/s)，默认5500 m/s
            s_velocity (float, optional): S波速度 (m/s)，默认3200 m/s
        """
        super().__init__("simple")
        
        # 获取默认速度配置
        defaults = get_default_velocities()
        
        # 设置P波和S波速度
        self.p_velocity = p_velocity if p_velocity is not None else defaults['p_velocity']
        self.s_velocity = s_velocity if s_velocity is not None else defaults['s_velocity']
        
        # 验证速度参数
        self._validate_velocities()
        
        # 标记为已初始化
        self._is_initialized = True
        self.add_debug_info(f"简单模型初始化: P波={self.p_velocity}m/s, S波={self.s_velocity}m/s")
    
    def _validate_velocities(self):
        """
        验证速度参数的合理性
        
        异常:
            ValueError: 速度参数不合理时抛出
        """
        # 检查速度是否为正数
        if self.p_velocity <= 0 or self.s_velocity <= 0:
            raise ValueError("波速必须为正数")
        
        # 检查P波速度是否大于S波速度
        if self.p_velocity <= self.s_velocity:
            self.add_debug_info("警告：P波速度应该大于S波速度")
        
        # 检查速度是否在合理范围内（1-20 km/s）
        if not (1000 <= self.p_velocity <= 20000):
            self.add_debug_info(f"警告：P波速度 {self.p_velocity} m/s 超出常见范围(1-20 km/s)")
        
        if not (500 <= self.s_velocity <= 15000):
            self.add_debug_info(f"警告：S波速度 {self.s_velocity} m/s 超出常见范围(0.5-15 km/s)")
    
    def calculate_time_delay(self, 
                           source_pos: Tuple[float, float, float], 
                           receiver_pos: Tuple[float, float, float],
                           fixed_speed: Optional[float] = None, 
                           phase: str = "P") -> float:
        """
        计算从震源到检波器的传播时间
        
        使用公式: 时间 = 直线距离 / 波速
        
        参数:
            source_pos (tuple): (x, y, z) 震源位置，单位米
            receiver_pos (tuple): (x, y, z) 检波器位置，单位米
            fixed_speed (float, optional): 固定速度值(m/s)，如果提供则使用此值
            phase (str): 波相（"P" 或 "S"），默认为P波
        
        返回:
            float: 传播时间，单位秒
            
        异常:
            CalculationError: 计算失败时抛出
        """
        try:
            # 计算直线距离
            distance = calculate_distance_3d(source_pos, receiver_pos)
            
            # 确定使用的速度
            if fixed_speed is not None:
                # 使用指定的固定速度
                velocity = fixed_speed
                speed_source = "固定速度"
            else:
                # 根据波相选择速度
                phase_upper = phase.upper()
                if phase_upper == "P":
                    velocity = self.p_velocity
                    speed_source = "P波速度"
                elif phase_upper == "S":
                    velocity = self.s_velocity
                    speed_source = "S波速度"
                else:
                    # 未知波相，默认使用P波速度
                    velocity = self.p_velocity
                    speed_source = "P波速度(默认)"
                    self.add_debug_info(f"未知波相'{phase}'，使用P波速度")
            
            # 计算传播时间
            if velocity <= 0:
                raise CalculationError(f"速度值无效: {velocity}", self.model_name)
            
            travel_time = distance / velocity
            
            # 记录计算信息
            self.add_debug_info(
                f"计算完成: 距离={distance:.2f}m, {speed_source}={velocity:.2f}m/s, "
                f"波相={phase}, 时间={travel_time:.4f}s"
            )
            
            return travel_time
            
        except Exception as e:
            error_msg = f"简单模型计算失败: {e}"
            self.add_debug_info(error_msg)
            raise CalculationError(error_msg, self.model_name) from e
    
    def set_p_velocity(self, velocity: float):
        """
        设置P波速度
        
        参数:
            velocity (float): P波速度 (m/s)
            
        异常:
            ValueError: 速度值无效时抛出
        """
        if velocity <= 0:
            raise ValueError("P波速度必须为正数")
        
        old_velocity = self.p_velocity
        self.p_velocity = velocity
        self.add_debug_info(f"P波速度从 {old_velocity} m/s 更改为 {velocity} m/s")
        
        # 重新验证速度
        self._validate_velocities()
    
    def set_s_velocity(self, velocity: float):
        """
        设置S波速度
        
        参数:
            velocity (float): S波速度 (m/s)
            
        异常:
            ValueError: 速度值无效时抛出
        """
        if velocity <= 0:
            raise ValueError("S波速度必须为正数")
        
        old_velocity = self.s_velocity
        self.s_velocity = velocity
        self.add_debug_info(f"S波速度从 {old_velocity} m/s 更改为 {velocity} m/s")
        
        # 重新验证速度
        self._validate_velocities()
    
    def get_velocities(self) -> dict:
        """
        获取当前的波速配置
        
        返回:
            dict: 包含P波和S波速度的字典
        """
        return {
            'p_velocity': self.p_velocity,
            's_velocity': self.s_velocity,
            'vp_vs_ratio': self.p_velocity / self.s_velocity if self.s_velocity > 0 else 0
        }
    
    def set_velocities_from_vp_vs_ratio(self, p_velocity: float, vp_vs_ratio: float = 1.7):
        """
        根据P波速度和Vp/Vs比值设置速度
        
        参数:
            p_velocity (float): P波速度 (m/s)
            vp_vs_ratio (float): Vp/Vs比值，默认1.7
            
        异常:
            ValueError: 参数无效时抛出
        """
        if p_velocity <= 0:
            raise ValueError("P波速度必须为正数")
        
        if vp_vs_ratio <= 1.0:
            raise ValueError("Vp/Vs比值必须大于1.0")
        
        s_velocity = p_velocity / vp_vs_ratio
        
        old_p = self.p_velocity
        old_s = self.s_velocity
        
        self.p_velocity = p_velocity
        self.s_velocity = s_velocity
        
        self.add_debug_info(
            f"根据Vp/Vs比值({vp_vs_ratio:.2f})设置速度: "
            f"P波 {old_p}→{p_velocity} m/s, S波 {old_s}→{s_velocity:.1f} m/s"
        )
        
        # 重新验证速度
        self._validate_velocities()
    
    def estimate_distance_from_time(self, travel_time: float, phase: str = "P") -> float:
        """
        根据传播时间估算距离（反向计算）
        
        参数:
            travel_time (float): 传播时间 (秒)
            phase (str): 波相（"P" 或 "S"）
        
        返回:
            float: 估算的距离 (米)
            
        异常:
            ValueError: 参数无效时抛出
        """
        if travel_time <= 0:
            raise ValueError("传播时间必须为正数")
        
        # 根据波相选择速度
        if phase.upper() == "P":
            velocity = self.p_velocity
        elif phase.upper() == "S":
            velocity = self.s_velocity
        else:
            raise ValueError(f"未知波相: {phase}")
        
        distance = travel_time * velocity
        self.add_debug_info(f"反向计算: 时间={travel_time:.4f}s, 波相={phase}, 距离={distance:.2f}m")
        
        return distance
    
    def __str__(self) -> str:
        """返回模型的字符串表示"""
        return (f"简单速度模型 (P={self.p_velocity:.0f}m/s, "
                f"S={self.s_velocity:.0f}m/s, "
                f"Vp/Vs={self.p_velocity/self.s_velocity:.2f})")


if __name__ == "__main__":
    # 简单测试代码
    print("🧪 测试简单速度模型...")
    
    # 创建模型实例
    model = SimpleVelocityModel()
    print(f"📋 模型信息: {model}")
    
    # 测试时间延迟计算
    source = (0, 0, 10000)      # 震源：(0, 0, 10km深)
    receiver = (50000, 0, 0)    # 检波器：(50km, 0, 地表)
    
    # P波计算
    p_delay = model.calculate_time_delay(source, receiver, phase="P")
    print(f"⏱️ P波传播时间: {p_delay:.3f} 秒")
    
    # S波计算
    s_delay = model.calculate_time_delay(source, receiver, phase="S")
    print(f"⏱️ S波传播时间: {s_delay:.3f} 秒")
    
    # 使用固定速度
    fixed_delay = model.calculate_time_delay(source, receiver, fixed_speed=6000, phase="P")
    print(f"⏱️ 固定速度(6000m/s)传播时间: {fixed_delay:.3f} 秒")
    
    # 反向计算距离
    estimated_distance = model.estimate_distance_from_time(p_delay, "P")
    print(f"📏 根据P波时间估算距离: {estimated_distance:.0f} 米")
    
    # 显示调试信息
    print("\n🔍 调试信息:")
    for info in model.get_debug_info():
        print(f"  {info}")
    
    print("✅ 测试完成!") 