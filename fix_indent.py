def fix_indent(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 修复 update_progress 方法中的缩进问题
    in_update_progress = False
    in_try_block = False
    correct_indent = ''
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # 检测方法定义
        if 'def update_progress' in line:
            in_update_progress = True
            fixed_lines.append(line)
            continue
        
        # 如果不在update_progress方法内，直接添加行
        if not in_update_progress:
            fixed_lines.append(line)
            continue
        
        # 检测下一个方法开始，表示update_progress结束
        if line.strip().startswith('def ') and in_update_progress:
            in_update_progress = False
            fixed_lines.append(line)
            continue
        
        # 修复update_progress方法内的缩进
        if in_update_progress:
            # 检测try块开始
            if 'try:' in line:
                in_try_block = True
                correct_indent = line[:line.find('try:')]
                fixed_lines.append(line)
                continue
                
            # 在try块内，需要修正缩进
            if in_try_block and 'except Exception as e:' in line and 'print(f"操作失败: {e}")' in lines[i+1]:
                # 跳过错误添加的except块
                continue
                
            # 修复已被错误缩进的行
            if in_try_block and line.strip() and not 'except Exception as e:' in line:
                # 保持正确的缩进级别
                if line.strip().startswith('#'):  # 注释行
                    fixed_line = correct_indent + '    ' + line.strip() + '\n'
                else:
                    if 'self.' in line:  # 代码行
                        fixed_line = correct_indent + '    ' + line.strip() + '\n'
                    else:
                        fixed_lines.append(line)
                        continue
                        
                fixed_lines.append(fixed_line)
                continue
                
            # 检测try块结束
            if in_try_block and 'except Exception as e:' in line and 'print(f"更新进度信息时出错: {e}")' in lines[i+1]:
                in_try_block = False
                fixed_lines.append(line)
                continue
                
        # 如果不需要特殊处理，直接添加行
        fixed_lines.append(line)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    # 一个更直接的修复方法 - 重写整个update_progress方法
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义正确格式的update_progress方法
    correct_method = '''    @pyqtSlot(int, str, str, str)
    def update_progress(self, progress, elapsed_time, remaining_time_str, speed_str):
        """更新进度显示"""
        try:
            # 确保progress是整数
            progress = int(progress)
            
            # 更新进度条
            self.progress_bar.setValue(progress)
            
            # 更新进度标签
            self.progress_label.setText(f"当前进度: {progress}%")
            
            # 更新时间标签 - 确保时间信息是字符串
            if isinstance(elapsed_time, str) and isinstance(remaining_time_str, str):
                self.time_label.setText(f"已用时间: {elapsed_time} / 预计剩余: {remaining_time_str}")
            else:
                try:
                    elapsed_str = str(elapsed_time)
                    remaining_str = str(remaining_time_str)
                    self.time_label.setText(f"已用时间: {elapsed_str} / 预计剩余: {remaining_str}")
                except:
                    self.time_label.setText("已用时间: 计算中... / 预计剩余: 计算中...")
            
            # 更新速度标签 - 确保speed_str是字符串
            if isinstance(speed_str, str):
                self.frontground_label.setText(f"处理速度: {speed_str}")
            else:
                # 如果不是字符串，尝试转换
                try:
                    speed_text = str(speed_str)
                    self.frontground_label.setText(f"处理速度: {speed_text}")
                except:
                    self.frontground_label.setText("处理速度: 计算中...")
        except Exception as e:
            print(f"更新进度信息时出错: {e}")
            # 确保即使出错也显示一些信息
            self.progress_label.setText("当前进度: 计算中...")
            self.time_label.setText("时间信息: 计算中...")
            self.frontground_label.setText("处理速度: 计算中...")
        
        # 强制处理所有待处理的事件，确保UI更新
        QCoreApplication.processEvents()
        
        # 如果进度条卡在某个值超过3秒，尝试重新绘制
        if not hasattr(self, '_last_progress'):
            self._last_progress = progress
            self._progress_time = 0
        elif self._last_progress == progress:
            self._progress_time += 1
            if self._progress_time > 30:  # 如果同一个进度超过30次更新(约3秒)
                # 重置计数器
                self._progress_time = 0
                # 强制重绘进度条
                self.progress_bar.repaint()
        else:
            self._last_progress = progress
            self._progress_time = 0'''
    
    # 替换整个方法
    import re
    pattern = re.compile(r'@pyqtSlot\(int, str, str, str\)\s+def update_progress.*?self\._progress_time = 0', re.DOTALL)
    new_content = re.sub(pattern, correct_method, content)
    
    # 修复display_heatmap_analysis方法中的try-except问题
    # 1. 删除错误的except块
    pattern = re.compile(r'try:\s+# 1\. 计算热力图的统计指标\s+except Exception as e:\s+print\(f"操作失败: \{e\}"\)')
    new_content = re.sub(pattern, 'try:\n            # 1. 计算热力图的统计指标', new_content)
    
    # 2. 修复其他try块中的except缩进问题
    pattern = re.compile(r'try:\s+x_indices = np\.where\(x_above_half\)\[0\]\s+except Exception as e:\s+print\(f"操作失败: \{e\}"\)')
    new_content = re.sub(pattern, 'try:\n                x_indices = np.where(x_above_half)[0]', new_content)
    
    pattern = re.compile(r'try:\s+from scipy import stats\s+except Exception as e:\s+print\(f"操作失败: \{e\}"\)')
    new_content = re.sub(pattern, 'try:\n                from scipy import stats', new_content)
    
    pattern = re.compile(r'try:\s+hist_bins = 10\s+except Exception as e:\s+print\(f"操作失败: \{e\}"\)')
    new_content = re.sub(pattern, 'try:\n                hist_bins = 10', new_content)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    fix_indent('Views/SourceDetectionWidget.py')
    print("缩进问题修复完成!")
