from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTableWidget, QTableWidgetItem, QPushButton, QFormLayout,
    QGroupBox, QSpinBox, QDoubleSpinBox, QMessageBox, QFileDialog,
    QHeaderView, QComboBox, QTabWidget, QWidget, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import json
import os
from pathlib import Path

class CustomModelDialog(QDialog):
    """
    自定义模型对话框，用于创建和编辑用户自定义的地震速度模型
    """
    
    # 定义信号，当新模型创建或现有模型修改时发出
    model_changed = pyqtSignal(str)
    
    def __init__(self, parent=None, existing_model_data=None):
        """
        初始化对话框
        
        参数:
        parent: 父窗口
        existing_model_data: 现有模型数据(如果是编辑模式)
        """
        super(CustomModelDialog, self).__init__(parent)
        
        # 初始化数据
        self.is_edit_mode = existing_model_data is not None
        
        # 设置默认模型数据
        self.model_data = existing_model_data or {
            "name": "",
            "description": "",
            "source": "用户自定义模型",
            "parameters": {
                "earth_radius": {
                    "value": 6371.0,
                    "unit": "km",
                    "description": "地球半径"
                },
                "cmb_depth": {
                    "value": 2891.0,
                    "unit": "km",
                    "description": "核幔边界深度"
                },
                "icb_depth": {
                    "value": 5150.0,
                    "unit": "km",
                    "description": "内外核边界深度"
                },
                "moho_depth": {
                    "value": 35.0,
                    "unit": "km",
                    "description": "莫霍面深度"
                }
            },
            "layers": []
        }
        
        # 设置窗口属性
        self.setWindowTitle("自定义速度模型" if not self.is_edit_mode else "编辑速度模型")
        self.setMinimumSize(800, 600)
        
        # 初始化组件
        self.init_components()
        
        # 设置布局
        self.init_layout()
        
        # 加载数据(如果是编辑模式)
        if self.is_edit_mode:
            self.load_model_data()
    
    def init_components(self):
        """初始化界面组件"""
        # 基本信息部分
        self.name_input = QLineEdit()
        self.description_input = QTextEdit()
        self.source_input = QLineEdit()
        
        # 模板选择
        self.template_label = QLabel("从现有模型导入:")
        self.template_combo = QComboBox()
        self.template_combo.addItem("-- 选择模板 --")
        self.load_template_btn = QPushButton("导入模板")
        self.load_template_btn.clicked.connect(self.load_selected_template)
        
        # 参数表格
        self.params_table = QTableWidget(0, 3)
        self.params_table.setHorizontalHeaderLabels(["参数", "值", "单位"])
        self.params_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # 层数据表格
        self.layers_table = QTableWidget(0, 4)
        self.layers_table.setHorizontalHeaderLabels(["深度(km)", "P波速度(km/s)", "S波速度(km/s)", "密度(g/cm³)"])
        self.layers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # 添加/删除层按钮
        self.add_layer_btn = QPushButton("添加层")
        self.delete_layer_btn = QPushButton("删除选中层")
        self.add_layer_btn.clicked.connect(self.add_layer)
        self.delete_layer_btn.clicked.connect(self.delete_layer)
        
        # 导入/导出按钮
        self.import_btn = QPushButton("从文件导入")
        self.export_btn = QPushButton("导出到文件")
        self.import_btn.clicked.connect(self.import_from_file)
        self.export_btn.clicked.connect(self.export_to_file)
        
        # 确定/取消按钮
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        # 初始化默认参数
        self.init_default_params()
    
    def init_default_params(self):
        """初始化默认参数表格"""
        # 添加默认参数行
        params = [
            ("地球半径", "6371.0", "km"),
            ("莫霍面深度", "35.0", "km"),
            ("核幔边界深度", "2891.0", "km"),
            ("内外核边界深度", "5150.0", "km")
        ]
        
        for param_name, value, unit in params:
            row = self.params_table.rowCount()
            self.params_table.insertRow(row)
            self.params_table.setItem(row, 0, QTableWidgetItem(param_name))
            self.params_table.setItem(row, 1, QTableWidgetItem(value))
            self.params_table.setItem(row, 2, QTableWidgetItem(unit))
    
    def init_layout(self):
        """初始化界面布局"""
        main_layout = QVBoxLayout()
        
        # 基本信息部分
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout()
        info_layout.addRow("模型名称:", self.name_input)
        info_layout.addRow("描述:", self.description_input)
        info_layout.addRow("来源:", self.source_input)
        info_group.setLayout(info_layout)
        
        # 模板选择部分
        template_group = QGroupBox("模板选择")
        template_layout = QHBoxLayout()
        template_layout.addWidget(self.template_label)
        template_layout.addWidget(self.template_combo, 1)
        template_layout.addWidget(self.load_template_btn)
        template_group.setLayout(template_layout)
        
        # 参数部分
        params_group = QGroupBox("模型参数")
        params_layout = QVBoxLayout()
        params_layout.addWidget(self.params_table)
        params_group.setLayout(params_layout)
        
        # 层数据部分
        layers_group = QGroupBox("层数据")
        layers_layout = QVBoxLayout()
        
        # 添加/删除层按钮布局
        layer_btn_layout = QHBoxLayout()
        layer_btn_layout.addWidget(self.add_layer_btn)
        layer_btn_layout.addWidget(self.delete_layer_btn)
        
        layers_layout.addLayout(layer_btn_layout)
        layers_layout.addWidget(self.layers_table)
        layers_group.setLayout(layers_layout)
        
        # 导入/导出按钮布局
        io_layout = QHBoxLayout()
        io_layout.addWidget(self.import_btn)
        io_layout.addWidget(self.export_btn)
        
        # 确定/取消按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        # 添加所有组件到主布局
        main_layout.addWidget(info_group)
        main_layout.addWidget(template_group)
        main_layout.addWidget(params_group)
        main_layout.addWidget(layers_group)
        main_layout.addLayout(io_layout)
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
    
    def load_model_data(self, model_data=None):
        """
        从模型数据加载到界面
        
        参数:
        model_data: 模型数据字典，如果为None则使用self.model_data
        """
        try:
            # 如果提供了model_data，则更新self.model_data
            if model_data is not None:
                self.model_data = model_data
                
            if not self.model_data:
                return
                
            # 清空所有表格
            self.params_table.setRowCount(0)
            self.layers_table.setRowCount(0)
                
            # 基本信息
            self.name_input.setText(self.model_data.get("name", ""))
            self.description_input.setText(self.model_data.get("description", ""))
            self.source_input.setText(self.model_data.get("source", "用户自定义模型"))
            
            # 添加参数到表格
            params = self.model_data.get("parameters", {})
            param_list = [
                {"name": "earth_radius", "display": "地球半径", "default": 6371.0, "unit": "km"},
                {"name": "moho_depth", "display": "莫霍面深度", "default": 35.0, "unit": "km"},
                {"name": "cmb_depth", "display": "核幔边界深度", "default": 2891.0, "unit": "km"},
                {"name": "icb_depth", "display": "内外核边界深度", "default": 5150.0, "unit": "km"}
            ]
            
            # 设置参数表格行数
            self.params_table.setRowCount(len(param_list))
            
            # 填充参数表格
            for i, param in enumerate(param_list):
                # 参数名称
                name_item = QTableWidgetItem(param["display"])
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 设置为不可编辑
                self.params_table.setItem(i, 0, name_item)
                
                # 参数值
                value = params.get(param["name"], {})
                if isinstance(value, dict) and "value" in value:
                    param_value = value["value"]
                elif isinstance(value, (int, float)):
                    param_value = value
                else:
                    param_value = param["default"]
                
                value_item = QTableWidgetItem(str(param_value))
                self.params_table.setItem(i, 1, value_item)
                
                # 参数单位
                unit_item = QTableWidgetItem(param["unit"])
                unit_item.setFlags(unit_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 设置为不可编辑
                self.params_table.setItem(i, 2, unit_item)
            
            # 添加层数据到表格
            layers = self.model_data.get("layers", [])
            if layers:
                # 设置层表格行数
                self.layers_table.setRowCount(len(layers))
                
                # 填充层表格
                for i, layer in enumerate(layers):
                    # 深度
                    depth_item = QTableWidgetItem(str(layer.get("depth", 0)))
                    self.layers_table.setItem(i, 0, depth_item)
                    
                    # P波速度
                    vp_item = QTableWidgetItem(str(layer.get("vp", 0)))
                    self.layers_table.setItem(i, 1, vp_item)
                    
                    # S波速度
                    vs_item = QTableWidgetItem(str(layer.get("vs", 0)))
                    self.layers_table.setItem(i, 2, vs_item)
                    
                    # 密度
                    density_item = QTableWidgetItem(str(layer.get("density", 0)))
                    self.layers_table.setItem(i, 3, density_item)
            else:
                # 如果没有层数据，添加一个默认行
                self.add_layer()
            
            # 调整表格列宽以适应内容
            self.params_table.resizeColumnsToContents()
            self.layers_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"加载模型数据时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _format_tables(self):
        """美化表格显示"""
        # 设置参数表格行高
        for row in range(self.params_table.rowCount()):
            self.params_table.setRowHeight(row, 25)
            
            # 设置单元格颜色
            for col in range(self.params_table.columnCount()):
                item = self.params_table.item(row, col)
                if item:
                    # 参数名列使用浅蓝色背景
                    if col == 0:
                        item.setBackground(QColor(230, 240, 250))
                    # 参数值列使用白色背景
                    elif col == 1:
                        item.setBackground(QColor(255, 255, 255))
                    # 单位列使用浅灰色背景
                    else:
                        item.setBackground(QColor(245, 245, 245))
        
        # 设置层表格行高和颜色
        for row in range(self.layers_table.rowCount()):
            self.layers_table.setRowHeight(row, 25)
            
            # 交替行颜色
            bg_color = QColor(240, 240, 250) if row % 2 == 0 else QColor(255, 255, 255)
            
            for col in range(self.layers_table.columnCount()):
                item = self.layers_table.item(row, col)
                if item:
                    item.setBackground(bg_color)
    
    def add_layer(self):
        """添加新层"""
        row = self.layers_table.rowCount()
        self.layers_table.insertRow(row)
        
        # 设置默认值
        depth = 0
        if row > 0:
            # 如果已经有行，取最后一行的深度加100
            last_depth_item = self.layers_table.item(row-1, 0)
            if last_depth_item and last_depth_item.text():
                try:
                    depth = float(last_depth_item.text()) + 100
                except ValueError:
                    depth = 100
        
        self.layers_table.setItem(row, 0, QTableWidgetItem(str(depth)))
        self.layers_table.setItem(row, 1, QTableWidgetItem("8.0"))  # 默认P波速度
        self.layers_table.setItem(row, 2, QTableWidgetItem("4.5"))  # 默认S波速度
        self.layers_table.setItem(row, 3, QTableWidgetItem("3.3"))  # 默认密度
    
    def delete_layer(self):
        """删除选中的层"""
        selected_rows = set(index.row() for index in self.layers_table.selectedIndexes())
        for row in sorted(selected_rows, reverse=True):
            self.layers_table.removeRow(row)
    
    def add_standard_layers(self, layer_type):
        """添加标准层"""
        if layer_type == "crust":
            standard_layers = [
                (0.0, 5.8, 3.2, 2.6, "地壳顶部"),
                (15.0, 6.5, 3.7, 2.9, "地壳中部"),
                (35.0, 8.04, 4.47, 3.32, "莫霍面")
            ]
        elif layer_type == "mantle":
            standard_layers = [
                (100.0, 8.05, 4.45, 3.4, "上地幔"),
                (410.0, 9.0, 4.9, 3.7, "410km不连续面"),
                (660.0, 10.3, 5.6, 4.0, "660km不连续面"),
                (1000.0, 11.2, 6.2, 4.5, "下地幔"),
                (2000.0, 12.5, 6.8, 5.0, "下地幔"),
                (2891.0, 13.7, 7.2, 5.5, "核幔边界")
            ]
        elif layer_type == "core":
            standard_layers = [
                (2891.0, 13.7, 7.2, 5.5, "核幔边界"),
                (2891.1, 8.0, 0.0, 9.9, "外核顶部"),
                (4000.0, 9.5, 0.0, 11.0, "外核中部"),
                (5150.0, 10.9, 0.0, 12.2, "内外核边界"),
                (5150.1, 11.0, 3.5, 12.7, "内核顶部"),
                (6371.0, 11.3, 3.7, 13.0, "地球中心")
            ]
        
        for depth, vp, vs, density, desc in standard_layers:
            row = self.layers_table.rowCount()
            self.layers_table.insertRow(row)
            self.layers_table.setItem(row, 0, QTableWidgetItem(str(depth)))
            self.layers_table.setItem(row, 1, QTableWidgetItem(str(vp)))
            self.layers_table.setItem(row, 2, QTableWidgetItem(str(vs)))
            self.layers_table.setItem(row, 3, QTableWidgetItem(str(density)))
            self.layers_table.setItem(row, 4, QTableWidgetItem(desc))
    
    def get_model_data(self):
        """收集表单和表格数据到模型数据结构"""
        # 基本信息
        model_name = self.name_input.text().strip()
        if not model_name:
            QMessageBox.warning(self, "错误", "请输入模型名称")
            return None
        
        self.model_data["name"] = model_name
        self.model_data["description"] = self.description_input.toPlainText().strip()
        self.model_data["source"] = self.source_input.text().strip() or "用户自定义模型"
        
        # 安全获取参数值的辅助函数
        def safe_float(row, col, default_value):
            item = self.params_table.item(row, col)
            if item and item.text().strip():
                try:
                    return float(item.text().strip())
                except ValueError:
                    return default_value
            return default_value
        
        # 参数
        self.model_data["parameters"] = {
            "earth_radius": {
                "value": safe_float(0, 1, 6371.0),
                "unit": "km",
                "description": "地球半径"
            },
            "moho_depth": {
                "value": safe_float(1, 1, 35.0),
                "unit": "km",
                "description": "莫霍面深度"
            },
            "cmb_depth": {
                "value": safe_float(2, 1, 2891.0),
                "unit": "km",
                "description": "核幔边界深度"
            },
            "icb_depth": {
                "value": safe_float(3, 1, 5150.0),
                "unit": "km",
                "description": "内外核边界深度"
            }
        }
        
        # 层数据
        layers = []
        try:
            for row in range(self.layers_table.rowCount()):
                # 安全获取每个单元格的值
                depth_item = self.layers_table.item(row, 0)
                vp_item = self.layers_table.item(row, 1)
                vs_item = self.layers_table.item(row, 2)
                density_item = self.layers_table.item(row, 3)
                
                # 检查单元格是否存在且有值
                if not depth_item or not depth_item.text().strip():
                    continue  # 跳过没有深度值的行
                
                try:
                    depth = float(depth_item.text().strip())
                    vp = float(vp_item.text().strip()) if vp_item and vp_item.text().strip() else 0.0
                    vs = float(vs_item.text().strip()) if vs_item and vs_item.text().strip() else 0.0
                    density = float(density_item.text().strip()) if density_item and density_item.text().strip() else 0.0
                    
                    layer = {
                        "depth": depth,
                        "vp": vp,
                        "vs": vs,
                        "density": density,
                        "description": ""  # 描述字段已移除
                    }
                    layers.append(layer)
                except ValueError as e:
                    # 记录具体哪行出现问题，但不中断处理
                    print(f"第{row+1}行数据格式错误: {e}")
                    continue
        except Exception as e:
            QMessageBox.warning(self, "错误", f"处理层数据时出错: {str(e)}")
            return None
        
        # 如果没有有效的层数据，添加一个默认层
        if not layers:
            layers.append({
                "depth": 0.0,
                "vp": 5.5,
                "vs": 3.0,
                "density": 2.7,
                "description": "默认层"
            })
        
        self.model_data["layers"] = layers
        
        return self.model_data
    
    def accept(self):
        """确认按钮点击事件处理"""
        # 保存模型
        self.save_model()
        # 注意：save_model成功时会自动调用super().accept()，所以这里不需要再调用

    def save_model(self):
        """保存模型"""
        model_data = self.get_model_data()
        if not model_data:
            return False
        
        # 确保目录存在
        models_dir = Path("./Models/data/velocity_models")
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建文件名
        model_name = model_data["name"]
        filename = models_dir / f"{model_name.lower().replace(' ', '_')}.json"
        
        # 检查是否覆盖现有文件
        if filename.exists() and not self.is_edit_mode:
            reply = QMessageBox.question(
                self, 
                "确认覆盖", 
                f"文件 {filename} 已存在，是否覆盖?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False
        
        # 保存文件
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(model_data, f, ensure_ascii=False, indent=4)
            
            QMessageBox.information(self, "成功", f"模型已保存到 {filename}")
            
            # 发出信号通知模型已更改
            self.model_changed.emit(model_name)
            
            # 调用父类的accept方法关闭对话框
            super().accept()
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存模型失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def export_model(self):
        """导出模型为JSON文件"""
        model_data = self.get_model_data()
        if not model_data:
            return
        
        # 打开文件对话框
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "导出模型",
            "",
            "JSON文件 (*.json)"
        )
        
        if not filename:
            return
        
        # 保存文件
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(model_data, f, ensure_ascii=False, indent=4)
            
            QMessageBox.information(self, "成功", f"模型已导出到 {filename}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出模型失败: {str(e)}")
    
    def import_model(self):
        """导入JSON模型文件"""
        # 打开文件对话框
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "导入模型",
            "",
            "JSON文件 (*.json)"
        )
        
        if not filename:
            return
        
        # 读取文件
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
            
            # 验证模型格式
            if not isinstance(model_data, dict) or "name" not in model_data or "layers" not in model_data:
                raise ValueError("无效的模型格式")
            
            # 更新模型数据
            self.model_data = model_data
            
            # 更新界面
            self.load_model_data()
            
            QMessageBox.information(self, "成功", f"已导入模型 {model_data.get('name', '')}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入模型失败: {str(e)}")
    
    def add_existing_models_to_combo(self):
        """添加现有模型到模板选择下拉框"""
        try:
            # 获取模型目录
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    "Models", "data", "velocity_models")
            
            # 检查目录是否存在
            if not os.path.exists(models_dir):
                return
            
            # 加载所有JSON模型文件
            model_files = [f for f in os.listdir(models_dir) if f.endswith('.json')]
            
            # 添加到下拉框
            for model_file in model_files:
                try:
                    file_path = os.path.join(models_dir, model_file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        model_data = json.load(f)
                    
                    # 获取模型名称
                    model_name = model_data.get('name')
                    if model_name:
                        self.template_combo.addItem(f"导入: {model_name}")
                except:
                    pass
            
            # 添加ObsPy标准模型
            standard_models = ["iasp91", "ak135", "prem", "jb", "sp6", "1066a", "herrin"]
            for model in standard_models:
                self.template_combo.addItem(f"ObsPy: {model}")
                
        except Exception as e:
            print(f"添加现有模型到下拉框失败: {e}")
    
    def apply_template(self):
        """从选定的模板加载模型"""
        template_name = self.template_combo.currentText()
        
        # 检查是否选择了模板
        if template_name == "选择模板..." or template_name == "--- 现有模型 ---":
            return
            
        # 处理预设模板
        if template_name == "标准地壳模型":
            self.model_data = {
                "name": self.name_input.text() or "标准地壳模型",
                "description": "标准地壳分层模型",
                "source": "预设模板",
                "parameters": self.model_data["parameters"],
                "layers": []
            }
            self.add_standard_layers("crust")
            self.load_model_data()
            QMessageBox.information(self, "成功", "已加载标准地壳模型模板")
            return
        
        elif template_name == "上地幔模型" or template_name == "下地幔模型":
            self.model_data = {
                "name": self.name_input.text() or template_name,
                "description": f"{template_name}分层模型",
                "source": "预设模板",
                "parameters": self.model_data["parameters"],
                "layers": []
            }
            self.add_standard_layers("mantle")
            self.load_model_data()
            QMessageBox.information(self, "成功", f"已加载{template_name}模板")
            return
            
        elif template_name == "外核模型" or template_name == "内核模型":
            self.model_data = {
                "name": self.name_input.text() or template_name,
                "description": f"{template_name}分层模型",
                "source": "预设模板",
                "parameters": self.model_data["parameters"],
                "layers": []
            }
            self.add_standard_layers("core")
            self.load_model_data()
            QMessageBox.information(self, "成功", f"已加载{template_name}模板")
            return
        
        # 处理导入现有模型
        if template_name.startswith("导入:"):
            model_name = template_name[4:].strip()
            self.load_existing_model(model_name)
            return
            
        # 处理ObsPy模型
        if template_name.startswith("ObsPy:"):
            model_name = template_name[6:].strip()
            self.load_obspy_model(model_name)
            return
    
    def load_existing_model(self, model_name):
        """加载现有自定义模型"""
        try:
            # 获取模型目录
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    "Models", "data", "velocity_models")
            
            # 尝试不同的文件名格式
            file_path = os.path.join(models_dir, f"{model_name}.json")
            if not os.path.exists(file_path):
                file_path = os.path.join(models_dir, f"{model_name.lower()}.json")
            if not os.path.exists(file_path):
                file_path = os.path.join(models_dir, f"{model_name.lower().replace(' ', '_')}.json")
                
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "错误", f"找不到模型 {model_name} 的数据文件")
                return
                
            # 读取模型数据
            with open(file_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
            
            # 修改模型名称，避免覆盖原模型
            if self.name_input.text():
                model_data["name"] = self.name_input.text()
            else:
                model_data["name"] = f"自定义_{model_name}"
                
            # 更新来源信息
            model_data["source"] = f"基于 {model_name} 修改"
            
            # 更新模型数据
            self.model_data = model_data
            
            # 更新界面
            self.load_model_data()
            
            QMessageBox.information(self, "成功", f"已导入模型 {model_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入模型 {model_name} 失败: {str(e)}")
    
    def load_obspy_model(self, model_name):
        """尝试加载ObsPy模型作为模板"""
        try:
            # 先检查ObsPy能否正常导入
            import obspy
            from obspy.taup import TauPyModel
            
            # 创建模型实例
            taup_model = TauPyModel(model=model_name)
            
            # 获取模型信息
            # 注意：ObsPy模型不直接提供层数据，需要手动构建
            
            # 创建基本模型数据
            if self.name_input.text():
                model_name_custom = self.name_input.text()
            else:
                model_name_custom = f"自定义_{model_name}"
                
            self.model_data = {
                "name": model_name_custom,
                "description": f"基于ObsPy {model_name}模型创建的自定义模型",
                "source": f"ObsPy {model_name}",
                "parameters": {
                    "earth_radius": {
                        "value": 6371.0,
                        "unit": "km",
                        "description": "地球半径"
                    },
                    "moho_depth": {
                        "value": 35.0,
                        "unit": "km",
                        "description": "莫霍面深度"
                    },
                    "cmb_depth": {
                        "value": 2891.0,
                        "unit": "km",
                        "description": "核幔边界深度"
                    },
                    "icb_depth": {
                        "value": 5150.0,
                        "unit": "km",
                        "description": "内外核边界深度"
                    }
                },
                "layers": []
            }
            
            # 根据不同模型添加典型层
            if model_name == "iasp91" or model_name == "ak135":
                # 添加典型的地壳层
                self.add_standard_layers("crust")
                # 添加典型的地幔层
                self.add_standard_layers("mantle")
                # 添加典型的地核层
                self.add_standard_layers("core")
            elif model_name == "prem":
                # PREM模型有更详细的分层
                self.add_standard_layers("crust")
                self.add_standard_layers("mantle")
                self.add_standard_layers("core")
            else:
                # 其他模型使用通用层
                self.add_standard_layers("crust")
                self.add_standard_layers("mantle")
                self.add_standard_layers("core")
            
            # 更新界面
            self.load_model_data()
            
            QMessageBox.information(self, "成功", f"已加载ObsPy {model_name}模型模板")
            
        except ImportError:
            QMessageBox.warning(self, "警告", "ObsPy未安装或导入失败，无法加载ObsPy模型")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载ObsPy模型失败: {str(e)}")

    def set_available_templates(self, models):
        """
        设置可用的模型模板
        
        参数:
        models: 可用模型名称列表
        """
        self.template_combo.clear()
        self.template_combo.addItem("-- 选择模板 --")
        for model_name in models:
            self.template_combo.addItem(model_name)
    
    def load_selected_template(self):
        """从选择的模板加载数据"""
        template_name = self.template_combo.currentText()
        
        if template_name == "-- 选择模板 --":
            QMessageBox.warning(self, "警告", "请先选择一个模板模型")
            return
        
        try:
            # 构建模型文件路径
            models_dir = Path("./Models/data/velocity_models")
            filename = models_dir / f"{template_name.lower().replace(' ', '_')}.json"
            
            if filename.exists():
                # 直接从文件加载
                with open(filename, 'r', encoding='utf-8') as f:
                    model_data = json.load(f)
                    
                # 保留用户输入的名称和描述
                user_name = self.name_input.text()
                user_desc = self.description_input.toPlainText()
                
                # 如果用户已经输入了名称和描述，则保留用户输入的值
                if user_name:
                    model_data["name"] = user_name
                else:
                    # 如果用户没有输入名称，为了防止与模板同名，添加"Copy of"前缀
                    model_data["name"] = f"Copy of {template_name}"
                    self.name_input.setText(model_data["name"])
                
                if user_desc:
                    model_data["description"] = user_desc
                else:
                    if "description" in model_data:
                        model_data["description"] = f"{model_data['description']} (复制自{template_name})"
                    else:
                        model_data["description"] = f"复制自{template_name}"
                    self.description_input.setText(model_data["description"])
                
                # 设置来源
                if "source" in model_data:
                    model_data["source"] = f"{model_data['source']} (用户自定义)"
                else:
                    model_data["source"] = "用户自定义 (基于" + template_name + ")"
                
                # 加载完整模型数据到界面
                self.load_model_data(model_data)
                
                # 显示成功提示
                QMessageBox.information(self, "成功", f"已成功导入模板 {template_name}")
            else:
                QMessageBox.warning(self, "错误", f"找不到模板文件: {filename}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "错误", f"导入模板失败: {str(e)}")

    def import_from_file(self):
        """从JSON文件导入模型数据"""
        try:
            # 打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入模型数据", "", "JSON文件 (*.json);;所有文件 (*.*)"
            )
            
            if not file_path:
                return  # 用户取消了操作
                
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
                
            # 验证数据格式
            if not isinstance(model_data, dict) or "name" not in model_data:
                QMessageBox.warning(self, "错误", "无效的模型数据格式")
                return
                
            # 加载数据到界面
            self.load_model_data(model_data)
            
            QMessageBox.information(self, "成功", f"已从文件导入模型数据: {model_data.get('name', '未命名')}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导入模型数据失败: {str(e)}")
            print(f"导入模型数据失败: {e}")
            import traceback
            traceback.print_exc()
    
    def export_to_file(self):
        """导出模型数据到JSON文件"""
        try:
            # 获取当前模型数据
            model_data = self.get_model_data()
            if not model_data:
                return
                
            # 打开文件保存对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出模型数据", f"{model_data['name']}.json", "JSON文件 (*.json);;所有文件 (*.*)"
            )
            
            if not file_path:
                return  # 用户取消了操作
                
            # 保存为JSON文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(model_data, f, ensure_ascii=False, indent=2)
                
            QMessageBox.information(self, "成功", f"模型数据已导出到: {file_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出模型数据失败: {str(e)}")
            print(f"导出模型数据失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = CustomModelDialog()
    dialog.show()
    sys.exit(app.exec())