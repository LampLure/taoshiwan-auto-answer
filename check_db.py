import sqlite3
import os

db_path = 'questions.db'
print(f'检查数据库文件: {db_path}')
print(f'文件是否存在: {os.path.exists(db_path)}')

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f'数据库中的表: {tables}')
    
    # 检查questions表的结构
    cursor.execute("PRAGMA table_info(questions);")
    columns = cursor.fetchall()
    print(f'questions表结构: {columns}')
    
    # 查询数据
    cursor.execute('SELECT COUNT(*) FROM questions')
    count = cursor.fetchone()[0]
    print(f'题目总数: {count}')
    
    if count > 0:
        cursor.execute('SELECT content, answer, keywords FROM questions LIMIT 3')
        results = cursor.fetchall()
        
        print('\n数据库中的题目和答案:')
        for i, (content, answer, keywords) in enumerate(results, 1):
            print(f'\n题目{i}: {content[:100]}...')
            print(f'答案: {answer}')
            print(f'关键词: {keywords[:100] if keywords else "无"}...')
            print('-' * 50)
    
    conn.close()
except Exception as e:
    print(f'错误: {e}')