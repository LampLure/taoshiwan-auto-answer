import sys
import os
import sys
import traceback
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui import AutoAnswerApp
from database import QuestionDatabase

# 设置Qt平台插件路径
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(os.path.dirname(__file__), 'venv', 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins')

# 配置日志记录
logging.basicConfig(
    filename='app_error.log',
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    try:
        app = QApplication(sys.argv)
        
        # 初始化题库数据库
        question_db = QuestionDatabase()
        
        # 创建并显示主窗口
        window = AutoAnswerApp(question_db)
        window.show()
        
        return app.exec_()
    except Exception as e:
        # 记录异常信息到日志文件
        error_msg = f"程序发生错误: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        
        # 显示错误对话框
        if 'app' in locals():
            QMessageBox.critical(None, "程序错误", f"程序发生错误: {str(e)}\n请查看app_error.log获取详细信息")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())