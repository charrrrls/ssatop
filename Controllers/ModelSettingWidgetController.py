from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QApplication
from PyQt6.QtCore import Qt
from Models.speed_model.model_manager import ModelManager
from Views.ModelSettingWidget import ModelSettingWidget
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import traceback
import time
import math

class ModelSettingWidgetController:
    """速度模型设置控制器，连接模型与视图"""
    
    def __init__(self, view: ModelSettingWidget):
        """
        初始化控制器
        
        参数:
        view: ModelSettingWidget视图实例
        """
        self.view = view
        self.model_manager = ModelManager()
        
        # 填充模型下拉菜单
        self.populate_model_list()
        
        # 绑定事件
        self.view.model_select_combobox.currentIndexChanged.connect(self.handle_model_selection_change)
        self.view.apply_button.clicked.connect(self.handle_apply_model)
        self.view.validate_button.clicked.connect(self.handle_validate_model)
        
        # 可视化控制事件绑定
        self.view.viz_type_combo.currentIndexChanged.connect(self.handle_viz_type_change)
        self.view.depth_slider.valueChanged.connect(self.handle_viz_params_change)
        self.view.distance_slider.valueChanged.connect(self.handle_viz_type_change)
        self.view.phase_combo.currentIndexChanged.connect(self.handle_viz_params_change)
        self.view.compare_models_list.itemSelectionChanged.connect(self.handle_viz_params_change)
        self.view.az_slider.valueChanged.connect(self.handle_viz_params_change)
        self.view.elev_slider.valueChanged.connect(self.handle_viz_params_change)
        
    def populate_model_list(self):
        """填充模型下拉列表"""
        try:
            # 清空当前列表
            self.view.model_select_combobox.clear()
            
            # 获取可用模型列表并添加到下拉框中
            models = self.model_manager.get_available_models()
            
            # 添加所有模型到下拉框
            self.view.model_select_combobox.addItems(models)
            
            # 设置当前选中的模型
            current_model = self.model_manager.get_current_model()
            if current_model:
                index = self.view.model_select_combobox.findText(current_model.model_name)
                if index >= 0:
                    self.view.model_select_combobox.setCurrentIndex(index)
                    
            print(f"已填充模型列表: {self.model_manager.get_available_models()}")
            
            # 更新用于比较的模型下拉框
            self.view.update_compare_models_combo(models)
            
            # 立即触发选择变更，以显示初始模型信息
            self.handle_model_selection_change()
            
        except Exception as e:
            print(f"填充模型列表失败: {e}")
            print(traceback.format_exc())
            QMessageBox.warning(self.view, "错误", f"获取可用模型列表失败: {str(e)}")
    
    def handle_model_selection_change(self):
        """处理模型选择变更"""
        # 获取当前选择的模型名称
        selected_model = self.view.model_select_combobox.currentText()
        if not selected_model:
            return
            
        try:
            # 获取模型描述信息
            description = self.model_manager.get_model_description(selected_model)
            self.view.model_description_text.setText(description)
            
            # 更新模型参数表格
            self.update_model_parameters(selected_model)
            
            # 更新模型可视化
            self.update_model_visualization(selected_model)
            
        except Exception as e:
            print(f"更新模型描述失败: {e}")
            print(traceback.format_exc())
    
    def update_model_parameters(self, model_name):
        """更新模型参数表格"""
        try:
            # 清空表格
            self.view.params_table.setRowCount(0)
            
            # 模型参数定义
            parameters = {
                "simple": [
                    ("P波速度", "3000", "m/s"),
                    ("S波速度", "1732", "m/s"),
                    ("地球密度", "2700", "kg/m³")
                ],
                "iasp91": [
                    ("地壳P波速度", "5800-6500", "m/s"),
                    ("地壳S波速度", "3360-3750", "m/s"),
                    ("上地幔P波速度", "8000-8900", "m/s"),
                    ("上地幔S波速度", "4500-4900", "m/s"),
                    ("莫霍面深度", "35", "km")
                ],
                "ak135": [
                    ("地壳P波速度", "5800-6500", "m/s"),
                    ("地壳S波速度", "3460-3850", "m/s"),
                    ("上地幔P波速度", "8040-8900", "m/s"),
                    ("上地幔S波速度", "4500-4900", "m/s"),
                    ("莫霍面深度", "35", "km")
                ],
                "prem": [
                    ("地壳P波速度", "5800-6800", "m/s"),
                    ("地壳S波速度", "3200-3900", "m/s"),
                    ("上地幔P波速度", "8000-11300", "m/s"),
                    ("上地幔S波速度", "4500-6200", "m/s"),
                    ("莫霍面深度", "24", "km")
                ],
                "jb": [
                    ("地壳P波速度", "5800-6500", "m/s"),
                    ("地壳S波速度", "3400-3800", "m/s"),
                    ("上地幔P波速度", "7900-8200", "m/s"),
                    ("上地幔S波速度", "4300-4700", "m/s"),
                    ("莫霍面深度", "33", "km")
                ],
                "sp6": [
                    ("地壳P波速度", "5800-6700", "m/s"),
                    ("地壳S波速度", "3300-3900", "m/s"),
                    ("上地幔P波速度", "8000-8700", "m/s"),
                    ("上地幔S波速度", "4500-4900", "m/s"),
                    ("莫霍面深度", "35", "km")
                ]
            }
            
            # 获取当前模型的参数
            model_params = parameters.get(model_name, [("无参数数据", "-", "-")])
            
            # 填充表格
            for i, (param, value, unit) in enumerate(model_params):
                row = self.view.params_table.rowCount()
                self.view.params_table.insertRow(row)
                
                # 添加参数名、值和单位
                self.view.params_table.setItem(row, 0, QTableWidgetItem(param))
                self.view.params_table.setItem(row, 1, QTableWidgetItem(value))
                self.view.params_table.setItem(row, 2, QTableWidgetItem(unit))
                
        except Exception as e:
            print(f"更新模型参数失败: {e}")
            print(traceback.format_exc())
    
    def update_model_visualization(self, model_name):
        """更新模型可视化"""
        try:
            # 获取当前可视化类型
            viz_type = self.view.viz_type_combo.currentText()
            
            # 根据不同的可视化类型调用相应的绘图函数
            if viz_type == "速度-深度剖面":
                self.draw_velocity_profile(model_name)
            elif viz_type == "射线路径图":
                self.draw_ray_path(model_name)
            elif viz_type == "多模型对比":
                self.draw_model_comparison(model_name)
            elif viz_type == "3D模型可视化":
                self.draw_3d_model(model_name)
            else:
                self.draw_velocity_profile(model_name)  # 默认使用速度-深度剖面图
            
        except Exception as e:
            print(f"更新模型可视化失败: {e}")
            print(traceback.format_exc())
    
    def handle_viz_type_change(self):
        """处理可视化类型变更"""
        try:
            selected_model = self.view.model_select_combobox.currentText()
            if selected_model:
                self.update_model_visualization(selected_model)
        except Exception as e:
            print(f"处理可视化类型变更失败: {e}")
            print(traceback.format_exc())
    
    def handle_viz_params_change(self):
        """处理可视化参数变更"""
        # 添加延迟以避免频繁更新
        QApplication.processEvents()
        try:
            # 获取当前选择的模型名称
            selected_model = self.view.model_select_combobox.currentText()
            if not selected_model:
                return
                
            # 更新可视化
            self.update_model_visualization(selected_model)
            
        except Exception as e:
            print(f"更新可视化参数失败: {e}")
            print(traceback.format_exc())
    
    def draw_velocity_profile(self, model_name):
        """绘制速度-深度剖面图"""
        try:
            # 获取画布并清空
            fig = self.view.fig
            fig.clear()
            
            # 创建绘图区域
            ax = fig.add_subplot(111)
            
            # 获取最大深度
            max_depth = self.view.depth_slider.value()
            
            # 深度范围
            depths = np.linspace(0, max_depth, 1000)  # 0-max_depth km
            
            # 不同模型的速度函数 (模拟数据)
            velocity_profiles = {
                "simple": lambda d: np.ones_like(d) * 6.0,  # 恒定速度
                "iasp91": lambda d: 5.8 + 0.7 * np.log10(d + 1) + 0.02 * d * np.sin(d / 5),  # 变化的速度曲线
                "ak135": lambda d: 5.8 + 0.75 * np.log10(d + 1) + 0.023 * d * np.sin(d / 4.8),
                "prem": lambda d: 5.8 + 0.8 * np.log10(d + 1) + 0.025 * d * np.sin(d / 4.5),
                "jb": lambda d: 5.8 + 0.73 * np.log10(d + 1) + 0.021 * d * np.sin(d / 5.2),
                "sp6": lambda d: 5.8 + 0.76 * np.log10(d + 1) + 0.024 * d * np.sin(d / 4.9),
                "1066a": lambda d: 5.8 + 0.72 * np.log10(d + 1) + 0.022 * d * np.sin(d / 5.1),
                "ak135f": lambda d: 5.8 + 0.75 * np.log10(d + 1) + 0.023 * d * np.sin(d / 4.8),
                "herrin": lambda d: 5.8 + 0.74 * np.log10(d + 1) + 0.022 * d * np.sin(d / 5.0)
            }
            
            # 获取当前模型的速度函数
            velocity_func = velocity_profiles.get(model_name, velocity_profiles["simple"])
            
            # 计算P波速度
            p_velocities = velocity_func(depths)
            
            # 计算S波速度 (假设S波速度为P波速度的约0.6倍)
            s_velocities = p_velocities * 0.6
            
            # 绘制速度曲线
            ax.plot(p_velocities, depths, 'r-', linewidth=2, label='P波速度')
            ax.plot(s_velocities, depths, 'b-', linewidth=2, label='S波速度')
            
            # 设置坐标轴
            ax.set_xlabel('速度 (km/s)', fontsize=12)
            ax.set_ylabel('深度 (km)', fontsize=12)
            ax.set_ylim(max_depth, 0)  # 深度从0开始向下增加
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # 图表标题
            ax.set_title(f"{model_name}模型速度-深度剖面", fontsize=14, fontweight='bold')
            
            # 添加模型特征标注
            if model_name != "simple":
                # 模拟莫霍面位置
                moho_depths = {
                    "iasp91": 35, "ak135": 35, "prem": 24, "jb": 33, 
                    "sp6": 35, "1066a": 30, "ak135f": 35, "herrin": 33
                }
                moho_depth = moho_depths.get(model_name, 35)
                
                # 绘制莫霍面位置
                if moho_depth <= max_depth:
                    ax.axhline(y=moho_depth, color='blue', linestyle='--', alpha=0.8)
                    ax.text(8.0, moho_depth - 2, '莫霍面', fontsize=10, color='blue')
                    
                    # 标注地壳和上地幔
                    ax.text(8.0, moho_depth * 0.3, '地壳', fontsize=12, color='darkgreen')
                    ax.text(8.0, moho_depth + (max_depth - moho_depth) * 0.3, '上地幔', fontsize=12, color='darkred')
            
            # 添加图例
            ax.legend(loc='upper right')
            
            # 更新图表布局
            fig.tight_layout()
            self.view.canvas.draw()
            
        except Exception as e:
            print(f"绘制速度剖面图失败: {e}")
            print(traceback.format_exc())
    
    def draw_ray_path(self, model_name):
        """绘制射线路径图"""
        try:
            # 获取画布并清空
            fig = self.view.fig
            fig.clear()
            
            # 创建绘图区域
            ax = fig.add_subplot(111)
            
            # 获取震中距离和深度
            distance_deg = self.view.distance_slider.value()
            source_depth = 10  # 固定震源深度为10km
            selected_phase = self.view.phase_combo.currentText()
            
            # 地球半径(km)
            earth_radius = 6371.0
            
            # 模拟射线路径数据
            theta = np.radians(np.linspace(0, distance_deg, 100))
            
            # 不同波相的路径函数 (模拟数据)
            def get_ray_path_depth(theta_rad, phase, model):
                # 根据波相和模型生成不同深度的射线路径
                max_depth_factor = {
                    "P": 0.1, "S": 0.12, 
                    "PcP": 0.5, "ScS": 0.5,
                    "PKP": 0.8, "SKS": 0.8,
                    "Pdiff": 0.5, "Sdiff": 0.5
                }
                
                # 模型影响因子
                model_factor = {
                    "simple": 1.0, "iasp91": 1.05, "ak135": 1.1,
                    "prem": 1.15, "jb": 1.05, "sp6": 1.1, 
                    "1066a": 1.05, "ak135f": 1.1, "herrin": 1.05
                }
                
                # 获取波相和模型的对应因子
                depth_factor = max_depth_factor.get(phase, 0.1) * model_factor.get(model, 1.0)
                
                # 生成路径
                if phase in ["P", "S"]:
                    # 直达波: 简单弧线
                    return earth_radius * depth_factor * np.sin(theta_rad)
                elif phase in ["PcP", "ScS"]:
                    # 核反射波: 更深的弧线
                    return earth_radius * depth_factor * np.sin(2 * theta_rad)
                elif phase in ["PKP", "SKS"]:
                    # 核穿透波: 深入地核
                    return earth_radius * depth_factor * (1 - np.cos(theta_rad * 2))
                else:
                    # 默认路径
                    return earth_radius * 0.1 * np.sin(theta_rad)
            
            # 计算射线路径
            depths = get_ray_path_depth(theta, selected_phase, model_name)
            
            # 绘制地球表面
            earth_surface = np.zeros_like(theta)
            ax.plot(np.degrees(theta), earth_surface, 'k-', linewidth=1.5)
            
            # 绘制射线路径
            ax.plot(np.degrees(theta), depths, 'r-', linewidth=2, label=selected_phase)
            
            # 添加震源和接收器标记
            ax.scatter([0], [source_depth], color='blue', s=100, marker='*', label='震源')
            ax.scatter([distance_deg], [0], color='green', s=100, marker='^', label='接收器')
            
            # 设置坐标轴
            ax.set_xlabel('震中距 (度)', fontsize=12)
            ax.set_ylabel('深度 (km)', fontsize=12)
            ax.set_xlim(0, distance_deg)
            ax.set_ylim(max(np.max(depths), source_depth) * 1.1, -10)  # 深度从0开始向下增加
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # 图表标题
            ax.set_title(f"{model_name}模型 {selected_phase}波射线路径", fontsize=14, fontweight='bold')
            
            # 添加图例
            ax.legend(loc='upper right')
            
            # 更新图表布局
            fig.tight_layout()
            self.view.canvas.draw()
            
        except Exception as e:
            print(f"绘制射线路径图失败: {e}")
            print(traceback.format_exc())
    
    def draw_model_comparison(self, model_name):
        """绘制多模型对比图"""
        try:
            # 获取画布并清空
            fig = self.view.fig
            fig.clear()
            
            # 创建绘图区域
            ax = fig.add_subplot(111)
            
            # 获取最大深度
            max_depth = self.view.depth_slider.value()
            
            # 深度范围
            depths = np.linspace(0, max_depth, 1000)  # 0-max_depth km
            
            # 不同模型的速度函数 (模拟数据)
            velocity_profiles = {
                "simple": lambda d: np.ones_like(d) * 6.0,  # 恒定速度
                "iasp91": lambda d: 5.8 + 0.7 * np.log10(d + 1) + 0.02 * d * np.sin(d / 5),  # 变化的速度曲线
                "ak135": lambda d: 5.8 + 0.75 * np.log10(d + 1) + 0.023 * d * np.sin(d / 4.8),
                "prem": lambda d: 5.8 + 0.8 * np.log10(d + 1) + 0.025 * d * np.sin(d / 4.5),
                "jb": lambda d: 5.8 + 0.73 * np.log10(d + 1) + 0.021 * d * np.sin(d / 5.2),
                "sp6": lambda d: 5.8 + 0.76 * np.log10(d + 1) + 0.024 * d * np.sin(d / 4.9),
                "1066a": lambda d: 5.8 + 0.72 * np.log10(d + 1) + 0.022 * d * np.sin(d / 5.1),
                "ak135f": lambda d: 5.8 + 0.75 * np.log10(d + 1) + 0.023 * d * np.sin(d / 4.8),
                "herrin": lambda d: 5.8 + 0.74 * np.log10(d + 1) + 0.022 * d * np.sin(d / 5.0)
            }
            
            # 获取所有可用模型
            available_models = self.model_manager.get_available_models()
            
            # 颜色列表用于区分不同模型
            colors = ['r', 'g', 'b', 'c', 'm', 'y', 'orange', 'purple', 'brown', 'pink']
            
            # 获取要对比的模型列表
            models_to_compare = []
            for item in self.view.compare_models_list.selectedItems():
                models_to_compare.append(item.text())
                
            # 如果没有选择模型，默认使用当前选中的模型和simple模型
            if not models_to_compare:
                models_to_compare = [model_name, "simple"]
            
            # 绘制选中模型的P波速度曲线
            for i, model in enumerate(models_to_compare):
                if i < len(colors):  # 限制绘制模型数量
                    # 获取当前模型的速度函数
                    velocity_func = velocity_profiles.get(model, velocity_profiles["simple"])
                    
                    # 计算P波速度
                    p_velocities = velocity_func(depths)
                    
                    # 绘制速度曲线
                    ax.plot(p_velocities, depths, color=colors[i], linewidth=2, label=f'{model}')
            
            # 设置坐标轴
            ax.set_xlabel('P波速度 (km/s)', fontsize=12)
            ax.set_ylabel('深度 (km)', fontsize=12)
            ax.set_ylim(max_depth, 0)  # 深度从0开始向下增加
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # 图表标题
            ax.set_title(f"多模型P波速度对比", fontsize=14, fontweight='bold')
            
            # 添加图例
            ax.legend(loc='upper right')
            
            # 更新图表布局
            fig.tight_layout()
            self.view.canvas.draw()
            
        except Exception as e:
            print(f"绘制模型对比图失败: {e}")
            print(traceback.format_exc())
    
    def draw_3d_model(self, model_name):
        """绘制3D模型可视化"""
        try:
            # 获取画布并清空
            fig = self.view.fig
            fig.clear()
            
            # 创建3D绘图区域
            ax = fig.add_subplot(111, projection='3d')
            
            # 获取方位角和仰角
            azimuth = self.view.az_slider.value()
            elevation = self.view.elev_slider.value()
            
            # 设置3D视角
            ax.view_init(elev=elevation, azim=azimuth)
            
            # 地球半径(km)
            earth_radius = 6371.0
            
            # 创建3D球面网格
            u = np.linspace(0, 2 * np.pi, 100)
            v = np.linspace(0, np.pi, 100)
            
            x = 0.95 * earth_radius * np.outer(np.cos(u), np.sin(v)) / 1000  # 转换到更小的刻度
            y = 0.95 * earth_radius * np.outer(np.sin(u), np.sin(v)) / 1000
            z = 0.95 * earth_radius * np.outer(np.ones(np.size(u)), np.cos(v)) / 1000
            
            # 绘制地球表面
            earth_surface = ax.plot_surface(x, y, z, color='lightblue', alpha=0.3)
            
            # 不同莫霍面深度
            moho_depths = {
                "simple": 35, "iasp91": 35, "ak135": 35, "prem": 24, 
                "jb": 33, "sp6": 35, "1066a": 30, "ak135f": 35, "herrin": 33
            }
            moho_depth = moho_depths.get(model_name, 35)
            
            # 绘制莫霍面
            moho_factor = 1 - moho_depth / earth_radius
            moho_x = moho_factor * x
            moho_y = moho_factor * y
            moho_z = moho_factor * z
            
            moho = ax.plot_surface(moho_x, moho_y, moho_z, color='green', alpha=0.3)
            
            # 绘制地核(模拟)
            core_factor = 0.5  # 假设地核占地球半径的50%
            core_x = core_factor * x
            core_y = core_factor * y
            core_z = core_factor * z
            
            core = ax.plot_surface(core_x, core_y, core_z, color='orange', alpha=0.5)
            
            # 绘制内核(模拟)
            inner_core_factor = 0.2  # 假设内核占地球半径的20%
            inner_x = inner_core_factor * x
            inner_y = inner_core_factor * y
            inner_z = inner_core_factor * z
            
            inner_core = ax.plot_surface(inner_x, inner_y, inner_z, color='red', alpha=0.7)
            
            # 设置坐标轴标签
            ax.set_xlabel('X (1000 km)', fontsize=10)
            ax.set_ylabel('Y (1000 km)', fontsize=10)
            ax.set_zlabel('Z (1000 km)', fontsize=10)
            
            # 设置图表标题
            ax.set_title(f"{model_name}模型3D可视化", fontsize=14, fontweight='bold')
            
            # 更新图表布局
            fig.tight_layout()
            self.view.canvas.draw()
            
        except Exception as e:
            print(f"绘制3D模型失败: {e}")
            print(traceback.format_exc())
    
    def handle_apply_model(self):
        """应用所选模型"""
        # 获取当前选择的模型名称
        selected_model = self.view.model_select_combobox.currentText()
        if not selected_model:
            QMessageBox.warning(self.view, "警告", "请先选择一个模型")
            return
            
        try:
            # 设置当前模型
            success = self.model_manager.set_current_model(selected_model)
            
            if success:
                QMessageBox.information(self.view, "成功", f"已成功切换到{selected_model}模型")
                
                # 获取当前模型并生成测试结果
                current_model = self.model_manager.get_current_model()
                test_result = current_model.calculate_time_delay(
                    source_pos=(0, 0, 1000),
                    receiver_pos=(1000, 0, 0),
                    phase="P"
                )
                
                # 更新状态文本
                status_text = f"当前模型: {selected_model}\n"
                status_text += f"测试路径传播时间: {test_result:.4f} 秒\n"
                status_text += f"模型描述: {self.model_manager.get_model_description(selected_model)}\n"
                status_text += "模型已应用并可以使用。"
                
                self.view.status_text.setText(status_text)
            else:
                QMessageBox.warning(self.view, "错误", f"无法切换到{selected_model}模型")
                
                # 更新下拉框为实际的当前模型
                current_model = self.model_manager.get_current_model()
                if current_model:
                    index = self.view.model_select_combobox.findText(current_model.model_name)
                    if index >= 0:
                        self.view.model_select_combobox.setCurrentIndex(index)
                
        except Exception as e:
            print(f"应用模型失败: {e}")
            print(traceback.format_exc())
            QMessageBox.warning(self.view, "错误", f"应用模型失败: {str(e)}")
    
    def handle_validate_model(self):
        """验证所有可用的模型"""
        try:
            # 验证所有模型
            results = self.model_manager.validate_all_models()
            
            # 构建状态文本
            status_text = "模型验证结果：\n\n"
            for model_name, result in results.items():
                if result["status"] == "可用":
                    test_result = result["test_result"]
                    status_text += f"{model_name}: 可用 (测试传播时间: {test_result:.4f} 秒)\n"
                else:
                    error = result["error"]
                    status_text += f"{model_name}: 不可用 ({error})\n"
                
                # 添加模型描述信息
                if "description" in result:
                    status_text += f"  {result['description']}\n\n"
                else:
                    status_text += "\n"
            
            # 更新状态文本
            self.view.status_text.setText(status_text)
            
        except Exception as e:
            print(f"验证模型失败: {e}")
            print(traceback.format_exc())
            QMessageBox.warning(self.view, "错误", f"验证模型失败: {str(e)}") 
