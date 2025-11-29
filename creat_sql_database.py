# create_survey_db_sqlite3.py
import sqlite3

def create_db(db_path="survey_system.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 开启外键支持
    cursor.execute("PRAGMA foreign_keys = ON;")

    # -------------------
    # 用户表
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS User (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        last_login TEXT
    )
    ''')

    # -------------------
    # 问卷表
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Survey (
        survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
        release_time TEXT,
        survey_status TEXT,
        created_by INTEGER,
        FOREIGN KEY (created_by) REFERENCES User(user_id)
    )
    ''')

    # -------------------
    # 问题表
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Question (
        question_id INTEGER PRIMARY KEY AUTOINCREMENT,
        survey_id INTEGER,
        question_index INTEGER,
        question_text TEXT,
        question_type TEXT,
        FOREIGN KEY (survey_id) REFERENCES Survey(survey_id)
    )
    ''')

    # -------------------
    # 创建问卷历史表
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Make_survey_history (
        make_survey_history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        survey_id INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES User(user_id),
        FOREIGN KEY (survey_id) REFERENCES Survey(survey_id)
    )
    ''')

    # -------------------
    # 填写问卷历史表
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Answer_survey_history (
        answer_survey_history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        survey_id INTEGER,
        answered_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES User(user_id),
        FOREIGN KEY (survey_id) REFERENCES Survey(survey_id)
    )
    ''')

    # -------------------
    # 答案表
    # -------------------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Answer (
        answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        survey_id INTEGER,
        question_id INTEGER,
        answer_content TEXT,
        answer_time TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES User(user_id),
        FOREIGN KEY (survey_id) REFERENCES Survey(survey_id),
        FOREIGN KEY (question_id) REFERENCES Question(question_id)
    )
    ''')

    conn.commit()
    conn.close()
    print(f"SQLite 数据库已创建: {db_path}")


if __name__ == "__main__":
    create_db()
