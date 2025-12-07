# tests/test_a_answer_submit.py
import os
import sys
import sqlite3

# 【路径修复】确保能找到 db_utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_utils import (
    add_user, get_user_id_by_name, add_survey, publish_survey,
    add_question, add_answer_survey_history, add_answer, DB_PATH
)

TEST_ANSWER_USER = "AnswerSubmitter"
TEST_USER_PASSWORD = "securepassword"


def setup_environment():
    """设置问卷和用户环境"""
    # 1. 确保填写用户存在
    user_id = get_user_id_by_name(TEST_ANSWER_USER)
    if not user_id:
        user_id = add_user(TEST_ANSWER_USER, TEST_USER_PASSWORD, "active")

    # 2. 插入并发布一个问卷
    survey_id = add_survey(user_id, "答案提交测试问卷", survey_status="draft")
    publish_survey(survey_id)  # 状态变为 active

    # 3. 插入两个问题
    q1_id = add_question(survey_id, 1, "你的工号？", "text")
    q2_id = add_question(survey_id, 2, "是否满意？", "choice")

    return user_id, survey_id, q1_id, q2_id


def verify_data(user_id, survey_id, expected_answers_count=2):
    """直接查询数据库验证数据是否成功写入"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 验证填写历史
    history_sql = "SELECT COUNT(*) FROM Answer_survey_history WHERE user_id = ? AND survey_id = ?"
    cursor.execute(history_sql, (user_id, survey_id))
    history_count = cursor.fetchone()[0]

    # 2. 验证答案数量
    answer_sql = "SELECT COUNT(*) FROM Answer WHERE user_id = ? AND survey_id = ?"
    cursor.execute(answer_sql, (user_id, survey_id))
    answer_count = cursor.fetchone()[0]

    conn.close()

    assert history_count == 1, "错误：填写历史记录未成功写入！"
    assert answer_count == expected_answers_count, f"错误：答案数量应为 {expected_answers_count}，但实际为 {answer_count}！"


def test_answer_submission():
    print("--- 测试答案提交接口 (供B模块使用) ---")
    user_id, survey_id, q1_id, q2_id = setup_environment()

    # --------------------------------
    # 1. 记录填写历史 (必须在提交答案前执行)
    # --------------------------------
    try:
        history_id = add_answer_survey_history(user_id, survey_id)
        print(f"✅ 填写历史记录 ID: {history_id} 已创建。")
    except ValueError as e:
        print(f"❌ 历史记录创建失败: {e}")
        return

    # --------------------------------
    # 2. 提交答案 (模拟用户提交的两个答案)
    # --------------------------------
    add_answer(user_id, survey_id, q1_id, "A888")
    add_answer(user_id, survey_id, q2_id, "非常满意")
    print("✅ 答案已提交。")

    # --------------------------------
    # 3. 验证数据
    # --------------------------------
    try:
        verify_data(user_id, survey_id, expected_answers_count=2)
        print("\n【✅ 测试通过！】答案提交接口 (add_answer, add_answer_survey_history) 功能正常。")
    except AssertionError as e:
        print(f"❌ 数据验证失败: {e}")


if __name__ == "__main__":
    test_answer_submission()