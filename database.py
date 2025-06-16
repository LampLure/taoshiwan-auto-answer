import sqlite3
import threading
from contextlib import contextmanager
from config import DATABASE_PATH, SIMILARITY_THRESHOLD

class QuestionDatabase:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器，实现连接复用"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path)
            # 启用WAL模式提高并发性能
            self._local.connection.execute('PRAGMA journal_mode=WAL')
            # 优化SQLite性能设置
            self._local.connection.execute('PRAGMA synchronous=NORMAL')
            self._local.connection.execute('PRAGMA cache_size=10000')
            self._local.connection.execute('PRAGMA temp_store=memory')
        
        try:
            yield self._local.connection
        except Exception:
            # 发生异常时回滚事务
            self._local.connection.rollback()
            raise
    
    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建题目表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                answer TEXT NOT NULL,
                type TEXT NOT NULL,
                keywords TEXT
            )
            ''')
            
            # 创建索引
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content ON questions(content)
            ''')
            
            conn.commit()
    
    def add_question(self, content, answer, type, keywords=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO questions (content, answer, type, keywords)
            VALUES (?, ?, ?, ?)
            ''', (content, answer, type, keywords))
            
            conn.commit()
    
    def find_answer(self, question_text):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 先尝试精确匹配
            cursor.execute('''
            SELECT answer FROM questions
            WHERE content = ?
            ''', (question_text,))
            
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # 预处理查询文本
            cleaned_query = self.clean_text(question_text)
            query_words = set(cleaned_query.split())
            
            # 如果没有精确匹配，使用优化的模糊匹配
            # 只获取必要的字段，减少内存使用
            cursor.execute('''
            SELECT answer, content FROM questions
            ''')
            
            best_match = None
            highest_similarity = 0
            min_threshold = SIMILARITY_THRESHOLD  # 使用配置的相似度阈值
            
            # 批量处理，减少函数调用开销
            for answer, content in cursor.fetchall():
                # 快速预筛选：检查是否有共同词汇
                cleaned_content = self.clean_text(content)
                content_words = set(cleaned_content.split())
                
                # 如果没有共同词汇，跳过详细计算
                if not query_words.intersection(content_words):
                    continue
                
                similarity = self.calculate_similarity_fast(cleaned_query, cleaned_content, query_words, content_words)
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = answer
                    
                    # 如果相似度很高，提前返回
                    if similarity > 0.9:
                        break
            
            # 只要找到相似度大于最低阈值的答案就返回
            if highest_similarity > min_threshold:
                return best_match
            
            return None
    
    def clean_text(self, text):
        """改进的文本清理方法，提高匹配准确性"""
        import re
        
        # 移除题号、分数等格式
        text = re.sub(r'\d+\.\s*\(\d+分\)\s*', '', text)
        
        # 统一标点符号：将中文标点替换为英文标点
        text = text.replace('，', ',')
        text = text.replace('。', '.')
        text = text.replace('；', ';')
        text = text.replace('：', ':')
        text = text.replace('？', '?')
        text = text.replace('！', '!')
        text = text.replace('《', '')
        text = text.replace('》', '')
        text = text.replace('「', '')
        text = text.replace('」', '')
        text = text.replace('（', '(')
        text = text.replace('）', ')')
        
        # 移除所有标点符号和特殊字符，替换为空格以避免词汇粘连
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
        
        # 统一处理空格：多个空格合并为一个，去除首尾空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text.lower()
    
    def calculate_similarity_fast(self, clean_text1, clean_text2, words1, words2):
        """优化的快速相似度计算"""
        # 如果清理后的文本包含关系，给予较高相似度
        if clean_text1 in clean_text2 or clean_text2 in clean_text1:
            return 0.8
        
        # 快速Jaccard相似度计算
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        jaccard = len(intersection) / len(union) if union else 0
        
        # 如果词汇相似度已经很高，直接返回
        if jaccard > 0.7:
            return jaccard
        
        # 只有在词汇相似度较低时才进行字符级计算
        chars1 = set(clean_text1.replace(' ', ''))
        chars2 = set(clean_text2.replace(' ', ''))
        char_intersection = chars1.intersection(chars2)
        char_union = chars1.union(chars2)
        char_similarity = len(char_intersection) / len(char_union) if char_union else 0
        
        # 综合相似度（词级别和字符级别的加权平均）
        return (jaccard * 0.6 + char_similarity * 0.4)
    
    def calculate_similarity(self, text1, text2):
        """保持向后兼容的相似度计算方法"""
        clean_text1 = self.clean_text(text1)
        clean_text2 = self.clean_text(text2)
        words1 = set(clean_text1.split())
        words2 = set(clean_text2.split())
        return self.calculate_similarity_fast(clean_text1, clean_text2, words1, words2)
    
    def question_exists(self, content):
        """检查题目是否已存在"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT COUNT(*) FROM questions WHERE content = ?
            ''', (content,))
            
            result = cursor.fetchone()
            return result[0] > 0 if result else False
    
    def get_all_questions(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, content, answer, type, keywords FROM questions
            ''')
            
            return cursor.fetchall()
    
    def delete_question(self, question_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            DELETE FROM questions WHERE id = ?
            ''', (question_id,))
            
            conn.commit()
        
    def update_question(self, question_id, answer, type, keywords=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if keywords is not None:
                cursor.execute('''
                UPDATE questions SET answer = ?, type = ?, keywords = ? WHERE id = ?
                ''', (answer, type, keywords, question_id))
            else:
                cursor.execute('''
                UPDATE questions SET answer = ?, type = ? WHERE id = ?
                ''', (answer, type, question_id))
            
            conn.commit()
    
    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        try:
            self.close_connection()
        except:
            pass