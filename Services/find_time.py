import numpy as np
import pandas as pd
import segyio
from Services.ssatop import amp_norm
import math

# 假设 segyfile 是已经加载的 SEGY 文件
# segyfile = segyio.open('path_to_segy_file.sgy', 'r')
def get_event_times(wave_data):
    
    # 判断 wave_data 是否为空
    
    event_data = []

    # 遍历每个trace并计算事件的开始和结束
    for trace_data in wave_data:
        trace_data = amp_norm(trace_data)  # 获取当前的trace

        # 计算信号的能量
        energy = np.square(trace_data)
        energy_cumsum = np.cumsum(energy)  # 累积能量

        # 找到地震波到达的时间点：假设能量突变为地震波到达的标志
        threshold = 0.1 * np.max(energy_cumsum)  # 设置一个阈值，表示地震波到达的临界点
        index_of_event_start = np.argmax(energy_cumsum > threshold)

        index_of_event_start -= 10

        # 找到地震结束的时间点：假设累积能量的增幅趋于平稳
        # 可以通过检测能量变化的稳定性来确定结束点
        threshold_end = 0.98 * np.max(energy_cumsum)  # 设定一个较高的阈值
        index_of_event_end = np.argmax(energy_cumsum > threshold_end)

        # 将计算的起始和结束时间转换为秒并存入列表
        event_data.append({
            "Event Start (s)": 0.002 * index_of_event_start ,  # 转换为秒
            "Event End (s)": 0.002 * index_of_event_end   # 转换为秒
        })

    # 将列表转换为 DataFrame
    df = pd.DataFrame(event_data)

    
    
    # 提取 'Event Start' 列
    event_start = df['Event Start (s)'].values
    event_end = df['Event End (s)'].values

    # 使用 Event Start 数据进行直方图计算
    y_values = event_start
    y_values2 = event_end

    # 计算直方图，增加 bins 数量为 50
    bins_count = 50
    hist, bins = np.histogram(y_values, bins=bins_count, density=True)
    hist2, bins2 = np.histogram(y_values2, bins=bins_count, density=True)


    # 找出最大密度区域
    max_density_index = np.argmax(hist)
    start_bin = bins[max_density_index]
    end_bin = bins[max_density_index + 1]

    max_density_index2 = np.argmax(hist2)
    start_bin2 = bins2[max_density_index2]
    end_bin2 = bins2[max_density_index2 + 1]

    # 处理 start_bin2 必须大于 0.9 的条件
    if start_bin2 <= 0.9:
        # 找到概率大于 0.10 的最左列区间
        for i in range(len(hist2)):
            if hist2[i] > 0.10 and bins2[i] > 0.9:
                start_bin2 = bins2[i]
                end_bin2 = bins2[i + 1]
                break

    # 计算 index_of_event_start 和 index_of_event_end 并向下取整
    index_of_event_start = math.floor((start_bin + end_bin) / 2 / 0.002)
    index_of_event_end = math.floor((start_bin2 + end_bin2) / 2 / 0.002)

    return {"start": start_bin, "end": end_bin}


if __name__ == '__main__':
    segy_file = segyio.open("1.sgy", 'r', ignore_geometry=True)

    wave_data = segy_file.trace
    get_event_times(wave_data)