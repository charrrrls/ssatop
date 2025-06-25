"""
速度模型模块 - 提供地震波速度模型和传播时间计算功能

该模块包含以下子模块：
- simple_model: 简单恒定速度模型
- obspy_model: ObsPy地球模型封装
- velocity_model: 主速度模型类
- model_manager: 模型管理器（单例模式）
- utils: 工具函数和配置

主要用途：
🌍 提供多种地震波速度模型
⏱️ 计算地震波传播时间
📊 绘制速度剖面图
🔧 模型管理和切换

作者: ssatop项目组
版本: 1.0
"""

from .simple_model import SimpleVelocityModel
from .obspy_model import ObsPyVelocityModel
from .velocity_model import VelocityModel
from .model_manager import ModelManager
from .utils import setup_matplotlib_fonts

__all__ = [
    'SimpleVelocityModel',
    'ObsPyVelocityModel', 
    'VelocityModel',
    'ModelManager',
    'setup_matplotlib_fonts'
]

__version__ = '1.0.0'
__author__ = 'ssatop项目组' 