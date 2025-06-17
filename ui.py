from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTextEdit, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTabWidget, QGroupBox, 
                             QCheckBox, QMessageBox, QSplitter, QFrame, QSlider, QProgressBar, QSpinBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QFont
import time
from config import DEFAULT_PASSWORD, UI_CONFIG, OPERATION_DELAY
from automation import BrowserAutomation
from question_importer import QuestionImporter
from multi_thread_manager import MultiThreadManager
from system_monitor import ResourceWidget

class AutoAnswerApp(QMainWindow):
    def __init__(self, question_db):
        super().__init__()
        self.setWindowTitle(UI_CONFIG["window_title"])
        self.setGeometry(*UI_CONFIG["window_geometry"])
        self.accounts = []
        self.current_account_index = 0
        self.question_db = question_db
        self.browser_automation = None
        self.delay_multiplier = 1.0  # 延迟倍数，与延迟滑块同步
        self.multi_thread_manager = MultiThreadManager(question_db)  # 多线程管理器
        self.is_multithread_mode = False  # 是否启用多线程模式
        self.initUI()
        self.setup_multithread_signals()  # 设置多线程信号连接
        
    def initUI(self):
        # 设置全局字体为圆滑字体
        font = QFont()
        font.setFamily(UI_CONFIG["global_font_family"])
        font.setPointSize(9)
        self.setFont(font)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局https://infotech.51taoshi.com/hw/fore/index.do?out=1
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)  # 减少边距
        main_layout.setSpacing(5)  # 减少间距
        
        # 创建左侧控制面板
        control_panel = QWidget()
        control_panel.setMaximumWidth(UI_CONFIG["control_panel_width"])
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(5, 5, 5, 5)  # 减少控制面板内边距
        control_layout.setSpacing(3)  # 减少控制面板内组件间距
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 自动答题标签页
        auto_answer_tab = QWidget()
        auto_answer_layout = QVBoxLayout(auto_answer_tab)
        auto_answer_layout.setContentsMargins(3, 3, 3, 3)  # 减少标签页内边距
        auto_answer_layout.setSpacing(3)  # 减少标签页内组件间距
        
        # 账号管理部分
        accounts_group = QWidget()
        accounts_layout = QVBoxLayout(accounts_group)
        accounts_layout.setContentsMargins(3, 3, 3, 3)  # 减少账号管理区域内边距
        accounts_layout.setSpacing(2)  # 减少账号管理区域内组件间距
        
        accounts_label = QLabel("账号管理")
        accounts_label.setStyleSheet(UI_CONFIG["label_style"])
        accounts_layout.addWidget(accounts_label)
        
        # 添加账号输入区域
        account_input = QWidget()
        account_input_layout = QHBoxLayout(account_input)
        account_input_layout.setContentsMargins(0, 0, 0, 0)  # 减少账号输入区域内边距
        account_input_layout.setSpacing(3)  # 减少账号输入区域内组件间距
        account_input_layout.addWidget(QLabel("账号:"))
        self.account_edit = QLineEdit()
        self.account_edit.setPlaceholderText("输入单个账号或粘贴多行账号（支持批量添加）")
        account_input_layout.addWidget(self.account_edit)
        accounts_layout.addWidget(account_input)
        
        # 添加密码输入区域
        password_input = QWidget()
        password_input_layout = QHBoxLayout(password_input)
        password_input_layout.setContentsMargins(0, 0, 0, 0)  # 减少密码输入区域内边距
        password_input_layout.setSpacing(3)  # 减少密码输入区域内组件间距
        password_input_layout.addWidget(QLabel("密码:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText(f"留空则使用默认密码{DEFAULT_PASSWORD}")
        password_input_layout.addWidget(self.password_edit)
        accounts_layout.addWidget(password_input)
        
        # 添加账号按钮
        add_account_btn = QPushButton("添加账号")
        add_account_btn.clicked.connect(self.add_account)
        accounts_layout.addWidget(add_account_btn)
        
        # 使用说明
        help_label = QLabel("支持单个账号或多行账号批量添加\n多行账号请直接粘贴到账号输入框中")
        help_label.setStyleSheet("font-size: 11px; color: #666; margin-top: 5px; font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;")
        accounts_layout.addWidget(help_label)
        
        # 账号列表
        self.accounts_table = QTableWidget(0, 3)
        self.accounts_table.setHorizontalHeaderLabels(["账号", "密码", "状态"])
        self.accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        accounts_layout.addWidget(self.accounts_table)
        
        # 删除账号按钮
        delete_account_btn = QPushButton("删除选中账号")
        delete_account_btn.clicked.connect(self.delete_account)
        accounts_layout.addWidget(delete_account_btn)
        
        auto_answer_layout.addWidget(accounts_group)
        
        # 操作按钮
        operations_group = QWidget()
        operations_layout = QVBoxLayout(operations_group)
        operations_layout.setContentsMargins(3, 3, 3, 3)  # 减少操作控制区域内边距
        operations_layout.setSpacing(2)  # 减少操作控制区域内组件间距
        
        operations_label = QLabel("操作控制")
        operations_label.setStyleSheet(UI_CONFIG["label_style"])
        operations_layout.addWidget(operations_label)
        
        # 浏览器显示选项 - 已隐藏
        # self.show_browser_checkbox = QCheckBox("显示浏览器窗口（便于调试）")
        # self.show_browser_checkbox.setChecked(True)  # 默认显示
        # self.show_browser_checkbox.setToolTip("勾选后将显示真实的浏览器窗口，便于观察自动化过程")
        # operations_layout.addWidget(self.show_browser_checkbox)
        
        # 创建隐藏的复选框以保持代码兼容性
        self.show_browser_checkbox = QCheckBox()
        self.show_browser_checkbox.setChecked(True)  # 默认显示浏览器
        self.show_browser_checkbox.setVisible(False)  # 隐藏控件
        
        # 延迟控制已移至设置页面
        
        # 开始按钮
        self.start_btn = QPushButton("开始自动答题")
        self.start_btn.setStyleSheet(UI_CONFIG["start_button_style"])
        self.start_btn.clicked.connect(self.start_automation)
        operations_layout.addWidget(self.start_btn)
        
        # 暂停按钮
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.pause_automation)
        self.pause_btn.setEnabled(False)  # 初始状态禁用
        operations_layout.addWidget(self.pause_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_automation)
        self.stop_btn.setEnabled(False)  # 初始状态禁用
        operations_layout.addWidget(self.stop_btn)
        
        auto_answer_layout.addWidget(operations_group)
        
        # 题库管理标签页
        question_db_tab = QWidget()
        question_db_layout = QVBoxLayout(question_db_tab)
        question_db_layout.setContentsMargins(3, 3, 3, 3)  # 减少题库管理标签页内边距
        question_db_layout.setSpacing(3)  # 减少题库管理标签页内组件间距
        
        # 题库导入部分
        import_group = QWidget()
        import_layout = QVBoxLayout(import_group)
        import_layout.setContentsMargins(3, 3, 3, 3)  # 减少题库导入区域内边距
        import_layout.setSpacing(2)  # 减少题库导入区域内组件间距
        
        import_label = QLabel("题库导入")
        import_label.setStyleSheet(UI_CONFIG["label_style"])
        import_layout.addWidget(import_label)
        
        # 题目文本输入区域
        self.question_text = QTextEdit()
        self.question_text.setAcceptRichText(False)  # 只接受纯文本
        self.question_text.setPlaceholderText("请粘贴题目文本，支持两种格式：\n\n格式1（选择题）：\n1.(30分)题目内容\nA.选项A\nB.选项B\n...\n【正确答案：】X分\n\n格式2（简单主观题）：\n1.(40分)题目内容\n答案内容")
        import_layout.addWidget(self.question_text)
        
        # 导入按钮区域
        import_buttons_widget = QWidget()
        import_buttons_layout = QVBoxLayout(import_buttons_widget)
        import_buttons_layout.setContentsMargins(0, 0, 0, 0)
        import_buttons_layout.setSpacing(3)
        
        # 第一行按钮
        first_row_widget = QWidget()
        first_row_layout = QHBoxLayout(first_row_widget)
        first_row_layout.setContentsMargins(0, 0, 0, 0)
        first_row_layout.setSpacing(3)
        
        # 智能导入按钮（自动识别格式）
        smart_import_btn = QPushButton("智能导入（自动识别）")
        smart_import_btn.clicked.connect(self.import_questions)
        smart_import_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        first_row_layout.addWidget(smart_import_btn)
        
        # 简单主观题专用导入按钮
        subjective_import_btn = QPushButton("简单主观题导入")
        subjective_import_btn.clicked.connect(self.import_simple_subjective_questions)
        subjective_import_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        first_row_layout.addWidget(subjective_import_btn)
        
        import_buttons_layout.addWidget(first_row_widget)
        
        # 第二行按钮 - 从已完成账号导入题库
        import_from_account_btn = QPushButton("从已完成账号导入题库")
        import_from_account_btn.clicked.connect(self.import_from_completed_account)
        import_from_account_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; }")
        import_from_account_btn.setToolTip("登录其他已完成作业的账号，自动提取题库")
        import_buttons_layout.addWidget(import_from_account_btn)
        
        import_layout.addWidget(import_buttons_widget)
        
        question_db_layout.addWidget(import_group)
        
        # 题库查看部分
        view_group = QWidget()
        view_layout = QVBoxLayout(view_group)
        view_layout.setContentsMargins(3, 3, 3, 3)  # 减少题库查看区域内边距
        view_layout.setSpacing(2)  # 减少题库查看区域内组件间距
        
        view_label = QLabel("题库管理")
        view_label.setStyleSheet(UI_CONFIG["label_style"])
        view_layout.addWidget(view_label)
        
        # 题库列表
        self.questions_table = QTableWidget(0, 3)
        self.questions_table.setHorizontalHeaderLabels(["题目内容", "答案", "类型"])
        self.questions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.questions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        # 隐藏ID列（不再显示）
        view_layout.addWidget(self.questions_table)
        
        # 刷新和删除按钮
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(3)
        
        refresh_btn = QPushButton("刷新题库")
        refresh_btn.clicked.connect(self.refresh_questions)
        buttons_layout.addWidget(refresh_btn)
        
        delete_question_btn = QPushButton("删除选中题目")
        delete_question_btn.clicked.connect(self.delete_question)
        buttons_layout.addWidget(delete_question_btn)
        
        view_layout.addWidget(buttons_widget)
        
        question_db_layout.addWidget(view_group)
        
        # 设置标签页
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(3, 3, 3, 3)
        settings_layout.setSpacing(3)
        
        # 多线程设置组
        multithread_group = QWidget()
        multithread_layout = QVBoxLayout(multithread_group)
        multithread_layout.setContentsMargins(3, 3, 3, 3)
        multithread_layout.setSpacing(2)
        
        multithread_label = QLabel("多线程设置")
        multithread_label.setStyleSheet(UI_CONFIG["label_style"])
        multithread_layout.addWidget(multithread_label)
        
        # 多线程开关
        self.multithread_checkbox = QCheckBox("启用多线程模式")
        self.multithread_checkbox.setToolTip("启用后将同时打开多个浏览器窗口处理不同账号")
        self.multithread_checkbox.stateChanged.connect(self.on_multithread_changed)
        multithread_layout.addWidget(self.multithread_checkbox)
        
        # 线程数控制
        thread_count_widget = QWidget()
        thread_count_layout = QHBoxLayout(thread_count_widget)
        thread_count_layout.setContentsMargins(0, 0, 0, 0)
        thread_count_layout.setSpacing(5)
        
        thread_count_layout.addWidget(QLabel("线程数量:"))
        self.thread_count_spinbox = QSpinBox()
        self.thread_count_spinbox.setMinimum(1)
        self.thread_count_spinbox.setMaximum(32)
        
        # 获取CPU优化建议的线程数
        try:
            from cpu_optimization import get_cpu_optimizer
            cpu_optimizer = get_cpu_optimizer()
            optimal_threads = cpu_optimizer.get_optimal_thread_count()
            cpu_info = cpu_optimizer.get_cpu_info()
            self.thread_count_spinbox.setValue(optimal_threads)
            tooltip_text = f"设置同时运行的浏览器窗口数量（1-32）\n" \
                          f"CPU信息: {cpu_info['physical_cores']}物理核心, {cpu_info['logical_cores']}逻辑核心\n" \
                          f"建议线程数: {optimal_threads}"
            self.thread_count_spinbox.setToolTip(tooltip_text)
        except Exception:
            self.thread_count_spinbox.setValue(2)
            self.thread_count_spinbox.setToolTip("设置同时运行的浏览器窗口数量（1-32）")
        
        thread_count_layout.addWidget(self.thread_count_spinbox)
        thread_count_layout.addStretch()
        
        multithread_layout.addWidget(thread_count_widget)
        
        # 多线程说明
        try:
            from cpu_optimization import get_cpu_optimizer
            cpu_optimizer = get_cpu_optimizer()
            cpu_info = cpu_optimizer.get_cpu_info()
            help_text = f"注意：多线程模式会同时打开多个浏览器窗口\n" \
                       f"CPU: {cpu_info['physical_cores']}物理核心/{cpu_info['logical_cores']}逻辑核心，已启用CPU优化"
        except Exception:
            help_text = "注意：多线程模式会同时打开多个浏览器窗口\n建议根据电脑性能调整线程数量"
        
        multithread_help = QLabel(help_text)
        multithread_help.setStyleSheet("font-size: 11px; color: #666; margin-top: 5px; font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;")
        multithread_layout.addWidget(multithread_help)
        
        settings_layout.addWidget(multithread_group)
        
        # 操作延迟控制组
        delay_group = QWidget()
        delay_layout = QVBoxLayout(delay_group)
        delay_layout.setContentsMargins(3, 3, 3, 3)
        delay_layout.setSpacing(2)
        
        delay_label = QLabel("操作延迟控制")
        delay_label.setStyleSheet(UI_CONFIG["label_style"])
        delay_layout.addWidget(delay_label)
        
        delay_desc = QLabel("过低的延迟会导致程序卡顿")
        delay_desc.setStyleSheet("font-size: 11px; color: #666; font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;")
        delay_layout.addWidget(delay_desc)
        
        # 延迟值显示标签
        self.delay_value_label = QLabel(f"当前延迟: {OPERATION_DELAY['default']:.2f}秒")
        self.delay_value_label.setStyleSheet("font-size: 11px; color: #666; font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;")
        delay_layout.addWidget(self.delay_value_label)
        
        # 延迟滑块
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setMinimum(int(OPERATION_DELAY['min'] * 100))  # 转换为整数，精度0.01秒
        self.delay_slider.setMaximum(int(OPERATION_DELAY['max'] * 100))
        self.delay_slider.setValue(int(OPERATION_DELAY['default'] * 100))
        self.delay_slider.setToolTip(f"调整操作间延迟时间 ({OPERATION_DELAY['min']}s - {OPERATION_DELAY['max']}s)")
        self.delay_slider.valueChanged.connect(self.on_delay_changed)
        delay_layout.addWidget(self.delay_slider)
        
        # 延迟范围标签
        range_widget = QWidget()
        range_layout = QHBoxLayout(range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(0)
        
        min_label = QLabel(f"{OPERATION_DELAY['min']}s")
        min_label.setStyleSheet("font-size: 10px; color: #888; font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;")
        max_label = QLabel(f"{OPERATION_DELAY['max']}s")
        max_label.setStyleSheet("font-size: 10px; color: #888; font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;")
        
        range_layout.addWidget(min_label)
        range_layout.addStretch()
        range_layout.addWidget(max_label)
        
        delay_layout.addWidget(range_widget)
        settings_layout.addWidget(delay_group)
        
        # 日志管理组
        log_management_group = QWidget()
        log_management_layout = QVBoxLayout(log_management_group)
        log_management_layout.setContentsMargins(3, 3, 3, 3)
        log_management_layout.setSpacing(2)
        
        log_management_label = QLabel("日志管理")
        log_management_label.setStyleSheet(UI_CONFIG["label_style"])
        log_management_layout.addWidget(log_management_label)
        
        # 日志控制按钮
        log_controls = QWidget()
        log_controls_layout = QHBoxLayout(log_controls)
        log_controls_layout.setContentsMargins(0, 0, 0, 0)
        log_controls_layout.setSpacing(3)
        
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.clear_log)
        log_controls_layout.addWidget(clear_log_btn)
        
        clean_log_files_btn = QPushButton("清理日志文件")
        clean_log_files_btn.clicked.connect(self.clean_log_files)
        log_controls_layout.addWidget(clean_log_files_btn)
        
        log_management_layout.addWidget(log_controls)
        settings_layout.addWidget(log_management_group)
        
        # 系统监控组
        system_monitor_group = QWidget()
        system_monitor_layout = QVBoxLayout(system_monitor_group)
        system_monitor_layout.setContentsMargins(3, 3, 3, 3)
        system_monitor_layout.setSpacing(2)
        
        # 添加系统监控组件
        self.resource_widget = ResourceWidget()
        system_monitor_layout.addWidget(self.resource_widget)
        settings_layout.addWidget(system_monitor_group)
        
        # 添加弹性空间
        settings_layout.addStretch()
        
        # 添加标签页
        tab_widget.addTab(auto_answer_tab, "自动答题")
        tab_widget.addTab(question_db_tab, "题库管理")
        tab_widget.addTab(settings_tab, "设置")
        control_layout.addWidget(tab_widget)
        main_layout.addWidget(control_panel)
        
        # 日志区域
        log_group = QWidget()
        log_group.setFixedWidth(400)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(3, 3, 3, 3)
        log_layout.setSpacing(2)
        
        log_label = QLabel("运行日志")
        log_label.setStyleSheet(UI_CONFIG["label_style"])
        log_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # 日志控制按钮已移至设置页面
        
        # 添加日志区域到主布局
        main_layout.addWidget(log_group)
        
        # 创建整体布局（包含主布局和进度条）
        overall_layout = QVBoxLayout()
        overall_layout.setContentsMargins(0, 0, 0, 0)
        overall_layout.setSpacing(0)
        
        # 创建主内容区域
        main_content = QWidget()
        main_content.setLayout(main_layout)
        overall_layout.addWidget(main_content)
        
        # 创建底部进度条
        self.status_bar = QProgressBar()
        self.status_bar.setFixedHeight(25)
        self.status_bar.setTextVisible(True)
        self.status_bar.setFormat("就绪")
        self.status_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
                font-family: 'Microsoft YaHei';
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        overall_layout.addWidget(self.status_bar)
        
        # 设置整体布局到中央窗口
        central_widget.setLayout(overall_layout)
        
        # 初始化进度条状态
        self.error_flash_timer = None
        self.flash_count = 0
        
        # 进度条动画相关属性
        self.progress_animation_timer = QTimer()
        self.progress_animation_timer.timeout.connect(self.animate_progress)
        self.target_progress = 0
        self.current_progress = 0
        self.progress_step = 1
        
        # 初始化题库
        self.refresh_questions()
        
        # 启动时进行环境检查
        self.check_environment()
        
        # 启动时清理日志文件
        self.clean_log_files(silent=True)
    
    def update_status_bar(self, message, progress=None, is_error=False):
        """更新状态栏信息"""
        self.status_bar.setFormat(message)
        if progress is not None:
            # 使用动画更新进度
            self.target_progress = progress
            if not self.progress_animation_timer.isActive():
                self.progress_animation_timer.start(20)
        
        if is_error:
            self.start_error_flash()
        else:
            self.stop_error_flash()
    
    def start_error_flash(self):
        """开始错误闪烁效果"""
        if self.error_flash_timer:
            self.error_flash_timer.stop()
        
        self.error_flash_timer = QTimer()
        self.error_flash_timer.timeout.connect(self.flash_error)
        self.flash_count = 0
        self.error_flash_timer.start(300)  # 每300ms闪烁一次
    
    def stop_error_flash(self):
        """停止错误闪烁效果"""
        if self.error_flash_timer:
            self.error_flash_timer.stop()
            self.error_flash_timer = None
        
        # 恢复正常样式
        self.status_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
                font-family: 'Microsoft YaHei';
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
    
    def flash_error(self):
        """错误闪烁效果"""
        self.flash_count += 1
        
        if self.flash_count % 2 == 0:
            # 红色
            self.status_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    text-align: center;
                    font-family: 'Microsoft YaHei';
                    font-size: 12px;
                    background-color: #ffebee;
                }
                QProgressBar::chunk {
                    background-color: #f44336;
                    border-radius: 2px;
                }
            """)
        else:
            # 白色
            self.status_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    text-align: center;
                    font-family: 'Microsoft YaHei';
                    font-size: 12px;
                    background-color: white;
                }
                QProgressBar::chunk {
                    background-color: #ddd;
                    border-radius: 2px;
                }
            """)
        
        # 闪烁10次后停止
        if self.flash_count >= 20:
            self.stop_error_flash()
        
    def add_account(self):
        account = self.account_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not account:
            self.update_status_bar("请输入账号！", is_error=True)
            return
        
        # 检查是否包含换行符（多个账号）
        import re
        if re.search(r'[\r\n]', account):
            # 如果包含换行符，直接进行批量处理
            self.log("检测到多行账号，开始批量添加...")
            self.process_multiple_accounts(account)
            self.account_edit.clear()
            return
            
        if not password:
            password = DEFAULT_PASSWORD
            
        # 验证账号格式（只包含数字）
        if not account.isdigit():
            self.update_status_bar(f"账号格式无效: {account} (账号只能包含数字)", is_error=True)
            return
            
        # 检查是否已存在
        for existing_account in self.accounts:
            if existing_account["username"] == account:
                self.update_status_bar(f"账号已存在: {account}", is_error=True)
                return
            
        # 添加到账号列表
        row_position = self.accounts_table.rowCount()
        self.accounts_table.insertRow(row_position)
        self.accounts_table.setItem(row_position, 0, QTableWidgetItem(account))
        self.accounts_table.setItem(row_position, 1, QTableWidgetItem("*" * len(password)))
        self.accounts_table.setItem(row_position, 2, QTableWidgetItem("待处理"))
        
        # 添加到账号数组
        self.accounts.append({"username": account, "password": password, "status": "待处理"})
        
        # 清空输入框
        self.account_edit.clear()
        self.password_edit.clear()
        self.log(f"已添加账号: {account}")
    
    def process_multiple_accounts(self, text):
        """处理多个账号"""
        text = text.strip()
        if not text:
            self.log("没有检测到有效的账号内容")
            return
        
        # 处理不同的换行符格式（\n, \r\n, \r）
        import re
        lines = re.split(r'[\r\n]+', text)
        added_count = 0
        
        self.log(f"开始处理批量账号，共检测到 {len(lines)} 行")
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                self.log(f"第{i}行为空，跳过")
                continue
                
            self.log(f"处理第{i}行: {line}")
                
            # 检查是否包含密码（格式：账号:密码）
            if ':' in line:
                parts = line.split(':', 1)
                account = parts[0].strip()
                password = parts[1].strip()
            else:
                account = line
                password = DEFAULT_PASSWORD
            
            # 验证账号格式（只包含数字）
            if not account.isdigit():
                self.log(f"跳过无效账号格式: {account}")
                continue
            
            # 检查是否已存在
            account_exists = False
            for existing_account in self.accounts:
                if existing_account["username"] == account:
                    account_exists = True
                    break
            
            if account_exists:
                self.log(f"账号已存在，跳过: {account}")
                continue
            
            # 添加到账号列表
            row_position = self.accounts_table.rowCount()
            self.accounts_table.insertRow(row_position)
            self.accounts_table.setItem(row_position, 0, QTableWidgetItem(account))
            self.accounts_table.setItem(row_position, 1, QTableWidgetItem("*" * len(password)))
            self.accounts_table.setItem(row_position, 2, QTableWidgetItem("待处理"))
            
            # 添加到账号数组
            self.accounts.append({"username": account, "password": password, "status": "待处理"})
            self.log(f"已添加账号: {account}")
            added_count += 1
        
        if added_count > 0:
            self.log(f"批量添加完成，成功添加 {added_count} 个账号")
        else:
            self.log("没有添加任何账号，请检查输入格式")
        
    def delete_account(self):
        selected_rows = self.accounts_table.selectionModel().selectedRows()
        if not selected_rows:
            self.update_status_bar("请先选择要删除的账号！", is_error=True)
            return
            
        for row in sorted(selected_rows, reverse=True):
            index = row.row()
            account = self.accounts[index]["username"]
            self.accounts_table.removeRow(index)
            self.accounts.pop(index)
            self.log(f"已删除账号: {account}")
    
    # start_automation方法已移至文件末尾，支持多线程模式
    
    # pause_automation, stop_automation, on_automation_finished 方法已移至文件末尾，支持多线程模式
    
    def update_account_status(self, account_index, status):
        if 0 <= account_index < self.accounts_table.rowCount():
            self.accounts_table.setItem(account_index, 2, QTableWidgetItem(status))
            self.accounts[account_index]["status"] = status
    
    def update_progress(self, progress, description):
        """更新进度条和状态描述"""
        # 更新状态描述
        self.status_bar.setFormat(description)
        
        # 启动平滑动画到目标进度
        self.target_progress = progress
        if not self.progress_animation_timer.isActive():
            self.progress_animation_timer.start(20)  # 每20ms更新一次，实现平滑动画
    
    def animate_progress(self):
        """进度条动画方法"""
        if self.current_progress < self.target_progress:
            # 计算动画步长，距离越远步长越大
            distance = self.target_progress - self.current_progress
            self.progress_step = max(1, distance // 10)  # 至少1，最多距离的1/10
            self.current_progress = min(self.current_progress + self.progress_step, self.target_progress)
        elif self.current_progress > self.target_progress:
            # 向下动画（虽然不常见）
            distance = self.current_progress - self.target_progress
            self.progress_step = max(1, distance // 10)
            self.current_progress = max(self.current_progress - self.progress_step, self.target_progress)
        
        # 更新进度条显示
        self.status_bar.setValue(self.current_progress)
        
        # 如果到达目标进度，停止动画
        if self.current_progress == self.target_progress:
            self.progress_animation_timer.stop()
    
    def on_delay_changed(self, value):
        """处理延迟滑块值变化"""
        delay_seconds = value / 100.0  # 转换回秒数
        self.delay_value_label.setText(f"当前延迟: {delay_seconds:.2f}秒")
        
        # 更新延迟倍数（基于默认延迟的倍数）
        self.delay_multiplier = delay_seconds / OPERATION_DELAY['default']
        
        # 如果自动化正在运行，更新其延迟设置
        if hasattr(self, 'browser_automation') and self.browser_automation:
            self.browser_automation.set_operation_delay(delay_seconds)
    
    def get_current_delay(self):
        """获取当前设置的延迟时间"""
        return self.delay_slider.value() / 100.0
    

    
    def log(self, message, color=None):
        timestamp = time.strftime("%H:%M:%S")
        if color:
            formatted_message = f"<span style='color: {color};'>[{timestamp}] {message}</span>"
            self.log_text.append(formatted_message)
        else:
            self.log_text.append(f"[{timestamp}] {message}")
        
        # 限制日志行数
        max_lines = 1000
        document = self.log_text.document()
        if document.blockCount() > max_lines:
            # 删除前面的行，保留最新的日志
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, document.blockCount() - max_lines)
            cursor.removeSelectedText()
        
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum())
        # 减少界面刷新频率，提高性能
        if not hasattr(self, '_last_refresh') or time.time() - self._last_refresh > 0.1:
            QApplication.processEvents()
            self._last_refresh = time.time()
            
        # 检查并自动清理日志文件
        self.auto_clean_log_files()
        
    def import_questions(self):
        # 获取文本内容
        text = self.question_text.toPlainText().strip()
        if not text:
            self.update_status_bar("请先输入题目文本！", is_error=True)
            return
            
        # 创建导入器并导入题目
        importer = QuestionImporter(self.question_db)
        try:
            result = importer.import_from_text(text)
            if result["success"]:
                self.update_status_bar(f"成功导入{result['imported_count']}个题目！")
                self.log(f"智能导入成功：{result['imported_count']}个题目")
                # 清空文本框
                self.question_text.clear()
                # 刷新题库显示
                self.refresh_questions()
            else:
                self.update_status_bar(result["message"], is_error=True)
                self.log(f"智能导入失败: {result['message']}")
        except KeyboardInterrupt:
            self.log("导入操作被用户中断")
            self.update_status_bar("导入操作被用户中断", is_error=True)
        except Exception as e:
            self.update_status_bar(f"导入过程中发生错误: {str(e)}", is_error=True)
            self.log(f"智能导入错误: {str(e)}")
    
    def import_simple_subjective_questions(self):
        # 获取文本内容
        text = self.question_text.toPlainText().strip()
        if not text:
            self.update_status_bar("请先输入题目文本！", is_error=True)
            return
            
        # 创建导入器并使用简单主观题专用方法导入题目
        importer = QuestionImporter(self.question_db)
        try:
            result = importer.import_simple_subjective_from_text(text)
            if result["success"]:
                self.update_status_bar(f"成功导入{result['imported_count']}个简单主观题！")
                self.log(f"简单主观题导入成功：{result['imported_count']}个题目")
                # 清空文本框
                self.question_text.clear()
                # 刷新题库显示
                self.refresh_questions()
            else:
                self.update_status_bar(result["message"], is_error=True)
                self.log(f"简单主观题导入失败: {result['message']}")
        except KeyboardInterrupt:
            self.log("导入操作被用户中断")
            self.update_status_bar("导入操作被用户中断", is_error=True)
        except Exception as e:
            self.update_status_bar(f"导入过程中发生错误: {str(e)}", is_error=True)
            self.log(f"简单主观题导入错误: {str(e)}")
    
    def import_from_completed_account(self):
        """从已完成账号导入题库"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar
        
        # 创建账号输入对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("从已完成账号导入题库")
        dialog.setFixedSize(400, 200)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # 说明标签
        info_label = QLabel("请输入已完成作业的账号信息，程序将自动登录并提取题库：")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 账号输入
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("账号:"))
        account_input = QLineEdit()
        account_input.setPlaceholderText("输入账号")
        account_layout.addWidget(account_input)
        layout.addLayout(account_layout)
        
        # 密码输入
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("密码:"))
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        password_input.setPlaceholderText(f"留空使用默认密码({DEFAULT_PASSWORD})")
        password_layout.addWidget(password_input)
        layout.addLayout(password_layout)
        
        # 进度条
        progress_bar = QProgressBar()
        progress_bar.setVisible(False)
        layout.addWidget(progress_bar)
        
        # 按钮
        button_layout = QHBoxLayout()
        start_btn = QPushButton("开始导入")
        cancel_btn = QPushButton("取消")
        button_layout.addWidget(start_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # 按钮事件
        cancel_btn.clicked.connect(dialog.reject)
        
        def start_import():
            account = account_input.text().strip()
            password = password_input.text().strip() or DEFAULT_PASSWORD
            
            if not account:
                self.update_status_bar("请输入账号！", is_error=True)
                return
            
            # 禁用按钮，显示进度条
            start_btn.setEnabled(False)
            cancel_btn.setEnabled(False)
            progress_bar.setVisible(True)
            progress_bar.setRange(0, 100)  # 设置为百分比进度条
            progress_bar.setValue(0)
            progress_bar.setFormat("准备开始导入... (0%)")
            
            # 关闭弹窗
            dialog.accept()
            
            # 在主界面显示进度
            self.update_status_bar("正在从已完成账号导入题库...", progress=0)
            
            # 启动导入线程
            self.start_question_import_thread(account, password)
        
        start_btn.clicked.connect(start_import)
        
        dialog.exec_()
    
    def start_question_import_thread(self, account, password):
        """启动题库导入线程"""
        from PyQt5.QtCore import QThread, pyqtSignal
        
        class QuestionImportThread(QThread):
            log_signal = pyqtSignal(str)
            finished_signal = pyqtSignal(bool, str, int)
            progress_signal = pyqtSignal(int, str)  # 进度信号
            
            def __init__(self, account, password, question_db, delay_multiplier=1.0):
                super().__init__()
                self.account = account
                self.password = password
                self.question_db = question_db
                self.delay_multiplier = delay_multiplier
                self.running = True
            
            def run(self):
                try:
                    from automation import QuestionBankImporter
                    # 创建导入器时显式设置显示浏览器窗口
                    importer = QuestionBankImporter(self.question_db, show_browser=True)
                    importer.log_signal.connect(self.log_signal.emit)
                    importer.progress_signal.connect(self.progress_signal.emit)
                    # 传递当前的延迟倍数设置
                    importer.set_delay_multiplier(self.delay_multiplier)
                    
                    result = importer.import_from_completed_account(self.account, self.password)
                    
                    if result["success"]:
                        self.finished_signal.emit(True, f"成功导入{result['imported_count']}个题目！", result['imported_count'])
                    else:
                        self.finished_signal.emit(False, result["message"], 0)
                        
                except Exception as e:
                    self.finished_signal.emit(False, f"导入过程中发生错误: {str(e)}", 0)
        
        # 创建并启动线程
        self.import_thread = QuestionImportThread(account, password, self.question_db, self.delay_multiplier)
        
        # 连接信号
        self.import_thread.log_signal.connect(self.log)
        
        def on_import_progress(percentage, description):
            # 更新主界面进度条
            self.update_status_bar(description, progress=percentage)
        
        self.import_thread.progress_signal.connect(on_import_progress)
        
        def on_import_finished(success, message, count):
            if success:
                self.update_status_bar(f"题库导入成功！共导入 {count} 个题目", progress=100)
                self.refresh_questions()  # 刷新题库显示
                QMessageBox.information(self, "导入成功", message)
            else:
                self.update_status_bar(f"题库导入失败: {message}", is_error=True)
                QMessageBox.warning(self, "导入失败", message)
        
        self.import_thread.finished_signal.connect(on_import_finished)
        self.import_thread.start()
    
    def refresh_questions(self):
        # 获取所有题目
        questions = self.question_db.get_all_questions()
        
        # 清空表格
        self.questions_table.setRowCount(0)
        
        # 填充表格
        for question in questions:
            row_position = self.questions_table.rowCount()
            self.questions_table.insertRow(row_position)
            
            # 设置题目内容（截断过长的内容）
            question_content = question[1]
            if len(question_content) > 50:
                question_content = question_content[:47] + "..."
            self.questions_table.setItem(row_position, 0, QTableWidgetItem(question_content))
            
            # 设置答案（截断过长的内容）
            answer_content = question[2]
            if len(answer_content) > 30:
                answer_content = answer_content[:27] + "..."
            self.questions_table.setItem(row_position, 1, QTableWidgetItem(answer_content))
            
            # 设置类型
            question_type = "选择题" if question[3] == "choice" else "主观题"
            self.questions_table.setItem(row_position, 2, QTableWidgetItem(question_type))
            
            # 存储原始ID用于删除操作
            self.questions_table.item(row_position, 0).setData(Qt.UserRole, question[0])
        
        self.log(f"已刷新题库，共{len(questions)}个题目")
    
    def delete_question(self):
        selected_rows = self.questions_table.selectionModel().selectedRows()
        if not selected_rows:
            self.update_status_bar("请先选择要删除的题目！", is_error=True)
            return
            
        # 确认删除
        reply = QMessageBox.question(self, "确认删除", 
                                   f"确定要删除选中的{len(selected_rows)}个题目吗？", 
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        if reply == QMessageBox.No:
            return
            
        # 执行删除
        deleted_count = 0
        for row in sorted(selected_rows, reverse=True):
            index = row.row()
            # 从UserRole数据中获取题目ID
            question_id = self.questions_table.item(index, 0).data(Qt.UserRole)
            try:
                self.question_db.delete_question(question_id)
                deleted_count += 1
            except Exception as e:
                self.log(f"删除题目ID:{question_id}失败: {str(e)}")
        
        # 刷新题库
        self.refresh_questions()
        self.log(f"已删除{deleted_count}个题目")
        QMessageBox.information(self, "删除成功", f"成功删除{deleted_count}个题目！")
    
    def clear_log(self):
        """清空当前显示的日志"""
        self.log_text.clear()
        self.log("日志已清空")
    
    def check_environment(self):
        """检查运行环境，主要检查外部依赖"""
        import os
        import subprocess
        import platform
        
        self.log("正在进行环境检查...")
        
        # 检查操作系统
        os_info = platform.system() + " " + platform.release()
        self.log(f"✓ 操作系统: {os_info}")
        
        # 检查Chrome浏览器（这是唯一真正需要的外部依赖）
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        chrome_found = False
        chrome_version = None
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                chrome_found = True
                # 尝试获取Chrome版本
                try:
                    result = subprocess.run([chrome_path, "--version"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        chrome_version = result.stdout.strip()
                except:
                    pass
                self.log(f"✓ Chrome浏览器已找到: {chrome_path}")
                if chrome_version:
                    self.log(f"  版本: {chrome_version}")
                break
        
        if not chrome_found:
            # 尝试通过命令行检查
            try:
                result = subprocess.run(["chrome", "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    chrome_found = True
                    chrome_version = result.stdout.strip()
                    self.log("✓ Chrome浏览器已找到（通过PATH环境变量）")
                    self.log(f"  版本: {chrome_version}")
            except:
                pass
        
        if not chrome_found:
            self.log("✗ 未找到Chrome浏览器！程序无法正常运行", color="red")
            self.log("请安装Chrome浏览器：https://www.google.com/chrome/", color="red")
            self.log("注意：程序需要Chrome浏览器来进行网页自动化操作", color="red")
        
        # 检查网络连接（尝试访问目标网站）
        try:
            import urllib.request
            import urllib.error
            
            # 简单的网络连接测试
            urllib.request.urlopen('https://www.baidu.com', timeout=5)
            self.log("✓ 网络连接正常")
        except urllib.error.URLError:
            self.log("⚠ 网络连接可能有问题，请检查网络设置", color="orange")
        except Exception:
            self.log("⚠ 无法测试网络连接", color="orange")
        
        # 检查系统权限（尝试创建临时文件）
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp.write(b'test')
            self.log("✓ 系统文件权限正常")
        except Exception as e:
            self.log(f"⚠ 系统文件权限可能有问题: {str(e)}", color="orange")
        
        self.log("环境检查完成")
        self.log("提示：程序已打包所有必需的Python模块和数据文件")
    
    def auto_clean_log_files(self):
        """自动清理日志文件，当文件超过300KB时"""
        import os
        
        # 避免频繁检查，每分钟最多检查一次
        current_time = time.time()
        if hasattr(self, '_last_auto_clean_check'):
            if current_time - self._last_auto_clean_check < 60:  # 60秒内不重复检查
                return
        
        self._last_auto_clean_check = current_time
        
        log_files = ['app_error.log', 'dist/app_error.log']
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    file_size = os.path.getsize(log_file)
                    # 如果文件大于300KB，则自动清理
                    if file_size > 300 * 1024:  # 300KB
                        # 保留最后500行
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        
                        if len(lines) > 500:
                            with open(log_file, 'w', encoding='utf-8') as f:
                                f.write(f"=== 日志文件已自动清理（超过300KB），保留最新500行 ===\n")
                                f.writelines(lines[-500:])
                            
                            old_kb = file_size / 1024
                            new_size = os.path.getsize(log_file)
                            new_kb = new_size / 1024
                            self.log(f"自动清理日志文件: {log_file} ({old_kb:.1f}KB → {new_kb:.1f}KB)")
                except Exception as e:
                    # 静默处理错误，避免影响正常使用
                    pass
    
    def clean_log_files(self, silent=False):
        """手动清理日志文件，删除过大的日志文件"""
        import os
        import glob
        
        log_files = ['app_error.log', 'dist/app_error.log']
        cleaned_files = []
        total_size_before = 0
        total_size_after = 0
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    file_size = os.path.getsize(log_file)
                    total_size_before += file_size
                    
                    # 如果文件大于5MB，则清理
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        # 保留最后1000行
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        
                        if len(lines) > 1000:
                            with open(log_file, 'w', encoding='utf-8') as f:
                                f.write(f"=== 日志文件已清理，保留最新1000行 ===\n")
                                f.writelines(lines[-1000:])
                            
                            new_size = os.path.getsize(log_file)
                            total_size_after += new_size
                            cleaned_files.append({
                                'file': log_file,
                                'old_size': file_size,
                                'new_size': new_size
                            })
                        else:
                            total_size_after += file_size
                    else:
                        total_size_after += file_size
                except Exception as e:
                    if not silent:
                        self.log(f"清理日志文件 {log_file} 时出错: {str(e)}")
        
        if cleaned_files and not silent:
            message = "日志文件清理完成:\n"
            for item in cleaned_files:
                old_mb = item['old_size'] / (1024 * 1024)
                new_mb = item['new_size'] / (1024 * 1024)
                message += f"- {item['file']}: {old_mb:.1f}MB → {new_mb:.1f}MB\n"
            
            total_saved = (total_size_before - total_size_after) / (1024 * 1024)
            if total_saved > 0:
                message += f"总共节省空间: {total_saved:.1f}MB"
            
            self.log(message)
    
    def setup_multithread_signals(self):
        """设置多线程信号连接"""
        self.multi_thread_manager.log_signal.connect(self.log)
        self.multi_thread_manager.status_signal.connect(self.update_account_status)
        self.multi_thread_manager.progress_signal.connect(self.update_progress)
        self.multi_thread_manager.all_finished_signal.connect(self.on_automation_finished)
    
    def on_multithread_changed(self, state):
        """多线程模式切换"""
        self.is_multithread_mode = state == Qt.Checked
        self.thread_count_spinbox.setEnabled(self.is_multithread_mode)
        
        if self.is_multithread_mode:
            self.log("已启用多线程模式")
        else:
            self.log("已禁用多线程模式")
    
    def start_automation(self):
        """开始自动化（支持单线程和多线程模式）"""
        if not self.accounts:
            self.log("请先添加账号")
            return
        
        if self.is_multithread_mode:
            self.start_multithread_automation()
        else:
            self.start_singlethread_automation()
    
    def start_singlethread_automation(self):
        """开始单线程自动化（原有逻辑）"""
        if self.browser_automation and self.browser_automation.isRunning():
            self.log("自动化程序正在运行中...")
            return
        
        # 根据用户选择更新浏览器显示配置
        import config
        config.SHOW_BROWSER_WINDOW = self.show_browser_checkbox.isChecked()
        
        if config.SHOW_BROWSER_WINDOW:
            self.log("已启用浏览器窗口显示，您可以观察自动化过程")
        else:
            self.log("浏览器将在后台运行（无头模式）")
        
        self.browser_automation = BrowserAutomation(self.accounts, self.question_db)
        self.browser_automation.set_operation_delay(self.delay_multiplier * OPERATION_DELAY['default'])
        
        # 连接信号
        self.browser_automation.log_signal.connect(self.log)
        self.browser_automation.status_signal.connect(self.update_account_status)
        self.browser_automation.progress_signal.connect(self.update_progress)
        self.browser_automation.finished.connect(self.on_automation_finished)
        
        # 启动自动化
        self.browser_automation.start()
        
        # 更新按钮状态
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setText("暂停")
        
        self.log("开始单线程自动答题...")
        self.update_status_bar(f"自动答题已启动 - 共{len(self.accounts)}个账号", progress=0)
        if config.SHOW_BROWSER_WINDOW:
            self.log("请关注外部Chrome浏览器窗口查看自动化进度")
        else:
            self.log("自动化进程已在后台运行，请查看日志了解进度")
    
    def start_multithread_automation(self):
        """开始多线程自动化"""
        if self.multi_thread_manager.running:
            self.log("多线程自动化程序正在运行中...")
            return
        
        # 设置多线程参数
        thread_count = self.thread_count_spinbox.value()
        self.multi_thread_manager.set_thread_count(thread_count)
        self.multi_thread_manager.set_delay_multiplier(self.delay_multiplier)
        
        # 启动多线程自动化
        self.multi_thread_manager.start_automation(self.accounts)
        
        # 更新按钮状态
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setText("暂停")
        
        self.log(f"开始多线程自动答题，使用 {thread_count} 个线程...")
    
    def pause_automation(self):
        """暂停/恢复自动化"""
        if self.is_multithread_mode:
            if self.multi_thread_manager.paused:
                self.multi_thread_manager.resume_automation()
                self.pause_btn.setText("暂停")
                self.log("已恢复多线程自动化")
                self.update_status_bar("多线程自动化已恢复")
            else:
                self.multi_thread_manager.pause_automation()
                self.pause_btn.setText("恢复")
                self.log("已暂停多线程自动化")
                self.update_status_bar("多线程自动化已暂停")
        else:
            if self.browser_automation and self.browser_automation.isRunning():
                if self.browser_automation.paused:
                    self.browser_automation.paused = False
                    self.pause_btn.setText("暂停")
                    self.log("已恢复自动答题")
                    self.update_status_bar("自动答题已恢复")
                else:
                    self.browser_automation.paused = True
                    self.pause_btn.setText("恢复")
                    self.log("已暂停自动答题")
                    self.update_status_bar("自动答题已暂停")
            else:
                self.update_status_bar("没有正在运行的自动化进程！", is_error=True)
    
    def stop_automation(self):
        """停止自动化"""
        # 确认停止
        reply = QMessageBox.question(self, "确认停止", 
                                   "确定要停止自动答题吗？", 
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        # 立即禁用按钮，防止重复点击
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        
        self.log("正在停止自动答题...")
        self.update_status_bar("正在停止自动答题...")
        
        # 使用清理管理器异步停止
        try:
            from cleanup_manager import get_cleanup_manager
            cleanup_manager = get_cleanup_manager()
            cleanup_manager.log_signal.connect(self.log)
            cleanup_manager.cleanup_finished.connect(self.on_stop_cleanup_finished)
            
            if self.is_multithread_mode:
                # 收集需要清理的资源
                workers = self.multi_thread_manager.workers if hasattr(self.multi_thread_manager, 'workers') else []
                drivers = []
                for worker in workers:
                    if hasattr(worker, 'automation') and worker.automation and hasattr(worker.automation, 'driver'):
                        drivers.append(worker.automation.driver)
                
                # 设置停止标志
                self.multi_thread_manager.running = False
                
                # 异步清理
                cleanup_manager.immediate_cleanup(drivers=drivers, workers=workers)
            else:
                drivers = []
                if self.browser_automation and hasattr(self.browser_automation, 'driver'):
                    drivers.append(self.browser_automation.driver)
                
                if self.browser_automation and self.browser_automation.isRunning():
                    self.browser_automation.running = False
                
                cleanup_manager.immediate_cleanup(drivers=drivers)
        except Exception as e:
            self.log(f"停止过程中发生错误: {str(e)}")
            self.on_stop_cleanup_finished()  # 确保按钮状态恢复
    
    def on_stop_cleanup_finished(self):
        """停止清理完成后的回调"""
        # 清理多线程管理器
        if self.is_multithread_mode and hasattr(self, 'multi_thread_manager'):
            self.multi_thread_manager.workers = []
        
        # 重置按钮状态
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("暂停")
        
        self.log("自动答题已停止")
        self.update_status_bar("自动答题已停止")
    
    def on_automation_finished(self):
        """自动化完成回调"""
        # 更新按钮状态
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("暂停")
        
        if self.is_multithread_mode:
            self.log("多线程自动化已完成")
            self.update_status_bar("多线程自动化已完成", progress=100)
        else:
            self.log("单线程自动化已完成")
            self.update_status_bar("单线程自动化已完成", progress=100)
        
        # 播放完成提示音（如果系统支持）
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_OK)
        except:
            pass
        
        # 显示完成通知
        QMessageBox.information(self, "自动化完成", "所有账号的自动答题已完成！")
    
    def closeEvent(self, event):
        """程序关闭事件处理"""
        # 如果有正在运行的任务，询问用户是否确认关闭
        if ((hasattr(self, 'multi_thread_manager') and self.multi_thread_manager.running) or 
            (hasattr(self, 'browser_automation') and self.browser_automation and self.browser_automation.isRunning())):
            
            reply = QMessageBox.question(self, "确认关闭", 
                                       "程序正在运行中，确定要关闭吗？\n关闭可能需要几秒钟来清理资源。", 
                                       QMessageBox.Yes | QMessageBox.No, 
                                       QMessageBox.No)
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        
        # 停止系统监控
        if hasattr(self, 'resource_widget'):
            self.resource_widget.stop_monitoring()
        
        # 使用异步清理管理器
        try:
            from cleanup_manager import get_cleanup_manager
            cleanup_manager = get_cleanup_manager()
            
            # 收集需要清理的资源
            drivers = []
            workers = []
            
            if hasattr(self, 'multi_thread_manager') and self.multi_thread_manager.workers:
                workers = self.multi_thread_manager.workers
                for worker in workers:
                    if hasattr(worker, 'automation') and worker.automation and hasattr(worker.automation, 'driver'):
                        drivers.append(worker.automation.driver)
                self.multi_thread_manager.running = False
            
            if hasattr(self, 'browser_automation') and self.browser_automation:
                if hasattr(self.browser_automation, 'driver'):
                    drivers.append(self.browser_automation.driver)
                self.browser_automation.running = False
            
            # 如果有资源需要清理，进行快速清理
            if drivers or workers:
                cleanup_manager.cleanup_chrome_processes_fast()
                
                # 快速清理线程
                if workers:
                    cleanup_manager.cleanup_threads_gracefully(workers, 2)
        
        except Exception as e:
            print(f"关闭清理时发生错误: {str(e)}")
        
        event.accept()