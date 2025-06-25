# SSATOP - 波数据分析系统

这是一个用于地震波数据分析的桌面应用程序，基于Python和PyQt6开发。

## 功能特性

- 波数据展示：可视化显示地震波形数据
- 源位置检测：分析并定位震源位置
- 批量处理：支持多文件批量分析
- 速度模型：构建和维护速度模型
- 文件管理：导入、管理波形数据和检波器位置数据
- 系统设置：配置系统参数
- 主题设置：自定义界面主题

## 系统要求

- Python 3.8+
- PyQt6
- 其他依赖见requirements.txt

## 安装方法

1. 克隆仓库
```bash
git clone https://github.com/charlllls/ssatop.git
cd ssatop
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 运行程序
```bash
python main.py
```

## 文件结构

- Controllers/：MVC控制器
- Models/：模型类
- Views/：视图组件
- Services/：业务服务层
- main.py：主程序入口 