# models.py
import segyio
import os
import threading
import pandas as pd
from Services.ssatop import normalize_data, calculate_source_location, calculate_heatmap
from Services.find_time import get_event_times
from PyQt6.QtCore import QObject
import time

class TraceFile(QObject):
    # 单例模式
    _instance = None
    _lock = threading.Lock()

    basic_info = None
    wave_data = None  # 保存加载的 data 
    location_data = None  # 保存加载的位置信息
    time_range = None


    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(TraceFile, cls).__new__(cls, *args, **kwargs)
            return cls._instance

    @classmethod
    def reset_instance(cls):
        """重置单例实例，用于清除之前加载的数据"""
        with cls._lock:
            if cls._instance:
                # 关闭可能打开的文件
                if hasattr(cls._instance, 'wave_data') and cls._instance.wave_data is not None:
                    try:
                        # 如果是 segyio 对象，尝试关闭它
                        if hasattr(cls._instance.wave_data, 'close'):
                            cls._instance.wave_data.close()
                    except:
                        pass
                
                # 重置实例变量
                cls._instance.basic_info = None
                cls._instance.wave_data = None
                cls._instance.location_data = None
                cls._instance.time_range = None
            
            # 不清空实例引用，只重置数据
            # cls._instance = None


    def show(self):
        print(f"""TraceFile
              {self.basic_info == None}
              {self.wave_data == None}
              {self.location_data == None}
              {self.time_range == None}
        """)

    # 加载波形数据文件
    def load_wave_data(self, wave_file_path: str):
        # 先重置数据，但不重置实例
        if self.wave_data is not None:
            try:
                # 如果是 segyio 对象，尝试关闭它
                if hasattr(self.wave_data, 'close'):
                    self.wave_data.close()
            except:
                pass
        
        # 重置实例变量
        self.basic_info = None
        self.wave_data = None
        self.time_range = None
        
        try:
            segy_file = segyio.open(wave_file_path, 'r', ignore_geometry=True)
        except Exception as e:
            raise Exception(f"无法打开 SEGY 文件：{str(e)}")

        self.wave_data = segy_file.trace
        self.time_range = None
        
        file_name = os.path.basename(wave_file_path)
        trace_count = segy_file.tracecount
        sample_interval = segy_file.header[0][segyio.TraceField.TRACE_SAMPLE_INTERVAL] * 1e-6
        sample_count = segy_file.header[0][segyio.TraceField.TRACE_SAMPLE_COUNT]
        self.basic_info = {
            "file_name": file_name, 
            "trace_count": trace_count, 
            "sample_interval": sample_interval, 
            "sample_count": sample_count
        }
        
        print(f"成功加载波形文件: {file_name}, 共 {trace_count} 条记录")
    

    # 加载位置信息文件
    def load_location_data(self, location_file_path):
        try:
            POSITION = pd.read_excel(location_file_path)
        except Exception as e:
            raise Exception(f"无法打开位置信息文件：{str(e)}")
        
        # 检查是否有 x, y, z 和 trace_number 列
        if not all(col in POSITION.columns for col in ['x', 'y', 'z', 'trace_number']):
            raise Exception("位置信息文件必须包含 x, y, z 和 trace_number 列！")
        
        self.location_data = POSITION
        print(f"成功加载位置信息文件: {os.path.basename(location_file_path)}, 共 {len(POSITION)} 条记录")
    

    # 读取文件信息
    def get_wave_file_info(self):
        if not self.basic_info:
            raise Exception("请先加载 SEGY 文件！")
        
        return self.basic_info
    

    # 读取指定 trace 编号的数据，并进行归一化处理
    def get_wave_data_by_trace_number(self, trace_number):
        """
        返回指定 trace 编号的数据，并进行归一化处理
        """
        # 检查 SEGY 文件是否已加载
        try:
            basic_info = self.get_wave_file_info()
        except Exception as e:
            raise Exception("获取 SEGY 文件信息失败: {e}！")

        # 验证 trace_number 是否在有效范围内
        trace_count = basic_info["trace_count"]
        if trace_number < 0 or trace_number >= trace_count:
            raise Exception(f"Trace 编号超出范围: 0 到 {trace_count - 1}！")

        try:
            # 读取指定 trace 数据
            trace_data = self.wave_data[trace_number]

            # 归一化数据
            normalized_data = normalize_data(trace_data)

            return normalized_data
        except Exception as e:
            raise Exception(f"读取 Trace 数据失败: {e}！")
    
    
    # 预估微地震时间区间
    def get_estimate_earthquake_time(self):
        # 检查是否已预测微地震时间区间
        if self.time_range is None:
            try:
                if self.wave_data is None:
                    raise Exception("请先加载 SEGY 文件！")
                self.time_range = get_event_times(self.wave_data)
            except Exception as e:
                raise Exception(f"预测微地震时间区间失败: {e}！")
            
        return self.time_range
    
    
    # 读取检波器位置信息
    def get_detector_location(self):
        if self.location_data is None:
            raise Exception("请先加载位置信息文件！")
        
        return self.location_data


    # 计算震源源位置
    def get_source_location(self, update_progress, grid_params=None):
        # 先获取预估微地震时间区间
        try:
            time_range = self.get_estimate_earthquake_time()
            
            # 更新进度，表示已完成时间区间估计
            start_time = time.time()
            update_progress(5, start_time, '初始化', None)
        except Exception as e:
            update_progress(100, time.time(), '错误', '错误')
            raise Exception(f"计算震源位置失败: {e}！")
        
        # 计算震源位置
        try:
            # 处理网格参数
            if grid_params is None:
                grid_params = {}
            
            # 从grid_params中获取是否使用遗传算法
            use_genetic = grid_params.get('use_genetic', True)
            
            # 包装进度回调函数，确保参数类型正确
            def progress_wrapper(progress, idx=0, 单位='', 更优的点=None):
                try:
                    # 确保进度是数值类型
                    if isinstance(progress, (int, float)):
                        progress_int = int(progress)
                    else:
                        progress_int = 0
                    
                    # 确保idx是数值或字符串
                    idx_value = 0
                    try:
                        if isinstance(idx, (int, float)):
                            idx_value = idx
                        elif isinstance(idx, str):
                            idx_value = int(idx) if idx.isdigit() else 0
                    except:
                        idx_value = 0
                    
                    # 确保单位是字符串
                    unit_str = str(单位) if 单位 is not None else ''
                    
                    # 调用原始的进度更新函数
                    return update_progress(progress_int, start_time, idx_value, unit_str, 更优的点)
                except Exception as e:
                    print(f"源位置检测进度回调出错: {e}")
                    # 确保即使出错也返回True继续处理
                    return True
            
            result = calculate_source_location(
                self.wave_data, 
                self.location_data, 
                self.basic_info['sample_interval'], 
                time_range,
                progress_wrapper,
                grid_params=grid_params
            )
            
            # 更新最终进度
            update_progress(100, start_time, '完成', '完成')
            
        except Exception as e:
            # 发生错误时，更新进度为100%并显示错误信息
            update_progress(100, time.time(), '错误', '错误')
            raise Exception(f"计算震源位置失败: {e}！")
        
        return result


    # 计算热点图
    def get_source_heatmap(self, update_progress, grid_params=None):
        # 先获取预估微地震时间区间
        try:
            time_range = self.get_estimate_earthquake_time()
            
            # 更新进度，表示已完成时间区间估计
            update_progress(5, 0, '初始化', None)
        except Exception as e:
            update_progress(100, 0, '错误', None)
            raise Exception(f"计算热力图失败: {e}！")
            
        # 计算热力图
        try:
            # 处理网格参数
            if grid_params is None:
                grid_params = {}
                
            # 从grid_params中获取是否使用遗传算法
            use_genetic = grid_params.get('use_genetic', True)
            
            # 更新进度，表示开始计算热力图
            start_time = time.time()
            update_progress(10, start_time, '开始计算', None)
            
            # 包装进度回调函数，确保进度范围在10-95之间
            def progress_wrapper(progress, idx=0, 单位='', 更优的点=None):
                # 将进度映射到10-95之间
                try:
                    # 确保进度是数值类型
                    if isinstance(progress, (int, float)):
                        mapped_progress = 10 + (float(progress) * 0.85)
                        progress_int = int(mapped_progress)
                    else:
                        progress_int = 10
                    
                    # 确保idx是数值或字符串
                    idx_value = 0
                    try:
                        if isinstance(idx, (int, float)):
                            idx_value = idx
                        elif isinstance(idx, str):
                            idx_value = int(idx) if idx.isdigit() else 0
                    except:
                        idx_value = 0
                    
                    # 确保单位是字符串
                    unit_str = str(单位) if 单位 is not None else ''
                    
                    # 调用原始的进度更新函数
                    return update_progress(progress_int, start_time, idx_value, unit_str, 更优的点)
                except Exception as e:
                    print(f"进度回调包装函数出错: {e}")
                    # 确保即使出错也返回True继续处理
                    return True
            
            # 调用计算函数
            result = calculate_heatmap(
                self.wave_data, 
                self.location_data, 
                self.basic_info['sample_interval'], 
                time_range,
                progress_wrapper,  # 使用包装的进度回调
                使用遗传算法=use_genetic,
                grid_params=grid_params
            )
            
            # 更新最终进度
            update_progress(100, start_time, '完成', '点')
            
        except Exception as e:
            # 发生错误时，更新进度为100%并显示错误信息
            update_progress(100, time.time(), '错误', '错误')
            raise Exception(f"计算热力图失败: {e}！")
        
        return result
