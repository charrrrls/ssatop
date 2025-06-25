"""
速度模型管理器模块

提供单例模式的模型管理器，用于管理和选择不同的速度模型。
支持多种模型的动态加载、验证和切换。

功能特点：
🔧 单例模式设计
🌍 多模型管理
🔄 动态切换
✅ 模型验证
📊 性能监控
🛡️ 异常处理

支持的模型包括简单恒定速度模型和各种ObsPy地球模型。
提供统一的接口供上层应用使用。

作者: ssatop项目组
创建时间: 2024
"""

import traceback
import os
from typing import Dict, List, Optional, Any
from PyQt6.QtCore import QObject

from .simple_model import SimpleVelocityModel
from .obspy_model import ObsPyVelocityModel
from .velocity_model import VelocityModel
from .base_model import ModelInitializationError, CalculationError


class ModelManager(QObject):
    """
    速度模型管理器
    
    使用单例模式管理多个速度模型实例，提供模型切换、验证和性能监控功能。
    
    功能：
    - 管理多种速度模型
    - 提供模型切换接口
    - 验证模型可用性
    - 缓存模型实例
    - 性能统计
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化模型管理器
        
        注意：由于单例模式，初始化只会执行一次
        """
        if ModelManager._initialized:
            return
            
        super().__init__()
        ModelManager._initialized = True
        
        # 初始化成员变量
        self._models: Dict[str, VelocityModel] = {}
        self._current_model_name: Optional[str] = None
        self._model_descriptions = self._init_model_descriptions()
        self._initialization_errors: Dict[str, str] = {}
        
        # 初始化模型
        self._initialize_models()
        
        # 设置默认模型
        self._set_default_model()
    
    def _init_model_descriptions(self) -> Dict[str, str]:
        """
        初始化模型描述信息
        
        返回:
            Dict[str, str]: 模型名称到描述的映射
        """
        return {
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
    
    def _check_obspy_availability(self) -> bool:
        """
        检查ObsPy是否可用
        
        返回:
            bool: ObsPy是否可用
        """
        try:
            import obspy
            from obspy.taup import TauPyModel
            return True
        except ImportError:
            return False
    
    def _check_model_file_exists(self, model_name: str) -> bool:
        """
        检查ObsPy模型文件是否存在
        
        参数:
            model_name (str): 模型名称
        
        返回:
            bool: 模型文件是否存在
        """
        try:
            if not self._check_obspy_availability():
                return False
            
            import obspy
            model_path = os.path.join(
                os.path.dirname(obspy.__file__), 
                "taup", "data", f"{model_name}.npz"
            )
            exists = os.path.exists(model_path)
            print(f"🔍 模型 {model_name} 文件{'存在' if exists else '不存在'}")
            return exists
        except Exception as e:
            print(f"❌ 检查模型文件时出错: {e}")
            return False
    
    def _initialize_models(self):
        """
        初始化所有可用的速度模型
        """
        print("🚀 开始初始化速度模型...")
        
        # 1. 初始化简单模型（总是可用）
        try:
            self._models["simple"] = VelocityModel("simple")
            print("✅ 简单模型初始化成功")
        except Exception as e:
            error_msg = f"简单模型初始化失败: {e}"
            print(f"❌ {error_msg}")
            self._initialization_errors["simple"] = error_msg
        
        # 2. 尝试初始化ObsPy模型
        if self._check_obspy_availability():
            print("🌍 检测到ObsPy，开始初始化地球模型...")
            
            # 标准模型列表
            standard_models = ["iasp91", "ak135", "prem"]
            # 附加模型列表
            additional_models = ["jb", "sp6", "1066a", "ak135f", "herrin"]
            
            all_models = standard_models + additional_models
            
            for model_name in all_models:
                try:
                    # 检查模型文件是否存在
                    if self._check_model_file_exists(model_name):
                        # 尝试创建模型实例
                        model = VelocityModel(model_name)
                        
                        # 验证模型是否可用
                        if model.validate_model():
                            self._models[model_name] = model
                            print(f"✅ ObsPy模型 {model_name} 初始化成功")
                        else:
                            error_msg = f"模型 {model_name} 验证失败"
                            print(f"❌ {error_msg}")
                            self._initialization_errors[model_name] = error_msg
                    else:
                        error_msg = f"模型文件不存在"
                        print(f"⚠️ ObsPy模型 {model_name}: {error_msg}")
                        self._initialization_errors[model_name] = error_msg
                        
                except Exception as e:
                    error_msg = f"初始化失败: {e}"
                    print(f"❌ ObsPy模型 {model_name}: {error_msg}")
                    self._initialization_errors[model_name] = error_msg
            
            # 统计ObsPy模型加载结果
            obspy_count = len([name for name in self._models if name != "simple"])
            if obspy_count > 0:
                print(f"🎉 成功加载了 {obspy_count} 个ObsPy模型")
            else:
                print("⚠️ 未能成功加载任何ObsPy模型")
        else:
            print("⚠️ ObsPy未安装或不可用，将只使用简单模型")
        
        print(f"📊 模型初始化完成，共加载 {len(self._models)} 个模型")
    
    def _set_default_model(self):
        """设置默认使用的模型"""
        try:
            # 优先级：iasp91 > ak135 > prem > simple
            preferred_order = ["iasp91", "ak135", "prem", "simple"]
            
            for model_name in preferred_order:
                if model_name in self._models:
                    self._current_model_name = model_name
                    print(f"🎯 设置默认模型: {model_name}")
                    return
            
            # 如果没有找到，使用第一个可用的模型
            if self._models:
                self._current_model_name = list(self._models.keys())[0]
                print(f"🎯 使用第一个可用模型: {self._current_model_name}")
            else:
                print("❌ 没有可用的模型")
                
        except Exception as e:
            print(f"❌ 设置默认模型失败: {e}")
    
    def get_model(self, model_name: str) -> Optional[VelocityModel]:
        """
        获取指定名称的速度模型
        
        参数:
            model_name (str): 模型名称
        
        返回:
            Optional[VelocityModel]: 模型实例，不存在时返回None
        """
        return self._models.get(model_name)
    
    def get_current_model(self) -> Optional[VelocityModel]:
        """
        获取当前使用的速度模型
        
        返回:
            Optional[VelocityModel]: 当前模型实例
        """
        if self._current_model_name and self._current_model_name in self._models:
            return self._models[self._current_model_name]
        return None
    
    def set_current_model(self, model_name: str) -> bool:
        """
        设置当前使用的速度模型
        
        参数:
            model_name (str): 模型名称
        
        返回:
            bool: 设置是否成功
        """
        try:
            if model_name not in self._models:
                print(f"❌ 模型 '{model_name}' 不存在")
                return False
            
            # 验证模型是否可用
            model = self._models[model_name]
            if not model.validate_model():
                print(f"❌ 模型 '{model_name}' 验证失败")
                return False
            
            # 设置为当前模型
            old_model = self._current_model_name
            self._current_model_name = model_name
            print(f"🔄 模型切换: {old_model} → {model_name}")
            return True
            
        except Exception as e:
            print(f"❌ 设置当前模型失败: {e}")
            print(traceback.format_exc())
            return False
    
    def get_available_models(self) -> List[str]:
        """
        获取所有可用的速度模型列表
        
        返回:
            List[str]: 可用模型名称列表
        """
        return list(self._models.keys())
    
    def get_model_description(self, model_name: str) -> str:
        """
        获取模型描述信息
        
        参数:
            model_name (str): 模型名称
        
        返回:
            str: 模型描述
        """
        return self._model_descriptions.get(model_name, f"未知模型: {model_name}")
    
    def get_initialization_errors(self) -> Dict[str, str]:
        """
        获取模型初始化错误信息
        
        返回:
            Dict[str, str]: 模型名称到错误信息的映射
        """
        return self._initialization_errors.copy()
    
    def validate_all_models(self) -> Dict[str, Dict[str, Any]]:
        """
        验证所有模型是否可用
        
        返回:
            Dict[str, Dict[str, Any]]: 模型验证结果
        """
        results = {}
        
        for model_name, model in self._models.items():
            try:
                # 执行验证测试
                is_valid = model.validate_model()
                
                if is_valid:
                    # 执行性能测试
                    test_result = model.calculate_time_delay(
                        source_pos=(0, 0, 1000),
                        receiver_pos=(1000, 0, 0),
                        phase="P"
                    )
                    
                    results[model_name] = {
                        "status": "可用",
                        "test_result": test_result,
                        "description": self.get_model_description(model_name),
                        "model_info": model.get_model_info()
                    }
                else:
                    results[model_name] = {
                        "status": "验证失败",
                        "description": self.get_model_description(model_name)
                    }
                    
            except Exception as e:
                results[model_name] = {
                    "status": "不可用",
                    "error": str(e),
                    "description": self.get_model_description(model_name)
                }
        
        return results
    
    def calculate_time_delay(self, 
                           source_pos, receiver_pos, 
                           fixed_speed=None, phase="P") -> float:
        """
        使用当前模型计算时间延迟（代理方法）
        
        参数:
            source_pos: 震源位置(x, y, z)
            receiver_pos: 接收器位置(x, y, z)
            fixed_speed: 固定速度值
            phase: 波相位
        
        返回:
            float: 时间延迟(秒)
        """
        try:
            current_model = self.get_current_model()
            if current_model:
                return current_model.calculate_time_delay(
                    source_pos, receiver_pos, fixed_speed, phase
                )
            else:
                # 没有当前模型，尝试使用任何可用模型
                if self._models:
                    backup_model = list(self._models.values())[0]
                    print(f"⚠️ 使用备用模型: {backup_model.model_name}")
                    return backup_model.calculate_time_delay(
                        source_pos, receiver_pos, fixed_speed, phase
                    )
                else:
                    # 最终回退计算
                    from .utils import calculate_distance_3d
                    distance = calculate_distance_3d(source_pos, receiver_pos)
                    return distance / (fixed_speed or 5500.0)  # 默认P波速度
                    
        except Exception as e:
            print(f"❌ 计算时间延迟失败: {e}")
            print(traceback.format_exc())
            
            # 错误时使用最简单的计算
            try:
                from .utils import calculate_distance_3d
                distance = calculate_distance_3d(source_pos, receiver_pos)
                return distance / (fixed_speed or 5500.0)
            except:
                # 最终保底
                return 0.01
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        返回:
            Dict[str, Any]: 性能统计数据
        """
        return {
            "total_models": len(self._models),
            "current_model": self._current_model_name,
            "available_models": list(self._models.keys()),
            "initialization_errors": len(self._initialization_errors),
            "obspy_available": self._check_obspy_availability(),
        }
    
    def reload_model(self, model_name: str) -> bool:
        """
        重新加载指定模型
        
        参数:
            model_name (str): 要重新加载的模型名称
        
        返回:
            bool: 重新加载是否成功
        """
        try:
            print(f"🔄 重新加载模型: {model_name}")
            
            # 移除旧模型实例
            if model_name in self._models:
                del self._models[model_name]
            
            # 清除错误记录
            if model_name in self._initialization_errors:
                del self._initialization_errors[model_name]
            
            # 重新创建模型
            if model_name == "simple":
                self._models[model_name] = VelocityModel("simple")
            else:
                if self._check_model_file_exists(model_name):
                    model = VelocityModel(model_name)
                    if model.validate_model():
                        self._models[model_name] = model
                    else:
                        raise ValueError("模型验证失败")
                else:
                    raise FileNotFoundError("模型文件不存在")
            
            print(f"✅ 模型 {model_name} 重新加载成功")
            return True
            
        except Exception as e:
            error_msg = f"重新加载模型失败: {e}"
            print(f"❌ {error_msg}")
            self._initialization_errors[model_name] = error_msg
            return False
    
    def __str__(self) -> str:
        """返回管理器的字符串表示"""
        current = self._current_model_name or "无"
        return (f"ModelManager(当前模型: {current}, "
                f"可用模型: {len(self._models)}, "
                f"错误: {len(self._initialization_errors)})")
    
    def __repr__(self) -> str:
        """返回管理器的详细表示"""
        return (f"ModelManager(current='{self._current_model_name}', "
                f"models={list(self._models.keys())}, "
                f"errors={list(self._initialization_errors.keys())})")


if __name__ == "__main__":
    # 测试代码
    print("🧪 测试ModelManager...")
    
    # 创建管理器实例（单例）
    manager = ModelManager()
    print(f"📋 管理器信息: {manager}")
    
    # 获取可用模型
    available_models = manager.get_available_models()
    print(f"🌍 可用模型: {available_models}")
    
    # 显示模型描述
    print("\n📖 模型描述:")
    for model_name in available_models[:3]:  # 只显示前3个
        description = manager.get_model_description(model_name)
        print(f"  {model_name}: {description[:50]}...")
    
    # 测试模型切换
    if "iasp91" in available_models:
        success = manager.set_current_model("iasp91")
        print(f"🔄 切换到iasp91: {'成功' if success else '失败'}")
    
    # 测试计算
    current_model = manager.get_current_model()
    if current_model:
        print(f"📊 当前模型: {current_model.model_name}")
        
        source = (0, 0, 10000)      # 震源：10km深
        receiver = (50000, 0, 0)    # 检波器：50km远
        
        delay = manager.calculate_time_delay(source, receiver, phase="P")
        print(f"⏱️ P波传播时间: {delay:.3f} 秒")
    
    # 验证所有模型
    print("\n🔍 验证所有模型:")
    validation_results = manager.validate_all_models()
    for model_name, result in validation_results.items():
        status = result.get("status", "未知")
        print(f"  {model_name}: {status}")
    
    # 显示性能统计
    stats = manager.get_performance_stats()
    print(f"\n📈 性能统计: {stats}")
    
    # 测试单例模式
    manager2 = ModelManager()
    print(f"\n🔗 单例测试: {manager is manager2}")
    
    print("✅ 测试完成!") 