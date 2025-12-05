## 🟦 User 表的最终结构：

| 字段            | 类型                   | 描述              |
| ------------- | -------------------- | --------------- |
| user_id       | INTEGER PK           | 自动递增            |
| user_name     | TEXT UNIQUE NOT NULL | 用户名唯一           |
| phone         | TEXT UNIQUE          | 手机号唯一           |
| password_hash | TEXT NOT NULL        | 存 SHA-256 哈希    |
| created_at    | TEXT                 | 默认本地时间          |
| last_login    | TEXT                 | 登录时间            |
| user_status   | TEXT NOT NULL        | active / banned |
| unban_time    | TEXT                 | 解禁时间            |

---

---

## 2️⃣ 答案表（Answer）

存储用户回答的内容。

| 字段名            | 类型           | 约束 / 说明                    |
| -------------- | ------------ | -------------------------- |
| answer_id      | INT / BIGINT | 主键，自增                      |
| user_id        | INT / BIGINT | 外键 → User(user_id)         |
| survey_id      | INT / BIGINT | 外键 → Survey(survey_id)     |
| question_id    | INT / BIGINT | 外键 → Question(question_id) |
| answer_content | TEXT         | 用户答案                       |
| answer_time    | DATETIME     | 答题时间                       |


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


