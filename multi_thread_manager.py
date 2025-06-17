import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from automation import BrowserAutomation
import queue
from cpu_optimization import get_cpu_optimizer

class ThreadWorker(QThread):
    """单个线程工作器"""
    log_signal = pyqtSignal(str, int)  # 日志信号，包含线程ID
    status_signal = pyqtSignal(int, str, int)  # 状态信号，包含线程ID
    progress_signal = pyqtSignal(int, str, int)  # 进度信号，包含线程ID
    finished_signal = pyqtSignal(int)  # 完成信号，包含线程ID
    
    def __init__(self, thread_id, accounts, question_db, delay_multiplier=1.0):
        super().__init__()
        self.thread_id = thread_id
        self.accounts = accounts
        self.question_db = question_db
        self.delay_multiplier = delay_multiplier
        self.running = False
        self.paused = False
        self.automation = None
        
    def run(self):
        """运行线程"""
        try:
            self.running = True
            self.log_signal.emit(f"线程 {self.thread_id} 开始处理 {len(self.accounts)} 个账号", self.thread_id)
            
            # 创建自动化实例
            self.automation = BrowserAutomation(self.accounts, self.question_db)
            self.automation.set_operation_delay(self.automation.operation_delay * self.delay_multiplier)
            
            # 连接信号
            self.automation.log_signal.connect(lambda msg: self.log_signal.emit(f"[线程{self.thread_id}] {msg}", self.thread_id))
            self.automation.status_signal.connect(lambda account_index, status: self.status_signal.emit(account_index, status, self.thread_id))
            self.automation.progress_signal.connect(lambda progress, msg: self.progress_signal.emit(progress, msg, self.thread_id))
            
            # 启动自动化
            self.automation.start()
            self.automation.wait()  # 等待完成
            
            self.log_signal.emit(f"线程 {self.thread_id} 处理完成", self.thread_id)
            
        except Exception as e:
            self.log_signal.emit(f"线程 {self.thread_id} 发生错误: {str(e)}", self.thread_id)
        finally:
            self.running = False
            self.finished_signal.emit(self.thread_id)
    
    def pause(self):
        """暂停线程"""
        self.paused = True
        if self.automation:
            self.automation.paused = True
    
    def resume(self):
        """恢复线程"""
        self.paused = False
        if self.automation:
            self.automation.paused = False
    
    def stop(self):
        """停止线程"""
        self.running = False
        if self.automation:
            self.automation.running = False
        
        # 快速退出，不等待
        self.quit()
        # 只等待很短时间，避免卡顿
        if not self.wait(500):  # 等待500毫秒
            self.terminate()  # 强制终止

class MultiThreadManager(QObject):
    """多线程管理器"""
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(int, str)
    progress_signal = pyqtSignal(int, str)
    all_finished_signal = pyqtSignal()
    
    def __init__(self, question_db):
        super().__init__()
        self.question_db = question_db
        self.workers = []
        self.cpu_optimizer = get_cpu_optimizer()
        # 使用CPU优化器建议的线程数
        self.thread_count = self.cpu_optimizer.get_optimal_thread_count()
        self.running = False
        self.paused = False
        self.delay_multiplier = 1.0
        self.finished_threads = 0
        
    def set_thread_count(self, count):
        """设置线程数量"""
        self.thread_count = max(1, min(count, 32))  # 限制在1-32之间
        
    def set_delay_multiplier(self, multiplier):
        """设置延迟倍数"""
        self.delay_multiplier = multiplier
        
    def distribute_accounts(self, accounts):
        """将账号分配给不同线程"""
        if not accounts:
            return []
            
        # 计算每个线程应该处理的账号数量
        accounts_per_thread = len(accounts) // self.thread_count
        remainder = len(accounts) % self.thread_count
        
        distributed_accounts = []
        start_index = 0
        
        for i in range(self.thread_count):
            # 如果有余数，前几个线程多分配一个账号
            current_count = accounts_per_thread + (1 if i < remainder else 0)
            if current_count > 0:
                end_index = start_index + current_count
                thread_accounts = accounts[start_index:end_index]
                distributed_accounts.append(thread_accounts)
                start_index = end_index
            else:
                break
                
        return distributed_accounts
        
    def start_automation(self, accounts):
        """开始多线程自动化"""
        if self.running:
            return
            
        self.running = True
        self.finished_threads = 0
        self.workers = []
        
        # 应用CPU优化
        try:
            self.cpu_optimizer.optimize_for_multithreading(self.thread_count)
            cpu_info = self.cpu_optimizer.get_cpu_info()
            self.log_signal.emit(f"CPU优化已启用 - 物理核心: {cpu_info['physical_cores']}, 逻辑核心: {cpu_info['logical_cores']}, 使用线程: {self.thread_count}")
        except Exception as e:
            self.log_signal.emit(f"CPU优化失败: {str(e)}")
        
        # 分配账号
        distributed_accounts = self.distribute_accounts(accounts)
        
        if not distributed_accounts:
            self.log_signal.emit("没有账号需要处理")
            return
            
        self.log_signal.emit(f"启动多线程模式，使用 {len(distributed_accounts)} 个线程处理 {len(accounts)} 个账号")
        
        # 创建并启动工作线程
        for i, thread_accounts in enumerate(distributed_accounts):
            worker = ThreadWorker(i + 1, thread_accounts, self.question_db, self.delay_multiplier)
            
            # 连接信号
            worker.log_signal.connect(self.on_worker_log)
            worker.status_signal.connect(self.on_worker_status)
            worker.progress_signal.connect(self.on_worker_progress)
            worker.finished_signal.connect(self.on_worker_finished)
            
            self.workers.append(worker)
            worker.start()
            
            # 错开启动时间，避免同时访问网站
            time.sleep(2)
    
    def on_worker_log(self, message, thread_id):
        """处理工作线程的日志信号"""
        # 在多线程模式下过滤重要消息，排除题目处理细节
        important_keywords = [
            "成功登录", "登录失败", "登录超时", "账号被锁定",
            "开始处理", "处理完成", "账号完成", "所有题目已完成",
            "错误", "异常", "失败", "超时", "网络问题",
            "线程", "启动", "完成", "暂停", "恢复", "停止"
        ]
        
        # 排除题目处理的详细信息
        exclude_keywords = [
            "正在处理题目", "题目类型", "选择答案", "提交答案",
            "查找题目", "点击选项", "滚动页面", "等待加载",
            "题目内容", "答案选项", "题目编号"
        ]
        
        # 检查是否包含重要关键词且不包含排除关键词
        should_show = any(keyword in message for keyword in important_keywords)
        should_exclude = any(keyword in message for keyword in exclude_keywords)
        
        if should_show and not should_exclude:
            self.log_signal.emit(message)
    
    def on_worker_status(self, account_index, status, thread_id):
        """处理工作线程的状态信号"""
        self.status_signal.emit(account_index, f"线程{thread_id}: {status}")
    
    def on_worker_progress(self, progress, message, thread_id):
        """处理工作线程的进度信号"""
        # 计算总体进度
        total_progress = sum(worker.automation.current_account_index if worker.automation else 0 for worker in self.workers)
        total_accounts = sum(len(worker.accounts) for worker in self.workers)
        
        if total_accounts > 0:
            overall_progress = int((total_progress / total_accounts) * 100)
            self.progress_signal.emit(overall_progress, f"总进度: {total_progress}/{total_accounts}")
    
    def on_worker_finished(self, thread_id):
        """处理工作线程完成信号"""
        self.finished_threads += 1
        self.log_signal.emit(f"线程 {thread_id} 已完成")
        
        if self.finished_threads >= len(self.workers):
            self.log_signal.emit("所有线程已完成")
            self.running = False
            self.all_finished_signal.emit()
    
    def pause_automation(self):
        """暂停所有线程"""
        self.paused = True
        for worker in self.workers:
            worker.pause()
        self.log_signal.emit("已暂停所有线程")
    
    def resume_automation(self):
        """恢复所有线程"""
        self.paused = False
        for worker in self.workers:
            worker.resume()
        self.log_signal.emit("已恢复所有线程")
    
    def stop_automation(self):
        """停止所有线程"""
        self.running = False
        
        # 快速设置停止标志
        for worker in self.workers:
            if hasattr(worker, 'running'):
                worker.running = False
            if hasattr(worker, 'automation') and worker.automation:
                worker.automation.running = False
        
        # 使用清理管理器进行异步清理
        try:
            from cleanup_manager import get_cleanup_manager
            cleanup_manager = get_cleanup_manager()
            
            # 收集驱动程序
            drivers = []
            for worker in self.workers:
                if hasattr(worker, 'automation') and worker.automation and hasattr(worker.automation, 'driver'):
                    drivers.append(worker.automation.driver)
            
            # 异步清理
            if drivers or self.workers:
                cleanup_manager.immediate_cleanup(drivers=drivers, workers=self.workers)
            
        except Exception as e:
            self.log_signal.emit(f"清理过程中发生错误: {str(e)}")
            # 回退到原始清理方法
            for worker in self.workers:
                try:
                    worker.quit()
                    worker.wait(1000)  # 等待1秒
                except:
                    pass
        
        self.workers = []
        self.log_signal.emit("已停止所有线程")