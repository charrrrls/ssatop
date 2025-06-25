import re

# 读取优化后的函数
with open('optimize_source_location.py', 'r') as f:
    optimized_function = f.read()

# 读取原始文件
with open('Services/ssatop.py', 'r') as f:
    original_content = f.read()

# 定义正则表达式模式来匹配calculate_source_location函数
pattern = r'def calculate_source_location\([^)]*\):.*?(?=\n\s*def|\n\s*if __name__ == \'__main__\'|\Z)'

# 使用re.DOTALL标志来匹配多行
match = re.search(pattern, original_content, re.DOTALL)

if match:
    # 提取函数定义
    original_function = match.group(0)
    
    # 从优化后的文件中提取函数定义
    optimized_match = re.search(r'def optimized_calculate_source_location\([^)]*\):.*', optimized_function, re.DOTALL)
    if optimized_match:
        optimized_function_content = optimized_match.group(0)
        
        # 替换函数名
        optimized_function_content = optimized_function_content.replace('optimized_calculate_source_location', 'calculate_source_location')
        
        # 替换原始函数
        new_content = original_content.replace(original_function, optimized_function_content)
        
        # 写回文件
        with open('Services/ssatop.py', 'w') as f:
            f.write(new_content)
        
        print("成功替换calculate_source_location函数")
    else:
        print("无法在优化文件中找到函数定义")
else:
    print("无法在原始文件中找到calculate_source_location函数")
