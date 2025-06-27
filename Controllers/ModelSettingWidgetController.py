from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QApplication
from PyQt6.QtCore import Qt
from Models.ModelManager import ModelManager
from Views.ModelSettingWidget import ModelSettingWidget
from Views.CustomModelDialog import CustomModelDialog
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import traceback
import time
import math
import json
from pathlib import Path
import os

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
        self.view.custom_model_button.clicked.connect(self.handle_custom_model)
        self.view.delete_model_button.clicked.connect(self.handle_delete_model)
        
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
            self.view.status_text.append(f"错误: 更新模型失败: {str(e)}")
    
    def update_model_parameters(self, model_name):
        """更新模型参数表格"""
        try:
            # 清空表格
            self.view.params_table.setRowCount(0)
            
            # 从模型管理器获取实际参数
            model_data = self.model_manager.get_model_data(model_name)
            if not model_data:
                raise ValueError(f"无法获取模型 {model_name} 的数据")
                
            # 添加基本参数
            if "parameters" in model_data:
                for param_name, param_info in model_data["parameters"].items():
                    value = param_info.get("value", "-")
                    unit = param_info.get("unit", "-")
                    
                    row = self.view.params_table.rowCount()
                    self.view.params_table.insertRow(row)
                    
                    self.view.params_table.setItem(row, 0, QTableWidgetItem(param_name))
                    self.view.params_table.setItem(row, 1, QTableWidgetItem(str(value)))
                    self.view.params_table.setItem(row, 2, QTableWidgetItem(unit))
            
            # 添加层数据
            if "layers" in model_data:
                # 添加分隔行
                row = self.view.params_table.rowCount()
                self.view.params_table.insertRow(row)
                separator = QTableWidgetItem("--- 模型层数据 ---")
                separator.setFlags(Qt.ItemFlag.ItemIsEnabled)  # 设为只读
                self.view.params_table.setItem(row, 0, separator)
                self.view.params_table.setSpan(row, 0, 1, 3)  # 合并单元格
                
                # 添加每一层的数据
                for i, layer in enumerate(model_data["layers"]):
                    # 深度
                    row = self.view.params_table.rowCount()
                    self.view.params_table.insertRow(row)
                    self.view.params_table.setItem(row, 0, QTableWidgetItem(f"第{i+1}层深度"))
                    self.view.params_table.setItem(row, 1, QTableWidgetItem(str(layer.get("depth", "-"))))
                    self.view.params_table.setItem(row, 2, QTableWidgetItem("km"))
                    
                    # P波速度
                    row = self.view.params_table.rowCount()
                    self.view.params_table.insertRow(row)
                    self.view.params_table.setItem(row, 0, QTableWidgetItem(f"第{i+1}层P波速度"))
                    self.view.params_table.setItem(row, 1, QTableWidgetItem(str(layer.get("vp", "-"))))
                    self.view.params_table.setItem(row, 2, QTableWidgetItem("km/s"))
                    
                    # S波速度
                    row = self.view.params_table.rowCount()
                    self.view.params_table.insertRow(row)
                    self.view.params_table.setItem(row, 0, QTableWidgetItem(f"第{i+1}层S波速度"))
                    self.view.params_table.setItem(row, 1, QTableWidgetItem(str(layer.get("vs", "-"))))
                    self.view.params_table.setItem(row, 2, QTableWidgetItem("km/s"))
            else:
                # 如果没有层数据，添加提示
                row = self.view.params_table.rowCount()
                self.view.params_table.insertRow(row)
                self.view.params_table.setItem(row, 0, QTableWidgetItem("错误"))
                self.view.params_table.setItem(row, 1, QTableWidgetItem("模型没有层数据"))
                self.view.params_table.setItem(row, 2, QTableWidgetItem("-"))
                
                self.view.status_text.append(f"警告: 模型 {model_name} 没有层数据，无法正确显示参数")
                
        except Exception as e:
            print(f"更新模型参数失败: {e}")
            print(traceback.format_exc())
            self.view.status_text.append(f"错误: 更新模型参数失败: {str(e)}")
            
            # 添加错误信息到表格
            row = self.view.params_table.rowCount()
            self.view.params_table.insertRow(row)
            self.view.params_table.setItem(row, 0, QTableWidgetItem("错误"))
            self.view.params_table.setItem(row, 1, QTableWidgetItem(f"无法加载参数: {str(e)}"))
            self.view.params_table.setItem(row, 2, QTableWidgetItem("-"))
    
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
            self.view.status_text.append(f"错误: 更新模型可视化失败: {str(e)}")
            
            # 清空图表并显示错误信息
            fig = self.view.fig
            fig.clear()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"错误: {str(e)}", 
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=12, color='red')
            ax.set_axis_off()
            self.view.canvas.draw()
    
    def handle_viz_type_change(self):
        """处理可视化类型变更"""
        try:
            selected_model = self.view.model_select_combobox.currentText()
            if selected_model:
                self.update_model_visualization(selected_model)
        except Exception as e:
            print(f"处理可视化类型变更失败: {e}")
            print(traceback.format_exc())
            self.view.status_text.append(f"错误: 处理可视化类型变更失败: {str(e)}")
    
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
            self.view.status_text.append(f"错误: 更新可视化参数失败: {str(e)}")
    
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
            
            # 获取模型数据
            model_data = self.model_manager.get_model_data(model_name)
            if not model_data or "layers" not in model_data:
                raise ValueError(f"模型 {model_name} 没有层数据，无法绘制速度-深度剖面图")
            
            # 提取深度和速度数据
            depths = []
            vp_values = []
            vs_values = []
            
            for layer in model_data["layers"]:
                depth = layer.get("depth")
                vp = layer.get("vp")
                vs = layer.get("vs")
                
                if depth is None or vp is None or vs is None:
                    raise ValueError(f"模型 {model_name} 的层数据不完整，缺少深度或速度值")
                
                depths.append(depth)
                vp_values.append(vp)
                vs_values.append(vs)
            
            # 检查是否有有效数据
            if not depths or not vp_values or not vs_values:
                raise ValueError(f"模型 {model_name} 没有有效的层数据")
                
            # 确保数据按深度排序
            sorted_data = sorted(zip(depths, vp_values, vs_values), key=lambda x: x[0])
            depths = [d for d, _, _ in sorted_data]
            vp_values = [vp for _, vp, _ in sorted_data]
            vs_values = [vs for _, _, vs in sorted_data]
            
            # 绘制速度曲线
            ax.plot(vp_values, depths, 'r-', linewidth=2, label='P波速度')
            ax.plot(vs_values, depths, 'b-', linewidth=2, label='S波速度')
            
            # 设置坐标轴
            ax.set_xlabel('速度 (km/s)', fontsize=12)
            ax.set_ylabel('深度 (km)', fontsize=12)
            ax.set_ylim(max_depth, 0)  # 深度从0开始向下增加
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # 图表标题
            ax.set_title(f"{model_name}模型速度-深度剖面", fontsize=14, fontweight='bold')
            
            # 查找莫霍面深度（如果有定义）
            if "parameters" in model_data and "moho_depth" in model_data["parameters"]:
                moho_depth = model_data["parameters"]["moho_depth"].get("value")
                if moho_depth is not None and moho_depth <= max_depth:
                    ax.axhline(y=moho_depth, color='blue', linestyle='--', alpha=0.8)
                    # 检查vp_values是否为空，避免max()操作空列表
                    if vp_values:
                        ax.text(max(vp_values) * 0.8, moho_depth - 2, '莫霍面', fontsize=10, color='blue')
                    else:
                        ax.text(5.0, moho_depth - 2, '莫霍面', fontsize=10, color='blue')  # 使用默认值5.0
            
            # 添加图例
            ax.legend(loc='upper right')
            
            # 更新图表布局
            fig.tight_layout()
            self.view.canvas.draw()
            
        except Exception as e:
            print(f"绘制速度剖面图失败: {e}")
            print(traceback.format_exc())
            self.view.status_text.append(f"错误: 绘制速度剖面图失败: {str(e)}")
            
            # 显示错误信息
            fig.clear()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"绘制速度剖面图失败: {str(e)}", 
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=12, color='red')
            ax.set_axis_off()
            self.view.canvas.draw()
    
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
            selected_phase = self.view.phase_combo.currentText()
            
            # 获取模型数据
            model_data = self.model_manager.get_model_data(model_name)
            if not model_data:
                raise ValueError(f"无法获取模型 {model_name} 的数据")
            
            # 调用视图类的射线路径计算方法
            try:
                x_values, y_values = self.view._calculate_real_ray_path(model_data, distance_deg, selected_phase)
                
                if len(x_values) == 0 or len(y_values) == 0:
                    raise ValueError("射线路径计算结果为空")
                    
                # 绘制射线路径
                ax.plot(x_values, y_values, 'r-', linewidth=2, label=f'{selected_phase}波射线路径')
                
                # 绘制地球表面
                ax.plot([0, distance_deg], [0, 0], 'k-', linewidth=1.5)
                
                # 添加震源和接收器标记
                ax.scatter([0], [10], color='blue', s=100, marker='*', label='震源')
                ax.scatter([distance_deg], [0], color='green', s=100, marker='^', label='接收器')
                
                # 设置坐标轴
                ax.set_xlabel('震中距 (度)', fontsize=12)
                ax.set_ylabel('深度 (km)', fontsize=12)
                ax.set_xlim(0, distance_deg)
                
                # 获取合适的深度范围
                max_y = max(y_values) * 1.1
                ax.set_ylim(max_y, -10)  # 深度从0开始向下增加
                
                # 绘制参考深度线
                # 核幔边界
                cmb_depth = 2889.0
                if cmb_depth < max_y:
                    ax.axhline(y=cmb_depth, color='orange', linestyle='-', alpha=0.5, label='核幔边界')
                
                # 图表标题
                ax.set_title(f"{model_name}模型 {selected_phase}波射线路径", fontsize=14, fontweight='bold')
                
                # 添加网格
                ax.grid(True, linestyle='--', alpha=0.7)
                
                # 添加图例
                ax.legend(loc='upper right')
                
                # 更新图表布局
                fig.tight_layout()
                self.view.canvas.draw()
                
            except Exception as e:
                raise ValueError(f"计算射线路径失败: {str(e)}")
            
        except Exception as e:
            print(f"绘制射线路径图失败: {e}")
            print(traceback.format_exc())
            self.view.status_text.append(f"错误: 绘制射线路径图失败: {str(e)}")
            
            # 显示错误信息
            fig.clear()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"绘制射线路径图失败: {str(e)}", 
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=12, color='red')
            ax.set_axis_off()
            self.view.canvas.draw()
    
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
            
            # 获取要对比的模型列表
            models_to_compare = []
            for item in self.view.compare_models_list.selectedItems():
                models_to_compare.append(item.text())
            
            # 如果没有选择模型，默认使用当前选中的模型
            if not models_to_compare:
                models_to_compare = [model_name]
            
            # 颜色列表用于区分不同模型
            colors = ['r', 'g', 'b', 'c', 'm', 'y', 'orange', 'purple', 'brown', 'pink']
            
            # 收集所有深度点以确保一致的图表范围
            all_depths = []
            all_vp_values = []
            
            # 绘制选中模型的P波速度曲线
            for i, model in enumerate(models_to_compare):
                if i >= len(colors):  # 限制绘制模型数量
                    break
                
                try:
                    # 获取模型数据
                    model_data = self.model_manager.get_model_data(model)
                    if not model_data or "layers" not in model_data:
                        self.view.status_text.append(f"警告: 模型 {model} 没有层数据，跳过绘制")
                        continue
                    
                    # 提取深度和速度数据
                    depths = []
                    vp_values = []
                    
                    for layer in model_data["layers"]:
                        depth = layer.get("depth")
                        vp = layer.get("vp")
                        
                        if depth is None or vp is None:
                            self.view.status_text.append(f"警告: 模型 {model} 的层数据不完整，缺少深度或P波速度")
                            continue
                        
                        depths.append(depth)
                        vp_values.append(vp)
                    
                    # 确保数据按深度排序
                    sorted_data = sorted(zip(depths, vp_values), key=lambda x: x[0])
                    depths = [d for d, _ in sorted_data]
                    vp_values = [vp for _, vp in sorted_data]
                    
                    # 收集所有点
                    all_depths.extend(depths)
                    all_vp_values.extend(vp_values)
                    
                    # 绘制速度曲线
                    ax.plot(vp_values, depths, color=colors[i], linewidth=2, label=f'{model}')
                    
                except Exception as e:
                    self.view.status_text.append(f"警告: 模型 {model} 绘制失败: {str(e)}")
            
            if not all_depths:  # 如果没有成功绘制任何模型
                raise ValueError("没有足够的数据进行模型对比")
            
            # 设置坐标轴
            ax.set_xlabel('P波速度 (km/s)', fontsize=12)
            ax.set_ylabel('深度 (km)', fontsize=12)
            ax.set_ylim(max_depth, 0)  # 深度从0开始向下增加
            
            # 确保X轴显示所有速度值
            min_vp = min(all_vp_values) * 0.95
            max_vp = max(all_vp_values) * 1.05
            ax.set_xlim(min_vp, max_vp)
            
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
            self.view.status_text.append(f"错误: 绘制模型对比图失败: {str(e)}")
            
            # 显示错误信息
            fig.clear()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"绘制模型对比图失败: {str(e)}", 
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=12, color='red')
            ax.set_axis_off()
            self.view.canvas.draw()
    
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
            
            # 获取模型数据
            model_data = self.model_manager.get_model_data(model_name)
            if not model_data or "layers" not in model_data:
                raise ValueError(f"模型 {model_name} 没有层数据，无法绘制3D可视化")
            
            # 地球半径(km)
            earth_radius = 6371.0
            
            # 创建3D球面网格
            u = np.linspace(0, 2 * np.pi, 100)
            v = np.linspace(0, np.pi, 100)
            
            # 绘制地球表面
            x_surface = earth_radius * np.outer(np.cos(u), np.sin(v)) / 1000  # 缩小比例
            y_surface = earth_radius * np.outer(np.sin(u), np.sin(v)) / 1000
            z_surface = earth_radius * np.outer(np.ones(np.size(u)), np.cos(v)) / 1000
            
            ax.plot_surface(x_surface, y_surface, z_surface, color='lightblue', alpha=0.3)
            
            # 按深度绘制主要界面
            for layer in model_data["layers"]:
                depth = layer.get("depth")
                if depth is None or depth <= 0:
                    continue
                    
                # 计算球面缩放因子
                scale_factor = (earth_radius - depth) / earth_radius
                
                # 创建该深度的球面
                x_layer = scale_factor * x_surface
                y_layer = scale_factor * y_surface
                z_layer = scale_factor * z_surface
                
                # 使用P波速度作为颜色指标
                vp = layer.get("vp", 0)
                
                # 绘制该层
                ax.plot_surface(x_layer, y_layer, z_layer, 
                                color=plt.cm.viridis(vp/10.0),  # 速度归一化作为颜色指标
                                alpha=0.4, linewidth=0, antialiased=True)
                
                # 如果是重要界面，添加标记
                if "name" in layer:
                    layer_name = layer["name"]
                    ax.text(x_layer[0, 0], y_layer[0, 0], z_layer[0, 0], 
                            layer_name, color='black', fontsize=8)
            
            # 设置坐标轴标签
            ax.set_xlabel('X (1000 km)', fontsize=10)
            ax.set_ylabel('Y (1000 km)', fontsize=10)
            ax.set_zlabel('Z (1000 km)', fontsize=10)
            
            # 设置图表标题
            ax.set_title(f"{model_name}模型3D可视化", fontsize=14, fontweight='bold')
            
            # 保持坐标轴比例一致
            max_range = max(
                np.max(x_surface) - np.min(x_surface),
                np.max(y_surface) - np.min(y_surface),
                np.max(z_surface) - np.min(z_surface)
            )
            mid_x = (np.max(x_surface) + np.min(x_surface)) * 0.5
            mid_y = (np.max(y_surface) + np.min(y_surface)) * 0.5
            mid_z = (np.max(z_surface) + np.min(z_surface)) * 0.5
            ax.set_xlim(mid_x - max_range/2, mid_x + max_range/2)
            ax.set_ylim(mid_y - max_range/2, mid_y + max_range/2)
            ax.set_zlim(mid_z - max_range/2, mid_z + max_range/2)
            
            # 添加颜色条表示速度范围
            from matplotlib.colors import Normalize
            import matplotlib.cm as cm
            
            # 收集所有P波速度值
            vp_values = [layer.get("vp", 0) for layer in model_data["layers"] if "vp" in layer]
            if vp_values:
                norm = Normalize(vmin=min(vp_values), vmax=max(vp_values))
                sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis, norm=norm)
                sm.set_array([])
                cbar = plt.colorbar(sm, ax=ax, shrink=0.5, aspect=10)
                cbar.set_label('P波速度 (km/s)')
            
            # 更新图表布局
            fig.tight_layout()
            self.view.canvas.draw()
            
        except Exception as e:
            print(f"绘制3D模型失败: {e}")
            print(traceback.format_exc())
            self.view.status_text.append(f"错误: 绘制3D模型失败: {str(e)}")
            
            # 显示错误信息
            fig.clear()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"绘制3D模型失败: {str(e)}", 
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=12, color='red')
            ax.set_axis_off()
            self.view.canvas.draw()
    
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
    
    def handle_custom_model(self):
        """
        处理自定义模型按钮点击事件
        
        打开自定义模型对话框，允许用户创建或编辑模型
        """
        try:
            # 获取当前所有可用模型，用于模板选择
            available_models = self.model_manager.get_available_models()
            
            # 创建自定义模型对话框
            dialog = CustomModelDialog(self.view)
            
            # 为对话框添加现有模型作为模板
            dialog.set_available_templates(available_models)
            
            # 连接模型变更信号到刷新方法
            dialog.model_changed.connect(self._on_model_changed)
            
            # 显示对话框并等待用户操作
            result = dialog.exec()
            
            # 用户点击了确定按钮，dialog内部会处理模型保存，这里只需刷新界面
            if result:
                # 刷新模型列表
                self.model_manager.refresh_models()
                self.populate_model_list()
                
                # 输出日志
                self.view.status_text.append("自定义模型已创建并保存")
                
        except Exception as e:
            print(f"处理自定义模型时出错: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self.view, "错误", f"处理自定义模型失败: {str(e)}")
    
    def _on_model_changed(self, model_name):
        """
        当模型变更时的回调函数
        
        参数:
        model_name: 变更的模型名称
        """
        # 刷新模型列表
        self.model_manager.refresh_models()
        self.populate_model_list()
        
        # 选择新创建/编辑的模型
        index = self.view.model_select_combobox.findText(model_name)
        if index >= 0:
            self.view.model_select_combobox.setCurrentIndex(index)
            # 触发模型选择变更
            self.handle_model_selection_change()
    
    def handle_delete_model(self):
        """
        处理删除自定义模型按钮点击事件
        
        只能删除自定义模型，不能删除内置模型
        """
        try:
            # 获取当前选择的模型名称
            selected_model = self.view.model_select_combobox.currentText()
            if not selected_model:
                QMessageBox.warning(self.view, "警告", "请先选择一个模型")
                return
            
            # 确认是否删除
            reply = QMessageBox.question(
                self.view,
                "确认删除",
                f"确定要删除模型 {selected_model} 吗？此操作不可恢复！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # 使用ModelManager的delete_model方法删除模型
            if self.model_manager.delete_model(selected_model):
                # 成功删除，刷新模型列表
                self.model_manager.refresh_models()
                self.populate_model_list()
                
                # 输出状态信息
                self.view.status_text.append(f"已删除模型: {selected_model}")
                
                # 检查当前模型是否还存在，如果不存在则选择第一个可用模型
                current_model = self.view.model_select_combobox.currentText()
                if not current_model:
                    if self.view.model_select_combobox.count() > 0:
                        self.view.model_select_combobox.setCurrentIndex(0)
                        self.handle_model_selection_change()
            else:
                # 删除失败
                QMessageBox.warning(self.view, "错误", f"删除模型 {selected_model} 失败")
            
        except Exception as e:
            print(f"处理删除模型时出错: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self.view, "错误", f"删除模型失败: {str(e)}")
