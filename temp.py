import pandas as pd

# 读取表格数据
location_data = pd.read_excel('检波器位置文件.xlsx')

N = len(location_data['trace_number'])
print(N)

for i in location_data['trace_number']:
    print(i)