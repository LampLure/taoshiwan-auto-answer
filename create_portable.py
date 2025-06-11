#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建便携式程序包
直接打包Python环境和脚本
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def create_portable_app():
    print("创建便携式自动答题程序...")
    
    # 创建输出目录
    output_dir = 'portable_app'
    if os.path.exists(output_dir):
        print(f"删除旧的 {output_dir} 目录...")
        shutil.rmtree(output_dir)
    
    os.makedirs(output_dir)
    print(f"创建目录: {output_dir}")
    
    # 1. 复制Python可执行文件
    python_exe = sys.executable
    venv_dir = os.path.dirname(python_exe)
    
    print("1. 复制Python环境...")
    # 复制Python可执行文件
    shutil.copy(python_exe, output_dir)
    shutil.copy(os.path.join(venv_dir, 'pythonw.exe'), output_dir)
    
    # 复制必要的DLL文件
    for dll_file in ['python312.dll', 'vcruntime140.dll', 'vcruntime140_1.dll']:
        dll_path = os.path.join(venv_dir, dll_file)
        if os.path.exists(dll_path):
            shutil.copy(dll_path, output_dir)
            print(f"复制: {dll_file}")
    
    # 2. 复制Lib目录（只复制必要的包）
    print("2. 复制Python库...")
    lib_source = os.path.join(venv_dir, '..', 'Lib')
    lib_target = os.path.join(output_dir, 'Lib')
    
    # 复制标准库
    shutil.copytree(os.path.join(lib_source, 'site-packages'), 
                   os.path.join(lib_target, 'site-packages'))
    
    # 复制一些必要的标准库模块
    essential_modules = [
        'json', 'sqlite3', 'logging', 'urllib', 'http', 'email',
        'encodings', 'importlib', 'collections', 'xml', 'html'
    ]
    
    python_lib = os.path.join(sys.prefix, 'Lib')
    for module in essential_modules:
        module_path = os.path.join(python_lib, module)
        if os.path.exists(module_path):
            if os.path.isdir(module_path):
                shutil.copytree(module_path, os.path.join(lib_target, module))
            else:
                shutil.copy(module_path + '.py', lib_target)
    
    # 3. 复制程序文件
    print("3. 复制程序文件...")
    program_files = [
        'main.py', 'ui.py', 'automation.py', 'database.py', 
        'config.py', 'questions.db'
    ]
    
    for file in program_files:
        if os.path.exists(file):
            shutil.copy(file, output_dir)
            print(f"复制: {file}")
    
    # 4. 创建启动脚本
    print("4. 创建启动脚本...")
    
    # Windows批处理文件
    bat_content = '''@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0;%~dp0\Lib;%~dp0\Lib\site-packages
python.exe main.py
pause
'''
    
    with open(os.path.join(output_dir, '启动程序.bat'), 'w', encoding='gbk') as f:
        f.write(bat_content)
    
    # 静默启动脚本（无控制台窗口）
    silent_bat = '''@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0;%~dp0\Lib;%~dp0\Lib\site-packages
pythonw.exe main.py
'''
    
    with open(os.path.join(output_dir, '静默启动.bat'), 'w', encoding='gbk') as f:
        f.write(silent_bat)
    
    # 5. 创建说明文件
    print("5. 创建说明文件...")
    readme_content = '''# 便携式自动答题程序

## 使用方法

### 方式一：双击运行
- 双击 "启动程序.bat" - 显示控制台窗口，可以看到运行信息
- 双击 "静默启动.bat" - 不显示控制台窗口，静默运行

### 方式二：命令行运行
在当前目录打开命令提示符，输入：
```
python main.py
```

## 文件说明
- python.exe / pythonw.exe: Python解释器
- main.py: 主程序文件
- ui.py: 用户界面
- automation.py: 自动化逻辑
- database.py: 数据库操作
- config.py: 配置文件
- questions.db: 题库数据库
- Lib/: Python库文件

## 注意事项
1. 首次运行可能需要较长时间加载
2. 确保网络连接正常
3. 不要删除或移动程序文件
4. 如遇问题，使用"启动程序.bat"查看错误信息

## 系统要求
- Windows 7/8/10/11
- 网络连接
- Chrome浏览器（程序会自动下载ChromeDriver）
'''
    
    with open(os.path.join(output_dir, 'README.txt'), 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    # 6. 测试程序
    print("6. 测试程序...")
    test_cmd = [os.path.join(output_dir, 'python.exe'), '-c', 'import sys; print("Python环境正常")']
    
    try:
        result = subprocess.run(test_cmd, capture_output=True, text=True, cwd=output_dir)
        if result.returncode == 0:
            print("✓ Python环境测试通过")
        else:
            print(f"✗ Python环境测试失败: {result.stderr}")
    except Exception as e:
        print(f"✗ 测试失败: {e}")
    
    # 7. 计算大小
    def get_dir_size(path):
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total += os.path.getsize(filepath)
        return total
    
    size_mb = get_dir_size(output_dir) / (1024 * 1024)
    
    print("\n" + "="*50)
    print("便携式程序创建完成！")
    print(f"输出目录: {os.path.abspath(output_dir)}")
    print(f"程序大小: {size_mb:.1f} MB")
    print("\n启动方式:")
    print("1. 双击 '启动程序.bat' (推荐)")
    print("2. 双击 '静默启动.bat'")
    print("="*50)
    
    return True

def main():
    try:
        success = create_portable_app()
        if success:
            print("\n程序打包成功！")
        else:
            print("\n程序打包失败！")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()