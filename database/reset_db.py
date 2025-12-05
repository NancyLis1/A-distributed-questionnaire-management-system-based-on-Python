# reset_db.py

import os
import sqlite3
import subprocess
import sys

# 假设数据库路径和 init_db.py 的位置
DB_PATH = "database/survey_system.db"
INIT_SCRIPT = "database/create_sql_database.py"


def reset_database():
    """删除现有数据库文件，并重新执行初始化脚本。"""

    # --- 1. 删除旧的数据库文件 ---
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"✅ 成功删除旧数据库文件: {DB_PATH}")
        except Exception as e:
            print(f"❌ 错误：无法删除数据库文件。请检查文件是否被占用。错误信息: {e}")
            sys.exit(1)
    else:
        print(f"ℹ️ 数据库文件 {DB_PATH} 不存在，跳过删除。")

    # --- 2. 重新初始化数据库 ---
    print(f"🔄 正在运行数据库初始化脚本: {INIT_SCRIPT}")
    try:
        # 使用 subprocess 执行初始化脚本
        result = subprocess.run([sys.executable, INIT_SCRIPT], capture_output=True, text=True, check=True)
        print("--- 初始化脚本输出 ---")
        print(result.stdout)
        print("--------------------")
        print(f"✅ 数据库已成功初始化！")

    except subprocess.CalledProcessError as e:
        print(f"❌ 错误：初始化脚本执行失败。请检查 {INIT_SCRIPT}。")
        print(f"错误输出:\n{e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ 错误：未找到初始化脚本 {INIT_SCRIPT}。请检查路径。")
        sys.exit(1)


if __name__ == "__main__":
    reset_database()