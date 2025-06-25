"""
速度模型工具函数模块

提供以下功能：
🔧 matplotlib中文字体配置
📐 坐标转换工具函数
🔢 数值验证和处理函数

该模块包含支持速度模型计算的各种工具函数，
主要用于解决跨平台字体显示问题和提供通用的计算辅助函数。

作者: ssatop项目组
创建时间: 2025
"""

import matplotlib
import platform
import numpy as np
import math
import sys


def setup_matplotlib_fonts():
    """
    设置matplotlib中文字体支持
    
    根据不同操作系统自动选择合适的中文字体，
    解决matplotlib中文显示乱码问题。
    
    支持的操作系统：
    - macOS: 使用Arial Unicode MS、STHeiti等
    - Windows: 使用Microsoft YaHei、SimHei等  
    - Linux: 使用DejaVu Sans
    
    返回:
        str: 成功设置的字体名称，失败时返回None
    """
    system = platform.system()
    
    # 根据系统选择合适的字体
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
            print(f"🎨 成功设置字体: {font}")
            
            # 解决负号显示问题
            matplotlib.rcParams['axes.unicode_minus'] = False
            return font
        except Exception as e:
            print(f"⚠️ 字体 {font} 设置失败: {e}")
            continue
    
    print("❌ 无法设置任何中文字体，可能影响中文显示")
    return None


def cartesian_to_spherical(source_pos, receiver_pos):
    """
    将笛卡尔坐标转换为球坐标（距离和深度）
    
    参数:
        source_pos (tuple): (x, y, z) 震源位置，z为深度(m)
        receiver_pos (tuple): (x, y, z) 检波器位置，z为深度(m)
    
    返回:
        tuple: (distance_in_degree, source_depth_in_km)
               - distance_in_degree: 水平距离（度）
               - source_depth_in_km: 震源深度（km）
    
    异常处理:
        如果计算失败，返回默认值(0.1, 10)
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
        print(f"❌ 坐标转换失败: {e}")
        # 返回安全值
        return 0.1, 10  # 默认0.1度距离，10km深度


def calculate_distance_3d(pos1, pos2):
    """
    计算两点间的三维直线距离
    
    参数:
        pos1 (tuple): (x, y, z) 第一个点的坐标
        pos2 (tuple): (x, y, z) 第二个点的坐标
    
    返回:
        float: 两点间距离（米）
    
    异常处理:
        计算失败时返回1000.0米作为默认值
    """
    try:
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1] 
        dz = pos1[2] - pos2[2]
        return math.sqrt(dx**2 + dy**2 + dz**2)
    except Exception as e:
        print(f"❌ 距离计算失败: {e}，使用默认距离1000m")
        return 1000.0


def validate_position(position):
    """
    验证位置坐标的有效性
    
    参数:
        position (tuple): (x, y, z) 位置坐标
    
    返回:
        bool: 坐标是否有效
    
    检查项目:
        - 是否为3元组
        - 是否为数值类型
        - 是否为有限值（非NaN、非无穷大）
    """
    try:
        if not isinstance(position, (tuple, list)) or len(position) != 3:
            return False
        
        for coord in position:
            if not isinstance(coord, (int, float, np.number)):
                return False
            if np.isnan(coord) or np.isinf(coord):
                return False
        
        return True
    except:
        return False


def safe_divide(numerator, denominator, default=0.0):
    """
    安全除法，避免除零错误
    
    参数:
        numerator (float): 分子
        denominator (float): 分母
        default (float): 分母为零时的默认返回值
    
    返回:
        float: 除法结果或默认值
    """
    try:
        if abs(denominator) < 1e-10:  # 避免除零
            return default
        return numerator / denominator
    except:
        return default


def format_time(seconds):
    """
    格式化时间显示
    
    参数:
        seconds (float): 时间（秒）
    
    返回:
        str: 格式化的时间字符串
    """
    try:
        if seconds < 1:
            return f"{seconds*1000:.1f}ms"
        elif seconds < 60:
            return f"{seconds:.3f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m{secs:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}h{minutes}m{secs:.1f}s"
    except:
        return f"{seconds}s"


def get_default_velocities():
    """
    获取默认的地震波速度值
    
    返回:
        dict: 包含默认P波和S波速度的字典
    """
    return {
        'p_velocity': 5500.0,  # P波速度 (m/s)
        's_velocity': 3200.0,  # S波速度 (m/s)  
        'vp_vs_ratio': 1.7     # P/S波速度比
    }


# 自动设置字体
setup_matplotlib_fonts() 