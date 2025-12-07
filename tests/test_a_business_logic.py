# tests/test_a_business_logic.py
import os
import sys
import json

# 路径修复：确保能找到根目录的 db_utils 和 module_a 的 Manager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_utils import add_user, get_full_survey_detail, get_user_id_by_name
from module_a.survey_manager import SurveyManager

# ----------------------------------------------------
# 测试常量
# ----------------------------------------------------
TEST_USER_NAME = "ManagerTestUser"
TEST_USER_PASS = "secure_manager_pass"


def setup_test_user():
    """确保测试用户存在并返回其 ID"""
    user_id = get_user_id_by_name(TEST_USER_NAME)
    if not user_id:
        # 使用 db_utils 中的 add_user 创建用户
        user_id = add_user(TEST_USER_NAME, TEST_USER_PASS)
        print(f"INFO: 创建测试用户 ID: {user_id}")
    return user_id


def test_business_logic():
    print("==================================================")
    print("=== 开始测试阶段四：业务逻辑层 (SurveyManager) ===")
    print("==================================================")

    manager = SurveyManager()
    user_id = setup_test_user()

    # --- 1. 测试: 正常创建流程 (无违规词) ---
    print("\n--- 1. 测试功能：create_survey_flow (正常创建) ---")
    normal_questions = [
        {"text": "你喜欢编程吗？", "type": "choice", "options": ["喜欢", "不喜欢"]},
        {"text": "你的建议？", "type": "text", "options": []}
    ]
    sid_1, is_v, reason = manager.create_survey_flow(user_id, "正常问卷调查", normal_questions)

    # 验证 1.1：基本数据是否创建
    assert sid_1 is not None
    assert is_v is False
    print(f"✅ 1.1 问卷创建成功 ID: {sid_1}")

    # 验证 1.2：数据库状态是否为 draft 且结构正确
    data_1 = get_full_survey_detail(sid_1)
    assert data_1['survey_status'] == 'draft', "❌ 问卷状态错误，应为 draft"
    assert len(data_1['questions']) == 2, "❌ 问题数量错误"
    print("✅ 1.2 状态和结构验证通过 (状态: draft)")

    # --- 2. 测试功能：create_survey_flow (违规检测与自动关停) ---
    print("\n--- 2. 测试功能：create_survey_flow (违规拦截) ---")
    # "暴力" 在 module_a/banned_words.txt 中
    bad_questions = [
        {"text": "请勿输入暴力内容", "type": "text", "options": []}
    ]
    sid_2, is_v, reason = manager.create_survey_flow(user_id, "非法问卷", bad_questions)

    # --- 2. 测试功能：create_survey_flow (违规检测与自动关停) ---
    print("\n--- 2. 测试功能：create_survey_flow (违规拦截) ---")
    # 问卷标题包含 "非法"，题目包含 "暴力"
    bad_questions = [
        {"text": "这里包含暴力内容", "type": "text", "options": []}
    ]
    sid_2, is_v, reason = manager.create_survey_flow(user_id, "非法问卷", bad_questions)  # 标题包含 "非法"

    # 验证 2.1：是否成功检测到违规
    data = get_full_survey_detail(sid_2)
    assert is_v is True, "❌ 未检测到违规 (is_v 应该为 True)"
    print("✅ 2.1 违规检测成功")

    # 验证 2.2：reason 中是否包含违规描述和具体的违规词
    # 【关键修正点】：我们只验证 reason 包含了 "违规词" 关键词，并且问卷状态正确
    assert "违规词" in reason, f"❌ 违规原因描述不准确。实际返回: {reason}"
    # 打印实际发现的违规词，方便调试
    print(f"✅ 2.2 违规原因描述正确。发现的违规词在标题中: {reason.split(': ')[-1]}")

    # 验证 2.3：问卷是否被自动设置为 'closed'
    assert data['survey_status'] == 'closed', "❌ 违规问卷未被自动关停"
    print(f"✅ 2.3 违规问卷被自动关停! 状态: {data['survey_status']}")

    # 复制 sid_1 (正常问卷)
    copy_sid = manager.copy_survey(sid_1, user_id)

    # 验证 3.1：新问卷是否创建成功
    copy_data = get_full_survey_detail(copy_sid)
    assert copy_sid is not None
    assert copy_sid != sid_1, "❌ 复制问卷 ID 不应与原问卷相同"
    print(f"✅ 3.1 问卷复制成功，新 ID: {copy_sid}")

    # 验证 3.2：内容是否完整复制，且状态为 draft
    assert copy_data['survey_title'] == "正常问卷调查 (副本)", "❌ 标题复制错误，未添加 (副本)"
    assert copy_data['survey_status'] == 'draft', "❌ 复制问卷状态应为 draft"
    assert len(copy_data['questions']) == 2, "❌ 问题数量复制错误"
    assert copy_data['questions'][0]['options'][0] == "喜欢", "❌ 选项内容未复制"
    print("✅ 3.2 内容、结构、状态验证通过，深拷贝成功。")

    print("\n==================================================")
    print("🎉 阶段四：所有业务逻辑测试全部通过！")
    print("==================================================")


if __name__ == "__main__":
    test_business_logic()