# tests/test_survey_list.py
import os
import sys
import json
from datetime import datetime, timedelta

# 【路径修复】确保能找到 db_utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_utils import add_user, get_user_id_by_name, add_survey, publish_survey, get_public_surveys

TEST_USER_NAME = "ListTester"
TEST_USER_PASSWORD = "testpassword123"


def setup_user():
    """确保用户存在并返回ID"""
    user_id = get_user_id_by_name(TEST_USER_NAME)
    if not user_id:
        user_id = add_user(TEST_USER_NAME, TEST_USER_PASSWORD, "active")
    return user_id


def test_survey_list():
    print("--- 测试问卷列表获取 (供B模块使用) ---")

    # 1. 准备用户
    creator_id = setup_user()

    # 2. 插入一个已发布的问卷 (Active) - 应该显示
    active_survey_id = add_survey(creator_id, "公开问卷 - 应该显示", survey_status="draft")
    publish_survey(active_survey_id)  # 将状态设为 active
    print(f"已发布问卷 ID: {active_survey_id}")

    # 3. 插入一个草稿问卷 (Draft) - 不应该显示
    draft_survey_id = add_survey(creator_id, "草稿问卷 - 不应显示", survey_status="draft")
    print(f"草稿问卷 ID: {draft_survey_id}")

    # 4. 调用核心接口
    public_surveys = get_public_surveys()

    # 5. 校验结果
    print("\n--- 验证结果 ---")
    active_found = False
    draft_found = False

    print(f"总共获取到 {len(public_surveys)} 条问卷记录。")

    for survey in public_surveys:
        if survey['survey_id'] == active_survey_id and survey['survey_title'].startswith("公开问卷"):
            active_found = True
        elif survey['survey_id'] == draft_survey_id:
            draft_found = True

    assert active_found, "错误：未找到已发布的问卷！"
    assert not draft_found, "错误：get_public_surveys 意外返回了草稿问卷！"

    print("\n【✅ 测试通过！】问卷列表接口 (get_public_surveys) 功能正常。")
    print("返回数据示例:")
    if public_surveys:
        print(json.dumps(public_surveys[0], indent=4, ensure_ascii=False))


if __name__ == "__main__":
    test_survey_list()