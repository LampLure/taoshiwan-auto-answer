# 配置信息和常量

import os
import sys

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发环境和打包后的环境"""
    try:
        # PyInstaller创建临时文件夹，并将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境中使用当前目录
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# 网站URL
WEBSITE_URL = "https://infotech.51taoshi.com/hw/fore/index.do"

# 默认密码
DEFAULT_PASSWORD = "123456"

# 数据库文件路径
DATABASE_PATH = get_resource_path("questions.db")

# 浏览器配置
# 浏览器显示设置
SHOW_BROWSER_WINDOW = True  # 强制显示外部浏览器窗口，作为主要显示界面
USE_EXTERNAL_BROWSER_AS_DISPLAY = True  # 使用外部浏览器作为主要显示界面

BROWSER_OPTIONS = [
    # 禁用GPU加速，避免一些渲染问题
    "--disable-gpu",
    # 禁用沙盒模式，避免一些权限问题
    "--no-sandbox",
    # 禁用开发者工具
    "--disable-dev-shm-usage",
    # 设置窗口大小，与QWebEngineView匹配
    "--window-size=1200,800",
    # 禁用扩展
    "--disable-extensions",
    # 禁用默认浏览器检查
    "--no-default-browser-check",
    # 禁用首次运行界面
    "--no-first-run",
    # 禁用弹出窗口阻止
    "--disable-popup-blocking",
    # 启用自动化
    "--enable-automation",
    # 增加稳定性配置
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-features=TranslateUI",
    "--disable-ipc-flooding-protection",
    "--disable-background-networking",
    "--disable-sync",
    "--disable-default-apps",
    "--disable-component-extensions-with-background-pages",
    # 内存管理
    "--memory-pressure-off",
    "--max_old_space_size=4096",
    # 进程管理
    "--disable-web-security",
    # 日志级别
    "--log-level=3"
]

# XPath选择器
# XPath选择器
XPATHS = {
    # 登录页面
    "login_button": "//a[contains(text(), '登录')]|//a[@onclick='showLoginModal()']|//a[contains(@class, 'login')]|//button[contains(text(), '登录')]|//button[@onclick='showLoginModal()']|//button[contains(@class, 'login')]",
    "login_modal": "loginModal",  # 使用ID直接定位登录框
    "username_input": "login_username",  # 使用ID直接定位
    "password_input": "login_password",  # 使用ID直接定位
    "pwd_hidden": "pwd",  # 隐藏的密码MD5字段ID
    "login_submit": "//a[@class='btn btn-primary btn-block']|//a[@onclick='login()']|//button[@id='loginSubmit']|//button[@type='submit']|//button[contains(text(), '登录')]|//input[@type='submit']",
    "logout_link": "//a[@onclick='Redirect_logout();']",
    
    # 课程列表页面
    "course_list": "//table[@class='table mb30']|//table[@class='table table-hover']|//div[contains(@class, 'course-list')]|//div[@id='courseList']|//ul[contains(@class, 'course-list')]|//ul[@id='courseList']",
    "makeup_buttons": "//button[contains(text(), '补作业')]|//a[contains(text(), '补作业')]",
    
    # 作业详情页相关
    "do_homework_button": "//button[contains(@onclick, 'gotoHomeWorkPage')]|//a[contains(text(), '做作业')]|//button[contains(text(), '做作业')]|//a[contains(@onclick, 'doHomework')]|//button[contains(@onclick, 'doHomework')]",
    
    # 答题页面相关
    "question": "//ul[contains(@class, 'test-list') and contains(@class, 'test-hover')]",
    "question_content": ".//div[contains(@class, 'timu')]|.//div[contains(@class, 'content')]|.//div[contains(@class, 'stem')]|.//div[contains(@class, 'question-text')]",
    "option": ".//ul[contains(@class, 'select-list')]//li[.//input[@type='radio' or @type='checkbox']]",
    "option_input": ".//input[@type='radio']|.//input[@type='checkbox']",
    "textarea": ".//textarea[@name='message']|.//textarea[contains(@onblur, 'setSubject')]|.//textarea[contains(@class, 'form-control')]|.//textarea",
    "submit_button": "//button[@id='postExamAnswer']|//button[contains(text(), '提交')]|//input[@type='submit']|//button[@type='submit']",
    "confirm_dialog": "//div[contains(@class, 'layui-layer-dialog')]|//div[contains(@class, 'modal') and contains(@style, 'display: block')]|//div[contains(@class, 'dialog') and contains(@style, 'display: block')]",
    "confirm_button": "//a[contains(@class, 'layui-layer-btn0')]|//button[contains(text(), '确定')]|//button[contains(text(), '确认')]|//button[@class='btn-primary']|//button[@class='btn-confirm']",
    
    # 答题卡相关
    "answer_card": "//div[contains(@class, 'sheetBody')]",
    "card_items": "//a[starts-with(@id, 'card_')]|//div[contains(@class, 'card-item')]|//div[contains(@class, 'question-card')]",
    
    # 结果页面
    "result": "//div[contains(@class, 'result')]|//div[contains(@class, 'score')]|//div[contains(@class, 'feedback')]",
    "back_button": "//a[contains(text(), '返回')]|//button[contains(text(), '返回')]|//button[@onclick='goBack()']|//a[@onclick='goBack()']"
}

# UI配置
UI_CONFIG = {
    "window_title": "Selenium暴打淘师湾作业网",
    "window_geometry": (100, 100, 800, 600),  # 设置窗口大小为800x600
    "control_panel_width": 320,  # 减少控制面板宽度
    "start_button_style": "background-color: #4CAF50; color: white; font-weight: bold; padding: 6px; font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;",
    "label_style": "font-weight: bold; font-size: 13px; font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;",
    "global_font_family": "Microsoft YaHei, PingFang SC, Helvetica Neue, Arial, sans-serif"
}

# 超时设置（秒）
TIMEOUTS = {
    "page_load": 3,  # 页面加载超时时间
    "element_wait": 3,  # 增加元素等待超时时间
    "between_actions": 0.2  # 操作间隔时间
}

# 操作延迟设置（秒）
OPERATION_DELAY = {
    "default": 0.3,  # 默认延迟时间（优化后减少）
    "min": 0,     # 最小延迟时间
    "max": 5.0       # 最大延迟时间
}

# 性能优化配置
PERFORMANCE_CONFIG = {
    "element_cache_size": 100,      # 元素缓存大小
    "text_cache_size": 1000,       # 文本处理缓存大小
    "ui_refresh_interval": 0.1,    # UI刷新间隔（秒）
    "batch_process_size": 10,      # 批处理大小
    "connection_pool_size": 5      # 数据库连接池大小
}

# 相似度阈值 (降低阈值以提高匹配成功率)
SIMILARITY_THRESHOLD = 0.3