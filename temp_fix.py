import re
import sys

# 读取原始文件
file_path = 'Views/SourceDetectionWidget.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 update_progress 方法中的缩进问题
pattern1 = re.compile(r'(\s+)# 更新进度条\n(\s+)self\.progress_bar\.setValue\(progress\)')
content = re.compile(pattern1).sub(r'\1# 更新进度条\n\1self.progress_bar.setValue(progress)', content)

pattern2 = re.compile(r'(\s+)# 更新进度标签\n(\s+)self\.progress_label\.setText')
content = re.compile(pattern2).sub(r'\1# 更新进度标签\n\1self.progress_label.setText', content)

pattern3 = re.compile(r'(\s+)# 更新时间标签.*\n(\s+)if isinstance.*\n(\s+)self\.time_label\.setText')
content = re.compile(pattern3).sub(r'\1# 更新时间标签 - 确保时间信息是字符串\n\1if isinstance(elapsed_time, str) and isinstance(remaining_time_str, str):\n\1\1self.time_label.setText', content)

pattern4 = re.compile(r'(\s+)# 更新速度标签.*\n(\s+)if isinstance.*\n(\s+)self\.frontground_label\.setText')
content = re.compile(pattern4).sub(r'\1# 更新速度标签 - 确保speed_str是字符串\n\1if isinstance(speed_str, str):\n\1\1self.frontground_label.setText', content)

pattern5 = re.compile(r'(\s+)try:\n(\s+)speed_text')
content = re.compile(pattern5).sub(r'\1try:\n\1\1speed_text', content)

# 修复try语句中缺少except部分的问题
pattern6 = re.compile(r'(\s+)try:\s*\n([\s\S]*?)(?=\n\s*except|\n\s*try|\n\s*[^\s])')
matches = re.finditer(pattern6, content)
processed_content = content

for match in reversed(list(matches)):
    if 'except' not in match.group(0) and 'finally' not in match.group(0):
        # 这个try块没有except或finally
        try_block = match.group(0)
        fixed_try_block = try_block + '\n' + ' ' * len(match.group(1)) + 'except Exception as e:\n' + ' ' * len(match.group(1)) + '    print(f"操作失败: {e}")'
        processed_content = processed_content[:match.start()] + fixed_try_block + processed_content[match.end():]

# 修复特定的缩进问题
processed_content = processed_content.replace('                    # 更新结果文本\n            self.result_text.setText', '            # 更新结果文本\n            self.result_text.setText')

# 写入修复后的文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(processed_content)

print("文件修复完成")
