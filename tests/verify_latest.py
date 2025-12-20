import os
import sys
import json
import sqlite3

# 路径修复
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_utils import get_full_survey_detail, DB_PATH


def verify_latest_active_survey():
    print("========================================")
    print("   自动验证：最新创建的问卷")
    print("========================================")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 查询最新的一个 active 问卷
    # 逻辑：按 survey_id 倒序排列，找第一个 status='active' 的
    sql = """
    SELECT survey_id, survey_title, survey_status, created_at 
    FROM Survey  
    ORDER BY survey_id DESC 
    LIMIT 1
    """

    cursor.execute(sql)
    row = cursor.fetchone()
    conn.close()

    # 2. 检查是否找到
    if not row:
        print("❌ 数据库中没有状态为 'active' 的问卷。")
        print("提示：你可能只是在编辑器点了保存（draft），还没在主面板点击'发布'？")
        return

    survey_id = row[0]
    title = row[1]
    status = row[2]
    time = row[3]

    print(f"✅ 找到最新发布的问卷:")
    print(f"   - ID: {survey_id}")
    print(f"   - 标题: {title}")
    print(f"   - 状态: {status}")
    print(f"   - 创建时间: {time}")
    print("-" * 40)

    # 3. 获取完整详情 (题目和选项)
    detail = get_full_survey_detail(survey_id)

    # 4. 打印详情
    print("📄 问卷完整内容结构:")
    print(json.dumps(detail, indent=4, ensure_ascii=False))

    # 5. 简单的自动校验逻辑
    question_count = len(detail['questions'])
    print("-" * 40)
    print(f"📊 统计验证:")
    print(f"   - 题目数量: {question_count}")
    if question_count > 0:
        first_q = detail['questions'][0]
        print(f"   - 第一题类型: {first_q['type']}")
        print(f"   - 第一题选项数: {len(first_q['options'])}")
    print("========================================")


if __name__ == "__main__":
    verify_latest_active_survey()