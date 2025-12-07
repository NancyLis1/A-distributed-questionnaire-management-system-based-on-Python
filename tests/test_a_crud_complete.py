# tests/test_a_crud_complete.py
import os
import sys

# 1. 路径修复：确保能找到根目录下的 db_utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_utils import (
    # C & R (用于准备数据)
    add_user, add_survey, add_question, add_option,
    get_survey, get_full_survey_detail,
    # U (本次测试目标)
    update_survey_status, update_survey_title,
    update_question_text, update_option_text,
    publish_survey,  # publish_survey 本质也是 Update
    # D (本次测试目标)
    delete_survey, delete_question, delete_option
)


def test_all_crud_functions():
    print("========================================")
    print("   开始全量测试阶段三：所有 U & D 函数")
    print("========================================")

    # ------------------------------------------------
    # 0. 数据准备 (Create)
    # ------------------------------------------------
    print("\n[Step 0] 准备测试数据...")
    user_id = add_user("FullTester", "pass123")
    survey_id = add_survey(user_id, "原始标题", "draft")
    q_id = add_question(survey_id, 1, "原始问题文本", "choice")
    op_id = add_option(q_id, 1, "原始选项文本")

    print(f"✅ 数据就绪: 问卷ID={survey_id}, 问题ID={q_id}, 选项ID={op_id}")

    # ------------------------------------------------
    # 1. 测试 Update (更新) 模块
    # ------------------------------------------------
    print("\n--- 测试 Update 函数 ---")

    # 1.1 测试 update_survey_title
    update_survey_title(survey_id, "新标题")
    s_info = get_survey(survey_id)
    assert s_info['survey_title'] == "新标题", "❌ update_survey_title 失败"
    print("✅ update_survey_title 测试通过")

    # 1.2 测试 update_question_text
    update_question_text(q_id, "新问题文本")
    detail = get_full_survey_detail(survey_id)
    # 获取第一个问题（索引0）
    assert detail['questions'][0]['text'] == "新问题文本", "❌ update_question_text 失败"
    print("✅ update_question_text 测试通过")

    # 1.3 测试 update_option_text
    update_option_text(op_id, "新选项文本")
    detail = get_full_survey_detail(survey_id)
    # 获取第一个问题的第一个选项
    assert detail['questions'][0]['options'][0] == "新选项文本", "❌ update_option_text 失败"
    print("✅ update_option_text 测试通过")

    # 1.4 测试 update_survey_status (通用状态修改)
    update_survey_status(survey_id, "closed")
    s_info = get_survey(survey_id)
    assert s_info['survey_status'] == "closed", "❌ update_survey_status 失败"
    print("✅ update_survey_status 测试通过")

    # 1.5 测试 publish_survey (特定状态修改)
    # 先改回 draft 模拟发布流程
    update_survey_status(survey_id, "draft")
    publish_survey(survey_id)
    s_info = get_survey(survey_id)
    assert s_info['survey_status'] == "active", "❌ publish_survey 失败"
    print("✅ publish_survey 测试通过")

    # ------------------------------------------------
    # 2. 测试 Delete (删除) 模块
    # ------------------------------------------------
    print("\n--- 测试 Delete 函数 ---")

    # 2.1 测试 delete_option (删除选项)
    delete_option(op_id)
    detail = get_full_survey_detail(survey_id)
    # 问题还在，但选项列表应该为空了
    current_options = detail['questions'][0]['options']
    assert len(current_options) == 0, "❌ delete_option 失败：选项未被删除"
    print("✅ delete_option 测试通过")

    # 2.2 测试 delete_question (删除问题)
    delete_question(q_id)
    detail = get_full_survey_detail(survey_id)
    # 问卷还在，但问题列表应该为空了
    assert len(detail['questions']) == 0, "❌ delete_question 失败：问题未被删除"
    print("✅ delete_question 测试通过")

    # 2.3 测试 delete_survey (删除问卷)
    delete_survey(survey_id)
    s_info = get_survey(survey_id)
    assert s_info is None, "❌ delete_survey 失败：问卷仍然存在"
    print("✅ delete_survey 测试通过")

    print("\n========================================")
    print("🎉 恭喜！所有 UD 模块新增函数均已通过测试！")
    print("========================================")


if __name__ == "__main__":
    test_all_crud_functions()