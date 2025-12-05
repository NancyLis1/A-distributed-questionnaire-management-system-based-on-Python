# utils.py
import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime
import hashlib

DB_PATH = "database/survey_system.db"

# -----------------------------
# 通用执行函数
# -----------------------------
def execute(sql: str, params: tuple = (), fetch: bool = False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute(sql, params)
    result = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return result


# -----------------------------
# 哈希密码工具
# -----------------------------
def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


# -----------------------------
# 用户表（已修改，使得其能接受password参数）
# -----------------------------
def add_user(user_name: str, password: str, user_status: str = "active", unban_time: Optional[str] = None) -> int:
    """新增用户，返回 user_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO User (user_name, password, user_status, unban_time)
        VALUES (?, ?, ?, ?)
    ''', (user_name, password, user_status, unban_time)) # 【修改：新增 password 参数】
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_login(identifier: str) -> Optional[Dict[str, Any]]:
    """
    通过用户名 or 手机号登录（identifier）
    """
    sql = """
    SELECT user_id, user_name, phone, password_hash, user_status
    FROM User
    WHERE user_name = ? OR phone = ?
    """
    res = execute(sql, (identifier, identifier), fetch=True)
    if not res:
        return None

    row = res[0]
    return {
        "user_id": row[0],
        "user_name": row[1],
        "phone": row[2],
        "password_hash": row[3],
        "user_status": row[4]
    }


def get_user_id_by_name(user_name: str) -> Optional[int]:
    """根据用户名查找用户ID"""
    sql = "SELECT user_id FROM User WHERE user_name = ?"
    res = execute(sql, (user_name,), fetch=True)
    if res:
        return res[0][0]
    return None


# -----------------------------
# 问卷表（已修改：适应新增的 survey_title 字段）
# -----------------------------
def add_survey(created_by: int, survey_title: str, survey_status: str = "draft", release_time: Optional[str] = None) -> int:
    """
    新增问卷，返回 survey_id
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO Survey (survey_title, created_by, survey_status, release_time)
        VALUES (?, ?, ?, ?)
    ''', (survey_title, created_by, survey_status, release_time))
    survey_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return survey_id


def get_survey(survey_id: int) -> Optional[Dict[str, Any]]:
    sql = "SELECT * FROM Survey WHERE survey_id = ?"
    res = execute(sql, (survey_id,), fetch=True)
    if not res:
        return None
    row = res[0]
    return {
        "survey_id": row[0],
        "release_time": row[1],
        "survey_status": row[2],
        "created_by": row[3],
        "created_at": row[4]
    }


def publish_survey(survey_id: int):
    """发布问卷"""
    release_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute(
        "UPDATE Survey SET survey_status = ?, release_time = ? WHERE survey_id = ?",
        ("active", release_time, survey_id)
    )
    return release_time



# -----------------------------
# 核心查询函数 (供 B 模块使用)
# -----------------------------
def get_full_survey_detail(survey_id: int) -> Optional[Dict[str, Any]]:
    """
    根据 survey_id 获取完整的问卷、问题、选项详情，用于发送给客户端。
    返回结构: {survey_id, survey_title, survey_status, questions: [...]}
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 使用 Row Factory 以名字访问字段
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. 查询问卷主体信息
    survey_sql = "SELECT * FROM Survey WHERE survey_id = ?"
    cursor.execute(survey_sql, (survey_id,))
    survey_row = cursor.fetchone()
    if not survey_row:
        conn.close()
        return None

    survey_data = dict(survey_row)
    result = {
        "survey_id": survey_data["survey_id"],
        "survey_title": survey_data["survey_title"],
        "survey_status": survey_data["survey_status"],
        "created_by": survey_data["created_by"],
        "release_time": survey_data["release_time"],
        "questions": []
    }

    # 2. 查询所有问题
    questions_sql = "SELECT * FROM Question WHERE survey_id = ? ORDER BY question_index ASC"
    cursor.execute(questions_sql, (survey_id,))
    question_rows = cursor.fetchall()

    for q_row in question_rows:
        question = {
            "question_id": q_row["question_id"],
            "index": q_row["question_index"],
            "text": q_row["question_text"],
            "type": q_row["question_type"],
            "options": []  # 默认空列表
        }

        # 3. 如果是选择题 (choice/radio/checkbox)，查询选项
        if q_row["question_type"] in ["choice", "radio", "checkbox"]:
            options_sql = "SELECT option_text FROM Option WHERE question_id = ? ORDER BY option_index ASC"
            cursor.execute(options_sql, (q_row["question_id"],))
            option_rows = cursor.fetchall()
            question["options"] = [r["option_text"] for r in option_rows]

        result["questions"].append(question)

    conn.close()
    return result


# -----------------------------
# 问题表
# -----------------------------
def add_question(survey_id: int, question_index: int, question_text: str, question_type: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO Question (survey_id, question_index, question_text, question_type)
        VALUES (?, ?, ?, ?)
    ''', (survey_id, question_index, question_text, question_type))
    qid = cursor.lastrowid
    conn.commit()
    conn.close()
    return qid

# -----------------------------
# 选项表
# -----------------------------
def add_option(question_id: int, option_index: int, option_text: str) -> int:
    """新增选择题的选项，返回 option_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO Option (question_id, option_index, option_text)
        VALUES (?, ?, ?)
    ''', (question_id, option_index, option_text))
    option_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return option_id

# -----------------------------
# 填写历史表（限制问卷必须 active）
# -----------------------------
def add_answer_survey_history(user_id: int, survey_id: int) -> int:
    survey = get_survey(survey_id)
    if not survey:
        raise ValueError("问卷不存在")
    if survey["survey_status"] != "active":
        raise ValueError("问卷未发布，不能填写")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO Answer_survey_history (user_id, survey_id)
        VALUES (?, ?)
    ''', (user_id, survey_id))

    hid = cursor.lastrowid
    conn.commit()
    conn.close()
    return hid


# -----------------------------
# 答案表
# -----------------------------
def add_answer(user_id: int, survey_id: int, question_id: int, answer_content: str) -> int:
    survey = get_survey(survey_id)
    if survey["survey_status"] != "active":
        raise ValueError("问卷未发布，不能填写答案")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO Answer (user_id, survey_id, question_id, answer_content)
        VALUES (?, ?, ?, ?)
    ''', (user_id, survey_id, question_id, answer_content))

    ans_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ans_id
