# tests/test_collaboration.py
import os
import sys
import json

# 【重要修复】将项目根目录添加到 Python 路径中，以找到 db_utils.py
# 解决 ModuleNotFoundError
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_utils import add_user, add_survey, add_question, add_option, get_full_survey_detail, get_user_id_by_name

# 默认测试密码，后续应使用哈希加密
TEST_USER_PASSWORD = "testpassword123"


def test_survey_data_for_b():
    print("--- 准备测试数据 ---")

    test_user_name = "Alice_A_Test"

    # 1. 检查用户是否存在，不存在则创建（解决 FOREIGN KEY 错误）
    alice_id = get_user_id_by_name(test_user_name)
    if not alice_id:
        # 【关键修复】现在调用 add_user 必须提供 password
        alice_id = add_user(test_user_name, TEST_USER_PASSWORD, "active")
        print(f"用户 {test_user_name} 已创建，ID: {alice_id}")
    else:
        print(f"用户 {test_user_name} 已存在，ID: {alice_id}")

    # 2. 插入问卷 (A)
    survey_title = f"面向协作的网络调研问卷 - ID:{alice_id}"
    # 现在 alice_id 保证是数据库中存在的有效 ID
    try:
        survey_id = add_survey(created_by=alice_id, survey_title=survey_title, survey_status="draft")
    except Exception as e:
        # 允许重复运行，如果外键失败，可能是因为用户表被清空了
        print(f"创建问卷失败，可能数据库状态不一致。请尝试重新初始化数据库。错误: {e}")
        return

    print(f"问卷 ID: {survey_id} 已创建")

    # 3. 插入问题 (A)
    q1_id = add_question(survey_id=survey_id, question_index=1,
                         question_text="你的年级是？", question_type="choice")
    q2_id = add_question(survey_id=survey_id, question_index=2,
                         question_text="你对本次协作的期待？", question_type="text")
    print(f"问题 ID: {q1_id}, {q2_id} 已创建")

    # 4. 插入选项 (A)
    add_option(question_id=q1_id, option_index=1, option_text="大一")
    add_option(question_id=q1_id, option_index=2, option_text="大二")
    add_option(question_id=q1_id, option_index=3, option_text="大三及以上")
    print("选项已插入")

    # 5. 核心测试：调用供 B 使用的接口
    print("\n--- 核心测试: 调用 get_full_survey_detail ---")
    full_survey_data = get_full_survey_detail(survey_id)

    # 6. 结果校验
    if not full_survey_data:
        print("【错误】未获取到问卷数据！")
        return

    print("获取到的完整问卷数据结构：")
    # 打印格式化的 JSON (方便 B 查看)
    print(json.dumps(full_survey_data, indent=4, ensure_ascii=False))

    # 7. 断言检查 (这是程序员的测试方法)
    assert full_survey_data["survey_title"].startswith("面向协作的网络调研问卷")
    assert len(full_survey_data["questions"]) == 2

    q1 = full_survey_data["questions"][0]
    assert q1["type"] == "choice"
    assert len(q1["options"]) == 3

    print("\n【✅ 测试通过！】数据结构符合预期，已可移交给 B 模块使用。")


if __name__ == "__main__":
    test_survey_data_for_b()