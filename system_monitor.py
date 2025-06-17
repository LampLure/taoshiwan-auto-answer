import psutil
import time
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class SystemMonitor(QThread):
    """系统资源监控线程"""
    resource_updated = pyqtSignal(float, float, float, float)  # CPU%, 内存%, 程序内存MB, 总内存MB
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.process = psutil.Process()  # 当前进程
        
    def run(self):
        """监控线程主循环"""
        while self.running:
            try:
                # 获取CPU使用率
                cpu_percent = psutil.cpu_percent(interval=0.1)
                
                # 获取系统内存信息
                memory = psutil.virtual_memory()
                total_memory_mb = memory.total / (1024 * 1024)  # 总内存MB
                
                # 获取当前程序内存使用
                process_memory = self.process.memory_info()
                program_memory_mb = process_memory.rss / (1024 * 1024)  # 程序内存MB
                
                # 计算内存使用百分比
                memory_percent = memory.percent
                
                # 发送信号
                self.resource_updated.emit(cpu_percent, memory_percent, program_memory_mb, total_memory_mb)
                
                # 等待1秒
                time.sleep(1)
                
            except Exception as e:
                print(f"监控线程错误: {e}")
                time.sleep(1)
                
    def stop(self):
        """停止监控"""
        self.running = False
        self.quit()
        self.wait()

class ResourceWidget(QWidget):
    """资源监控显示组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.monitor = SystemMonitor()
        self.monitor.resource_updated.connect(self.update_resource_display)
        self.monitor.start()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # 标题
        title_label = QLabel("系统资源监控")
        title_label.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        layout.addWidget(title_label)
        
        # CPU监控
        cpu_layout = QVBoxLayout()
        cpu_layout.setSpacing(2)
        
        self.cpu_label = QLabel("CPU: 0.0%")
        self.cpu_label.setStyleSheet("font-size: 11px; color: #666;")
        cpu_layout.addWidget(self.cpu_label)
        
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setMaximum(100)
        self.cpu_bar.setMinimum(0)
        self.cpu_bar.setValue(0)
        self.cpu_bar.setMaximumHeight(15)
        self.cpu_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        cpu_layout.addWidget(self.cpu_bar)
        
        layout.addLayout(cpu_layout)
        
        # 内存监控（叠加显示）
        memory_layout = QVBoxLayout()
        memory_layout.setSpacing(2)
        
        self.memory_label = QLabel("内存: 0.0% (程序: 0MB / 总计: 0MB)")
        self.memory_label.setStyleSheet("font-size: 11px; color: #666;")
        memory_layout.addWidget(self.memory_label)
        
        # 创建分段内存进度条容器
        memory_progress_container = QWidget()
        memory_progress_container.setMaximumHeight(15)
        memory_progress_layout = QHBoxLayout(memory_progress_container)
        memory_progress_layout.setContentsMargins(0, 0, 0, 0)
        memory_progress_layout.setSpacing(0)
        
        # 系统其他内存使用（蓝色部分）
        self.system_memory_bar = QProgressBar()
        self.system_memory_bar.setMaximum(100)
        self.system_memory_bar.setMinimum(0)
        self.system_memory_bar.setValue(0)
        self.system_memory_bar.setMaximumHeight(15)
        self.system_memory_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-top-left-radius: 3px;
                border-bottom-left-radius: 3px;
                border-right: none;
                text-align: center;
                font-size: 10px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-top-left-radius: 2px;
                border-bottom-left-radius: 2px;
            }
        """)
        
        # 程序内存使用（橙色部分）
        self.program_memory_bar = QProgressBar()
        self.program_memory_bar.setMaximum(100)
        self.program_memory_bar.setMinimum(0)
        self.program_memory_bar.setValue(0)
        self.program_memory_bar.setMaximumHeight(15)
        self.program_memory_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
                border-left: none;
                text-align: center;
                font-size: 10px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #FF9800;
                border-top-right-radius: 2px;
                border-bottom-right-radius: 2px;
            }
        """)
        
        memory_progress_layout.addWidget(self.system_memory_bar)
        memory_progress_layout.addWidget(self.program_memory_bar)
        memory_layout.addWidget(memory_progress_container)
        
        layout.addLayout(memory_layout)
        
    def update_resource_display(self, cpu_percent, memory_percent, program_memory_mb, total_memory_mb):
        """更新资源显示"""
        # 更新CPU显示
        self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
        self.cpu_bar.setValue(int(cpu_percent))
        
        # 计算程序内存占总内存的百分比
        program_memory_percent = (program_memory_mb / total_memory_mb * 100) if total_memory_mb > 0 else 0
        # 计算系统其他内存使用百分比（总使用率减去程序使用率）
        system_other_memory_percent = max(0, memory_percent - program_memory_percent)
        
        # 更新内存显示
        self.memory_label.setText(f"内存: {memory_percent:.1f}% (程序: {program_memory_mb:.0f}MB / 总计: {total_memory_mb:.0f}MB)")
        
        # 更新分段内存进度条
        self.system_memory_bar.setValue(int(system_other_memory_percent))
        self.program_memory_bar.setValue(int(program_memory_percent))
        
        # 根据使用率调整颜色
        if cpu_percent > 80:
            self.cpu_bar.setStyleSheet(self.cpu_bar.styleSheet().replace("#4CAF50", "#F44336"))
        elif cpu_percent > 60:
            self.cpu_bar.setStyleSheet(self.cpu_bar.styleSheet().replace("#4CAF50", "#FF9800"))
        else:
            self.cpu_bar.setStyleSheet(self.cpu_bar.styleSheet().replace("#F44336", "#4CAF50").replace("#FF9800", "#4CAF50"))
            
        # 根据总内存使用率调整系统内存条颜色
        if memory_percent > 80:
            self.system_memory_bar.setStyleSheet(self.system_memory_bar.styleSheet().replace("#2196F3", "#F44336"))
        elif memory_percent > 60:
            self.system_memory_bar.setStyleSheet(self.system_memory_bar.styleSheet().replace("#2196F3", "#FF9800"))
        else:
            self.system_memory_bar.setStyleSheet(self.system_memory_bar.styleSheet().replace("#F44336", "#2196F3").replace("#FF9800", "#2196F3"))
            
    def closeEvent(self, event):
        """关闭事件"""
        if hasattr(self, 'monitor'):
            self.monitor.stop()
        event.accept()
        
    def stop_monitoring(self):
        """停止监控"""
        if hasattr(self, 'monitor'):
            self.monitor.stop()