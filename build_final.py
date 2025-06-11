#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终打包脚本 - 解决中文路径问题
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("开始打包自动答题程序...")
    
    # 检查文件
    if not os.path.exists('main.py'):
        print("错误: 找不到main.py文件")
        return
    
    if not os.path.exists('questions.db'):
        print("错误: 找不到questions.db文件")
        return
        
    try:
        # 1. 安装PyInstaller
        print("1. 检查PyInstaller...")
        try:
            import PyInstaller
            print("PyInstaller已安装")
        except ImportError:
            print("安装PyInstaller...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
        # 2. 清理旧文件
        print("2. 清理旧的构建文件...")
        for folder in ['build', 'dist', '__pycache__']:
            if os.path.exists(folder):
                shutil.rmtree(folder)
        
        # 3. 创建临时spec文件来避免中文路径问题
        print("3. 创建打包配置...")
        spec_content = '''# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('questions.db', '.'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.common.by',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.wait',
        'selenium.common.exceptions',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'psutil',
        'sqlite3',
        'json',
        'time',
        'random'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5.Qt'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='auto_answer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
        
        with open('temp_build.spec', 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        # 4. 使用spec文件打包
        print("4. 开始打包...")
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "temp_build.spec"]
        print(f"执行命令: {' '.join(cmd)}")
        
        # 设置环境变量来避免编码问题
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("打包成功！")
            
            # 5. 创建最终发布包
            print("5. 创建发布包...")
            release_dir = 'release'
            if os.path.exists(release_dir):
                shutil.rmtree(release_dir)
            os.makedirs(release_dir)
            
            # 复制exe文件
            if os.path.exists('dist/auto_answer.exe'):
                shutil.copy('dist/auto_answer.exe', release_dir)
                print(f"exe文件已复制到: {release_dir}/auto_answer.exe")
            
            # 复制数据文件（作为备份）
            shutil.copy('questions.db', release_dir)
            shutil.copy('config.py', release_dir)
            
            # 创建使用说明
            readme_content = '''# 自动答题程序使用说明

## 文件说明
- auto_answer.exe: 主程序文件
- questions.db: 题库数据库（已内置到exe中）
- config.py: 配置文件（已内置到exe中）

## 使用方法
1. 双击运行 auto_answer.exe
2. 按照程序界面提示操作

## 注意事项
- 首次运行可能需要较长时间加载
- 确保网络连接正常
- 如遇问题请查看控制台输出信息
'''
            
            with open(f'{release_dir}/README.txt', 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            print("\n" + "="*50)
            print("打包完成！")
            print(f"发布文件位置: {os.path.abspath(release_dir)}/")
            print("主程序: auto_answer.exe")
            print("题库文件已内置到exe中")
            print("="*50)
            
        else:
            print("打包失败！")
            print("错误输出:")
            print(result.stderr)
            
            # 尝试简化打包
            print("\n尝试简化打包...")
            simple_cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onefile",
                "--windowed",
                "--name=auto_answer",
                "--exclude-module=PyQt5.Qt",
                "main.py"
            ]
            
            print(f"简化命令: {' '.join(simple_cmd)}")
            result2 = subprocess.run(simple_cmd, env=env)
            
            if result2.returncode == 0:
                print("简化打包成功！")
                # 手动处理数据文件
                release_dir = 'release_simple'
                if os.path.exists(release_dir):
                    shutil.rmtree(release_dir)
                os.makedirs(release_dir)
                
                if os.path.exists('dist/auto_answer.exe'):
                    shutil.copy('dist/auto_answer.exe', release_dir)
                    shutil.copy('questions.db', release_dir)
                    shutil.copy('config.py', release_dir)
                    
                    print(f"\n简化版打包完成！")
                    print(f"文件位置: {os.path.abspath(release_dir)}/")
                    print("注意: 需要将questions.db和config.py与exe文件放在同一目录")
            else:
                print("简化打包也失败了")
                return False
        
        # 清理临时文件
        if os.path.exists('temp_build.spec'):
            os.remove('temp_build.spec')
            
        return True
        
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n程序打包完成！")
    else:
        print("\n程序打包失败！")
    
    input("按回车键退出...")