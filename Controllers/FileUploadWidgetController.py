# controllers.py
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from Models.TraceFile import TraceFile
from Models.speed_model.model_manager import ModelManager
from Views.FileUploadWidget import FileUploadWidget
import matplotlib.pyplot as plt
import traceback
# 隐藏工具栏
#plt.rcParams['toolbar'] = 'None'
class FileUploadWidgetController:
    def __init__(self, view: FileUploadWidget):
        # 获取 view 和 model
        self.view = view
        self.trace_file = TraceFile()  # 单例模式，获取同一个实例
        self.model_manager = ModelManager()  # 添加模型管理器引用

        # 绑定事件
        self.view.upload_wave_button.clicked.connect(self.handle_wave_file_upload)
        self.view.upload_detector_button.clicked.connect(self.handle_detector_file_upload)
        self.view.show_position_button.clicked.connect(self.plot_3d)
        
        # 设置历史表格单元格点击事件
        self.view.history_table.cellClicked.connect(self.handle_history_cell_click)

    # 确保模型已初始化
    def _ensure_model_initialized(self):
        """确保模型已经初始化，防止闪退"""
        try:
            # 获取当前模型并确保它已初始化
            current_model = self.model_manager.get_current_model()
            
            # 进行一个简单的计算以验证模型是否可用
            test_result = current_model.calculate_time_delay(
                source_pos=(0, 0, 1000),
                receiver_pos=(1000, 0, 0),
                phase="P"
            )
            
            print(f"模型初始化测试: {current_model.model_name}, 测试计算结果: {test_result}")
            return True
        except Exception as e:
            print(f"模型初始化失败: {e}")
            print(traceback.format_exc())
            
            # 尝试回退到简单模型
            try:
                success = self.model_manager.set_current_model("simple")
                if success:
                    print("已回退到简单模型")
                    return True
            except:
                pass
                
            return False
        
    def plot_3d(self):
        """
        点击按钮后弹出新的窗口展示检波器位置的3D图
        """
        # 首先确保模型已初始化，这是为了避免显示3D图时的闪退问题
        if not self._ensure_model_initialized():
            QMessageBox.warning(
                self.view, 
                "准备中",
                "系统正在准备中，请先在设置中选择并应用速度模型后再试。"
            )
            return
        
        try:
            # 检查数据是否已加载
            detector_positions = self.trace_file.get_detector_location()
            
            # 提取位置
            x = detector_positions['x']
            y = detector_positions['y']
            z = detector_positions['z']
            
            # 验证数据有效性
            if len(x) == 0 or len(y) == 0 or len(z) == 0:
                QMessageBox.warning(self.view, "警告", "检波器位置数据为空!")
                return
            
            # 安全创建图形
            try:
                # 创建新窗口
                fig = plt.figure(figsize=(10, 8))
                ax = fig.add_subplot(111, projection='3d')
                
                # 绘制检波器的位置
                scatter = ax.scatter(x, y, z, s=10)
                
                # 设置z轴从小到大显示
                ax.set_zlim(z.max(), z.min())  # 设置z轴范围，确保从小到大
                
                # 添加标题和坐标轴标签
                ax.set_title('检波器位置三维图')
                ax.set_xlabel('X 坐标')
                ax.set_ylabel('Y 坐标')
                ax.set_zlabel('深度 (Z 坐标)')
                
                # 显示图形（使用非阻塞模式）
                plt.show(block=False)
            except Exception as e:
                print(f"创建3D图表时出错: {e}")
                print(traceback.format_exc())
                QMessageBox.warning(self.view, "警告", f"创建3D图表失败: {str(e)}")
                
        except Exception as e:
            print(f"获取检波器位置数据时出错: {e}")
            print(traceback.format_exc())
            QMessageBox.warning(self.view, "警告", str(e))
            return
    
    # 处理波形文件上传事件
    def handle_wave_file_upload(self):
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(self.view, "选择波形文件", "", "波形文件 (*.sgy *.segy);;所有文件 (*)")
        if not file_path:
            return
        
        try:
            # 重置TraceFile实例，确保每次上传都是新的数据
            TraceFile.reset_instance()
            
            # 加载波形数据文件
            self.trace_file.load_wave_data(file_path)
            # 读取并设置基本文件信息
            self.view.show_file_info(
                self.trace_file.get_wave_file_info()
            )
            QMessageBox.information(self.view, "成功", "波形数据加载成功！")
            
            # 添加到历史记录
            self.view.add_history_item(file_path, "信号文件")
        except Exception as e:
            print(f"加载波形数据文件失败: {e}")
            print(traceback.format_exc())
            QMessageBox.warning(self.view, "警告", str(e))
            self.view.file_info_label.setText(str(e))
    
    # 处理检测器位置文件上传事件
    def handle_detector_file_upload(self):
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(self.view, "选择检测器位置文件", "", "Excel文件 (*.xlsx);;所有文件 (*)")
        if not file_path:
            return
        
        try:
            # 加载位置数据文件
            self.trace_file.load_location_data(file_path)
            # 读取并设置位置信息
            self.view.show_location_info(
                self.trace_file.get_detector_location()
            )
            QMessageBox.information(self.view, "成功", "检测器位置数据加载成功！")
            
            # 添加到历史记录
            self.view.add_history_item(file_path, "位置数据")
        except Exception as e:
            print(f"加载位置数据文件失败: {e}")
            print(traceback.format_exc())
            QMessageBox.warning(self.view, "警告", str(e))
            self.view.position_label.setText(str(e))
            
    # 处理历史记录表格单元格点击
    def handle_history_cell_click(self, row, column):
        if column == 2:  # 点击了"重新加载"按钮所在的列
            try:
                # 获取文件名和类型
                filename = self.view.history_table.item(row, 0).text()
                filetype = self.view.history_table.item(row, 1).text()
                
                # 根据文件类型执行不同的加载操作
                if filetype == "信号文件":
                    # 重置TraceFile实例，确保每次重新加载都是新的数据
                    TraceFile.reset_instance()
                    
                    self.trace_file.load_wave_data(filename)
                    self.view.show_file_info(self.trace_file.get_wave_file_info())
                    QMessageBox.information(self.view, "成功", f"成功重新加载信号文件: {filename}")
                elif filetype == "位置数据":
                    self.trace_file.load_location_data(filename)
                    self.view.show_location_info(self.trace_file.get_detector_location())
                    QMessageBox.information(self.view, "成功", f"成功重新加载位置数据文件: {filename}")
            except Exception as e:
                QMessageBox.warning(self.view, "警告", f"重新加载文件失败: {str(e)}")