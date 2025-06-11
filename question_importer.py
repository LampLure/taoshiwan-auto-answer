import re
import sqlite3
from config import DATABASE_PATH

class QuestionImporter:
    def __init__(self, question_db):
        self.question_db = question_db
        
    def _filter_non_text(self, text):
        """过滤非文本字符和可能的图片数据"""
        # 只保留可打印的ASCII字符、常见中文字符和标点符号
        filtered_text = ""
        for char in text:
            # 检查字符是否为可打印ASCII字符或常见中文字符
            if (ord(char) >= 32 and ord(char) <= 126) or \
               (ord(char) >= 0x4E00 and ord(char) <= 0x9FFF) or \
               (ord(char) >= 0xFF00 and ord(char) <= 0xFFEF) or \
               (ord(char) >= 0x3000 and ord(char) <= 0x303F) or \
               char in '\n\r\t，。！？：；''"（）【】《》、':
                filtered_text += char
        return filtered_text
    
    def import_from_text(self, text):
        """从文本中导入题目和答案到题库"""
        try:
            # 过滤非文本字符和可能的图片数据
            text = self._filter_non_text(text)
            
            # 首先尝试标准格式（包含选项或标准答案格式）
            questions = self._split_questions(text)
            imported_count = 0
            
            if questions:
                # 解析标准格式题目
                for question in questions:
                    if self._parse_and_add_question(question):
                        imported_count += 1
            
            # 如果标准格式没有识别到题目，尝试简单主观题格式
            if imported_count == 0:
                simple_questions = self._split_simple_subjective_questions(text)
                if simple_questions:
                    for question in simple_questions:
                        if self._parse_simple_subjective_question(question):
                            imported_count += 1
            
            if imported_count == 0:
                return {"success": False, "message": "未能识别任何题目，请检查格式是否正确"}
            
            return {"success": True, "imported_count": imported_count}
        except Exception as e:
            return {"success": False, "message": f"导入过程中发生错误: {str(e)}"}
    
    def import_simple_subjective_from_text(self, text):
        """专门导入简单主观题格式：题号+分值+题目+答案"""
        try:
            # 过滤非文本字符和可能的图片数据
            text = self._filter_non_text(text)
            
            # 分割文本为单独的题目
            questions = self._split_simple_subjective_questions(text)
            
            if not questions:
                return {"success": False, "message": "未能识别任何简单主观题，请检查格式是否正确"}
            
            # 解析每个题目并添加到数据库
            imported_count = 0
            for question in questions:
                if self._parse_simple_subjective_question(question):
                    imported_count += 1
            
            if imported_count == 0:
                return {"success": False, "message": "未能成功导入任何题目，请检查格式是否正确"}
            
            return {"success": True, "imported_count": imported_count}
        except Exception as e:
            return {"success": False, "message": f"导入过程中发生错误: {str(e)}"}
    
    def _split_questions(self, text):
        """将文本分割为单独的题目"""
        # 使用题号作为分隔符，例如"1.(30分)"、"2.(40分)"等
        pattern = r'\d+\.\s*\(\d+分\)'
        
        # 查找所有匹配的位置
        matches = list(re.finditer(pattern, text))
        
        if not matches:
            return []
        
        questions = []
        for i in range(len(matches)):
            start = matches[i].start()
            # 如果是最后一个题目，结束位置为文本末尾
            end = matches[i+1].start() if i < len(matches) - 1 else len(text)
            question_text = text[start:end].strip()
            
            # 检查题目是否包含答案信息（支持选择题和解答题）
            has_answer = ("【正确答案：】" in question_text or 
                         "【我的答案：】" in question_text)
            
            if has_answer:
                questions.append(question_text)
            else:
                # 如果没有标准答案格式，但包含基本题目结构，也尝试添加
                if len(question_text) > 20:  # 确保不是空题目
                    questions.append(question_text)
        
        return questions
    
    def _split_simple_subjective_questions(self, text):
        """分割简单主观题格式：题号+分值+题目+答案"""
        # 使用题号作为分隔符，例如"1.(40分)"、"2.(40分)"等
        pattern = r'\d+\.\s*\(\d+分\)'
        
        # 查找所有匹配的位置
        matches = list(re.finditer(pattern, text))
        
        if not matches:
            return []
        
        questions = []
        for i in range(len(matches)):
            start = matches[i].start()
            # 如果是最后一个题目，结束位置为文本末尾
            end = matches[i+1].start() if i < len(matches) - 1 else len(text)
            question_text = text[start:end].strip()
            
            # 简单主观题格式不包含选项标识符A、B、C、D
            if not re.search(r'[A-D]\.', question_text) and len(question_text) > 20:
                questions.append(question_text)
        
        return questions
    
    def _parse_and_add_question(self, question_text):
        """解析题目文本并添加到数据库"""
        try:
            # 提取题干 - 修改正则表达式以支持解答题
            content_match = re.search(r'\d+\.\s*\(\d+分\)(.+?)(?=A\.|【我的答案：】|【正确答案：】)', question_text, re.DOTALL)
            if not content_match:
                print(f"无法提取题干: {question_text[:50]}...")
                return False
            
            content = content_match.group(1).strip()
            
            # 提取选项（如果是选择题）
            options = {}
            for option in ['A', 'B', 'C', 'D']:
                option_pattern = r'{}\.(.+?)(?=B\.|C\.|D\.|【|$)'.format(option)
                option_match = re.search(option_pattern, question_text, re.DOTALL)
                if option_match:
                    options[option] = option_match.group(1).strip()
            
            # 判断题目类型（选择题或主观题）
            question_type = "choice" if options else "subjective"
            
            # 提取正确答案 - 支持解答题格式
            answer = None
            
            # 首先尝试提取选择题答案格式
            if question_type == "choice":
                answer_pattern = r'【正确答案：】\s*([A-D])\s*分'
                answer_match = re.search(answer_pattern, question_text)
                if answer_match:
                    answer = answer_match.group(1).strip()
            
            # 如果没有找到选择题答案或者是主观题，尝试提取解答题答案
            if not answer:
                # 对于解答题，使用【我的答案：】作为正确答案
                my_answer_pattern = r'【我的答案：】\s*(.+?)\s*【正确答案：】'
                my_answer_match = re.search(my_answer_pattern, question_text, re.DOTALL)
                
                if my_answer_match:
                    answer = my_answer_match.group(1).strip()
                    # 清理答案文本，移除多余的空白字符
                    answer = re.sub(r'\s+', ' ', answer).strip()
                else:
                    # 尝试直接提取【正确答案：】后的内容
                    answer_pattern = r'【正确答案：】\s*(.+?)(?=【|$)'
                    answer_match = re.search(answer_pattern, question_text, re.DOTALL)
                    if answer_match:
                        answer = answer_match.group(1).strip()
                        # 移除末尾的"分"字
                        answer = re.sub(r'\s*分\s*$', '', answer).strip()
            
            if not answer:
                print(f"无法提取答案: {question_text[-100:]}")
                return False
            
            # 将题目添加到数据库
            self._add_to_database(content, answer, question_type, options)
            
            return True
        except Exception as e:
            print(f"解析题目时出错: {str(e)}")
            return False
    
    def _parse_simple_subjective_question(self, question_text):
        """解析简单主观题格式：题号+分值+题目+答案"""
        try:
            # 提取题干：从题号开始到答案开始之前
            # 先找到题号和分值部分
            header_match = re.search(r'(\d+\.\s*\(\d+分\))', question_text)
            if not header_match:
                print(f"无法提取题号: {question_text[:50]}...")
                return False
            
            header_end = header_match.end()
            remaining_text = question_text[header_end:].strip()
            
            # 分离题目内容和答案
            # 寻找答案开始的位置，通常答案会在题目描述之后
            lines = remaining_text.split('\n')
            content_lines = []
            answer_lines = []
            
            # 找到题目和答案的分界点
            # 通常题目描述较短，答案较长且更详细
            content_found = False
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                    
                if not content_found:
                    # 题目内容通常是第一个非空行
                    content_lines.append(line)
                    content_found = True
                else:
                    # 后续内容作为答案
                    answer_lines.append(line)
            
            if not content_lines:
                print(f"无法提取题目内容: {question_text[:50]}...")
                return False
            
            content = ' '.join(content_lines).strip()
            answer = ' '.join(answer_lines).strip() if answer_lines else ""
            
            # 如果没有明确的答案分离，尝试其他方法
            if not answer:
                # 如果整个文本较长，可能题目和答案在一起
                # 尝试根据长度和内容特征分离
                full_content = remaining_text.strip()
                sentences = re.split(r'[。！？]', full_content)
                
                if len(sentences) >= 2:
                    # 第一句作为题目，其余作为答案
                    content = sentences[0].strip() + '。'
                    answer = '。'.join(sentences[1:]).strip()
                    # 清理答案开头的句号
                    answer = re.sub(r'^。+', '', answer).strip()
                else:
                    # 如果无法分离，将整个内容作为题目，答案为空
                    content = full_content
                    answer = "需要补充答案"
            
            if not content:
                print(f"题目内容为空: {question_text[:50]}...")
                return False
            
            # 清理内容和答案
            content = re.sub(r'\s+', ' ', content).strip()
            answer = re.sub(r'\s+', ' ', answer).strip()
            
            # 将题目添加到数据库（主观题类型）
            self._add_to_database(content, answer, "subjective", {})
            
            return True
        except Exception as e:
            print(f"解析简单主观题时出错: {str(e)}")
            return False
    
    def _add_to_database(self, content, answer, question_type, options=None):
        """将题目添加到数据库"""
        try:
            # 生成关键词
            keywords = ",".join(options.values()) if options else ""
            
            # 检查题目是否已存在
            existing_question = None
            all_questions = self.question_db.get_all_questions()
            for question in all_questions:
                if question[1] == content:  # 比较题目内容
                    existing_question = question
                    break
            
            if existing_question:
                # 更新现有题目
                self.question_db.update_question(existing_question[0], answer, question_type, keywords)
            else:
                # 添加新题目
                self.question_db.add_question(content, answer, question_type, keywords)
            
            return True
        except Exception as e:
            print(f"添加题目到数据库时出错: {str(e)}")
            return False

# 测试代码
if __name__ == "__main__":
    from database import QuestionDatabase
    
    # 初始化数据库和导入器
    question_db = QuestionDatabase()
    importer = QuestionImporter(question_db)
    
    # 测试标准格式
    sample = """
    1.(30分)小杰使用OCR软件进行字符识别时，操作界面如图所示： 
    
    
    从图中可以看出，他正在进行的操作是 
    
    A.扫描稿件 
    B.倾斜校正 
    C.选择识别区域 
    D.校对文字 
    【我的答案：】 A 
    【正确答案：】C分 
    【试题分值：】30分 
    【我的得分：】 0 
    2.(40分)小张想把《红楼梦》这部小说的第一、二章输入电脑编辑，他可用的最快的速度是(    )。 
    A.用健盘把它们输入电脑 
    B.利用扫描仪扫描和汉王OCR识别 
    C.用数码照相机拍摄输入电脑 
    D.用手写板把它们写进电脑 
    【我的答案：】 B 
    【正确答案：】B分 
    【试题分值：】40分 
    【我的得分：】 40 
    3.(30分)(      )  在文本中被指定具有特殊含义或需要进一步解释的字、词或词组 
    A.热字 
    B.热区 
    C.热点 
    D.热元 
    【我的答案：】 A 
    【正确答案：】A分 
    【试题分值：】30分 
    【我的得分：】 30
    """
    
    result = importer.import_from_text(sample)
    print(f"标准格式导入结果: {result}")
    
    # 测试简单主观题格式
    simple_sample = """
    1.(40分)了解搜索引擎的工作原理及发展历程。
    
    搜索引擎通过爬虫抓取网页，建立索引库，用户输入关键词后，系统匹配索引并返回结果。发展历程从目录导航到全文检索，再到智能语义理解，不断优化搜索效率和用户体验
    
    2.(40分)利用搜索引擎查找：如何下载网页中的flash动画。
    
    右键点击网页 → 选择"查看页面源代码" → 按 Ctrl+F 搜索 .swf，找到Flash文件链接后直接下载
    
    3.(40分)你觉得搜索引擎还有那些需要创新的地方
    
    搜索引擎需要创新的地方包括：提升搜索结果的相关性和准确性，优化用户体验，加强隐私保护，整合多媒体搜索，发展个性化搜索服务，以及探索更智能的自然语言处理技术
    """
    
    result2 = importer.import_simple_subjective_from_text(simple_sample)
    print(f"简单主观题格式导入结果: {result2}")
    
    # 测试自动识别功能
    result3 = importer.import_from_text(simple_sample)
    print(f"自动识别导入结果: {result3}")