# test_utils.py
from db_utils import *

print("=== 测试开始 ===")

# 创建用户
u1 = add_user("Alice", "13800001111", "pass123")
u2 = add_user("Bob", "13800002222", "mypwd")
print("用户创建:", u1, u2)

# 创建问卷
s1 = add_survey(created_by=u1)
print("问卷创建: survey_id =", s1)

# 增加问题
q1 = add_question(s1, 1, "你喜欢猫吗？\n非常喜欢 \n一般喜欢 \n无感 \n讨厌 \n非常讨厌", "single")
q2 = add_question(s1, 2, "你每天睡几个小时？", "text")
q3 = add_question(s1, 3, "你最喜欢的颜色？", "text")
print("创建问题:", q1, q2, q3)

# 发布问卷
release_time = publish_survey(s1)
print("问卷已发布，时间:", release_time)

# 用户填写历史
h1 = add_answer_survey_history(u2, s1)
print("填写历史:", h1)

# 添加答案
a1 = add_answer(u2, s1, q1, "喜欢")
a2 = add_answer(u2, s1, q2, "7")
a3 = add_answer(u2, s1, q3, "蓝色")
print("回答完成:", a1, a2, a3)

print("=== 测试完成 ===")
