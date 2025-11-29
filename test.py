from db_utils import add_user, add_survey, add_question, add_answer_survey_history, add_answer, publish_survey

def insert_test_data():
    # -----------------
    # 插入用户
    # -----------------
    alice_id = add_user("Alice", "active")
    bob_id = add_user("Bob", "active")
    charlie_id = add_user("Charlie", "active")

    # -----------------
    # 插入问卷
    # -----------------
    survey1_id = add_survey(created_by=alice_id, survey_status="draft")
    publish_survey(survey1_id)
    print("survey1已发布")
    survey2_id = add_survey(created_by=charlie_id, survey_status="draft")  # 未发布

    # -----------------
    # 插入问题
    # -----------------
    q1_id = add_question(survey_id=survey1_id, question_index=1, question_text="你的年龄是多少？", question_type="text")
    q2_id = add_question(survey_id=survey1_id, question_index=2, question_text="你的性别？", question_type="choice")
    q3_id = add_question(survey_id=survey2_id, question_index=1, question_text="你喜欢Python吗？", question_type="choice")

    # -----------------
    # 填写 survey1
    # -----------------
    add_answer_survey_history(user_id=bob_id, survey_id=survey1_id)
    add_answer(user_id=bob_id, survey_id=survey1_id, question_id=q1_id, answer_content="25")
    add_answer(user_id=bob_id, survey_id=survey1_id, question_id=q2_id, answer_content="男")

    # -----------------
    # 尝试填写未发布问卷 survey2
    # -----------------
    try:
        add_answer_survey_history(user_id=alice_id, survey_id=survey2_id)
    except ValueError as e:
        print(f"未发布问卷无法填写: {e}")

    # -----------------
    # 发布 survey2
    # -----------------
    release_time = publish_survey(survey2_id)
    print(f"survey2 已发布，release_time={release_time}")

    # 填写 survey2
    add_answer_survey_history(user_id=alice_id, survey_id=survey2_id)
    add_answer(user_id=alice_id, survey_id=survey2_id, question_id=q3_id, answer_content="是")

    print("测试数据已插入完成！")

if __name__ == "__main__":
    insert_test_data()
