#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
最终验证脚本 - 测试修复后的浏览器显示问题
"""

import sys
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

def test_main_program():
    """测试主程序的浏览器显示"""
    print("=== 测试主程序浏览器显示 ===")
    
    try:
        # 导入主程序模块
        from ui import AutoAnswerApp
        from database import QuestionDatabase
        
        # 创建QApplication
        app = QApplication(sys.argv)
        
        # 创建数据库实例
        db = QuestionDatabase()
        
        # 创建主窗口
        window = AutoAnswerApp(db)
        window.show()
        
        print("✅ 主程序窗口已显示")
        
        # 添加一些测试账号
        test_accounts = [
            {"username": "test1", "password": "123456"},
            {"username": "test2", "password": "123456"}
        ]
        
        for account in test_accounts:
            window.username_input.setText(account["username"])
            window.password_input.setText(account["password"])
            window.add_account()
        
        print(f"✅ 已添加 {len(test_accounts)} 个测试账号")
        
        # 设置定时器，5秒后启动自动化
        def start_automation():
            print("🚀 启动自动化测试...")
            window.start_automation()
            
            # 再设置一个定时器，10秒后停止
            def stop_automation():
                print("⏹️ 停止自动化测试...")
                if hasattr(window, 'thread_manager') and window.thread_manager:
                    window.thread_manager.stop_all_threads()
                print("✅ 自动化测试已停止")
                
                # 3秒后关闭程序
                QTimer.singleShot(3000, app.quit)
            
            QTimer.singleShot(10000, stop_automation)
        
        QTimer.singleShot(5000, start_automation)
        
        print("程序将在5秒后启动自动化，15秒后自动停止")
        print("请观察是否有浏览器窗口显示...")
        
        # 运行应用
        app.exec_()
        
        print("✅ 主程序测试完成")
        
    except Exception as e:
        print(f"❌ 主程序测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_direct_automation():
    """直接测试自动化模块"""
    print("\n=== 直接测试自动化模块 ===")
    
    try:
        from automation import BrowserAutomation
        from database import QuestionDatabase
        
        # 创建测试账号
        test_accounts = [
            {"username": "test1", "password": "123456"}
        ]
        
        # 创建数据库实例
        db = QuestionDatabase()
        
        # 创建自动化实例
        automation = BrowserAutomation(test_accounts, db)
        
        print("启动自动化线程...")
        automation.start()
        
        print("等待10秒，观察浏览器窗口...")
        time.sleep(10)
        
        print("停止自动化...")
        automation.running = False
        automation.wait()
        
        print("✅ 直接自动化测试完成")
        
    except Exception as e:
        print(f"❌ 直接自动化测试失败: {e}")
        import traceback
        traceback.print_exc()

def check_environment():
    """检查运行环境"""
    print("=== 环境检查 ===")
    
    # 检查虚拟环境
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 当前在虚拟环境中")
    else:
        print("⚠️ 当前在系统环境中")
    
    # 检查打包环境
    if hasattr(sys, '_MEIPASS'):
        print("📦 检测到打包环境")
    else:
        print("🔧 检测到开发环境")
    
    # 检查配置
    try:
        import config
        print(f"SHOW_BROWSER_WINDOW: {config.SHOW_BROWSER_WINDOW}")
        print(f"浏览器选项数量: {len(config.BROWSER_OPTIONS)}")
        
        # 检查是否有headless选项
        has_headless = any('headless' in opt for opt in config.BROWSER_OPTIONS)
        if has_headless:
            print("❌ 配置中包含headless选项")
        else:
            print("✅ 配置中没有headless选项")
            
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")

if __name__ == "__main__":
    print("浏览器显示问题最终验证")
    print("=" * 60)
    
    # 1. 环境检查
    check_environment()
    
    # 2. 直接测试自动化模块
    test_direct_automation()
    
    # 3. 测试主程序（需要GUI）
    print("\n是否测试主程序GUI？(y/n): ", end="")
    try:
        choice = input().strip().lower()
        if choice == 'y':
            test_main_program()
        else:
            print("跳过主程序GUI测试")
    except:
        print("跳过主程序GUI测试")
    
    print("\n=== 最终验证完成 ===")
    print("\n🔧 修复总结:")
    print("1. ✅ 移除了可能导致窗口隐藏的浏览器选项")
    print("2. ✅ 添加了强制显示窗口的选项 (--start-maximized)")
    print("3. ✅ 简化了CPU优化选项，避免冲突")
    print("4. ✅ 保持了SHOW_BROWSER_WINDOW=True的配置")
    print("\n如果浏览器仍然不显示，可能的原因:")
    print("- 显卡驱动问题")
    print("- Windows显示设置问题")
    print("- Chrome浏览器版本兼容性问题")
    print("- 防火墙或安全软件阻止")