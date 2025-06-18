import threading
import time
import subprocess
import psutil
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread

class CleanupWorker(QThread):
    """异步清理工作线程"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, cleanup_tasks):
        super().__init__()
        self.cleanup_tasks = cleanup_tasks
        self.running = True
    
    def run(self):
        """执行清理任务"""
        for task_name, task_func in self.cleanup_tasks:
            if not self.running:
                break
            try:
                self.log_signal.emit(f"正在执行清理任务: {task_name}")
                task_func()
                self.log_signal.emit(f"清理任务完成: {task_name}")
            except Exception as e:
                self.log_signal.emit(f"清理任务失败 {task_name}: {str(e)}")
        
        self.finished_signal.emit()
    
    def stop(self):
        """停止清理"""
        self.running = False

class CleanupManager(QObject):
    """资源清理管理器"""
    log_signal = pyqtSignal(str)
    cleanup_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.cleanup_worker = None
        self.cleanup_timer = QTimer()
        self.cleanup_timer.setSingleShot(True)
        self.cleanup_timer.timeout.connect(self.force_cleanup_timeout)
        self.max_cleanup_time = 5000  # 最大清理时间5秒
        
    def cleanup_chrome_processes_fast(self, specific_pids=None):
        """快速清理Chrome进程"""
        try:
            if specific_pids:
                # 只清理指定的进程ID
                for pid in specific_pids:
                    try:
                        subprocess.Popen(['taskkill', '/f', '/pid', str(pid)], 
                                       stdout=subprocess.DEVNULL, 
                                       stderr=subprocess.DEVNULL)
                        self.log_signal.emit(f"已发送清理命令给进程: {pid}")
                    except Exception as e:
                        self.log_signal.emit(f"清理进程 {pid} 失败: {str(e)}")
            else:
                # 只在紧急情况下才全局清理
                self.log_signal.emit("⚠️ 执行全局Chrome进程清理（紧急模式）")
                subprocess.Popen(['taskkill', '/f', '/im', 'chrome.exe'], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                subprocess.Popen(['taskkill', '/f', '/im', 'chromedriver.exe'], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                self.log_signal.emit("全局Chrome进程清理命令已发送")
        except Exception as e:
            self.log_signal.emit(f"Chrome进程清理失败: {str(e)}")
    
    def cleanup_browser_gracefully(self, driver):
        """优雅关闭浏览器"""
        if driver:
            try:
                # 设置较短的超时时间
                driver.set_page_load_timeout(3)
                driver.implicitly_wait(1)
                driver.quit()
                self.log_signal.emit("浏览器已优雅关闭")
            except Exception as e:
                self.log_signal.emit(f"浏览器关闭异常: {str(e)}")
    
    def cleanup_threads_gracefully(self, workers, timeout=3):
        """优雅关闭线程"""
        if not workers:
            return
        
        # 首先设置停止标志
        for worker in workers:
            if hasattr(worker, 'running'):
                worker.running = False
            if hasattr(worker, 'automation') and worker.automation:
                worker.automation.running = False
        
        # 等待线程结束，但不超过指定时间
        start_time = time.time()
        for worker in workers:
            remaining_time = timeout - (time.time() - start_time)
            if remaining_time > 0:
                worker.wait(int(remaining_time * 1000))  # 转换为毫秒
            else:
                worker.terminate()  # 强制终止
        
        self.log_signal.emit(f"已清理 {len(workers)} 个工作线程")
    
    def start_async_cleanup(self, cleanup_tasks):
        """开始异步清理"""
        if self.cleanup_worker and self.cleanup_worker.isRunning():
            self.cleanup_worker.stop()
            self.cleanup_worker.wait(1000)
        
        self.cleanup_worker = CleanupWorker(cleanup_tasks)
        self.cleanup_worker.log_signal.connect(self.log_signal)
        self.cleanup_worker.finished_signal.connect(self.on_cleanup_finished)
        
        # 启动超时定时器
        self.cleanup_timer.start(self.max_cleanup_time)
        
        # 启动清理线程
        self.cleanup_worker.start()
        self.log_signal.emit("开始异步资源清理...")
    
    def on_cleanup_finished(self):
        """清理完成"""
        self.cleanup_timer.stop()
        self.cleanup_finished.emit()
        self.log_signal.emit("资源清理完成")
    
    def force_cleanup_timeout(self):
        """强制清理超时"""
        if self.cleanup_worker and self.cleanup_worker.isRunning():
            self.cleanup_worker.stop()
            self.cleanup_worker.terminate()
        
        # 超时情况下进行全局清理（紧急模式）
        self.log_signal.emit("⚠️ 清理超时，启用紧急全局清理模式")
        self.cleanup_chrome_processes_fast()
        
        self.cleanup_finished.emit()
        self.log_signal.emit("清理超时，已强制完成")
    
    def immediate_cleanup(self, drivers=None, workers=None):
        """立即清理（用于紧急情况）"""
        cleanup_tasks = []
        chrome_pids = set()
        
        # 收集需要清理的Chrome进程ID
        if workers:
            for worker in workers:
                if hasattr(worker, 'automation') and worker.automation:
                    if hasattr(worker.automation, 'chrome_processes'):
                        chrome_pids.update(worker.automation.chrome_processes)
        
        if drivers:
            for i, driver in enumerate(drivers):
                if driver:
                    cleanup_tasks.append((f"浏览器{i+1}", lambda d=driver: self.cleanup_browser_gracefully(d)))
        
        if workers:
            cleanup_tasks.append(("工作线程", lambda: self.cleanup_threads_gracefully(workers, 2)))
        
        # 只清理特定的Chrome进程，而不是全局清理
        if chrome_pids:
            cleanup_tasks.append(("特定Chrome进程", lambda: self.cleanup_chrome_processes_fast(list(chrome_pids))))
            self.log_signal.emit(f"将清理特定的Chrome进程: {list(chrome_pids)}")
        else:
            # 只有在没有找到特定进程时才进行全局清理
            cleanup_tasks.append(("Chrome进程", lambda: self.cleanup_chrome_processes_fast()))
        
        if cleanup_tasks:
            self.start_async_cleanup(cleanup_tasks)
        else:
            self.cleanup_finished.emit()

# 全局清理管理器实例
_cleanup_manager = None

def get_cleanup_manager():
    """获取全局清理管理器实例"""
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = CleanupManager()
    return _cleanup_manager