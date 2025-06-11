#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动答题程序打包脚本
使用PyInstaller将程序打包成exe文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    """安装PyInstaller"""
    print("正在安装PyInstaller...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller安装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller安装失败: {e}")
        return False

def create_spec_file():
    """创建PyInstaller spec文件"""
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

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
        'selenium.webdriver.common',
        'selenium.webdriver.support',
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'psutil',
        'sqlite3',
        'hashlib',
        'time',
        'threading',
        'logging',
        'traceback',
        'subprocess',
        'functools',
        'contextlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='自动答题程序',
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
    icon=None,
)
'''
    
    with open('auto_answer.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("已创建 auto_answer.spec 文件")

def build_exe():
    """构建exe文件"""
    print("开始构建exe文件...")
    try:
        # 清理之前的构建文件
        if os.path.exists('build'):
            shutil.rmtree('build')
        if os.path.exists('dist'):
            shutil.rmtree('dist')
        
        # 使用spec文件构建
        subprocess.check_call([sys.executable, "-m", "PyInstaller", "auto_answer.spec"])
        
        print("\n" + "="*50)
        print("构建完成！")
        print("exe文件位置: dist/自动答题程序.exe")
        print("="*50)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        return False

def main():
    """主函数"""
    print("自动答题程序打包工具")
    print("="*30)
    
    # 检查是否在正确的目录
    if not os.path.exists('main.py'):
        print("错误: 请在包含main.py的目录中运行此脚本")
        return
    
    # 安装PyInstaller
    if not install_pyinstaller():
        return
    
    # 创建spec文件
    create_spec_file()
    
    # 构建exe
    if build_exe():
        print("\n打包成功！您可以将dist文件夹中的exe文件发送给其他人使用。")
        print("注意: 首次运行时程序会自动下载Chrome驱动，请确保网络连接正常。")
    else:
        print("\n打包失败，请检查错误信息。")

if __name__ == "__main__":
    main()