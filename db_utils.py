import sqlite3
from typing import Optional, Dict, Any

DB_PATH = "survey_system.db"

# -----------------------------
# 通用执行函数（保留，用于非ID查询）
# -----------------------------
def execute(sql: str, params: tuple = (), fetch: bool = False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute(sql, params)
    result = None
    if fetch:
        result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result


# -----------------------------
# 用户表
# -----------------------------
def add_user(user_name: str, user_status: str = "active", unban_time: Optional[str] = None) -> int:
    """新增用户，返回 user_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO User (user_name, user_status, unban_time)
        VALUES (?, ?, ?)
    ''', (user_name, user_status, unban_time))
    user_id = cursor.lastrowid  # 同一连接里获取最后插入ID
    conn.commit()
    conn.close()
    return user_id


# -----------------------------
# 问卷表相关函数
# -----------------------------
def add_survey(created_by: int, survey_status: str = "draft", release_time: Optional[str] = None) -> int:
    """
    新增问卷，返回 survey_id
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO Survey (created_by, survey_status, release_time)
        VALUES (?, ?, ?)
    ''', (created_by, survey_status, release_time))
    survey_id = cursor.lastrowid  # 在同一连接里获取最后插入 ID
    conn.commit()
    conn.close()
    return survey_id

def get_survey(survey_id: int) -> Optional[Dict[str, Any]]:
    """
    根据 survey_id 获取问卷信息
    """
    sql = "SELECT * FROM Survey WHERE survey_id = ?"
    res = execute(sql, (survey_id,), fetch=True)
    if res:
        row = res[0]
        return {
            "survey_id": row[0],
            "release_time": row[1],
            "survey_status": row[2],
            "created_by": row[3],
            "created_at": row[4]
        }
    return None

def update_survey_status(survey_id: int, new_status: str):
    """
    修改问卷状态
    """
    sql = "UPDATE Survey SET survey_status = ? WHERE survey_id = ?"
    execute(sql, (new_status, survey_id))

def set_survey_release_time(survey_id: int, release_time: str):
    """
    设置问卷的发布时间
    """
    sql = "UPDATE Survey SET release_time = ? WHERE survey_id = ?"
    execute(sql, (release_time, survey_id))

    return survey_id


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
    question_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return question_id


# -----------------------------
# 填写历史表
# -----------------------------
def add_answer_survey_history(user_id: int, survey_id: int) -> int:
    """
    在填写历史表里添加记录。
    仅允许问卷状态为 'active' 时填写。
    """
    # 检查问卷状态
    survey = get_survey(survey_id)
    if not survey:
        raise ValueError(f"问卷 {survey_id} 不存在")
    if survey["survey_status"] != "active":
        raise ValueError(f"问卷 {survey_id} 尚未发布，无法填写")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO Answer_survey_history (user_id, survey_id)
        VALUES (?, ?)
    ''', (user_id, survey_id))
    history_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return history_id

# -----------------------------
# 答案表
# -----------------------------
def add_answer(user_id: int, survey_id: int, question_id: int, answer_content: str) -> int:
    """
    添加用户答案，仅在问卷状态为 'active' 时允许
    """
    survey = get_survey(survey_id)
    if not survey:
        raise ValueError(f"问卷 {survey_id} 不存在")
    if survey["survey_status"] != "active":
        raise ValueError(f"问卷 {survey_id} 尚未发布，无法填写答案")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        INSERT INTO Answer (user_id, survey_id, question_id, answer_content)
        VALUES (?, ?, ?, ?)
    ''', (user_id, survey_id, question_id, answer_content))
    answer_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return answer_id

from datetime import datetime

# -----------------------------
# 发布问卷
# -----------------------------
def publish_survey(survey_id: int):
    """
    发布问卷：
    - 将 survey_status 设为 'active'
    - 将 release_time 设置为当前时间
    """
    release_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "UPDATE Survey SET survey_status = ?, release_time = ? WHERE survey_id = ?"
    execute(sql, ("active", release_time, survey_id))
    return release_time
