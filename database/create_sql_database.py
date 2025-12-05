# database/create_sql_database.py
import sqlite3

# 保持路径与 db_utils.py 一致
DB_PATH = "database/survey_system.db"

def create_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 开启外键支持
    cursor.execute("PRAGMA foreign_keys = ON;")

    # -------------------
    # 用户表 (未修改)
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS User (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        last_login TEXT,
        user_status TEXT NOT NULL,
        unban_time TEXT
    )
    ''')

    # -------------------
    # 问卷表 (新增 survey_title)
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Survey (
        survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
        survey_title TEXT NOT NULL, -- 新增：问卷标题
        release_time TEXT,
        survey_status TEXT,
        created_by INTEGER,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (created_by) REFERENCES User(user_id)
    )
    ''')

    # -------------------
    # 问题表 (未修改)
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Question (
        question_id INTEGER PRIMARY KEY AUTOINCREMENT,
        survey_id INTEGER,
        question_index INTEGER,
        question_text TEXT,
        question_type TEXT,
        FOREIGN KEY (survey_id) REFERENCES Survey(survey_id) ON DELETE CASCADE
    )
    ''')

    # -------------------
    # 选项表 (新增：用于选择题)
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Option (
        option_id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER,
        option_index INTEGER NOT NULL,  -- 选项序号，用于排序
        option_text TEXT NOT NULL,
        FOREIGN KEY (question_id) REFERENCES Question(question_id) ON DELETE CASCADE
    )
    ''')

    # -------------------
    # 填写问卷历史表 (未修改)
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Answer_survey_history (
        answer_survey_history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        survey_id INTEGER,
        answered_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE,
        FOREIGN KEY (survey_id) REFERENCES Survey(survey_id) ON DELETE CASCADE
    )
    ''')

    # -------------------
    # 答案表 (未修改)
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Answer (
        answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        survey_id INTEGER,
        question_id INTEGER,
        answer_content TEXT,
        answer_time TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE,
        FOREIGN KEY (survey_id) REFERENCES Survey(survey_id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES Question(question_id) ON DELETE CASCADE
    )
    ''')

    # -------------------
    # 违规问卷表 (新增：A 的管理功能)
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Violation (
        violation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        survey_id INTEGER NOT NULL,
        reported_at TEXT DEFAULT (datetime('now','localtime')),
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'resolved', 'ignored'
        handled_by INTEGER,
        FOREIGN KEY (survey_id) REFERENCES Survey(survey_id) ON DELETE CASCADE,
        FOREIGN KEY (handled_by) REFERENCES User(user_id)
    )
    ''')

    conn.commit()
    conn.close()
    print(f"SQLite 数据库结构已更新/创建: {db_path}")


if __name__ == "__main__":
    create_db()