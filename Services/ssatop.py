import numpy as np
import pandas as pd
import time
import matplotlib
from functools import lru_cache
from Models.Config import Config
from Models.ModelManager import ModelManager  # 添加模型管理器导入
import platform
import traceback

# 设置matplotlib中文字体支持
system = platform.system()
if system == 'Darwin':  # macOS
    matplotlib.rcParams['font.family'] = 'Arial Unicode MS'
elif system == 'Windows':
    matplotlib.rcParams['font.family'] = 'Microsoft YaHei'
else:
    matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def normalize_data(data):
    """
    对数据进行归一化处理，将数据缩放到 [0, 1] 范围
    """
    data = np.array(data)
    min_val = np.min(data)
    max_val = np.max(data)
    if max_val - min_val == 0:  # 避免除以零的情况
        return np.zeros_like(data)
    normalized_data = (data - min_val) / (max_val - min_val)
    return normalized_data
    

# 振幅归一化
def amp_norm(trace_data):
    data = trace_data
    # 计算基线
    baseline = np.mean(data[:100])
    # 归一化
    data = data - baseline
    # 计算最大振幅
    max_amp = np.max(np.abs(data))
    if max_amp == 0:
        return data
    data = data / max_amp
    return data


def calculate_heatmap(wave_data, location_data, sample_interval, time_range, update_progress, 使用遗传算法=False, grid_params=None):
    """
    计算亮度热图
    
    参数:
    - wave_data: 波形数据
    - location_data: 检波器位置数据
    - sample_interval: 采样间隔
    - time_range: 时间范围
    - update_progress: 进度更新回调函数
    - 使用遗传算法: 是否使用遗传算法优化亮度
    - grid_params: 网格参数
    
    返回:
    - max_point: 最大亮度点坐标和时间 [x, y, z, t]
    - max_slice/max_br: 如果使用网格搜索，返回二维亮度切片；如果使用遗传算法，可选择返回最大亮度值或生成热图
    - grid_x: x轴网格坐标
    - grid_y: y轴网格坐标
    """
    try:
        # 初始化配置和模型管理器
        config = Config()
        model_manager = ModelManager()
        
        try:
            # 从配置文件读取默认值
            speed = float(config.get("Default", "speed"))
            length = int(config.get("Default", "length"))
            height = int(config.get("Default", "height"))
            z_min = int(config.get("Default", "z_min"))
            z_max = int(config.get("Default", "z_max"))
            time_slice = float(config.get("Default", "time_slice"))
            
            # 如果提供了网格参数，则使用提供的值
            if grid_params:
                # 使用提供的网格参数覆盖默认值
                if 'x_grid' in grid_params:
                    length = int(grid_params['x_grid'])
                if 'y_grid' in grid_params:
                    length = int(grid_params['y_grid'])
                if 'z_grid' in grid_params:
                    height = int(grid_params['z_grid'])
                
                print(f"使用自定义网格参数: x网格={length}, y网格={length}, z网格={height}")
                
        except Exception as e:
            raise Exception(f"配置文件读取失败：{e}")
    
        time_range_array = np.arange(time_range['start']-2, time_range['end']+2, time_slice)
        
        # 全局的亮度值缓存，确保遗传算法和网格搜索使用相同的缓存
        brightness_cache = {}
        
        # 振幅归一化
        @lru_cache(maxsize=None)
        def amp_norm(trace_index):
            try:
                data = wave_data[trace_index]
                # 计算基线
                baseline = np.mean(data[:100])
                # 归一化
                data = data - baseline
                # 计算最大振幅
                max_amp = np.max(np.abs(data))
                if max_amp == 0:
                    return data
                data = data / max_amp
                return data
            except Exception as e:
                print(f"振幅归一化错误: {e}")
                return np.zeros(100)  # 返回一个安全的默认值

        # 速度模型 - 使用ModelManager
        @lru_cache(maxsize=None)
        def time_delay(x, y, z, trace_index):
            try:
                # 采样点坐标
                x_s = location_data['x'][trace_index]
                y_s = location_data['y'][trace_index]
                z_s = location_data['z'][trace_index]
                
                # 使用模型管理器计算时间延迟
                try:
                    # 使用当前选择的模型计算时间延迟
                    return model_manager.calculate_time_delay(
                        source_pos=(x, y, z),
                        receiver_pos=(x_s, y_s, z_s),
                        fixed_speed=speed,  # 提供固定速度值作为回退选项
                        phase="P"  # 默认使用P波
                    )
                except Exception as e:
                    # 如果模型计算失败，回退到原始方法
                    print(f"使用模型计算时间延迟失败: {e}，使用简单距离/速度计算")
                    distance = ((x - x_s) ** 2 + (y - y_s) ** 2 + (z - z_s) ** 2) ** 0.5
                    return distance / speed
            except Exception as e:
                print(f"时间延迟计算错误: {e}")
                return 0.0  # 返回一个安全的默认值

        # 计算时窗中不同时刻的权重
        def get_local_max(trace_data, time):
            try:
                point_index = int(time // sample_interval)
                start_index = max(0, point_index - 50)
                end_index = min(len(trace_data), point_index + 51)
                
                # 计算前后50个点的绝对值并获取最大值
                local_max = np.max(np.abs(trace_data[start_index:end_index]))
                
                return local_max
            except Exception as e:
                print(f"计算局部最大值错误: {e}")
                return 0.0  # 返回一个安全的默认值
        
        # 统一的亮度函数，使用全局缓存，确保相同的输入获得相同的输出
        def br(x, y, z, t):
            try:
                # 创建一个唯一的键用于缓存
                key = (round(x, 4), round(y, 4), round(z, 4), round(t, 4))
                
                # 如果已经计算过，直接返回缓存的结果
                if key in brightness_cache:
                    return brightness_cache[key]
                
                # 如果没有缓存，进行计算
                N = len(location_data['trace_number'])
                sum_brightness = 0
                
                for i in range(N):
                    u = get_local_max(amp_norm(location_data['trace_number'][i]), t + time_delay(x, y, z, i))
                    sum_brightness += u
                    
                result = sum_brightness / N
                
                # 存入缓存
                brightness_cache[key] = result
                
                return result
            except Exception as e:
                print(f"亮度计算错误: {e}")
                return 0.0  # 返回一个安全的默认值

        # 暴力搜索计算亮度
        def calculate_brightness():
            try:
                # 得到网格范围
                grid_x = np.arange(location_data['x'].min(), location_data['x'].max() + 1, length)
                grid_y = np.arange(location_data['y'].min(), location_data['y'].max() + 1, length)
                grid_z = np.arange(z_min, z_max, height)

                num_x = len(grid_x)
                num_y = len(grid_y)
                num_z = len(grid_z)

                # 使用广播计算网格点和时间范围的组合
                grid_points = np.array(np.meshgrid(grid_x, grid_y, grid_z, time_range_array)).T.reshape(-1, 4)
                
                # 计算每个网格点和时间片的亮度
                brightness_values = []
                start_time = time.time()
                total_points = len(grid_points)
                
                # 确定更新频率，确保至少有100次进度更新
                update_frequency = max(1, total_points // 100)
                
                for i, (x, y, z, t) in enumerate(grid_points):
                    brightness_values.append(br(x, y, z, t))
                    
                    # 更频繁地更新进度
                    if i % update_frequency == 0 or i == total_points - 1:
                        current_progress = int((i + 1) / total_points * 100)
                        update_progress(current_progress, i, 'points')
                        
                brightness_values = np.array(brightness_values)

                max_index = np.argmax(brightness_values)
                max_point = grid_points[max_index]

                max_slice_index = np.where((grid_points[:, 2] == max_point[2]) & (grid_points[:, 3] == max_point[3]))
                max_slice = brightness_values[max_slice_index].reshape(num_y, num_x)

                print(f'Max point: x: {max_point[0]}, y: {max_point[1]}, z: {max_point[2]}, t: {max_point[3]}')
                return max_point, max_slice, grid_x, grid_y
            except Exception as e:
                print(f"暴力搜索计算错误: {e}")
                traceback.print_exc()
                
                # 创建安全的默认返回值
                grid_x = np.linspace(0, 1000, 10)
                grid_y = np.linspace(0, 1000, 10)
                max_point = np.array([500, 500, 500, 0])
                max_slice = np.ones((10, 10))
                return max_point, max_slice, grid_x, grid_y
        
        # 遗传算法优化亮度
        def calculate_brightness_ga(population_size=300, generations=20, mutation_rate=0.2, tournament_size=3, generate_heatmap=True):
            try:
                grid_x = np.arange(location_data['x'].min(), location_data['x'].max() + 1, length)
                grid_y = np.arange(location_data['y'].min(), location_data['y'].max() + 1, length)
                grid_z = np.arange(z_min, z_max, height)
                grid_t = time_range_array
                
                # 从网格参数中获取遗传算法参数
                if grid_params:
                    if 'population_size' in grid_params:
                        population_size = int(grid_params['population_size'])
                    if 'generations' in grid_params:
                        generations = int(grid_params['generations'])
                    if 'mutation_rate' in grid_params:
                        mutation_rate = float(grid_params['mutation_rate'])
                    
                    print(f"使用自定义遗传算法参数: 种群大小={population_size}, 迭代次数={generations}, 变异率={mutation_rate}")

                # 初始化种群
                # 更好的初始化策略：确保种群覆盖整个搜索空间
                population = np.zeros((population_size, 4))
                # 70%的个体随机分布
                random_population = np.random.uniform(
                    low=[grid_x.min(), grid_y.min(), grid_z.min(), grid_t.min()],
                    high=[grid_x.max(), grid_y.max(), grid_z.max(), grid_t.max()],
                    size=(int(population_size * 0.7), 4)
                )
                population[:int(population_size * 0.7)] = random_population
                
                # 30%的个体在网格点上
                grid_points = np.array(np.meshgrid(
                    np.linspace(grid_x.min(), grid_x.max(), 10),
                    np.linspace(grid_y.min(), grid_y.max(), 10),
                    np.linspace(grid_z.min(), grid_z.max(), 10),
                    np.linspace(grid_t.min(), grid_t.max(), 10)
                )).T.reshape(-1, 4)
                
                if len(grid_points) > 0:
                    grid_indices = np.random.choice(len(grid_points), int(population_size * 0.3), replace=True)
                    population[int(population_size * 0.7):] = grid_points[grid_indices]
        
                fitness_cache = {}
                best_brightness = -np.inf
                best_point = None

                # 记录进度条要用的算法开始时间
                start_time = time.time()

                # 收敛计数器
                convergence_counter = 0
                last_best_brightness = -np.inf

                for generation in range(generations):
                    fitness = np.zeros(population_size)
                    
                    # 用于实时显示更优的点的变量
                    更优的点 = None

                    for idx, ind in enumerate(population):
                        # 直接使用全局统一的亮度函数，不使用局部缓存
                        fitness_val = br(ind[0], ind[1], ind[2], ind[3])
                        fitness[idx] = fitness_val
                    
                        # 更新进度，考虑到总体进度是基于代数的
                        if idx % max(1, population_size // 10) == 0:
                            current_progress = int((generation * population_size + idx) / (generations * population_size) * 100)
                            # 如果当前有最佳点，则传递
                            if best_point is not None:
                                update_progress(current_progress, int(idx), 'evaluations', (best_point, best_brightness))
                            else:
                                update_progress(current_progress, int(idx), 'evaluations')
                    
                    # 更新最佳点
                    max_fitness_idx = np.argmax(fitness)
                    if fitness[max_fitness_idx] > best_brightness:
                        best_brightness = fitness[max_fitness_idx]
                        best_point = population[max_fitness_idx]
                        更优的点 = (best_point, best_brightness)
                        print(f"更新全局最佳点: {best_point}, 亮度: {best_brightness}")
                        
                        # 重置收敛计数器
                        convergence_counter = 0
                    else:
                        # 增加收敛计数器
                        convergence_counter += 1
                    
                    # 检查收敛性 - 如果连续5代没有改进，减小变异率以精细搜索
                    if convergence_counter > 5:
                        mutation_rate = max(0.05, mutation_rate * 0.8)  # 降低变异率但不低于5%
                        print(f"第{generation}代: 连续{convergence_counter}代无改进，减小变异率至{mutation_rate}")
                    
                    # 精英保留策略 - 保留最好的10%个体
                    elite_count = max(1, int(population_size * 0.1))
                    elite_indices = np.argsort(fitness)[-elite_count:]
                    elites = population[elite_indices].copy()

                    # 锦标赛选择
                    parents = []
                    for _ in range(population_size // 2):
                        participants_idx = np.random.choice(population_size, tournament_size, replace=False)
                        winner_idx = participants_idx[np.argmax(fitness[participants_idx])]
                        parents.append(population[winner_idx])

                    parents = np.array(parents)

                    # 交叉操作
                    offspring = []
                    while len(offspring) < population_size - len(parents) - len(elites):
                        parent_indices = np.random.choice(parents.shape[0], 2, replace=False)
                        parent1, parent2 = parents[parent_indices]

                        # 不同的交叉方式
                        if np.random.random() < 0.5:
                            # 单点交叉
                            crossover_point = np.random.randint(1, 4)
                            child1 = np.concatenate([parent1[:crossover_point], parent2[crossover_point:]])
                            child2 = np.concatenate([parent2[:crossover_point], parent1[crossover_point:]])
                        else:
                            # 均匀交叉
                            mask = np.random.random(4) < 0.5
                            child1 = np.where(mask, parent1, parent2)
                            child2 = np.where(mask, parent2, parent1)

                        offspring.append(child1)
                        offspring.append(child2)

                    offspring = np.array(offspring[:population_size - len(parents) - len(elites)])

                    # 变异操作
                    mutation_mask = np.random.rand(*offspring.shape) < mutation_rate
                    # 变异幅度随迭代次数减小
                    mutation_scale = 1.0 - 0.5 * (generation / generations)
                    mutation_values = np.random.uniform(
                        low=[-length * mutation_scale, -length * mutation_scale, -height * mutation_scale, -(time_range_array[1] - time_range_array[0]) * mutation_scale],
                        high=[length * mutation_scale, length * mutation_scale, height * mutation_scale, (time_range_array[1] - time_range_array[0]) * mutation_scale],
                        size=offspring.shape
                    )
                    offspring += mutation_mask * mutation_values

                    # 确保个体在边界内
                    offspring[:, 0] = np.clip(offspring[:, 0], grid_x.min(), grid_x.max())
                    offspring[:, 1] = np.clip(offspring[:, 1], grid_y.min(), grid_y.max())
                    offspring[:, 2] = np.clip(offspring[:, 2], grid_z.min(), grid_z.max())
                    offspring[:, 3] = np.clip(offspring[:, 3], grid_t.min(), grid_t.max())

                    # 新一代种群 - 包含精英
                    population = np.vstack((elites, parents, offspring))

                    # 在每代结束时更新进度条，同时传递更优的点
                    update_progress(int((generation + 1) / generations * 100), int(generation + 1), 'generations', (best_point, best_brightness))

                print(f"遗传算法完成，最佳点: {best_point}, 最大亮度: {best_brightness}")
                
                # 如果不需要生成热图，直接返回最佳点和亮度值
                if not generate_heatmap:
                    return best_point, best_brightness, grid_x, grid_y
                
                # 如果需要热图，为了可视化生成一个二维切片
                update_progress(95, 0, 'generating heatmap')
                
                # 计算与最佳点对应的二维切片
                grid_points = np.array(np.meshgrid(grid_x, grid_y, [best_point[2]], [best_point[3]])).T.reshape(-1, 4)
                brightness_values = np.zeros(len(grid_points))
                
                # 计算网格上每个点的亮度，使用相同的亮度函数
                for i, point in enumerate(grid_points):
                    brightness_values[i] = br(point[0], point[1], point[2], point[3])
                
                # 将亮度值重塑为二维数组
                max_slice = brightness_values.reshape(len(grid_y), len(grid_x))
                
                # 找到最接近遗传算法最佳点的网格点索引
                best_x_idx = np.argmin(np.abs(grid_x - best_point[0]))
                best_y_idx = np.argmin(np.abs(grid_y - best_point[1]))
                
                # 将该点的亮度值设置为遗传算法找到的最大亮度值，确保热图上显示正确的最大亮度
                max_slice[best_y_idx, best_x_idx] = best_brightness
                
                update_progress(100, 0, 'completed')
                
                print(f"最大亮度: {best_brightness}, 时间: {best_point[3]}")
                print(f"最佳点坐标: {best_point[:3]}")
                print(f"在热图中最佳点索引: ({best_y_idx}, {best_x_idx}), 热图中的最大值: {max_slice.max()}")
                
                return best_point, max_slice, grid_x, grid_y
            except Exception as e:
                print(f"遗传算法计算错误: {e}")
                traceback.print_exc()
                
                # 创建安全的默认返回值
                grid_x = np.linspace(0, 1000, 10)
                grid_y = np.linspace(0, 1000, 10)
                max_point = np.array([500, 500, 500, 0])
                max_slice = np.ones((10, 10))
                return max_point, max_slice, grid_x, grid_y
        
        # 根据是否使用遗传算法选择计算方法
        if 使用遗传算法:
            return calculate_brightness_ga(generate_heatmap=True)
        else:
            return calculate_brightness()
                
    except Exception as e:
        print(f"热图计算异常: {e}")
        traceback.print_exc()
        # 创建安全的默认返回值
        grid_x = np.linspace(0, 1000, 10)
        grid_y = np.linspace(0, 1000, 10)
        max_point = np.array([500, 500, 500, 0])
        max_slice = np.ones((10, 10))
        return max_point, max_slice, grid_x, grid_y

    
# 计算震源位置 - 直接调用遗传算法，不生成热图，只返回最优点和最大亮度
def calculate_source_location(wave_data, location_data, sample_interval, time_range, update_progress, grid_params=None):
    """
    计算震源位置 - 专门用于源位置检测，直接使用遗传算法
    
    参数与calculate_heatmap函数相同，但会忽略使用遗传算法的参数，始终使用遗传算法
    
    返回:
    - max_point: 最大亮度点坐标和时间 [x, y, z, t]
    - max_brightness: 最大亮度值
    """
    try:
        # 获取配置和模型参数
        config = Config()
        model_manager = ModelManager()
        
        try:
            # 从配置文件读取默认值
            speed = float(config.get("Default", "speed"))
            length = int(config.get("Default", "length"))
            height = int(config.get("Default", "height"))
            z_min = int(config.get("Default", "z_min"))
            z_max = int(config.get("Default", "z_max"))
            time_slice = float(config.get("Default", "time_slice"))
            
            # 如果提供了网格参数，使用提供的值
            if grid_params:
                if 'x_grid' in grid_params:
                    length = int(grid_params['x_grid'])
                if 'y_grid' in grid_params:
                    length = int(grid_params['y_grid'])
                if 'z_grid' in grid_params:
                    height = int(grid_params['z_grid'])
                
                print(f"源位置检测: 使用自定义网格参数: x网格={length}, y网格={length}, z网格={height}")
                
        except Exception as e:
            raise Exception(f"配置文件读取失败：{e}")
        
        # 创建一个包装的进度回调函数，确保参数格式正确
        def progress_wrapper(progress, idx=0, 单位='', 更优的点=None):
            # 确保progress和idx是合适的类型
            try:
                # 确保progress是整数
                progress = int(progress) if isinstance(progress, (int, float)) else 0
            
            # 确保idx是数值类型
                if isinstance(idx, (int, float)):
                    idx_value = idx
                else:
                    try:
                        idx_value = int(idx) if isinstance(idx, str) and idx.isdigit() else 0
                    except:
                        idx_value = 0
                
                # 确保单位是字符串
                unit_str = str(单位) if 单位 is not None else ''
                
                # 确保更优的点格式正确
                if 更优的点 is not None:
                    if isinstance(更优的点, tuple) and len(更优的点) >= 2:
                        # 保持原始格式
                        better_point = 更优的点
                    else:
                        print(f"更优的点格式不正确: {type(更优的点)}")
                        better_point = None
                else:
                    better_point = None
            
                # 调用原始回调函数
                return update_progress(progress, idx_value, unit_str, better_point)
            except Exception as e:
                print(f"源位置进度回调处理错误: {e}")
                # 返回True以继续处理
                return True

        # 使用calculate_heatmap内的遗传算法函数，但不生成热图
        # 创建内部辅助函数来重用代码
        def _run_ga():
            # 确保遗传算法参数被正确传递
            ga_params = {}
            if grid_params:
                if 'population_size' in grid_params:
                    ga_params['population_size'] = grid_params['population_size']
                if 'generations' in grid_params:
                    ga_params['generations'] = grid_params['generations']
                if 'mutation_rate' in grid_params:
                    ga_params['mutation_rate'] = grid_params['mutation_rate']
            
            # 复用calculate_heatmap的代码，但只获取最佳点和最大亮度
            result = calculate_heatmap(
                wave_data, 
                location_data, 
                sample_interval, 
                time_range, 
                progress_wrapper,
                使用遗传算法=True, # 强制使用遗传算法
                grid_params=grid_params
            )
            
            # 从结果中提取最佳点和最大亮度
            max_point, max_br = result[0], result[1]
            
            # 如果max_br是数组，取其最大值
            if isinstance(max_br, np.ndarray):
                max_br = np.max(max_br)
                
            return max_point, max_br
        
        # 执行遗传算法并返回结果
        return _run_ga()
    
    except Exception as e:
        print(f"震源位置计算异常: {e}")
        traceback.print_exc()
        # 创建安全的默认返回值
        return np.array([500, 500, 500, 0]), 0.0


if __name__ == '__main__':
    import segyio
    
    # 读取配置文件
    config = Config()
    config.load_config("config.yaml")
    print(config.get("Default", "speed"))
    # # 读取位置信息
    location_data = pd.read_excel("检波器位置文件.xlsx")
    # # 读取 SEGY 文件
    segy_file = segyio.open("1.sgy", 'r', ignore_geometry=True)
    wave_data = segy_file.trace

    # 测试函数
    def mock_update_progress(progress, idx=0, type_str='', better_point=None):
        print(f"进度: {progress}%, 类型: {type_str}")
        
    time_range = {'start': 11, 'end': 13}
    
    # 测试震源位置检测（遗传算法）
    print("测试震源位置检测（强制遗传算法）:")
    max_point, max_br = calculate_source_location(
        wave_data, location_data, 0.002, time_range, mock_update_progress
    )
    print(f"最大亮度点: {max_point}, 最大亮度: {max_br}")
    
    # 测试热图计算（网格搜索）
    print("\n测试热图计算（网格搜索）:")
    max_point, max_slice, grid_x, grid_y = calculate_heatmap(
        wave_data, location_data, 0.002, time_range, mock_update_progress, 使用遗传算法=False
    )
    print(f"最大亮度点: {max_point}, 热图形状: {max_slice.shape}")
    
    # 测试热图计算（遗传算法）
    print("\n测试热图计算（遗传算法）:")
    max_point, max_slice, grid_x, grid_y = calculate_heatmap(
        wave_data, location_data, 0.002, time_range, mock_update_progress, 使用遗传算法=True
    )
    print(f"最大亮度点: {max_point}, 热图形状: {max_slice.shape if isinstance(max_slice, np.ndarray) else '标量值'}")
