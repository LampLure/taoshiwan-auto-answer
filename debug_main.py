#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from multi_thread_manager import MultiThreadManager
from database import QuestionDatabase
import time

def debug_main():
    print('开始调试多线程程序...')
    
    # 创建Qt应用
    app = QApplication(sys.argv)
    
    # 创建数据库管理器
    question_db = QuestionDatabase()
    
    # 创建一些测试账号
    test_accounts = [
        {'username': 'test1', 'password': 'pass1'},
        {'username': 'test2', 'password': 'pass2'},
        {'username': 'test3', 'password': 'pass3'}
    ]
    
    print(f'创建了 {len(test_accounts)} 个测试账号')
    
    # 创建多线程管理器
    manager = MultiThreadManager(question_db)
    manager.set_thread_count(2)  # 使用2个线程进行测试
    
    # 连接信号
    manager.log_signal.connect(lambda msg: print(f'[管理器] {msg}'))
    manager.status_signal.connect(lambda idx, status: print(f'[状态] 账号{idx}: {status}'))
    manager.progress_signal.connect(lambda progress, msg: print(f'[进度] {progress}%: {msg}'))
    manager.all_finished_signal.connect(lambda: print('[完成] 所有线程已完成'))
    
    # 使用测试账号
    accounts = test_accounts
    print(f'使用 {len(accounts)} 个测试账号')
    
    try:
        print('启动多线程处理...')
        manager.start_automation(accounts)
        
        # 设置定时器检查状态
        def check_status():
            print(f'当前运行状态: {manager.running}, 完成线程数: {manager.finished_threads}/{len(manager.workers)}')
            if not manager.running and manager.finished_threads >= len(manager.workers):
                print('所有线程已完成，退出程序')
                app.quit()
        
        timer = QTimer()
        timer.timeout.connect(check_status)
        timer.start(2000)  # 每2秒检查一次
        
        # 运行应用
        app.exec_()
        
    except Exception as e:
        print(f'调试过程中发生错误: {e}')
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理
        if manager.running:
            manager.stop_all()
        print('调试完成')

if __name__ == '__main__':
    debug_main()