# tests/test_violation_details.py
import os
import sys

# 路径修复
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_utils import add_user, get_all_violations
from module_a.survey_manager import SurveyManager


def test_violation_details_recording():
    print("=== 测试：违规记录详情完整性验证 ===")

    manager = SurveyManager()
    # 1. 创建一个用户 (User ID)
    user_name = "BadUser"
    user_id = add_user(user_name, "123456")
    print(f"准备数据: 创建用户 {user_name}, ID={user_id}")

    # 2. 创建一个违规问卷
    # "非法" 是违规词
    bad_questions = [{"text": "普通问题", "type": "text"}]
    sid, is_v, reason = manager.create_survey_flow(user_id, "包含非法的标题", bad_questions)

    print(f"准备数据: 创建违规问卷 ID={sid}, 原因={reason}")

    # 3. 【核心测试】管理员查询违规列表
    print("\n[开始验证] 模拟管理员查询违规列表...")
    violations_list = get_all_violations()

    # 找到刚才那条记录
    target_record = None
    for v in violations_list:
        if v['survey_id'] == sid:
            target_record = v
            break

    # 4. 断言检查：是否包含你要求的4个要素
    if target_record:
        print("✅ 成功查询到记录，内容如下：")
        print(target_record)

        # 检查 Survey ID
        assert target_record['survey_id'] == sid, "Survey ID 缺失或错误"
        # 检查 User ID
        assert target_record['user_id'] == user_id, "User ID 缺失或错误"
        # 检查 Reason
        assert "非法" in target_record['reason'], "Reason 缺失或错误"
        # 检查 Time
        assert target_record['time'] is not None, "Time (时间) 缺失"

        print("\n🎉 验证通过！Violation 表查询接口成功返回了：")
        print(f"1. Survey ID: {target_record['survey_id']}")
        print(f"2. User ID:   {target_record['user_id']} (发布者)")
        print(f"3. Reason:    {target_record['reason']}")
        print(f"4. Time:      {target_record['time']}")
    else:
        print("❌ 测试失败：未在列表中找到刚才创建的违规记录。")
        raise AssertionError("违规记录写入失败")


if __name__ == "__main__":
    test_violation_details_recording()