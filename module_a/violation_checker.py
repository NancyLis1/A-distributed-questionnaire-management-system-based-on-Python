# module_a/violation_checker.py
import os


class ViolationChecker:
    def __init__(self):
        self.banned_words = []
        self.load_banned_words()

    def load_banned_words(self):
        """
        从同级目录下的 banned_words.txt 加载敏感词
        """
        # 1. 获取当前脚本 (violation_checker.py) 所在的绝对目录
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # 2. 拼接出 txt 文件的完整路径
        file_path = os.path.join(current_dir, "banned_words.txt")

        # 3. 读取文件
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    # 读取每一行，去除首尾空格和换行符，并过滤掉空行
                    self.banned_words = [line.strip() for line in f if line.strip()]
                print(f"✅ 已加载 {len(self.banned_words)} 个违规词。")
            except Exception as e:
                print(f"❌ 读取违规词文件失败: {e}")
                # 发生错误时使用兜底默认列表，防止程序崩溃
                self.banned_words = ["暴力", "赌博", "诈骗"]
        else:
            print(f"⚠️ 未找到违规词文件: {file_path}，将使用默认列表。")
            self.banned_words = ["暴力", "赌博", "诈骗"]

    def check_text(self, text: str):
        """
        检查文本是否包含违规词。
        返回: (is_violation, found_word)
        """
        if not text:
            return False, None

        for word in self.banned_words:
            if word in text:
                return True, word
        return False, None

    def check_survey_content(self, title: str, questions_data: list):
        """
        检查整个问卷内容（标题 + 所有题目文本）。
        """
        # 1. 检查标题
        is_v, word = self.check_text(title)
        if is_v:
            return True, f"标题包含违规词: {word}"

        # 2. 检查所有题目
        for q in questions_data:
            q_text = q.get("question_text", "")
            is_v, word = self.check_text(q_text)
            if is_v:
                return True, f"题目包含违规词: {word}"

        return False, None