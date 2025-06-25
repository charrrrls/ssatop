# 速度模型模块 (Speed Model Module)

## 📋 概述

这是ssatop项目的速度模型模块，提供地震波速度模型和传播时间计算功能。该模块已从原来的单文件结构重构为模块化架构，提供更好的代码组织和功能扩展性。

## 🏗️ 模块结构

```
Models/speed_model/
├── __init__.py              # 包初始化文件，导出主要类
├── README.md               # 本说明文档
├── base_model.py           # 抽象基类和异常定义
├── simple_model.py         # 简单恒定速度模型
├── obspy_model.py          # ObsPy地球模型封装
├── velocity_model.py       # 主速度模型类
├── model_manager.py        # 模型管理器（单例模式）
└── utils.py               # 工具函数和通用计算
```

## 🎯 主要功能

### 1. 多种速度模型支持
- **简单模型**: 恒定P波/S波速度，适合局部研究
- **ObsPy模型**: 专业地震学模型（iasp91、ak135、prem等）

### 2. 统一接口
- 所有模型实现相同的接口
- 自动回退机制：ObsPy失败时自动使用简单模型
- 完善的异常处理和调试信息

### 3. 高级功能
- 🎨 速度剖面图绘制
- 📊 模型验证和性能监控
- 🔄 动态模型切换
- 🛡️ 线程安全的单例管理器

## 🚀 快速开始

### 基本使用

```python
from Models.speed_model import VelocityModel, ModelManager

# 方式1：直接使用速度模型
model = VelocityModel("simple")  # 或 "iasp91", "ak135"等
time_delay = model.calculate_time_delay(
    source_pos=(0, 0, 10000),    # 震源位置 (x, y, z) 米
    receiver_pos=(50000, 0, 0),  # 检波器位置 (x, y, z) 米
    phase="P"                    # 波相（P或S）
)

# 方式2：使用模型管理器（推荐）
manager = ModelManager()  # 单例模式
current_model = manager.get_current_model()
time_delay = manager.calculate_time_delay(
    source_pos=(0, 0, 10000),
    receiver_pos=(50000, 0, 0)
)
```

### 模型管理

```python
from Models.speed_model import ModelManager

manager = ModelManager()

# 获取可用模型列表
available_models = manager.get_available_models()
print(f"可用模型: {available_models}")

# 切换模型
success = manager.set_current_model("iasp91")
if success:
    print("模型切换成功")

# 验证所有模型
validation_results = manager.validate_all_models()
for model_name, result in validation_results.items():
    print(f"{model_name}: {result['status']}")
```

### 可视化功能

```python
from Models.speed_model import VelocityModel
import matplotlib.pyplot as plt

model = VelocityModel("iasp91")

# 绘制速度剖面图
fig = model.plot_velocity_profile(max_depth=100)  # 100km深度
if fig:
    plt.show()
```

## 📦 支持的模型

### 简单模型
- **名称**: `"simple"`
- **特点**: 恒定P波/S波速度
- **适用**: 局部小尺度地震研究
- **速度**: P波=5500m/s, S波=3200m/s（可配置）

### ObsPy地球模型
| 模型名称 | 全称 | 特点 |
|---------|------|-----|
| `iasp91` | IASPEI 1991 | 国际标准参考模型 |
| `ak135` | AK135 | 改进的参考模型 |
| `prem` | PREM | 考虑地球旋转的模型 |
| `jb` | Jeffreys-Bullen | 经典地球模型 |
| `sp6` | SP6 | 现代高精度模型 |

## 🔧 高级配置

### 自定义简单模型

```python
from Models.speed_model import SimpleVelocityModel

# 创建自定义速度的简单模型
model = SimpleVelocityModel(
    p_velocity=6000,  # P波速度 m/s
    s_velocity=3500   # S波速度 m/s
)

# 或者根据Vp/Vs比值设置
model.set_velocities_from_vp_vs_ratio(
    p_velocity=6000,
    vp_vs_ratio=1.73
)
```

### 调试信息

```python
from Models.speed_model import VelocityModel

model = VelocityModel("iasp91")

# 执行一些计算...

# 获取调试信息
debug_info = model.get_debug_info()
for info in debug_info:
    print(info)
```

## 🛠️ 异常处理

模块提供了完善的异常处理机制：

```python
from Models.speed_model import (
    VelocityModel, 
    ModelInitializationError, 
    CalculationError
)

try:
    model = VelocityModel("invalid_model")
except ModelInitializationError as e:
    print(f"模型初始化失败: {e}")

try:
    result = model.calculate_time_delay(invalid_pos, invalid_pos)
except CalculationError as e:
    print(f"计算失败: {e}")
```

## 📈 性能优化

1. **单例模式**: ModelManager使用单例模式，避免重复初始化
2. **模型缓存**: 已加载的模型会被缓存，提高切换速度
3. **智能回退**: 自动选择最佳可用模型
4. **并发安全**: 支持多线程环境

## 🔄 迁移指南

### 从旧版本迁移

**旧代码**:
```python
from Models.VelocityModel import VelocityModel
from Models.ModelManager import ModelManager
```

**新代码**:
```python
from Models.speed_model import VelocityModel, ModelManager
```

### 兼容性说明
- 保留了原有API的完全兼容性
- 旧的导入方式仍然可用（会显示弃用警告）
- 建议逐步迁移到新的导入方式

## 🧪 测试

模块包含完整的测试代码，可以独立运行各个组件：

```bash
# 测试简单模型
python -m Models.speed_model.simple_model

# 测试ObsPy模型（需要安装ObsPy）
python -m Models.speed_model.obspy_model

# 测试模型管理器
python -m Models.speed_model.model_manager
```

## 🔗 依赖项

### 必需依赖
- `PyQt6`: GUI框架
- `numpy`: 数值计算
- `matplotlib`: 绘图功能

### 可选依赖
- `obspy`: 专业地震学模型支持（强烈推荐）

## 🤝 贡献指南

1. 新的速度模型应继承 `BaseVelocityModel`
2. 实现必需的抽象方法：`calculate_time_delay`
3. 添加适当的异常处理和调试信息
4. 编写相应的测试代码

## 📄 许可证

本模块遵循项目整体的许可证协议。

---

**作者**: ssatop项目组  
**创建时间**: 2024  
**最后更新**: 2024年  

如有问题或建议，请联系项目维护者。 