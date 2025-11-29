## 1️⃣ 用户表（User）

存储用户信息和历史记录引用。

| 字段名        | 类型           | 约束 / 说明     |
| ---------- | ------------ | ----------- |
| user_id    | INT / BIGINT | 主键，自增       |
| user_name  | VARCHAR(50)  | 唯一，不为空      |
| created_at | DATETIME     | 注册时间，默认当前时间 |
| last_login | DATETIME     | 可选，最后登录时间   |



---

## 2️⃣ 问卷创建历史（Make_survey_history）

记录用户创建过的问卷。

| 字段名                    | 类型           | 约束 / 说明                     |
| ---------------------- | ------------ | --------------------------- |
| make_survey_history_id | INT / BIGINT | 主键，自增                       |
| user_id                | INT / BIGINT | 外键 → User(user_id)，不能为空     |
| survey_id              | INT / BIGINT | 外键 → Survey(survey_id)，不能为空 |
| created_at             | DATETIME     | 创建时间，默认当前时间                 |

---

## 3️⃣ 问卷答题历史（Answer_survey_history）

记录用户填写过的问卷。

| 字段名                      | 类型           | 约束 / 说明                     |
| ------------------------ | ------------ | --------------------------- |
| answer_survey_history_id | INT / BIGINT | 主键，自增                       |
| user_id                  | INT / BIGINT | 外键 → User(user_id)，不能为空     |
| survey_id                | INT / BIGINT | 外键 → Survey(survey_id)，不能为空 |
| answered_at              | DATETIME     | 填写时间，默认当前时间                 |

---

## 4️⃣ 问卷表（Survey）

存储问卷信息。

| 字段名              | 类型                                | 约束 / 说明                   |
| ---------------- | --------------------------------- | ------------------------- |
| survey_id        | INT / BIGINT                      | 主键，自增                     |
| release_time     | DATETIME                          | 发布时间                      |
| survey_status    | ENUM('draft','released','closed') | 问卷状态                      |
| created_by       | INT / BIGINT                      | 外键 → User(user_id)，问卷创建者  |

---

## 5️⃣ 问题表（Question）

每个问卷包含多道题。

| 字段名            | 类型                                              | 约束 / 说明                |
| -------------- |-------------------------------------------------| ---------------------- |
| question_id    | INT / BIGINT                                    | 主键，自增                  |
| survey_id      | INT / BIGINT                                    | 外键 → Survey(survey_id) |
| question_index | INT                                             | 问题序号                   |
| question_text  | TEXT                                            | 问题内容                   |
| question_type  | ENUM('single','multiple','text','must','select') | 题型                     |

---

## 6️⃣ 答案表（Answer）

存储用户回答的内容。

| 字段名            | 类型           | 约束 / 说明                    |
| -------------- | ------------ | -------------------------- |
| answer_id      | INT / BIGINT | 主键，自增                      |
| user_id        | INT / BIGINT | 外键 → User(user_id)         |
| survey_id      | INT / BIGINT | 外键 → Survey(survey_id)     |
| question_id    | INT / BIGINT | 外键 → Question(question_id) |
| answer_content | TEXT         | 用户答案                       |
| answer_time    | DATETIME     | 答题时间                       |

