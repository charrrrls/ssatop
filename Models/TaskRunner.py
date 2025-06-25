from PyQt6.QtCore import QThread, pyqtSignal
import time
import traceback

# 定义任务执行器类，用于异步执行耗时函数
class TaskRunner(QThread):
    task_completed = pyqtSignal(object)  # 定义信号，可以传递任意类型的返回结果

    def __init__(self, func=None, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.should_stop = False

    def run(self):
        if self.func:
            try:
                result = self.func(*self.args, **self.kwargs)  # 执行函数并获取返回值
            except Exception as e:
                result = e  # 捕获函数执行过程中出现的异常
            self.task_completed.emit(result)  # 发射回调信号，并传递返回值
    
    def run_task(self, task_func, args=(), progress_callback=None):
        """
        在当前线程中运行任务，支持进度回调
        
        参数:
        task_func: 要执行的任务函数
        args: 传递给任务函数的参数元组
        progress_callback: 进度回调函数，接收进度百分比和其他参数
        
        返回:
        任务函数的返回值
        """
        self.should_stop = False
        self.result = None
        
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 检查args中是否已经包含了progress_callback
            # 如果最后一个参数是可调用的，假设它是进度回调函数
            if args and callable(args[-1]):
                # 直接使用args中的回调函数
                self.result = task_func(*args)
            elif progress_callback:
                # 如果提供了进度回调，则将其包装在args中传递给任务函数
                # 创建一个包装函数，用于传递进度信息
                def wrapped_callback(progress, idx, unit, best_point=None):
                    # 检查是否应该停止
                    if self.should_stop:
                        return False
                    
                    # 调用原始回调
                    return progress_callback(progress, start_time, idx, unit, best_point)
                
                # 将wrapped_callback作为参数传递给任务函数
                args_with_callback = args + (wrapped_callback,)
                self.result = task_func(*args_with_callback)
            else:
                # 如果没有提供进度回调，则直接执行任务函数
                self.result = task_func(*args)
                
            return self.result
            
        except Exception as e:
            print(f"任务执行出错: {e}")
            print(traceback.format_exc())
            return e
    
    def stop_task(self):
        """停止当前任务"""
        self.should_stop = True

