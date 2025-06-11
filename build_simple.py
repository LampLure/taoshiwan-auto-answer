#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版打包脚本
"""

import os
import sys
import subprocess
import shutil

def main():
    import shutil
    print("开始打包自动答题程序...")
    
    # 检查文件
    if not os.path.exists('main.py'):
        print("错误: 找不到main.py文件")
        return
    
    try:
        # 安装PyInstaller
        print("1. 安装PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
        # 清理旧文件
        print("2. 清理旧的构建文件...")
        for folder in ['build', 'dist', '__pycache__']:
            if os.path.exists(folder):
                shutil.rmtree(folder)
        
        # 打包命令
        print("3. 开始打包...")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",  # 打包成单个exe文件
            "--windowed",  # 隐藏控制台窗口
            "--name=auto_answer",  # 使用英文文件名避免编码问题
            "--add-data=questions.db;.",  # 包含数据库文件
            "--add-data=config.py;.",  # 包含配置文件
            "--hidden-import=selenium",
            "--hidden-import=PyQt5",
            "--hidden-import=psutil",
            "--exclude-module=PyQt5.Qt",  # 排除有问题的模块
            "main.py"
        ]
        
        print(f"执行命令: {' '.join(cmd)}")
        
        # 直接运行命令，不捕获输出，这样可以看到实时输出
        try:
            subprocess.check_call(cmd)
            print("打包成功！")
        except subprocess.CalledProcessError as e:
            print(f"打包失败，返回码: {e.returncode}")
            # 尝试使用更简单的命令
            print("\n尝试使用更简单的打包命令...")
            simple_cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onefile",
                "--windowed",
                "--name=auto_answer",
                "main.py"
            ]
            print(f"简化命令: {' '.join(simple_cmd)}")
            subprocess.check_call(simple_cmd)
            
            # 手动复制数据文件
            print("手动复制数据文件...")
            if os.path.exists('dist/auto_answer.exe'):
                # 创建一个包含exe和数据文件的文件夹
                output_dir = 'dist/auto_answer_package'
                os.makedirs(output_dir, exist_ok=True)
                shutil.copy('dist/auto_answer.exe', output_dir)
                shutil.copy('questions.db', output_dir)
                shutil.copy('config.py', output_dir)
                print(f"打包完成！文件位置: {output_dir}/")
            raise
        
        print("\n" + "="*50)
        print("打包完成！")
        print("exe文件位置: dist/暴打淘师湾作业网.exe")
        print("文件大小约: 50-100MB")
        print("="*50)
        print("\n使用说明:")
        print("1. 将dist文件夹中的'暴打淘师湾作业网.exe'发送给其他人")
        print("2. 双击exe文件即可运行")
        print("3. 首次运行会自动下载Chrome驱动(需要网络)")
        print("4. 确保目标电脑已安装Chrome浏览器")
        
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        print("\n可能的解决方案:")
        print("1. 确保网络连接正常")
        print("2. 尝试更新pip: python -m pip install --upgrade pip")
        print("3. 手动安装依赖: pip install -r requirements.txt")
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    main()