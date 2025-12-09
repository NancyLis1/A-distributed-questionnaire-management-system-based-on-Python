# module_a/survey_manager.py
import sys
import os

# 路径适配，确保能引用根目录的 db_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_utils import (
    add_survey, add_question, add_option,
    get_full_survey_detail, add_violation, update_survey_status
)
from module_a.violation_checker import ViolationChecker


class SurveyManager:
    def __init__(self):
        self.checker = ViolationChecker()

    def create_survey_flow(self, user_id: int, title: str, questions_data: list):
        """
        创建问卷的完整业务流程：
        1. 检查违规词
        2. 如果违规，自动标记为 'closed' 并记录（或直接禁止创建，这里演示标记为 closed）
        3. 写入数据库

        questions_data 格式:
        [
            {"text": "问题1", "type": "choice", "options": ["A", "B"]},
            {"text": "问题2", "type": "text", "options": []}
        ]
        """
        # 1. 违规检测
        is_violation, reason = self.checker.check_survey_content(title, questions_data)

        # 决定初始状态：如果违规，设为 closed (关停)；否则设为 draft (草稿)
        initial_status = "closed" if is_violation else "draft"

        # 2. 创建问卷
        survey_id = add_survey(user_id, title, initial_status)

        # 3. 【关键】如果违规，记录详细信息到 Violation 表
        if is_violation:
            # 这里记录了 survey_id 和 reason
            # user_id 已经包含在 survey_id 对应的 Survey 表里了
            # time 会由数据库自动记录当前时间
            add_violation(survey_id, reason, 'pending')
            print(f"INFO: 违规记录已保存。")

        # 4. 循环插入问题和选项
        for index, q in enumerate(questions_data, start=1):
            q_text = q["text"]
            q_type = q["type"]
            q_options = q.get("options", [])

            # 插入问题
            q_id = add_question(survey_id, index, q_text, q_type)

            # 如果有选项，插入选项
            if q_options:
                for opt_idx, opt_text in enumerate(q_options, start=1):
                    add_option(q_id, opt_idx, opt_text)

        return survey_id, is_violation, reason

    def copy_survey(self, source_survey_id: int, user_id: int):
        """
        复制问卷（深度拷贝）：
        读取原问卷 -> 创建新问卷(标题加'副本') -> 复制所有题目 -> 复制所有选项
        """
        # 1. 获取原问卷所有详情
        source_data = get_full_survey_detail(source_survey_id)
        if not source_data:
            return None

        new_title = source_data["survey_title"] + " (副本)"

        # 2. 创建新问卷 (默认草稿)
        new_survey_id = add_survey(user_id, new_title, "draft")

        # 3. 遍历复制问题和选项
        for q in source_data["questions"]:
            # 复制问题
            new_q_id = add_question(
                new_survey_id,
                q["index"],
                q["text"],
                q["type"]
            )

            # 复制该问题的选项
            for opt_idx, opt_text in enumerate(q["options"], start=1):
                add_option(new_q_id, opt_idx, opt_text)

        return new_survey_id