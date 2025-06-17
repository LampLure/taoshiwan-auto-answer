import os
import psutil
import threading
from multiprocessing import cpu_count

class CPUOptimizer:
    """CPU多核优化器"""
    
    def __init__(self):
        self.cpu_count = cpu_count()
        self.logical_cores = os.cpu_count()
        self.physical_cores = psutil.cpu_count(logical=False)
        self.current_process = psutil.Process()
        
    def get_cpu_info(self):
        """获取CPU信息"""
        return {
            'logical_cores': self.logical_cores,
            'physical_cores': self.physical_cores,
            'cpu_count': self.cpu_count
        }
    
    def set_process_priority(self, priority='normal'):
        """设置进程优先级"""
        try:
            if priority == 'high':
                self.current_process.nice(psutil.HIGH_PRIORITY_CLASS)
            elif priority == 'above_normal':
                self.current_process.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
            elif priority == 'normal':
                self.current_process.nice(psutil.NORMAL_PRIORITY_CLASS)
            return True
        except Exception as e:
            print(f"设置进程优先级失败: {e}")
            return False
    
    def set_cpu_affinity(self, core_list=None):
        """设置CPU亲和性"""
        try:
            if core_list is None:
                # 默认使用所有可用核心
                core_list = list(range(self.logical_cores))
            
            self.current_process.cpu_affinity(core_list)
            return True
        except Exception as e:
            print(f"设置CPU亲和性失败: {e}")
            return False
    
    def optimize_for_multithreading(self, thread_count):
        """为多线程优化CPU使用"""
        try:
            # 设置进程优先级为高于正常
            self.set_process_priority('above_normal')
            
            # 如果线程数少于物理核心数，可以设置CPU亲和性
            if thread_count <= self.physical_cores:
                # 使用前N个物理核心（避免超线程干扰）
                core_list = list(range(0, thread_count * 2, 2))  # 使用物理核心
                self.set_cpu_affinity(core_list)
            else:
                # 使用所有核心
                self.set_cpu_affinity()
            
            return True
        except Exception as e:
            print(f"多线程优化失败: {e}")
            return False
    
    def get_optimal_thread_count(self):
        """获取建议的线程数量"""
        # 对于I/O密集型任务（如网页自动化），建议线程数为CPU核心数的1.5-2倍
        # 但考虑到浏览器资源消耗，建议不超过物理核心数
        optimal_count = min(self.physical_cores, max(2, self.physical_cores // 2))
        return optimal_count
    
    def monitor_cpu_usage(self):
        """监控CPU使用情况"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            avg_cpu = sum(cpu_percent) / len(cpu_percent)
            
            return {
                'average_cpu': avg_cpu,
                'per_core_cpu': cpu_percent,
                'process_cpu': self.current_process.cpu_percent()
            }
        except Exception as e:
            print(f"监控CPU使用失败: {e}")
            return None
    
    def apply_chrome_optimizations(self):
        """应用Chrome浏览器优化参数"""
        optimization_args = [
            # CPU和内存优化
            '--max_old_space_size=4096',
            '--memory-pressure-off',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            
            # 进程管理优化
            '--process-per-site',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            
            # 网络优化
            '--aggressive-cache-discard',
            '--disable-background-networking',
            '--disable-sync',
            
            # 渲染优化
            '--disable-gpu-sandbox',
            '--disable-software-rasterizer',
            '--enable-gpu-rasterization',
            
            # 多进程优化
            f'--renderer-process-limit={min(8, self.physical_cores)}',
            '--max-gum-fps=60'
        ]
        
        return optimization_args

# 全局CPU优化器实例
cpu_optimizer = CPUOptimizer()

def get_cpu_optimizer():
    """获取CPU优化器实例"""
    return cpu_optimizer

def print_cpu_info():
    """打印CPU信息"""
    info = cpu_optimizer.get_cpu_info()
    optimal_threads = cpu_optimizer.get_optimal_thread_count()
    
    print(f"=== CPU信息 ===")
    print(f"逻辑核心数: {info['logical_cores']}")
    print(f"物理核心数: {info['physical_cores']}")
    print(f"建议线程数: {optimal_threads}")
    print(f"当前最大线程数设置: 32")
    print(f"==============")

if __name__ == "__main__":
    print_cpu_info()