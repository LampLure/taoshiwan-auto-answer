#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cx_Freeze打包脚本
"""

import sys
import os
from cx_Freeze import setup, Executable

# 确保包含的文件
include_files = [
    ('questions.db', 'questions.db'),
    ('config.py', 'config.py'),
]

# 需要包含的包
packages = [
    'selenium',
    'PyQt5',
    'psutil',
    'sqlite3',
    'json',
    'time',
    'random',
    'os',
    'sys',
    'traceback',
    'logging'
]

# 构建选项
build_exe_options = {
    'packages': packages,
    'include_files': include_files,
    'excludes': ['tkinter'],  # 排除不需要的模块
    'optimize': 2,
}

# 如果是Windows，设置为窗口应用
base = None
if sys.platform == 'win32':
    base = 'Win32GUI'  # 使用Win32GUI隐藏控制台窗口

# 可执行文件配置
executables = [
    Executable(
        'main.py',
        base=base,
        target_name='auto_answer.exe',
        icon=None
    )
]

# 设置配置
setup(
    name='AutoAnswer',
    version='1.0',
    description='自动答题程序',
    options={'build_exe': build_exe_options},
    executables=executables
)