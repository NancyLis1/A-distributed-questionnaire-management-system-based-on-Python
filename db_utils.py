# utils.py
import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime
import hashlib

DB_PATH = "survey_system.db"

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
# 用户表
# -----------------------------
def add_user(user_name: str, phone: str, password: str,
             user_status: str = "active", unban_time: Optional[str] = None) -> int:
    """新增用户（用户名唯一 + 手机号唯一 + 密码哈希）"""
    password_hash = hash_password(password)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute('''
        INSERT INTO User (user_name, phone, password_hash, user_status, unban_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_name, phone, password_hash, user_status, unban_time))

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


# -----------------------------
# 问卷表
# -----------------------------
def add_survey(created_by: int, survey_status: str = "draft", release_time: Optional[str] = None) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO Survey (created_by, survey_status, release_time)
        VALUES (?, ?, ?)
    ''', (created_by, survey_status, release_time))
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
