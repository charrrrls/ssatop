"""
主速度模型模块

提供统一的速度模型接口，集成简单模型和ObsPy模型，
为上层应用提供一致的API和高级功能。

功能特点：
🔄 自动模型切换
📊 速度剖面绘制
🎯 智能回退机制
📈 性能优化
🛡️ 完善的异常处理

该模块作为速度模型的主要入口点，
根据配置自动选择合适的底层模型实现。

作者: ssatop项目组
创建时间: 2024
"""

import numpy as np
import matplotlib.pyplot as plt
import traceback
from typing import Tuple, Optional, List, Union
from PyQt6.QtCore import QObject

from .base_model import BaseVelocityModel, ModelInitializationError, CalculationError
from .simple_model import SimpleVelocityModel
from .obspy_model import ObsPyVelocityModel
from .utils import setup_matplotlib_fonts, validate_position, format_time


class VelocityModel(QObject):
    """
    主速度模型类
    
    提供统一的速度模型接口，封装ObsPy的TauPy功能和简单速度模型。
    根据模型名称自动选择合适的实现，提供高级功能如速度剖面绘制等。
    
    支持的模型：
    - "simple": 简单恒定速度模型
    - "iasp91", "ak135", "prem"等: ObsPy地球模型
    
    特点：
    - 自动回退机制：ObsPy模型失败时自动使用简单模型
    - 统一接口：不同底层模型使用相同API
    - 完善的调试信息管理
    - 支持可视化功能
    """
    
    def __init__(self, model_name: str = "iasp91"):
        """
        初始化速度模型
        
        参数:
            model_name (str): 模型名称，可选值包括:
                            - "simple": 简单恒定速度模型
                            - "iasp91", "ak135", "prem"等: ObsPy地球模型
        """
        super().__init__()
        self.model_name = model_name
        self.is_simple_model = (model_name.lower() == "simple")
        self.debug_info = []  # 用于存储调试信息
        self._model = None
        
        # 确保matplotlib字体已设置
        setup_matplotlib_fonts()
        
        # 初始化模型
        self._initialize_model()
    
    def _initialize_model(self):
        """
        初始化底层速度模型
        
        根据模型名称选择合适的实现：
        - 简单模型：直接创建SimpleVelocityModel
        - ObsPy模型：尝试创建ObsPyVelocityModel，失败时回退到简单模型
        """
        try:
            if self.is_simple_model:
                # 直接使用简单模型
                self._model = SimpleVelocityModel()
                self.add_debug_info("使用简单恒定速度模型")
            else:
                # 尝试使用ObsPy模型
                try:
                    self._model = ObsPyVelocityModel(self.model_name)
                    self.add_debug_info(f"成功加载ObsPy速度模型: {self.model_name}")
                except Exception as e:
                    # ObsPy模型初始化失败，回退到简单模型
                    error_info = f"加载ObsPy速度模型失败: {e}，回退到简单速度模型"
                    print(f"⚠️ {error_info}")
                    self.add_debug_info(error_info)
                    
                    self._model = SimpleVelocityModel()
                    self.is_simple_model = True
                    self.model_name = "simple"
                    
        except Exception as e:
            # 最终回退
            error_msg = f"初始化速度模型失败: {e}"
            print(f"❌ {error_msg}")
            self.add_debug_info(error_msg)
            print(traceback.format_exc())
            
            # 确保有一个可用的模型
            try:
                self._model = SimpleVelocityModel()
                self.is_simple_model = True
                self.model_name = "simple"
                self.add_debug_info("使用最后回退的简单模型")
            except Exception as final_e:
                self.add_debug_info(f"最终回退也失败: {final_e}")
                raise ModelInitializationError(f"无法初始化任何速度模型: {final_e}")
    
    def add_debug_info(self, info: str):
        """
        添加调试信息
        
        参数:
            info (str): 调试信息字符串
        """
        self.debug_info.append(f"[VelocityModel] {info}")
        if len(self.debug_info) > 100:  # 限制调试信息数量
            self.debug_info = self.debug_info[-100:]
    
    def get_debug_info(self) -> List[str]:
        """
        获取所有调试信息（包括底层模型的调试信息）
        
        返回:
            List[str]: 调试信息列表
        """
        all_debug_info = self.debug_info.copy()
        
        # 添加底层模型的调试信息
        if self._model and hasattr(self._model, 'get_debug_info'):
            model_debug = self._model.get_debug_info()
            all_debug_info.extend(model_debug)
        
        return all_debug_info
    
    def clear_debug_info(self):
        """清空调试信息"""
        self.debug_info.clear()
        if self._model and hasattr(self._model, 'clear_debug_info'):
            self._model.clear_debug_info()
    
    def calculate_time_delay(self, 
                           source_pos: Tuple[float, float, float], 
                           receiver_pos: Tuple[float, float, float],
                           fixed_speed: Optional[float] = None, 
                           phase: str = "P") -> float:
        """
        计算从震源到接收器的时间延迟
        
        参数:
            source_pos (tuple): 震源位置(x, y, z)，单位米
            receiver_pos (tuple): 接收器位置(x, y, z)，单位米
            fixed_speed (float, optional): 固定速度值(m/s)，仅用于简单模型
            phase (str): 波相位，默认为P
        
        返回:
            float: 时间延迟(秒)
            
        异常:
            CalculationError: 计算失败时抛出
        """
        try:
            # 验证输入参数
            if not validate_position(source_pos) or not validate_position(receiver_pos):
                raise CalculationError("位置参数无效")
            
            # 确保有可用的模型
            if self._model is None:
                raise CalculationError("速度模型未初始化")
            
            # 使用底层模型计算
            if hasattr(self._model, 'safe_calculate_time_delay'):
                # 使用安全计算方法（如果可用）
                result = self._model.safe_calculate_time_delay(
                    source_pos, receiver_pos, fixed_speed, phase
                )
            else:
                # 使用标准计算方法
                result = self._model.calculate_time_delay(
                    source_pos, receiver_pos, fixed_speed, phase
                )
            
            self.add_debug_info(
                f"计算时间延迟: 模型={self.model_name}, 结果={result:.4f}s, 波相={phase}"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"计算时间延迟失败: {e}"
            self.add_debug_info(error_msg)
            
            # 尝试使用备用计算
            try:
                return self._fallback_calculation(source_pos, receiver_pos, fixed_speed, phase)
            except Exception as fallback_e:
                self.add_debug_info(f"备用计算也失败: {fallback_e}")
                raise CalculationError(error_msg) from e
    
    def _fallback_calculation(self, 
                            source_pos: Tuple[float, float, float], 
                            receiver_pos: Tuple[float, float, float],
                            fixed_speed: Optional[float] = None, 
                            phase: str = "P") -> float:
        """
        备用计算方法
        
        当主计算方法失败时使用的简单距离/速度计算
        """
        from .utils import calculate_distance_3d, get_default_velocities
        
        distance = calculate_distance_3d(source_pos, receiver_pos)
        
        if fixed_speed is not None:
            velocity = fixed_speed
        else:
            defaults = get_default_velocities()
            velocity = defaults['p_velocity'] if phase.upper() == "P" else defaults['s_velocity']
        
        result = distance / velocity
        self.add_debug_info(f"备用计算: 距离={distance:.2f}m, 速度={velocity:.2f}m/s, 结果={result:.4f}s")
        return result
    
    def get_travel_time(self, 
                       source_depth: float, 
                       receiver_distance: float,
                       phase_list: Optional[List[str]] = None) -> List:
        """
        计算给定震源深度和接收器距离的理论到达时间
        
        参数:
            source_depth (float): 震源深度，单位km
            receiver_distance (float): 接收器与震源的距离，单位度
            phase_list (List[str], optional): 要计算的相位列表，如["P", "S"]
        
        返回:
            List: 到达时间列表
        """
        if self.is_simple_model or not hasattr(self._model, 'get_travel_times'):
            self.add_debug_info("简单模型不支持获取到达时间")
            return []  # 简单模型不支持此功能
        
        try:
            arrivals = self._model.get_travel_times(source_depth, receiver_distance, phase_list)
            self.add_debug_info(
                f"获取到达时间: 深度={source_depth}km, 距离={receiver_distance}度, 找到{len(arrivals)}个到达"
            )
            return arrivals
        except Exception as e:
            self.add_debug_info(f"获取到达时间失败: {e}")
            return []
    
    def get_ray_paths(self, 
                     source_depth: float, 
                     receiver_distance: float,
                     phase_list: Optional[List[str]] = None) -> List:
        """
        计算给定震源深度和接收器距离的射线路径
        
        参数:
            source_depth (float): 震源深度，单位km
            receiver_distance (float): 接收器与震源的距离，单位度
            phase_list (List[str], optional): 要计算的相位列表，如["P", "S"]
        
        返回:
            List: 射线路径列表
        """
        if self.is_simple_model or not hasattr(self._model, 'get_ray_paths'):
            self.add_debug_info("简单模型不支持获取射线路径")
            return []  # 简单模型不支持此功能
        
        try:
            paths = self._model.get_ray_paths(source_depth, receiver_distance, phase_list)
            self.add_debug_info(
                f"获取射线路径: 深度={source_depth}km, 距离={receiver_distance}度, 找到{len(paths)}条路径"
            )
            return paths
        except Exception as e:
            self.add_debug_info(f"获取射线路径失败: {e}")
            return []
    
    def plot_velocity_profile(self, max_depth: float = 700) -> Optional[plt.Figure]:
        """
        绘制速度模型的速度-深度剖面图
        
        参数:
            max_depth (float): 最大深度(km)，默认700km
        
        返回:
            matplotlib.pyplot.Figure: 图表对象，失败时返回None
        """
        try:
            if self.is_simple_model:
                # 简单模型绘制恒定速度
                return self._plot_simple_velocity_profile(max_depth)
            else:
                # ObsPy模型绘制实际速度剖面
                return self._plot_obspy_velocity_profile(max_depth)
                
        except Exception as e:
            self.add_debug_info(f"绘制速度剖面图失败: {e}")
            print(f"❌ 绘制速度剖面图失败: {e}")
            print(traceback.format_exc())
            return None
    
    def _plot_simple_velocity_profile(self, max_depth: float) -> plt.Figure:
        """绘制简单模型的速度剖面"""
        depths = np.linspace(0, max_depth, 100)
        
        if hasattr(self._model, 'get_velocities'):
            velocities = self._model.get_velocities()
            p_vel = velocities['p_velocity'] / 1000  # 转换为km/s
            s_vel = velocities['s_velocity'] / 1000
        else:
            p_vel = 5.5  # 默认值
            s_vel = 3.2
        
        p_velocities = np.ones_like(depths) * p_vel
        s_velocities = np.ones_like(depths) * s_vel
        
        return self._create_velocity_plot(depths, p_velocities, s_velocities, max_depth)
    
    def _plot_obspy_velocity_profile(self, max_depth: float) -> plt.Figure:
        """绘制ObsPy模型的速度剖面"""
        try:
            # 尝试从ObsPy模型获取数据
            if hasattr(self._model, '_obspy_model') and self._model._obspy_model:
                model_data = self._model._obspy_model.model
                depths = []
                p_velocities = []
                s_velocities = []
                
                # 提取模型数据
                for layer in model_data.s_mod.v_mod.layers:
                    if layer.depth <= max_depth:
                        depths.append(layer.depth)
                        p_velocities.append(layer.v_p)
                        s_velocities.append(layer.v_s)
                
                if depths:
                    return self._create_velocity_plot(depths, p_velocities, s_velocities, max_depth)
            
            # 如果无法获取ObsPy数据，回退到简单模型绘制
            self.add_debug_info("无法获取ObsPy模型数据，使用简单模型绘制")
            return self._plot_simple_velocity_profile(max_depth)
            
        except Exception as e:
            self.add_debug_info(f"获取ObsPy模型数据失败: {e}")
            return self._plot_simple_velocity_profile(max_depth)
    
    def _create_velocity_plot(self, depths: List[float], 
                            p_velocities: List[float], 
                            s_velocities: List[float],
                            max_depth: float) -> plt.Figure:
        """创建速度剖面图"""
        fig, ax = plt.subplots(figsize=(8, 10))
        
        ax.plot(p_velocities, depths, 'r-', linewidth=2, label='P波速度')
        ax.plot(s_velocities, depths, 'b-', linewidth=2, label='S波速度')
        
        # 设置轴标签和标题
        ax.set_xlabel('速度 (km/s)', fontsize=12)
        ax.set_ylabel('深度 (km)', fontsize=12)
        ax.set_title(f'速度模型: {self.model_name}', fontsize=14, fontweight='bold')
        
        # 反转Y轴使深度向下增加
        ax.invert_yaxis()
        
        # 设置网格和图例
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)
        
        # 美化图表
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.tight_layout()
        
        self.add_debug_info(f"成功绘制速度剖面图，深度范围: 0-{max_depth}km")
        return fig
    
    def get_model_info(self) -> dict:
        """
        获取模型详细信息
        
        返回:
            dict: 包含模型信息的字典
        """
        info = {
            'model_name': self.model_name,
            'is_simple_model': self.is_simple_model,
            'is_initialized': self._model is not None,
        }
        
        # 添加底层模型的信息
        if self._model:
            if hasattr(self._model, 'get_model_info'):
                info.update(self._model.get_model_info())
            elif hasattr(self._model, 'get_velocities'):
                info['velocities'] = self._model.get_velocities()
        
        return info
    
    def validate_model(self) -> bool:
        """
        验证模型是否可用
        
        返回:
            bool: 模型是否可用
        """
        try:
            if self._model is None:
                return False
            
            # 使用底层模型的验证方法
            if hasattr(self._model, 'validate_model'):
                return self._model.validate_model()
            
            # 执行简单的测试计算
            test_result = self.calculate_time_delay(
                source_pos=(0, 0, 1000),
                receiver_pos=(1000, 0, 0),
                phase="P"
            )
            
            return isinstance(test_result, (int, float)) and test_result > 0
            
        except Exception as e:
            self.add_debug_info(f"模型验证失败: {e}")
            return False
    
    def get_performance_stats(self) -> dict:
        """
        获取性能统计信息
        
        返回:
            dict: 性能统计数据
        """
        return {
            'model_type': 'simple' if self.is_simple_model else 'obspy',
            'model_name': self.model_name,
            'debug_info_count': len(self.debug_info),
            'is_initialized': self._model is not None,
        }
    
    def __str__(self) -> str:
        """返回模型的字符串表示"""
        status = "可用" if self._model is not None else "不可用"
        model_type = "简单模型" if self.is_simple_model else "ObsPy模型"
        return f"{model_type}: {self.model_name} ({status})"
    
    def __repr__(self) -> str:
        """返回模型的详细表示"""
        return f"VelocityModel(model_name='{self.model_name}', is_simple={self.is_simple_model})"


if __name__ == "__main__":
    # 测试代码
    print("🧪 测试VelocityModel...")
    
    # 测试简单模型
    print("\n📋 测试简单模型:")
    simple_model = VelocityModel("simple")
    print(f"  {simple_model}")
    
    # 测试计算
    source = (0, 0, 10000)      # 震源：10km深
    receiver = (50000, 0, 0)    # 检波器：50km远
    
    delay = simple_model.calculate_time_delay(source, receiver, phase="P")
    print(f"  P波传播时间: {format_time(delay)}")
    
    # 测试绘图
    fig = simple_model.plot_velocity_profile(100)
    if fig:
        print("  ✅ 速度剖面图绘制成功")
        plt.close(fig)  # 关闭图表以节省内存
    
    # 测试ObsPy模型（如果可用）
    print("\n📋 测试ObsPy模型:")
    try:
        obspy_model = VelocityModel("iasp91")
        print(f"  {obspy_model}")
        
        delay = obspy_model.calculate_time_delay(source, receiver, phase="P")
        print(f"  P波传播时间: {format_time(delay)}")
        
        # 测试到达时间
        arrivals = obspy_model.get_travel_time(10, 0.45, ["P"])
        if arrivals:
            print(f"  到达时间: {arrivals[0].time:.3f}s")
        
    except Exception as e:
        print(f"  ⚠️ ObsPy模型测试失败: {e}")
    
    print("\n✅ 测试完成!") 