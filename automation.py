from selenium import webdriver
from selenium.webdriver.common.by import By
import sys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from PyQt5.QtCore import QThread, pyqtSignal, QObject
import time
import hashlib
from functools import lru_cache
import subprocess
try:
    import psutil
except ImportError:
    psutil = None
from config import WEBSITE_URL, XPATHS, TIMEOUTS, BROWSER_OPTIONS, OPERATION_DELAY
import config
import re
from bs4 import BeautifulSoup

class BrowserAutomation(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(int, str)
    progress_signal = pyqtSignal(int, str)  # 进度信号: (百分比, 描述)
    
    def __init__(self, accounts, question_db):
        super().__init__()
        self.accounts = accounts
        self.question_db = question_db
        self.current_account_index = 0
        self.running = False
        self.paused = False
        self.driver = None
        self.operation_delay = OPERATION_DELAY['default']  # 默认延迟时间
        self._element_cache = {}  # 元素缓存
        self._wait_cache = {}     # WebDriverWait对象缓存
        self.skipped_homeworks = set()  # 记录已跳过的作业，避免重复处理
    
    def set_operation_delay(self, delay_seconds):
        """设置操作延迟时间"""
        self.operation_delay = max(OPERATION_DELAY['min'], min(delay_seconds, OPERATION_DELAY['max']))
        self.log_signal.emit(f"操作延迟已设置为: {self.operation_delay:.2f}秒")
    
    def wait_with_delay(self, custom_delay=None):
        """统一的延迟等待函数"""
        delay = custom_delay if custom_delay is not None else self.operation_delay
        time.sleep(delay)
    
    def get_wait(self, timeout=None):
        """获取缓存的WebDriverWait对象"""
        timeout = timeout or TIMEOUTS["element_wait"]
        if timeout not in self._wait_cache:
            self._wait_cache[timeout] = WebDriverWait(self.driver, timeout)
        return self._wait_cache[timeout]
    
    def check_login_errors(self):
        """检查layer.js弹窗中的登录错误信息"""
        try:
            # 检查是否有layer弹窗存在
            layer_elements = self.driver.find_elements(By.CSS_SELECTOR, ".layui-layer-content")
            
            for layer in layer_elements:
                try:
                    # 检查弹窗是否可见
                    if layer.is_displayed():
                        layer_text = layer.text.strip()
                        self.log_signal.emit(f"检测到弹窗内容: {layer_text}")
                        
                        # 检查常见的登录错误信息
                        if any(error in layer_text for error in [
                            "用户名或密码错误", "密码错误", "账号不存在", 
                            "用户被置为无效", "请填写用户名", "请填写密码"
                        ]):
                            # 尝试关闭弹窗
                            try:
                                close_btn = layer.find_element(By.CSS_SELECTOR, ".layui-layer-close")
                                if close_btn.is_displayed():
                                    close_btn.click()
                                    self.wait_with_delay(0.5)
                            except:
                                pass
                            return layer_text
                except:
                    continue
            
            # 也检查页面源码中的错误信息（作为备用方法）
            page_source = self.driver.page_source
            if "用户名或密码错误" in page_source:
                return "用户名或密码错误"
            elif "密码错误" in page_source:
                return "密码错误"
            elif "账号不存在" in page_source:
                return "账号不存在"
            elif "用户被置为无效" in page_source:
                return "用户被置为无效"
                
            return None
            
        except Exception as e:
            self.log_signal.emit(f"检查登录错误时出现异常: {str(e)}")
            return None
    
    def verify_login_status(self):
        """改进的登录状态验证"""
        try:
            current_url = self.driver.current_url
            
            # 方法1：检查URL是否包含登录成功后的特征
            if "myHomework.do" in current_url or "stu/" in current_url:
                self.log_signal.emit(f"通过URL验证登录成功: {current_url}")
                return True
                
            # 方法2：检查页面源码中的登录状态标识
            page_source = self.driver.page_source
            if "退出" in page_source or "作业列表" in page_source:
                self.log_signal.emit("通过页面内容验证登录成功")
                return True
                
            # 方法3：尝试查找登录后才有的元素（使用较短超时）
            try:
                logout_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, XPATHS["logout_link"])))
                if logout_element:
                    self.log_signal.emit("通过退出按钮验证登录成功")
                    return True
            except TimeoutException:
                pass
                
            return False
            
        except Exception as e:
            self.log_signal.emit(f"登录状态验证出错: {str(e)}")
            return False
    
    def find_element_optimized(self, by, value, timeout=None, cache_key=None):
        """优化的元素查找方法"""
        # 如果有缓存键且元素仍然有效，直接返回
        if cache_key and cache_key in self._element_cache:
            try:
                element = self._element_cache[cache_key]
                # 检查元素是否仍然有效
                element.is_enabled()
                return element
            except:
                # 元素已失效，从缓存中移除
                del self._element_cache[cache_key]
        
        # 查找新元素
        wait = self.get_wait(timeout)
        element = wait.until(EC.presence_of_element_located((by, value)))
        
        # 缓存元素
        if cache_key:
            self._element_cache[cache_key] = element
        
        return element
    
    def clear_element_cache(self):
        """清空元素缓存"""
        self._element_cache.clear()
        self._wait_cache.clear()
    
    def kill_chrome_processes(self):
        """强制关闭所有Chrome进程"""
        try:
            # 如果psutil可用，使用它来关闭进程
            if psutil:
                # 查找并关闭Chrome相关进程
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if 'chrome' in proc.info['name'].lower():
                            proc.kill()
                            self.log_signal.emit(f"已关闭Chrome进程: {proc.info['pid']}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            
            # 使用taskkill命令作为主要或备用方案
            try:
                result1 = subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], 
                                       capture_output=True, check=False)
                result2 = subprocess.run(['taskkill', '/f', '/im', 'chromedriver.exe'], 
                                       capture_output=True, check=False)
                
                if result1.returncode == 0 or result2.returncode == 0:
                    self.log_signal.emit("已使用taskkill命令关闭Chrome进程")
                    
            except Exception as e:
                self.log_signal.emit(f"taskkill命令执行失败: {str(e)}")
                
        except Exception as e:
            self.log_signal.emit(f"关闭Chrome进程时出错: {str(e)}")
    
    def cleanup_browser(self):
        """清理浏览器资源，确保完全关闭"""
        if self.driver:
            try:
                # 首先尝试正常关闭
                self.driver.quit()
                self.log_signal.emit("浏览器已正常关闭")
            except Exception as e:
                self.log_signal.emit(f"正常关闭浏览器失败: {str(e)}，尝试强制关闭")
            finally:
                self.driver = None
        
        # 等待一段时间让浏览器进程完全退出
        self.wait_with_delay(2)  # 统一延迟控制
        
        # 强制关闭残留的Chrome进程
        try:
            self.kill_chrome_processes()
            self.wait_with_delay(1)  # 统一延迟控制，等待进程完全关闭
            self.log_signal.emit("浏览器清理完成")
        except Exception as e:
            self.log_signal.emit(f"清理浏览器进程时出错: {str(e)}")
    
    def run(self):
        self.running = True
        self.paused = False
        
        # 初始化WebDriver
        options = webdriver.ChromeOptions()
        for option in BROWSER_OPTIONS:
            options.add_argument(option)
        
        # 根据配置决定是否显示浏览器窗口
        # 打包环境下强制显示浏览器窗口
        if hasattr(sys, '_MEIPASS'):
            self.log_signal.emit("")
            show_browser = True
        else:
            # 开发环境下使用配置文件设置
            show_browser = config.SHOW_BROWSER_WINDOW
        
        if not show_browser:
            options.add_argument("--headless")  # 无头模式，不显示浏览器界面
            self.log_signal.emit("浏览器运行在无头模式")
        else:
            self.log_signal.emit("浏览器窗口将显示，便于调试")
        
        self.driver = webdriver.Chrome(options=options)
        
        try:
            total_accounts = len(self.accounts)
            while self.running and self.current_account_index < total_accounts:
                if self.paused:
                    self.wait_with_delay(1)  # 统一延迟控制，暂停状态等待
                    continue
                    
                account = self.accounts[self.current_account_index]
                # 计算总体进度
                overall_progress = int((self.current_account_index / total_accounts) * 100)
                self.progress_signal.emit(overall_progress, f"正在处理账号 {self.current_account_index + 1}/{total_accounts}: {account['username']}")
                
                self.log_signal.emit(f"处理账号: {account['username']}")
                self.status_signal.emit(self.current_account_index, "处理中")
                
                try:
                    self.process_account(account)
                    self.status_signal.emit(self.current_account_index, "已完成")
                    # 更新完成进度
                    completed_progress = int(((self.current_account_index + 1) / total_accounts) * 100)
                    self.progress_signal.emit(completed_progress, f"账号 {self.current_account_index + 1}/{total_accounts} 已完成: {account['username']}")
                except KeyboardInterrupt:
                    self.log_signal.emit("自动化过程被用户中断")
                    self.status_signal.emit(self.current_account_index, "已中断")
                    break
                except Exception as e:
                    # 如果程序已停止，不输出错误信息
                    if not self.running:
                        break
                    self.log_signal.emit(f"处理账号 {account['username']} 时出错: {str(e)}")
                    self.status_signal.emit(self.current_account_index, "出错")
                    
                    error_str = str(e).lower()
                    
                    # 检查是否是登录失败错误，如果是则直接跳过
                    if "登录失败" in error_str:
                        self.log_signal.emit(f"账号 {account['username']} 登录失败，跳过该账号继续处理下一个")
                        # 记录登录失败到日志文件
                        import traceback
                        with open('app_error.log', 'a', encoding='utf-8') as f:
                            f.write(f"\n=== 登录失败时间: {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                            f.write(f"账号: {account['username']}\n")
                            f.write(f"错误信息: {str(e)}\n")
                        # 直接跳过，不重新初始化浏览器
                    # 检查是否是浏览器会话失效或崩溃错误
                    elif ("invalid session id" in error_str or 
                        "session deleted" in error_str or 
                        "chrome not reachable" in error_str or
                        "gethandleverifier" in error_str or
                        "no such session" in error_str or
                        "disconnected" in error_str or
                        "crashed" in error_str):
                        
                        # 如果程序已停止，不输出错误信息
                        if not self.running:
                            break
                        self.log_signal.emit("检测到浏览器会话失效或崩溃，尝试重新初始化浏览器...")
                        
                        # 等待一段时间，让系统资源释放
                        self.wait_with_delay(5)  # 统一延迟控制
                        
                        try:
                            # 关闭旧的浏览器实例
                            if self.driver:
                                try:
                                    self.driver.quit()
                                except:
                                    pass
                            
                            # 确保所有Chrome进程都已关闭
                            self.kill_chrome_processes()
                            
                            # 等待进程完全关闭
                            self.wait_with_delay(3)  # 统一延迟控制
                            
                            # 重新初始化浏览器
                            options = webdriver.ChromeOptions()
                            for option in BROWSER_OPTIONS:
                                options.add_argument(option)
                            
                            # 打包环境下强制显示浏览器窗口
                            if hasattr(sys, '_MEIPASS'):
                                # 检测到打包环境，强制显示浏览器窗口
                                self.log_signal.emit("重新初始化：检测到打包环境，强制显示浏览器窗口")
                                show_browser = True
                            else:
                                # 开发环境下使用配置文件设置
                                show_browser = config.SHOW_BROWSER_WINDOW
                            
                            if not show_browser:
                                options.add_argument("--headless")
                            
                            # 添加额外的崩溃恢复选项
                            options.add_experimental_option('excludeSwitches', ['enable-logging'])
                            # 移除detach选项，确保浏览器可以正常关闭
                            
                            # 设置服务对象，增加启动超时时间
                            from selenium.webdriver.chrome.service import Service
                            service = Service()
                            service.start()
                            
                            self.driver = webdriver.Chrome(options=options, service=service)
                            self.log_signal.emit("浏览器重新初始化成功，将重试当前账号")
                            
                            # 重试当前账号，不增加索引
                            continue
                            
                        except Exception as reinit_error:
                            # 如果程序已停止，不输出错误信息
                            if not self.running:
                                break
                            self.log_signal.emit(f"浏览器重新初始化失败: {str(reinit_error)}")
                    else:
                        # 记录其他类型错误的详细信息到日志文件
                        import traceback
                        with open('app_error.log', 'a', encoding='utf-8') as f:
                            f.write(f"\n=== 错误时间: {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                            f.write(f"账号: {account['username']}\n")
                            try:
                                f.write(f"当前URL: {self.driver.current_url if self.driver else 'N/A'}\n")
                            except:
                                f.write(f"当前URL: 无法获取（浏览器会话失效）\n")
                            f.write(f"错误信息: {str(e)}\n")
                            f.write(f"详细堆栈:\n{traceback.format_exc()}\n")
                
                self.current_account_index += 1
                
            self.log_signal.emit("所有账号处理完毕")
            # 发送完成信号
            if self.running:
                self.progress_signal.emit(100, f"所有账号处理完毕 ({total_accounts}/{total_accounts})")
        except KeyboardInterrupt:
            self.log_signal.emit("自动化过程被用户中断")
        except Exception as e:
            # 捕获所有其他未处理的异常，防止程序崩溃
            self.log_signal.emit(f"程序运行时发生严重错误: {str(e)}")
            import traceback
            with open('app_error.log', 'a', encoding='utf-8') as f:
                f.write(f"\n=== 严重错误时间: {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                try:
                    f.write(f"当前URL: {self.driver.current_url if self.driver else 'N/A'}\n")
                except:
                    f.write(f"当前URL: 无法获取（浏览器会话失效）\n")
                f.write(f"错误信息: {str(e)}\n")
                f.write(f"详细堆栈:\n{traceback.format_exc()}\n")
        finally:
            # 确保浏览器完全关闭
            self.cleanup_browser()
            self.running = False
    
    def process_account(self, account):
        # 清空缓存和跳过记录，开始新的账号处理
        self.clear_element_cache()
        self.skipped_homeworks.clear()  # 清空跳过作业记录
        self.log_signal.emit(f"开始处理账号: {account['username']}，已清空跳过作业记录")
        
        # 发送登录进度信号
        current_progress = int((self.current_account_index / len(self.accounts)) * 100)
        self.progress_signal.emit(current_progress, f"正在登录账号: {account['username']}")
        
        # 打开登录页面
        self.driver.get(WEBSITE_URL)
        
        # 点击登录按钮打开登录框
        login_button = self.get_wait().until(
            EC.element_to_be_clickable((By.XPATH, XPATHS["login_button"])))
        login_button.click()
        self.wait_with_delay() # 统一延迟控制
        
        # 等待登录框出现
        self.get_wait().until(
            EC.visibility_of_element_located((By.ID, XPATHS["login_modal"])))
        
        # 输入用户名和密码（使用缓存）
        username_input = self.find_element_optimized(By.ID, XPATHS["username_input"], cache_key="username_input")
        password_input = self.find_element_optimized(By.ID, XPATHS["password_input"], cache_key="password_input")
        
        username_input.clear()
        username_input.send_keys(account["username"])
        self.wait_with_delay() # 统一延迟控制
        
        password_input.clear()
        password_input.send_keys(account["password"])
        self.wait_with_delay() # 统一延迟控制
        
        # 使用JavaScript执行MD5加密并设置隐藏字段
        self.driver.execute_script(f'''
            document.getElementById("{XPATHS['pwd_hidden']}").value = hex_md5(document.getElementById("{XPATHS['password_input']}").value);
        ''')
        self.wait_with_delay() # 统一延迟控制
        
        # 点击登录按钮 - 使用JavaScript执行login()函数
        try:
            # 首先尝试使用JavaScript执行login()函数
            self.driver.execute_script("login();")
            self.log_signal.emit("已执行登录函数")
        except Exception as e:
            # 如果JavaScript执行失败，尝试直接点击登录按钮
            self.log_signal.emit(f"JavaScript登录失败，尝试直接点击: {str(e)}")
            try:
                login_submit_btn = self.driver.find_element(By.XPATH, XPATHS["login_submit"])
                login_submit_btn.click()
                self.log_signal.emit("已点击登录按钮")
            except Exception as e2:
                self.log_signal.emit(f"直接点击登录按钮也失败: {str(e2)}")
                raise Exception("无法执行登录操作")
        
        self.wait_with_delay(1) # 等待登录处理
        
        # 等待登录成功
        try:
            # 等待登录处理完成
            self.wait_with_delay(2)  # 统一延迟控制
            
            # 检查是否有layer.js错误弹窗
            error_detected = self.check_login_errors()
            if error_detected:
                error_info = error_detected
                self.log_signal.emit(f"账号 {account['username']} 登录失败: {error_info}")
                raise Exception(f"登录失败: {error_info}")
            
            # 再等待一秒确保页面完全加载
            self.wait_with_delay(1)  # 统一延迟控制
            
            # 使用改进的登录状态验证
            if self.verify_login_status():
                self.log_signal.emit(f"账号 {account['username']} 登录成功")
                
                # 如果是viewHomework页面，需要导航到myHomework页面
                current_url = self.driver.current_url
                if "viewHomework.do" in current_url:
                    try:
                        self.log_signal.emit("当前在作业详情页面，尝试导航到作业列表页面")
                        # 构造myHomework页面URL
                        base_url = current_url.split('/hw/')[0] + '/hw/stu/myHomework.do'
                        self.driver.get(base_url)
                        self.wait_with_delay(1)
                        self.log_signal.emit(f"已导航到作业列表页面: {self.driver.current_url}")
                    except Exception as nav_e:
                        self.log_signal.emit(f"导航到作业列表页面失败: {str(nav_e)}")
                
                # 继续处理课程
                self.process_courses()
                
                # 尝试登出
                try:
                    logout_link = WebDriverWait(self.driver, TIMEOUTS["element_wait"]).until(
                        EC.element_to_be_clickable((By.XPATH, XPATHS["logout_link"])))
                    logout_link.click()
                    self.wait_with_delay() # 统一延迟控制
                    
                    # 等待登出成功（减少等待时间）
                    WebDriverWait(self.driver, 3).until(
                        lambda driver: "fore/index.do" in driver.current_url or "index.do" in driver.current_url)
                    self.log_signal.emit(f"账号 {account['username']} 已登出")
                except TimeoutException:
                    self.log_signal.emit(f"账号 {account['username']} 登出按钮未找到，可能已经登出或页面状态异常")
                    # 尝试直接导航到首页来完成登出
                    try:
                        self.driver.get(WEBSITE_URL + "?out=1")
                        self.wait_with_delay(1)
                        self.log_signal.emit(f"账号 {account['username']} 已通过导航到首页完成登出")
                    except Exception as nav_e:
                        self.log_signal.emit(f"导航到首页失败: {str(nav_e)}")
                except Exception as logout_e:
                    self.log_signal.emit(f"登出过程出错: {str(logout_e)}")
                    # 尝试直接导航到首页
                    try:
                        self.driver.get(WEBSITE_URL + "?out=1")
                        self.wait_with_delay(1)
                        self.log_signal.emit(f"账号 {account['username']} 已通过导航到首页完成登出")
                    except Exception as nav_e:
                        self.log_signal.emit(f"导航到首页失败: {str(nav_e)}")
            else:
                # 如果登录状态验证失败，再次检查是否有错误信息
                final_error_check = self.check_login_errors()
                if final_error_check:
                    error_info = final_error_check
                else:
                    error_info = "登录状态检测超时或未知错误"
                    
                self.log_signal.emit(f"账号 {account['username']} 登录失败: {error_info}")
                raise Exception(f"登录失败: {error_info}")
                
        except Exception as e:
            if "登录失败" not in str(e):
                self.log_signal.emit(f"登录处理过程出错: {str(e)}")
            raise
    
    def process_courses(self):
        try:
            # 检查程序是否已停止
            if not self.running:
                return
                
            # 检查浏览器会话是否有效
            try:
                self.driver.current_url
            except Exception as session_error:
                # 如果程序已停止，不输出错误信息
                if not self.running:
                    return
                if "invalid session id" in str(session_error).lower():
                    raise Exception("浏览器会话已失效，需要重新初始化")
                else:
                    raise session_error
            
            # 等待课程列表加载
            self.get_wait(TIMEOUTS["page_load"]).until(
                EC.presence_of_element_located((By.XPATH, XPATHS["course_list"])))
            
            # 查找所有补作业按钮
            # 增加显式等待，确保至少一个补作业按钮出现
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, XPATHS["makeup_buttons"]))
                )
                makeup_buttons = self.driver.find_elements(By.XPATH, XPATHS["makeup_buttons"])
            except TimeoutException:
                self.log_signal.emit("未找到任何补作业按钮，可能没有待完成的作业或加载超时")
                return
            
            if not makeup_buttons:
                self.log_signal.emit("未找到任何补作业按钮，可能没有待完成的作业")
                return
                
            self.log_signal.emit(f"找到 {len(makeup_buttons)} 个待完成的作业")
        except TimeoutException:
            self.log_signal.emit("等待课程列表加载超时")
            return
        except Exception as e:
            # 如果程序已停止，不输出错误信息
            if not self.running:
                return
            self.log_signal.emit(f"加载课程列表时出错: {str(e)}")
            return
        
        # 使用索引而不是直接遍历元素，避免stale element reference错误
        # 每次处理完一个作业后，重新从第一个开始检查，因为作业列表会动态更新
        while True:
            if not self.running or self.paused:
                return
                
            try:
                # 每次循环开始时重新获取补作业按钮列表，确保列表是最新的
                makeup_buttons = self.driver.find_elements(By.XPATH, XPATHS["makeup_buttons"])
                
                # 如果没有找到任何补作业按钮，说明所有作业已处理完成
                if not makeup_buttons:
                    self.log_signal.emit("所有作业已处理完成")
                    break
                    
                self.log_signal.emit(f"找到 {len(makeup_buttons)} 个待完成的作业")
                
                # 查找第一个未被跳过的作业
                button = None
                button_index = -1
                for i, btn in enumerate(makeup_buttons):
                    onclick_attr = btn.get_attribute("onclick")
                    # 从onclick属性中提取作业标识
                    homework_id = self.extract_homework_id_from_onclick(onclick_attr)
                    
                    if homework_id not in self.skipped_homeworks:
                        button = btn
                        button_index = i
                        # 发送作业处理进度信号
                        account_progress = int((self.current_account_index / len(self.accounts)) * 100)
                        self.progress_signal.emit(account_progress, f"账号 {self.current_account_index + 1}/{len(self.accounts)}: 处理作业 {i+1}/{len(makeup_buttons)}")
                        self.log_signal.emit(f"选择第 {i+1} 个作业进行处理（作业ID: {homework_id}）")
                        break
                    else:
                        self.log_signal.emit(f"跳过第 {i+1} 个作业，该作业已被标注为无法完成（作业ID: {homework_id}）")
                
                # 如果所有作业都已被跳过，结束处理
                if button is None:
                    self.log_signal.emit("所有可见的作业都已被标注为跳过，处理完成")
                    break
                
                # 获取按钮的onclick属性以判断跳转类型
                onclick_attr = button.get_attribute("onclick")
                self.log_signal.emit(f"补作业按钮onclick属性: {onclick_attr}")
                
                button.click()
                self.wait_with_delay() # 统一延迟控制，等待页面跳转
                self.log_signal.emit("已点击补作业按钮")
                
                # 等待页面跳转完成
                try:
                    # 检查浏览器会话是否仍然有效
                    try:
                        self.driver.current_url
                    except Exception as session_error:
                        # 如果程序已停止，不输出错误信息
                        if not self.running:
                            return
                        if "invalid session id" in str(session_error).lower():
                            raise Exception("浏览器会话在页面跳转过程中失效")
                        else:
                            raise session_error
                    
                    WebDriverWait(self.driver, TIMEOUTS["page_load"]).until(
                        lambda driver: "doHomework.do" in driver.current_url or "viewHomework.do" in driver.current_url)
                    
                    # 检查当前页面类型
                    current_url = self.driver.current_url
                    self.log_signal.emit(f"页面跳转完成，当前URL: {current_url}")
                    
                    if "doHomework.do" in current_url:
                        self.log_signal.emit("已直接跳转到作业页面")
                    elif "viewHomework.do" in current_url:
                        self.log_signal.emit("跳转到作业详情页面，需要点击做作业按钮")
                        
                        # 尝试点击做作业按钮
                        try:
                            do_homework_button = WebDriverWait(self.driver, TIMEOUTS["element_wait"]).until(
                                EC.element_to_be_clickable((By.XPATH, XPATHS["do_homework_button"])))
                            do_homework_button.click()
                            self.wait_with_delay() # 统一延迟控制，等待页面跳转
                            self.log_signal.emit("已点击做作业按钮")
                            
                            # 等待跳转到作业页面
                            try:
                                WebDriverWait(self.driver, TIMEOUTS["page_load"]).until(
                                    lambda driver: "doHomework.do" in driver.current_url)
                                self.log_signal.emit("成功跳转到作业页面")
                            except Exception as jump_error:
                                # 如果程序已停止，不输出错误信息
                                if not self.running:
                                    return
                                if "invalid session id" in str(jump_error).lower():
                                    raise Exception("浏览器会话在跳转到作业页面时失效")
                                else:
                                    raise jump_error
                            
                        except TimeoutException:
                            # 在viewHomework页面找不到做作业按钮，标注并跳过该作业
                            self.log_signal.emit("⚠️ 在作业详情页面未找到做作业按钮，该作业可能已完成或无法进行，标注并跳过")
                            self.mark_homework_as_skipped(current_url)
                            # 立即返回到作业列表页面
                            self.ensure_on_course_list_page()
                            continue
                        except Exception as e:
                            # 如果程序已停止，不输出错误信息
                            if not self.running:
                                return
                            self.log_signal.emit(f"点击做作业按钮失败: {str(e)}")
                            # 如果是找不到元素的错误，也标注并跳过
                            if "no such element" in str(e).lower() or "element not found" in str(e).lower():
                                self.log_signal.emit("⚠️ 做作业按钮不存在，该作业可能已完成或无法进行，标注并跳过")
                                self.mark_homework_as_skipped(current_url)
                                # 立即返回到作业列表页面
                                self.ensure_on_course_list_page()
                            continue
                    else:
                        self.log_signal.emit(f"未知的页面类型: {current_url}")
                        continue
                        
                except TimeoutException:
                    self.log_signal.emit("等待页面跳转超时")
                    current_url = self.driver.current_url
                    self.log_signal.emit(f"超时时的当前URL: {current_url}")
                    continue
                
                # 处理题目
                self.answer_questions()
                
                # 注意：提交逻辑已在answer_questions方法中处理
                # 这里不再重复提交，避免冲突
                self.log_signal.emit("作业处理完成")
                
            except Exception as e:
                # 如果程序已停止，不输出错误信息
                if not self.running:
                    return
                self.log_signal.emit(f"处理作业时发生外部错误: {str(e)}")
            
            # 无论是否发生错误，都尝试确保返回到课程列表页面
            self.ensure_on_course_list_page()
            
            # 重新获取补作业按钮列表以更新总数，用于日志输出
            try:
                updated_makeup_buttons = self.driver.find_elements(By.XPATH, XPATHS["makeup_buttons"])
                if updated_makeup_buttons:
                    self.log_signal.emit(f"当前还有 {len(updated_makeup_buttons)} 个待完成的作业")
                else:
                    self.log_signal.emit("没有更多待完成的作业")
            except Exception as e:
                self.log_signal.emit(f"重新获取作业列表时出错: {str(e)}")
                # 如果获取失败，不中断循环，继续尝试下一个
                pass

    def ensure_on_course_list_page(self):
        """确保当前页面是作业列表页面，如果不是则尝试导航回去"""
        try:
            current_url = self.driver.current_url
            if "myHomework.do" not in current_url:
                self.log_signal.emit(f"当前不在作业列表页面 ({current_url})，尝试导航回课程列表")
                
                # 构造正确的作业列表页面URL
                if "51taoshi.com" in current_url:
                    # 从当前URL提取基础URL
                    base_url = current_url.split('/hw/')[0] + '/hw/stu/myHomework.do'
                else:
                    # 使用默认URL
                    base_url = WEBSITE_URL.replace("fore/index.do", "stu/myHomework.do")
                
                self.driver.get(base_url)
                self.wait_with_delay(2) # 额外等待确保页面加载
                
                # 验证是否成功返回到作业列表页面
                final_url = self.driver.current_url
                if "myHomework.do" in final_url:
                    self.log_signal.emit("✅ 已成功导航回课程列表")
                else:
                    self.log_signal.emit(f"⚠️ 导航后的URL可能不正确: {final_url}")
            else:
                self.log_signal.emit("已在课程列表页面")
        except Exception as e:
            self.log_signal.emit(f"确保在课程列表页面时出错: {str(e)}")
            # 尝试使用浏览器后退功能作为备用方案
            try:
                self.log_signal.emit("尝试使用浏览器后退功能")
                self.driver.back()
                self.wait_with_delay(1)
                if "myHomework.do" in self.driver.current_url:
                    self.log_signal.emit("✅ 通过后退功能成功返回课程列表")
                else:
                    self.log_signal.emit("⚠️ 后退功能未能返回到正确页面")
            except Exception as back_error:
                self.log_signal.emit(f"浏览器后退功能也失败: {str(back_error)}")

    def answer_questions(self):
        try:
            # 清空元素缓存，确保在新页面上重新查找元素
            self.clear_element_cache()
            
            # 检查浏览器会话是否有效
            try:
                self.driver.current_url
            except Exception as session_error:
                if "invalid session id" in str(session_error).lower():
                    raise Exception("浏览器会话在答题过程中失效")
                else:
                    raise session_error
            
            # 获取所有题目
            questions = self.driver.find_elements(By.XPATH, XPATHS["question"])
            
            if not questions:
                self.log_signal.emit("未找到任何题目，可能页面加载不完整")
                return
                
            self.log_signal.emit(f"找到 {len(questions)} 道题目")
        except Exception as e:
            self.log_signal.emit(f"获取题目列表时出错: {str(e)}")
            return
        
        # 使用索引而不是直接遍历元素，避免stale element reference错误
        for i in range(len(questions)):
            if not self.running or self.paused:
                return
                
            self.log_signal.emit(f"处理第 {i+1}/{len(questions)} 题")
            
            try:
                # 检查浏览器会话是否仍然有效
                try:
                    self.driver.current_url
                except Exception as session_error:
                    if "invalid session id" in str(session_error).lower():
                        raise Exception(f"浏览器会话在处理第{i+1}题时失效")
                    else:
                        raise session_error
                
                # 重新获取题目元素，避免stale element reference
                current_questions = self.driver.find_elements(By.XPATH, XPATHS["question"])
                if i >= len(current_questions):
                    self.log_signal.emit("所有题目已处理完成")
                    break
                    
                question = current_questions[i]
                
                # 获取题目内容
                question_content = question.find_element(By.XPATH, XPATHS["question_content"])
                question_text = question_content.text
                
                # 清理题目文本，去除序号和分数信息
                cleaned_question_text = self.clean_question_text(question_text)
                self.log_signal.emit(f"原始题目文本: {question_text[:50]}...")
                self.log_signal.emit(f"清理后题目文本: {cleaned_question_text[:50]}...")
                
                # 从题库中查找答案
                answer = self.question_db.find_answer(cleaned_question_text)
                
                if answer:
                    self.log_signal.emit(f"找到题目答案: {answer}")
                    
                    # 判断题目类型并填写答案
                    if self.is_choice_question(question):
                        self.answer_choice_question(question, answer)
                    else:
                        self.answer_subjective_question(question, answer)
                else:
                    # 如果没有找到答案，随机选择一个选项（仅对选择题）
                    if self.is_choice_question(question):
                        self.log_signal.emit(f"未找到题目答案，随机选择: {question_text[:30]}...")
                        self.random_answer_choice(question)
                    else:
                        self.log_signal.emit(f"未找到题目答案，跳过: {question_text[:30]}...")
            except Exception as e:
                self.log_signal.emit(f"处理题目时出错: {str(e)}")
                continue
        
        # 提交答案
        try:
            # 等待一下确保所有答案都已保存
            self.wait_with_delay()
            
            # 检查是否所有题目都已回答（使用JavaScript检查，更准确）
            try:
                answered_count = self.driver.execute_script("return $('[id^=card_].active').length;")
                total_count = self.driver.execute_script("return $('[id^=card_]').length;")
                unanswered_count = total_count - answered_count
                
                if unanswered_count > 0:
                    self.log_signal.emit(f"警告: 有 {unanswered_count} 道题目未回答")
                else:
                    self.log_signal.emit(f"所有 {total_count} 道题目已回答完毕")
            except Exception as check_error:
                self.log_signal.emit(f"检查答题状态时出错: {str(check_error)}")
            
            # 点击提交按钮
            submit_button = self.driver.find_element(By.XPATH, XPATHS["submit_button"])
            submit_button.click()
            self.wait_with_delay() # 统一延迟控制，等待对话框出现
            
            # 处理确认对话框
            try:
                WebDriverWait(self.driver, TIMEOUTS["element_wait"]).until(
                    EC.presence_of_element_located((By.XPATH, XPATHS["confirm_dialog"])))
                
                # 点击确认按钮
                confirm_button = self.driver.find_element(By.XPATH, XPATHS["confirm_button"])
                confirm_button.click()
                self.wait_with_delay() # 统一延迟控制
                self.log_signal.emit("已确认提交答案")
                
                # 等待提交完成，检查是否有成功或失败的提示
                try:
                    # 等待提交结果
                    WebDriverWait(self.driver, TIMEOUTS['element_wait'] * 3).until(
                        lambda driver: "提交试卷成功" in driver.page_source or "提交试卷失败" in driver.page_source
                    )
                    
                    if "提交试卷成功" in self.driver.page_source:
                        self.log_signal.emit("答案提交成功")
                        
                        # 等待自动跳转到成绩页面 (myResult.do)
                        try:
                            WebDriverWait(self.driver, 5).until(
                                lambda driver: "myResult.do" in driver.current_url
                            )
                            self.log_signal.emit("已跳转到成绩页面")
                            
                            # 点击返回按钮
                            try:
                                back_button = WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable((By.XPATH, XPATHS["back_button"]))
                                )
                                back_button.click()
                                self.log_signal.emit("已点击返回按钮")
                                
                                # 等待返回到课程列表页面
                                WebDriverWait(self.driver, 5).until(
                                    lambda driver: "myHomework.do" in driver.current_url
                                )
                                self.log_signal.emit("已返回课程列表")
                                
                            except TimeoutException:
                                self.log_signal.emit("未找到返回按钮，手动返回课程列表")
                                self.driver.get(WEBSITE_URL.replace("fore/index.do", "stu/myHomework.do"))
                                
                        except TimeoutException:
                            self.log_signal.emit("未自动跳转到成绩页面，手动返回课程列表")
                            self.driver.get(WEBSITE_URL.replace("fore/index.do", "stu/myHomework.do"))
                            
                    elif "提交试卷失败" in self.driver.page_source:
                        self.log_signal.emit("答案提交失败")
                    else:
                        self.log_signal.emit("答案提交状态未知")
                        
                except TimeoutException:
                    self.log_signal.emit("等待提交结果超时，可能已成功提交")
                    # 等待可能的页面跳转
                    self.wait_with_delay(3)
                    current_url = self.driver.current_url
                    if "myResult.do" in current_url:
                        # 如果已跳转到成绩页面，点击返回
                        try:
                            back_button = self.driver.find_element(By.XPATH, XPATHS["back_button"])
                            back_button.click()
                            self.log_signal.emit("已点击返回按钮")
                        except:
                            self.driver.get(WEBSITE_URL.replace("fore/index.do", "stu/myHomework.do"))
                    elif "doHomework.do" in current_url:
                        # 如果还在答题页面，手动返回
                        self.driver.get(WEBSITE_URL.replace("fore/index.do", "stu/myHomework.do"))
                        self.log_signal.emit("已返回课程列表")
                
            except TimeoutException:
                self.log_signal.emit("未出现确认对话框，可能已直接提交")
                # 等待一下看是否有提交结果
                self.wait_with_delay(3)
                
        except Exception as e:
            self.log_signal.emit(f"提交答案时出错: {str(e)}")
            # 尝试返回课程列表
            try:
                self.driver.get(WEBSITE_URL.replace("fore/index.do", "stu/myHomework.do"))
            except:
                pass

    
    def is_choice_question(self, question):
        # 检查是否有选项元素来判断是否为选择题
        try:
            options = question.find_elements(By.XPATH, XPATHS["option"])
            return len(options) > 0
        except:
            return False
    
    def random_answer_choice(self, question):
        # 随机选择一个选项
        try:
            select_options = question.find_elements(By.XPATH, XPATHS["option"])
            choice_options = question.find_elements(By.XPATH, ".//ul[contains(@class, 'choose-list')]//li")
            
            if select_options:
                import random
                random_index = random.randint(0, len(select_options) - 1)
                random_option = select_options[random_index]
                random_option.find_element(By.XPATH, XPATHS["option_input"]).click()
                
                # 获取对应的选项文本和字母
                option_letter = chr(ord('A') + random_index)
                option_text = choice_options[random_index].text if random_index < len(choice_options) else f"选项{random_index+1}"
                self.log_signal.emit(f"随机选择了选项: {option_letter}.{option_text[:20]}...")
                return True
            return False
        except Exception as e:
            self.log_signal.emit(f"随机选择选项时出错: {str(e)}")
            return False
    
    def answer_choice_question(self, question, answer):
        try:
            # 获取选项文本（从choose-list）
            choice_options = question.find_elements(By.XPATH, ".//ul[contains(@class, 'choose-list')]//li")
            # 获取选项输入框（从select-list）
            select_options = question.find_elements(By.XPATH, XPATHS["option"])
            
            if len(choice_options) != len(select_options):
                self.log_signal.emit(f"选项数量不匹配: 文本选项{len(choice_options)}个，输入选项{len(select_options)}个")
                # 如果数量不匹配，尝试直接使用select_options的文本
                choice_options = select_options
            
            # 直接根据题库答案选择对应选项
            # answer应该是A、B、C、D等选项标识
            answer_letter = answer.strip().upper()
            
            # 将选项字母转换为索引
            option_index = -1
            if answer_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                option_index = ord(answer_letter) - ord('A')
            
            # 检查索引是否有效
            if 0 <= option_index < len(select_options):
                select_options[option_index].find_element(By.XPATH, XPATHS["option_input"]).click()
                self.wait_with_delay()
                selected_option = choice_options[option_index].text if option_index < len(choice_options) else f"选项{option_index+1}"
                self.log_signal.emit(f"根据题库答案{answer_letter}，选择了选项: {answer_letter}.{selected_option[:30]}...")
                return True
            else:
                self.log_signal.emit(f"题库答案{answer_letter}超出选项范围，选择第一个选项")
                if select_options:
                    select_options[0].find_element(By.XPATH, XPATHS["option_input"]).click()
                    self.wait_with_delay()
                    first_option_text = choice_options[0].text if choice_options else "第一个选项"
                    self.log_signal.emit(f"默认选择了第一个选项: A.{first_option_text[:30]}...")
                    return True
            return False
        except Exception as e:
            self.log_signal.emit(f"选择选项时出错: {str(e)}")
            return False
    
    def extract_option_content(self, option_text):
        """提取选项的纯净内容，去除题目编号、分数等信息"""
        import re
        
        # 去除开头的数字编号和分数信息，如 "1.(25分)"
        clean_text = re.sub(r'^\d+\.\(\d+分\)', '', option_text)
        
        # 去除开头的字母选项，如 "A." "B." 等
        clean_text = re.sub(r'^[A-Z]\s*[\.、]\s*', '', clean_text)
        
        # 去除多余的空白字符
        clean_text = clean_text.strip()
        
        return clean_text
    
    @lru_cache(maxsize=1000)
    def clean_question_text(self, question_text):
        """优化的题目文本清理方法，使用LRU缓存"""
        import re
        
        # 去除开头的数字编号和分数信息
        # 例如: "1.(25分)一个好的多媒体作品..." -> "一个好的多媒体作品..."
        cleaned = re.sub(r'^\d+\.\s*\(\d+分\)\s*', '', question_text)
        
        # 去除多余的空白字符
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()
    
    def answer_subjective_question(self, question, answer):
        try:
            # 查找文本输入框
            textarea = question.find_element(By.XPATH, XPATHS["textarea"])
            
            # 清空并输入答案
            textarea.clear()
            
            # 对于解答题，确保答案格式正确
            formatted_answer = answer.strip()
            
            # 使用JavaScript设置值，避免输入问题
            self.driver.execute_script("arguments[0].value = arguments[1];", textarea, formatted_answer)
            self.wait_with_delay() # 统一延迟控制
            
            # 获取textarea的ID，用于调用setSubject函数
            textarea_id = textarea.get_attribute('id')
            
            # 触发网站特定的setSubject函数（主观题专用）
            if textarea_id:
                try:
                    # 调用网站的setSubject函数，参数：questionId, questionType='5', element
                    self.driver.execute_script("""
                        var textarea = arguments[0];
                        var questionId = arguments[1];
                        if (typeof setSubject === 'function') {
                            setSubject(questionId, '5', textarea);
                        }
                    """, textarea, textarea_id)
                    self.log_signal.emit(f"已调用setSubject函数，题目ID: {textarea_id[:20]}...")
                except Exception as js_error:
                    self.log_signal.emit(f"调用setSubject函数失败: {str(js_error)}")
            
            # 触发标准事件确保输入被识别
            self.driver.execute_script("""
                var element = arguments[0];
                element.dispatchEvent(new Event('input', {bubbles: true}));
                element.dispatchEvent(new Event('change', {bubbles: true}));
                element.dispatchEvent(new Event('blur', {bubbles: true}));
            """, textarea)
            
            # 验证输入是否成功
            current_value = self.driver.execute_script("return arguments[0].value;", textarea)
            if current_value.strip() == formatted_answer:
                self.log_signal.emit(f"已成功输入解答题答案: {formatted_answer[:50]}...")
                
                # 检查答题卡是否更新为已答状态
                if textarea_id:
                    try:
                        card_element = self.driver.find_element(By.ID, f"card_{textarea_id}")
                        card_class = card_element.get_attribute('class')
                        if 'active' in card_class:
                            self.log_signal.emit("答题卡状态已更新为已答")
                        else:
                            self.log_signal.emit("答题卡状态未更新，可能需要手动触发")
                    except:
                        self.log_signal.emit("无法检查答题卡状态")
                
                return True
            else:
                self.log_signal.emit(f"答案输入验证失败，重试中...")
                # 尝试直接发送按键
                textarea.click()
                textarea.clear()
                textarea.send_keys(formatted_answer)
                self.wait_with_delay(0.3)
                
                # 再次触发blur事件
                self.driver.execute_script("arguments[0].blur();", textarea)
                
                self.log_signal.emit(f"已通过按键输入解答题答案: {formatted_answer[:50]}...")
                return True
                
        except Exception as e:
            self.log_signal.emit(f"输入解答题答案时出错: {str(e)}")
            return False
    
    def pause(self):
        self.paused = True
        self.log_signal.emit("自动化已暂停")
    
    def resume(self):
        self.paused = False
        self.log_signal.emit("自动化已恢复")
    
    def stop(self):
        self.running = False
        # 确保浏览器完全关闭
        self.cleanup_browser()
        self.log_signal.emit("自动化已停止")
    
    def extract_homework_id_from_onclick(self, onclick_attr):
        """从onclick属性中提取作业ID"""
        try:
            if onclick_attr and "view('" in onclick_attr:
                # 提取view('xxx')中的xxx部分
                start = onclick_attr.find("view('") + 6
                end = onclick_attr.find("')", start)
                if end > start:
                    return onclick_attr[start:end]
            elif onclick_attr and "kcid=" in onclick_attr:
                # 从URL参数中提取kcid
                start = onclick_attr.find("kcid=") + 5
                end = onclick_attr.find("&", start)
                if end == -1:
                    end = onclick_attr.find("'", start)
                if end > start:
                    return onclick_attr[start:end]
            return onclick_attr or "unknown"
        except Exception as e:
            self.log_signal.emit(f"提取作业ID时出错: {str(e)}")
            return "unknown"
    
    def mark_homework_as_skipped(self, homework_url):
        """标注跳过的作业，记录相关信息"""
        try:
            # 从URL中提取作业ID并添加到跳过列表
            homework_id = "unknown"
            if "kcid=" in homework_url:
                homework_id = homework_url.split("kcid=")[1].split("&")[0]
            elif "homeworkId=" in homework_url:
                homework_id = homework_url.split("homeworkId=")[1].split("&")[0]
            
            # 将作业ID添加到跳过集合中
            self.skipped_homeworks.add(homework_id)
            
            # 尝试获取作业标题或其他标识信息
            homework_title = "未知作业"
            try:
                # 尝试从页面获取作业标题
                title_elements = self.driver.find_elements(By.XPATH, "//h1|//h2|//h3|//title|//*[contains(@class,'title')]")
                for element in title_elements:
                    if element.is_displayed() and element.text.strip():
                        homework_title = element.text.strip()[:100]  # 限制长度
                        break
                
                # 如果没有找到标题，使用作业ID作为标题
                if homework_title == "未知作业":
                    homework_title = f"作业ID: {homework_id}"
            except Exception as title_error:
                self.log_signal.emit(f"获取作业标题时出错: {str(title_error)}")
            
            # 记录跳过的作业信息
            skip_info = {
                'id': homework_id,
                'title': homework_title,
                'url': homework_url,
                'reason': '在作业详情页面未找到做作业按钮',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 输出详细的跳过信息
            self.log_signal.emit(f"📝 跳过作业记录:")
            self.log_signal.emit(f"   ID: {skip_info['id']}")
            self.log_signal.emit(f"   标题: {skip_info['title']}")
            self.log_signal.emit(f"   原因: {skip_info['reason']}")
            self.log_signal.emit(f"   时间: {skip_info['timestamp']}")
            self.log_signal.emit(f"   URL: {homework_url}")
            self.log_signal.emit(f"🔒 该作业已被标记为跳过，后续不会再次处理")
            
        except Exception as e:
            self.log_signal.emit(f"标注跳过作业时出错: {str(e)}")


class QuestionBankImporter(QObject):
    """题库导入器 - 从已完成账号导入题库"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)  # 进度信号: (百分比, 描述)
    
    def __init__(self, question_db, show_browser=True):
        super().__init__()
        self.question_db = question_db
        self.driver = None
        self.delay_multiplier = 1.0  # 延迟倍数，与主程序保持一致
        self.show_browser = show_browser  # 是否显示浏览器窗口
    
    def wait_with_delay(self, base_delay=None, min_delay=None):
        """统一的延迟控制方法"""
        if base_delay is None:
            base_delay = OPERATION_DELAY['default']
        actual_delay = base_delay * self.delay_multiplier
        
        # 确保最小延迟时间，防止页面加载不完整
        if min_delay is not None:
            actual_delay = max(actual_delay, min_delay)
        
        time.sleep(actual_delay)
    
    def set_delay_multiplier(self, multiplier):
        """设置延迟倍数"""
        self.delay_multiplier = multiplier
        
    def import_from_completed_account(self, account, password):
        """从已完成账号导入题库"""
        try:
            self.log_signal.emit(f"🚀 开始从账号 {account} 导入题库...")
            self.progress_signal.emit(0, "正在初始化浏览器...")
            
            # 初始化浏览器
            if not self._init_browser():
                return {"success": False, "message": "浏览器初始化失败"}
            
            self.progress_signal.emit(20, "正在登录账号...")
            # 登录账号
            if not self._login(account, password):
                return {"success": False, "message": "登录失败"}
            
            self.progress_signal.emit(40, "正在查找作业...")
            # 直接开始导入作业题目（不需要额外导航到作业页面）
            imported_count = self._import_all_homework_questions()
            
            self.progress_signal.emit(100, "题库导入完成")
            self.log_signal.emit(f"✅ 题库导入完成！共导入 {imported_count} 个题目")
            return {"success": True, "imported_count": imported_count}
            
        except Exception as e:
            self.log_signal.emit(f"❌ 导入过程中发生错误: {str(e)}")
            return {"success": False, "message": str(e)}
        finally:
            self._cleanup()
    
    def _init_browser(self):
        """初始化浏览器"""
        try:
            # 使用与主程序相同的浏览器配置
            options = webdriver.ChromeOptions()
            for option in BROWSER_OPTIONS:
                options.add_argument(option)
            
            # 根据实例配置决定是否显示浏览器窗口
            if not self.show_browser:
                options.add_argument("--headless")  # 无头模式，不显示浏览器界面
                self.log_signal.emit("🌐 浏览器运行在无头模式")
            else:
                self.log_signal.emit("🌐 浏览器窗口将显示，便于调试")
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            self.log_signal.emit("🌐 浏览器初始化成功")
            return True
            
        except Exception as e:
            self.log_signal.emit(f"❌ 浏览器初始化失败: {str(e)}")
            return False
    
    def _login(self, account, password):
        """登录账号 - 复用主程序的稳定登录逻辑"""
        try:
            self.log_signal.emit(f"🔐 正在登录账号: {account}")
            
            # 打开登录页面
            self.driver.get(WEBSITE_URL)
            
            # 点击登录按钮打开登录框
            login_button = WebDriverWait(self.driver, TIMEOUTS['element_wait'] * 3).until(
                EC.element_to_be_clickable((By.XPATH, XPATHS["login_button"])))
            login_button.click()
            self.wait_with_delay()  # 统一延迟控制
            
            # 等待登录框出现
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, XPATHS["login_modal"])))
            
            # 输入用户名和密码
            username_input = WebDriverWait(self.driver, TIMEOUTS['element_wait'] * 3).until(
                EC.presence_of_element_located((By.ID, XPATHS["username_input"])))
            password_input = self.driver.find_element(By.ID, XPATHS["password_input"])
            
            username_input.clear()
            username_input.send_keys(account)
            self.wait_with_delay()  # 统一延迟控制
            
            password_input.clear()
            password_input.send_keys(password)
            self.wait_with_delay()  # 统一延迟控制
            
            # 使用JavaScript执行MD5加密并设置隐藏字段
            self.driver.execute_script(f'''
                document.getElementById("{XPATHS['pwd_hidden']}").value = hex_md5(document.getElementById("{XPATHS['password_input']}").value);
            ''')
            self.wait_with_delay()  # 统一延迟控制
            
            # 点击登录按钮 - 使用JavaScript执行login()函数
            try:
                self.driver.execute_script("login();")
                self.log_signal.emit("已执行JavaScript登录函数")
            except Exception as js_error:
                self.log_signal.emit(f"JavaScript登录失败，尝试直接点击: {str(js_error)}")
                # 备用方案：直接点击登录按钮
                submit_button = self.driver.find_element(By.XPATH, XPATHS["submit_button"])
                submit_button.click()
            
            self.wait_with_delay(3, min_delay=1.5)  # 统一延迟控制，等待登录处理，最少1.5秒
            
            # 检查登录是否成功
            if self._check_login_success():
                self.log_signal.emit("✅ 登录成功")
                return True
            else:
                # 检查具体的登录错误
                error_msg = self._check_login_error()
                if error_msg:
                    self.log_signal.emit(f"❌ 登录失败: {error_msg}")
                else:
                    self.log_signal.emit("❌ 登录失败: 未知原因")
                return False
                
        except Exception as e:
            self.log_signal.emit(f"❌ 登录过程中发生错误: {str(e)}")
            return False
    
    def _check_login_error(self):
        """检查登录错误信息 - 复用主程序的错误检查逻辑"""
        try:
            # 检查是否有弹窗错误信息
            layers = self.driver.find_elements(By.CSS_SELECTOR, ".layui-layer-content")
            for layer in layers:
                try:
                    # 检查弹窗是否可见
                    if layer.is_displayed():
                        layer_text = layer.text.strip()
                        self.log_signal.emit(f"检测到弹窗内容: {layer_text}")
                        
                        # 检查常见的登录错误信息
                        if any(error in layer_text for error in [
                            "用户名或密码错误", "密码错误", "账号不存在", 
                            "用户被置为无效", "请填写用户名", "请填写密码"
                        ]):
                            # 尝试关闭弹窗
                            try:
                                close_btn = layer.find_element(By.CSS_SELECTOR, ".layui-layer-close")
                                if close_btn.is_displayed():
                                    close_btn.click()
                                    self.wait_with_delay(0.5)  # 统一延迟控制
                            except:
                                pass
                            return layer_text
                except:
                    continue
            
            # 也检查页面源码中的错误信息（作为备用方法）
            page_source = self.driver.page_source
            if "用户名或密码错误" in page_source:
                return "用户名或密码错误"
            elif "密码错误" in page_source:
                return "密码错误"
            elif "账号不存在" in page_source:
                return "账号不存在"
            elif "用户被置为无效" in page_source:
                return "用户被置为无效"
                
            return None
            
        except Exception as e:
            self.log_signal.emit(f"检查登录错误时出现异常: {str(e)}")
            return None
    
    def _check_login_success(self):
        """检查登录是否成功"""
        try:
            # 检查URL是否包含登录成功的标识
            current_url = self.driver.current_url
            if 'myHomework.do' in current_url or 'index.do' in current_url:
                return True
            
            # 检查页面是否包含登录后的元素
            try:
                self.driver.find_element(By.XPATH, "//a[contains(@href, 'logout')]")
                return True
            except:
                pass
            
            return False
            
        except Exception:
            return False
    
    def _navigate_to_homework(self):
        """导航到作业页面"""
        try:
            self.log_signal.emit("📚 正在访问作业页面...")
            
            # 构建正确的学生作业页面URL
            homework_url = WEBSITE_URL.replace('fore/index.do', 'stu/myHomework.do')
            self.log_signal.emit(f"🔗 访问URL: {homework_url}")
            self.driver.get(homework_url)
            self.wait_with_delay(3, min_delay=2.0)  # 统一延迟控制，确保页面完全加载
            
            # 检查是否成功到达作业页面
            current_url = self.driver.current_url
            self.log_signal.emit(f"📍 当前URL: {current_url}")
            
            if 'myHomework.do' in current_url:
                self.log_signal.emit("✅ 成功访问作业页面")
                return True
            else:
                # 检查是否被重定向到登录页面
                if 'login' in current_url.lower() or 'index.do' in current_url:
                    self.log_signal.emit("⚠️ 可能需要重新登录或会话已过期")
                else:
                    self.log_signal.emit("❌ 无法访问作业页面")
                return False
                
        except Exception as e:
            self.log_signal.emit(f"❌ 访问作业页面时发生错误: {str(e)}")
            return False
    
    def _import_all_homework_questions(self):
        """导入所有作业的题目"""
        import re  # 在方法开头导入re模块
        imported_count = 0
        
        try:
            # 检查当前是否在作业页面，如果不是则导航到作业页面
            current_url = self.driver.current_url
            if 'myHomework.do' not in current_url:
                if not self._navigate_to_homework():
                    self.log_signal.emit("❌ 无法访问作业页面")
                    return 0
            else:
                self.log_signal.emit("✅ 已在作业页面")
            
            self.log_signal.emit("🔍 正在查找所有作业...")
            
            # 尝试多种方式查找"查看"按钮
            view_buttons = []
            
            # 方式1: 标准的按钮查找
            buttons1 = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn') and contains(text(), '查看')]")
            view_buttons.extend(buttons1)
            
            # 方式2: 更宽松的按钮查找（不限制class）
            if not view_buttons:
                buttons2 = self.driver.find_elements(By.XPATH, "//button[contains(text(), '查看')]")
                view_buttons.extend(buttons2)
            
            # 方式3: 查找链接形式的"查看"
            if not view_buttons:
                links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '查看')]")
                view_buttons.extend(links)
            
            # 方式4: 查找包含"查看"的任何可点击元素
            if not view_buttons:
                clickables = self.driver.find_elements(By.XPATH, "//*[contains(text(), '查看') and (@onclick or @href)]")
                view_buttons.extend(clickables)
            
            # 调试信息：输出页面源码片段
            if not view_buttons:
                self.log_signal.emit("🔍 未找到查看按钮，正在分析页面结构...")
                page_source = self.driver.page_source
                # 查找包含"查看"的HTML片段
                view_matches = re.findall(r'.{0,100}查看.{0,100}', page_source, re.IGNORECASE)
                if view_matches:
                    self.log_signal.emit(f"📄 页面中包含'查看'的HTML片段数量: {len(view_matches)}")
                    for i, match in enumerate(view_matches[:3]):  # 只显示前3个
                        self.log_signal.emit(f"📄 片段{i+1}: {match.strip()}")
                else:
                    self.log_signal.emit("📄 页面中未找到包含'查看'的内容")
                
                # 查找所有按钮和链接
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                self.log_signal.emit(f"📊 页面统计: {len(all_buttons)}个按钮, {len(all_links)}个链接")
                
                self.log_signal.emit("⚠️ 未找到任何作业")
                return 0
            
            self.log_signal.emit(f"📋 找到 {len(view_buttons)} 个作业")
            
            # 先提取所有作业ID，避免stale element reference错误
            homework_ids = []
            for i, button in enumerate(view_buttons):
                try:
                    onclick_attr = button.get_attribute('onclick')
                    if onclick_attr and 'view(' in onclick_attr:
                        match = re.search(r"view\('([^']+)'\)", onclick_attr)
                        if match:
                            homework_id = match.group(1)
                            homework_ids.append(homework_id)
                        else:
                            self.log_signal.emit(f"⚠️ 第 {i+1} 个作业ID提取失败")
                    else:
                        self.log_signal.emit(f"⚠️ 第 {i+1} 个作业onclick属性异常")
                except Exception as e:
                    self.log_signal.emit(f"⚠️ 提取第 {i+1} 个作业ID时发生错误: {str(e)}")
                    continue
            
            self.log_signal.emit(f"📝 成功提取 {len(homework_ids)} 个作业ID")
            
            # 遍历处理每个作业ID
            for i, homework_id in enumerate(homework_ids):
                try:
                    # 计算当前进度 (40% 到 95% 之间)
                    progress = 40 + int((i / len(homework_ids)) * 55)
                    self.progress_signal.emit(progress, f"正在处理作业 {i+1}/{len(homework_ids)}")
                    self.log_signal.emit(f"📖 正在处理第 {i+1}/{len(homework_ids)} 个作业 (ID: {homework_id})...")
                    
                    # 导入该作业的题目
                    count = self._import_homework_questions(homework_id)
                    imported_count += count
                    
                    self.log_signal.emit(f"✅ 第 {i+1} 个作业导入完成，导入 {count} 个题目")
                    
                except Exception as e:
                    self.log_signal.emit(f"❌ 处理第 {i+1} 个作业时发生错误: {str(e)}")
                    continue
            
            return imported_count
            
        except Exception as e:
            self.log_signal.emit(f"❌ 导入作业题目时发生错误: {str(e)}")
            return imported_count
    
    def _import_homework_questions(self, homework_id):
        """导入单个作业的题目"""
        try:
            # 构造查看作业的URL - 使用kcid参数而不是rsid
            base_url = "https://infotech.51taoshi.com/hw/stu/viewHomework.do"
            view_url = f"{base_url}?kcid={homework_id}"
            self.log_signal.emit(f"📍 正在访问作业页面: {view_url}")
            self.driver.get(view_url)
            self.wait_with_delay(2, min_delay=1.0)  # 统一延迟控制，确保页面加载
            
            # 查找"查看作业"按钮并点击
            view_homework_btn = None
            
            # 尝试多种方式查找"查看作业"按钮
            search_strategies = [
                ("//a[contains(text(), '查看作业')]", "链接形式的查看作业按钮"),
                ("//button[contains(text(), '查看作业')]", "按钮形式的查看作业按钮"),
                ("//input[@type='button' and contains(@value, '查看作业')]", "输入按钮形式的查看作业"),
                ("//a[contains(@onclick, 'viewHomework') or contains(@href, 'viewHomework')]", "包含viewHomework的链接"),
                ("//button[contains(@onclick, 'viewHomework')]", "包含viewHomework的按钮"),
                ("//a[contains(text(), '查看')]", "包含查看的链接"),
                ("//button[contains(text(), '查看')]", "包含查看的按钮")
            ]
            
            for xpath, description in search_strategies:
                try:
                    view_homework_btn = WebDriverWait(self.driver, TIMEOUTS['element_wait']).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    self.log_signal.emit(f"✅ 找到{description}")
                    break
                except:
                    continue
            
            if view_homework_btn:
                try:
                    view_homework_btn.click()
                    self.log_signal.emit("✅ 成功点击查看作业按钮")
                    self.wait_with_delay(3, min_delay=2.0)  # 统一延迟控制，确保页面跳转完成
                except Exception as e:
                    self.log_signal.emit(f"⚠️ 点击查看作业按钮失败: {str(e)}")
            else:
                self.log_signal.emit("⚠️ 未找到任何形式的'查看作业'按钮")
                # 添加页面调试信息
                page_source = self.driver.page_source
                if '查看' in page_source:
                    import re
                    view_matches = re.findall(r'.{0,50}查看.{0,50}', page_source, re.IGNORECASE)
                    self.log_signal.emit(f"📄 页面中包含'查看'的内容片段数量: {len(view_matches)}")
                    for i, match in enumerate(view_matches[:3]):
                        self.log_signal.emit(f"📄 片段{i+1}: {match.strip()}")
                else:
                    self.log_signal.emit("📄 页面中未找到包含'查看'的内容")
                
                # 检查是否已经在题目页面
                if any(keyword in page_source for keyword in ['题目', '答案', 'timu', 'answer']):
                    self.log_signal.emit("💡 页面可能已经显示题目内容，直接解析")
                else:
                    self.log_signal.emit("❌ 页面既没有查看按钮也没有题目内容")
            
            # 解析页面中的题目和答案
            return self._parse_questions_from_page()
            
        except Exception as e:
            self.log_signal.emit(f"❌ 导入作业 {homework_id} 时发生错误: {str(e)}")
            return 0
    
    def _parse_questions_from_page(self):
        """从页面解析题目和答案"""
        imported_count = 0
        
        try:
            # 获取页面源码
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 查找所有题目容器
            question_containers = soup.find_all('li')
            
            for container in question_containers:
                try:
                    # 查找题目内容
                    timu_div = container.find('div', class_='timu')
                    if not timu_div:
                        continue
                    
                    # 提取题目文本
                    question_text = self._extract_question_text(timu_div)
                    if not question_text:
                        continue
                    
                    # 查找答案信息
                    info_div = container.find('div', class_='info')
                    if not info_div:
                        continue
                    
                    # 提取正确答案
                    correct_answer = self._extract_correct_answer(info_div)
                    if not correct_answer:
                        continue
                    
                    # 确定题目类型
                    question_type = self._determine_question_type(timu_div)
                    
                    # 保存到数据库
                    if self._save_question_to_db(question_text, correct_answer, question_type):
                        imported_count += 1
                        
                except Exception as e:
                    self.log_signal.emit(f"⚠️ 解析单个题目时发生错误: {str(e)}")
                    continue
            
            return imported_count
            
        except Exception as e:
            self.log_signal.emit(f"❌ 解析页面题目时发生错误: {str(e)}")
            return 0
    
    def _extract_question_text(self, timu_div):
        """提取题目文本"""
        try:
            # 获取题目的主要文本，去除题号和分数
            question_text = timu_div.get_text(strip=True)
            
            # 去除题号（如"1.(30分)"）
            question_text = re.sub(r'^\d+\.\(\d+分\)', '', question_text)
            
            # 去除选择题的选项部分
            lines = question_text.split('\n')
            question_lines = []
            
            for line in lines:
                line = line.strip()
                # 如果遇到选项（A. B. C. D.），停止添加
                if re.match(r'^[A-Z]\.|^[A-Z]、', line):
                    break
                if line:
                    question_lines.append(line)
            
            return '\n'.join(question_lines).strip()
            
        except Exception:
            return None
    
    def _extract_correct_answer(self, info_div):
        """提取正确答案"""
        try:
            # 查找正确答案
            answer_spans = info_div.find_all('span')
            
            for i, span in enumerate(answer_spans):
                if '【正确答案：】' in span.get_text():
                    # 正确答案在下一个span中
                    if i + 1 < len(answer_spans):
                        answer_text = answer_spans[i + 1].get_text().strip()
                        # 去除可能的"分"字
                        answer_text = re.sub(r'分$', '', answer_text)
                        return answer_text
            
            return None
            
        except Exception:
            return None
    
    def _determine_question_type(self, timu_div):
        """确定题目类型"""
        try:
            # 查找选择列表
            choose_list = timu_div.find('ul', class_='choose-list')
            
            if choose_list:
                # 有选择列表，是选择题
                options = choose_list.find_all('li')
                if len(options) > 0:
                    return 'choice'
            
            # 默认为主观题
            return 'subjective'
            
        except Exception:
            return 'subjective'
    
    def _save_question_to_db(self, question_text, correct_answer, question_type):
        """保存题目到数据库"""
        try:
            # 检查题目是否已存在
            if self.question_db.question_exists(question_text):
                return False
            
            # 添加题目到数据库
            self.question_db.add_question(question_text, correct_answer, question_type)
            return True
            
        except Exception as e:
            self.log_signal.emit(f"⚠️ 保存题目到数据库时发生错误: {str(e)}")
            return False
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.driver:
                self.driver.quit()
                self.log_signal.emit("🧹 浏览器资源已清理")
        except Exception as e:
            self.log_signal.emit(f"⚠️ 清理资源时发生错误: {str(e)}")