# 创建临时文件来存储优化的calculate_source_location函数
import numpy as np
import time
import traceback
from functools import lru_cache

def optimized_calculate_source_location(wave_data, location_data, sample_interval, time_range, update_progress, grid_params=None):
    """
    计算震源位置 - 专门用于源位置检测，直接使用遗传算法
    
    参数与calculate_heatmap函数相同，但会忽略使用遗传算法的参数，始终使用遗传算法
    
    返回:
    - max_point: 最大亮度点坐标和时间 [x, y, z, t]
    - max_brightness: 最大亮度值
    """
    try:
        # 获取配置和模型参数
        from Models.Config import Config
        from Models.ModelManager import ModelManager
        
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
                if 'speed' in grid_params:
                    speed = float(grid_params['speed'])
                
                print(f"源位置检测: 使用自定义网格参数: x网格={length}, y网格={length}, z网格={height}, 速度={speed}")
                
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

        # 直接实现优化的遗传算法，不通过calculate_heatmap
        # 这样可以避免额外的热图计算开销
        
        # 从ssatop.py导入normalize_data函数
        from Services.ssatop import normalize_data
        
        # 预处理数据
        # 规范化波形数据
        normalized_data = [normalize_data(trace) for trace in wave_data]
        
        # 创建时间范围数组
        if isinstance(time_range, dict) and 'start' in time_range and 'end' in time_range:
            time_start = time_range['start']
            time_end = time_range['end']
        else:
            time_start = 0
            time_end = 20  # 默认20秒
            
        time_range_array = np.arange(time_start, time_end, time_slice)
        
        # 创建亮度计算缓存
        brightness_cache = {}
        
        # 使用LRU缓存优化频繁调用的函数
        @lru_cache(maxsize=None)
        def amp_norm(trace_index):
            return normalized_data[trace_index]
        
        @lru_cache(maxsize=None)
        def time_delay(x, y, z, trace_index):
            """计算从点(x,y,z)到检波器的时间延迟"""
            detector_x = location_data['x'][trace_index]
            detector_y = location_data['y'][trace_index]
            detector_z = location_data['z'][trace_index]
            
            distance = np.sqrt((x - detector_x)**2 + (y - detector_y)**2 + (z - detector_z)**2)
            delay = distance / speed
            return delay
        
        def get_local_max(trace_data, time):
            """获取给定时间点附近的局部最大值"""
            sample_index = int(time / sample_interval)
            window_size = 5  # 局部窗口大小
            
            start_idx = max(0, sample_index - window_size)
            end_idx = min(len(trace_data) - 1, sample_index + window_size)
            
            if start_idx >= end_idx:
                return 0
                
            window_data = trace_data[start_idx:end_idx+1]
            local_max = np.max(window_data)
            return local_max
        
        def br(x, y, z, t):
            """计算给定点的亮度值"""
            # 使用缓存避免重复计算
            cache_key = (x, y, z, t)
            if cache_key in brightness_cache:
                return brightness_cache[cache_key]
                
            brightness = 0
            valid_traces = 0
            
            for i in range(len(wave_data)):
                delay = time_delay(x, y, z, i)
                arrival_time = t + delay
                
                # 检查时间是否在有效范围内
                if arrival_time < 0 or arrival_time >= len(amp_norm(i)) * sample_interval:
                    continue
                    
                # 获取局部最大值作为振幅
                amplitude = get_local_max(amp_norm(i), arrival_time)
                brightness += amplitude
                valid_traces += 1
                
            # 如果没有有效的检波器数据，返回0
            if valid_traces == 0:
                return 0
                
            # 归一化亮度值
            brightness = brightness / valid_traces
            
            # 缓存结果
            brightness_cache[cache_key] = brightness
            return brightness
            
        # 设置网格范围
        grid_x = np.arange(location_data['x'].min(), location_data['x'].max() + 1, length)
        grid_y = np.arange(location_data['y'].min(), location_data['y'].max() + 1, length)
        grid_z = np.arange(z_min, z_max, height)
        grid_t = time_range_array
        
        # 从网格参数中获取遗传算法参数
        population_size = 300  # 默认值
        generations = 20  # 默认值
        mutation_rate = 0.2  # 默认值
        
        if grid_params:
            if 'population_size' in grid_params:
                population_size = int(grid_params['population_size'])
            if 'generations' in grid_params:
                generations = int(grid_params['generations'])
            if 'mutation_rate' in grid_params:
                mutation_rate = float(grid_params['mutation_rate'])
                
        print(f"源位置检测: 使用遗传算法参数: 种群大小={population_size}, 迭代次数={generations}, 变异率={mutation_rate}")
        
        # 尝试导入并行计算库
        try:
            import multiprocessing
            from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
            num_cores = multiprocessing.cpu_count()
            use_parallel = num_cores > 1 and population_size >= 100
            print(f"检测到{num_cores}个CPU核心，{'启用' if use_parallel else '不启用'}并行计算")
        except ImportError:
            use_parallel = False
            print("未找到multiprocessing模块，使用单线程计算")
        
        # 初始化种群 - 改进的初始化策略
        population = np.zeros((population_size, 4))
        
        # 50%的个体随机分布
        random_population = np.random.uniform(
            low=[grid_x.min(), grid_y.min(), grid_z.min(), grid_t.min()],
            high=[grid_x.max(), grid_y.max(), grid_z.max(), grid_t.max()],
            size=(int(population_size * 0.5), 4)
        )
        population[:int(population_size * 0.5)] = random_population
        
        # 30%的个体在网格点上
        grid_points = np.array(np.meshgrid(
            np.linspace(grid_x.min(), grid_x.max(), 10),
            np.linspace(grid_y.min(), grid_y.max(), 10),
            np.linspace(grid_z.min(), grid_z.max(), 5),
            np.linspace(grid_t.min(), grid_t.max(), 5)
        )).T.reshape(-1, 4)
        
        if len(grid_points) > 0:
            grid_indices = np.random.choice(len(grid_points), int(population_size * 0.3), replace=True)
            population[int(population_size * 0.5):int(population_size * 0.8)] = grid_points[grid_indices]
        
        # 20%的个体在检波器附近
        detector_points = np.zeros((int(population_size * 0.2), 4))
        for i in range(int(population_size * 0.2)):
            # 随机选择一个检波器
            detector_idx = np.random.randint(0, len(location_data['x']))
            # 在检波器周围随机生成点
            detector_points[i, 0] = location_data['x'][detector_idx] + np.random.uniform(-length*5, length*5)
            detector_points[i, 1] = location_data['y'][detector_idx] + np.random.uniform(-length*5, length*5)
            detector_points[i, 2] = location_data['z'][detector_idx] + np.random.uniform(-height*5, height*5)
            detector_points[i, 3] = np.random.uniform(grid_t.min(), grid_t.max())
        
        population[int(population_size * 0.8):] = detector_points
        
        # 确保所有点都在边界内
        population[:, 0] = np.clip(population[:, 0], grid_x.min(), grid_x.max())
        population[:, 1] = np.clip(population[:, 1], grid_y.min(), grid_y.max())
        population[:, 2] = np.clip(population[:, 2], grid_z.min(), grid_z.max())
        population[:, 3] = np.clip(population[:, 3], grid_t.min(), grid_t.max())
        
        # 使用局部缓存提高性能
        local_fitness_cache = {}
        best_brightness = -np.inf
        best_point = None
        
        # 添加早期停止条件
        no_improvement_limit = 10  # 连续10代无改进则提前停止
        no_improvement_count = 0
        improvement_threshold = 0.001  # 改进小于0.1%视为无改进
        
        # 自适应变异率参数
        initial_mutation_rate = mutation_rate
        min_mutation_rate = 0.05
        
        # 批量计算适应度的函数
        def calculate_fitness_batch(individuals):
            results = np.zeros(len(individuals))
            for i, ind in enumerate(individuals):
                # 转换为元组以便缓存
                ind_tuple = tuple(ind)
                if ind_tuple in local_fitness_cache:
                    results[i] = local_fitness_cache[ind_tuple]
                else:
                    fitness_val = br(ind[0], ind[1], ind[2], ind[3])
                    local_fitness_cache[ind_tuple] = fitness_val
                    results[i] = fitness_val
            return results
        
        # 使用并行计算时的批处理函数
        def parallel_fitness(population):
            if not use_parallel:
                return calculate_fitness_batch(population)
            
            # 将种群分成多个批次
            batch_size = max(10, population_size // (num_cores * 2))
            batches = [population[i:i+batch_size] for i in range(0, len(population), batch_size)]
            
            # 使用线程池并行计算
            with ThreadPoolExecutor(max_workers=num_cores) as executor:
                results = list(executor.map(calculate_fitness_batch, batches))
            
            # 合并结果
            return np.concatenate(results)
        
        # 记录开始时间
        start_time = time.time()
        
        # 主遗传算法循环
        for generation in range(generations):
            # 计算适应度 - 使用向量化或并行计算
            fitness = parallel_fitness(population)
            
            # 更新进度
            current_progress = int((generation + 1) / generations * 100)
            
            # 更新最佳点
            max_fitness_idx = np.argmax(fitness)
            current_best = fitness[max_fitness_idx]
            
            # 检查是否有改进
            if current_best > best_brightness * (1 + improvement_threshold):
                best_brightness = current_best
                best_point = population[max_fitness_idx].copy()
                更优的点 = (best_point, best_brightness)
                print(f"第{generation}代: 更新全局最佳点: {best_point}, 亮度: {best_brightness}")
                
                # 重置无改进计数
                no_improvement_count = 0
            else:
                no_improvement_count += 1
                
            # 更新进度条并传递最佳点
            if best_point is not None:
                progress_wrapper(current_progress, generation + 1, 'generations', (best_point, best_brightness))
            else:
                progress_wrapper(current_progress, generation + 1, 'generations')
            
            # 早期停止检查
            if no_improvement_count >= no_improvement_limit:
                print(f"连续{no_improvement_limit}代无显著改进，提前停止算法")
                break
            
            # 自适应变异率 - 根据进度和收敛情况调整
            if no_improvement_count > 5:
                # 增加变异率以跳出局部最优
                mutation_rate = min(initial_mutation_rate * 1.5, 0.5)
                print(f"第{generation}代: 连续{no_improvement_count}代无改进，增加变异率至{mutation_rate}")
            elif no_improvement_count > 2:
                # 减小变异率以精细搜索
                mutation_rate = max(min_mutation_rate, initial_mutation_rate * 0.8)
                print(f"第{generation}代: 连续{no_improvement_count}代无改进，减小变异率至{mutation_rate}")
            else:
                # 恢复正常变异率
                mutation_rate = initial_mutation_rate
            
            # 精英保留策略 - 保留最好的10%个体
            elite_count = max(1, int(population_size * 0.1))
            elite_indices = np.argsort(fitness)[-elite_count:]
            elites = population[elite_indices].copy()

            # 锦标赛选择
            tournament_size = 3
            parents = []
            for _ in range(population_size // 2):
                participants_idx = np.random.choice(population_size, tournament_size, replace=False)
                winner_idx = participants_idx[np.argmax(fitness[participants_idx])]
                parents.append(population[winner_idx])

            parents = np.array(parents)

            # 交叉操作 - 使用向量化操作
            num_offspring = population_size - len(parents) - len(elites)
            offspring = np.zeros((num_offspring, 4))
            
            # 随机选择父母对
            parent_indices1 = np.random.randint(0, len(parents), num_offspring)
            parent_indices2 = np.random.randint(0, len(parents), num_offspring)
            
            # 生成交叉掩码
            crossover_type = np.random.random(num_offspring) < 0.5
            
            # 单点交叉
            single_point_indices = np.where(crossover_type)[0]
            if len(single_point_indices) > 0:
                crossover_points = np.random.randint(1, 4, len(single_point_indices))
                for i, idx in enumerate(single_point_indices):
                    cp = crossover_points[i]
                    offspring[idx, :cp] = parents[parent_indices1[idx], :cp]
                    offspring[idx, cp:] = parents[parent_indices2[idx], cp:]
            
            # 均匀交叉
            uniform_indices = np.where(~crossover_type)[0]
            if len(uniform_indices) > 0:
                for i, idx in enumerate(uniform_indices):
                    mask = np.random.random(4) < 0.5
                    offspring[idx] = np.where(mask, 
                                             parents[parent_indices1[idx]], 
                                             parents[parent_indices2[idx]])

            # 变异操作 - 使用向量化操作
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
            
            # 每5代进行一次局部搜索，对最佳点进行精细搜索
            if generation % 5 == 0 and best_point is not None:
                # 在最佳点周围生成10个点进行局部搜索
                local_search_points = np.tile(best_point, (10, 1))
                local_search_scale = 0.1 * (1.0 - generation / generations)  # 随迭代减小搜索范围
                local_noise = np.random.uniform(
                    low=[-length * local_search_scale, -length * local_search_scale, 
                         -height * local_search_scale, -(time_range_array[1] - time_range_array[0]) * local_search_scale],
                    high=[length * local_search_scale, length * local_search_scale, 
                          height * local_search_scale, (time_range_array[1] - time_range_array[0]) * local_search_scale],
                    size=(10, 4)
                )
                local_search_points += local_noise
                
                # 确保在边界内
                local_search_points[:, 0] = np.clip(local_search_points[:, 0], grid_x.min(), grid_x.max())
                local_search_points[:, 1] = np.clip(local_search_points[:, 1], grid_y.min(), grid_y.max())
                local_search_points[:, 2] = np.clip(local_search_points[:, 2], grid_z.min(), grid_z.max())
                local_search_points[:, 3] = np.clip(local_search_points[:, 3], grid_t.min(), grid_t.max())
                
                # 计算局部搜索点的适应度
                local_fitness = calculate_fitness_batch(local_search_points)
                local_best_idx = np.argmax(local_fitness)
                
                # 如果找到更好的点，更新最佳点
                if local_fitness[local_best_idx] > best_brightness:
                    best_brightness = local_fitness[local_best_idx]
                    best_point = local_search_points[local_best_idx].copy()
                    print(f"局部搜索找到更好的点: {best_point}, 亮度: {best_brightness}")
                    
                    # 将这个点添加到种群中
                    population[-1] = best_point.copy()
        
        # 计算完成，更新进度为100%
        progress_wrapper(100, generations, 'completed')
        
        # 计算总耗时
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"遗传算法完成，耗时: {elapsed_time:.2f}秒")
        print(f"最佳点: {best_point}, 最大亮度: {best_brightness}")
        
        return best_point, best_brightness
    
    except Exception as e:
        print(f"震源位置计算异常: {e}")
        traceback.print_exc()
        # 创建安全的默认返回值
        return np.array([500, 500, 500, 0]), 0.0
