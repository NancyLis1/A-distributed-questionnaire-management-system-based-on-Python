# user_system_tkinter.py
import sqlite3
from db_utils import *
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

DATABASE = "database/survey_system.db"

# ----------------------------------------
# 数据库操作
# ----------------------------------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------------------------------
# 注册用户
# ----------------------------------------
def register(user_name: str, phone: str, password: str, is_admin=False):
    status = "admin" if is_admin else "active"
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO User (user_name, phone, password, user_status) VALUES (?,?,?,?)",
            (user_name, phone, password, status)
        )
        conn.commit()
        messagebox.showinfo("注册成功", f"{user_name} 注册成功！{'管理员' if is_admin else ''}")
    except sqlite3.IntegrityError:
        messagebox.showerror("错误", "用户名或手机号已存在")
    finally:
        conn.close()

# ----------------------------------------
# 登录用户
# ----------------------------------------
def login(user_name: str, password: str) -> Optional[int]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, user_name, user_status FROM User WHERE user_name=? AND password=?",
        (user_name, password)
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        messagebox.showinfo("登录成功", f"欢迎 {user['user_name']}，状态：{user['user_status']}")
        return user["user_id"]
    else:
        messagebox.showerror("登录失败", "用户名或密码错误")
        return None


# ----------------------------------------
# 修改用户信息
# ----------------------------------------
def update_user(user_id: int, new_name: Optional[str]=None, new_phone: Optional[str]=None, new_password: Optional[str]=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        if new_name:
            cursor.execute("UPDATE User SET user_name=? WHERE user_id=?", (new_name, user_id))
        if new_phone:
            cursor.execute("UPDATE User SET phone=? WHERE user_id=?", (new_phone, user_id))
        if new_password:
            cursor.execute("UPDATE User SET password=? WHERE user_id=?", (new_password, user_id))
        conn.commit()
        messagebox.showinfo("成功", "用户信息更新成功")
    except sqlite3.IntegrityError:
        messagebox.showerror("错误", "用户名或手机号已存在")
    finally:
        conn.close()

# ----------------------------------------
# >>> 新增功能：查看问卷详情 + 答卷数量
# ----------------------------------------
def view_survey_detail(survey_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Survey WHERE survey_id=?", (survey_id,))
    survey = cursor.fetchone()
    if not survey:
        messagebox.showerror("错误", "问卷不存在")
        conn.close()
        return

    cursor.execute("SELECT * FROM Question WHERE survey_id=? ORDER BY question_index", (survey_id,))
    questions = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS cnt FROM Answer_survey_history WHERE survey_id=?", (survey_id,))
    filled = cursor.fetchone()["cnt"]

    conn.close()

    msg = f"【问卷 ID】: {survey['survey_id']}\n" \
          f"【状态】: {survey['survey_status']}\n" \
          f"【发布时间】: {survey['release_time']}\n" \
          f"【收到答卷】: {filled} 份\n\n" \
          f"===== 问卷题目 =====\n"

    for q in questions:
        msg += f"{q['question_index']}. {q['question_text']}（类型：{q['question_type']}）\n"

    messagebox.showinfo("问卷详情", msg)


# ----------------------------------------
# >>> 新增功能：删除问卷（创建者专用）
# ----------------------------------------
def delete_survey(survey_id: int, user_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT created_by FROM Survey WHERE survey_id=?", (survey_id,))
    row = cursor.fetchone()
    if not row:
        messagebox.showerror("错误", "问卷不存在")
        conn.close()
        return

    if row["created_by"] != user_id:
        messagebox.showerror("错误", "不能删除他人创建的问卷")
        conn.close()
        return

    cursor.execute("DELETE FROM Answer WHERE survey_id=?", (survey_id,))
    cursor.execute("DELETE FROM Answer_survey_history WHERE survey_id=?", (survey_id,))
    cursor.execute("DELETE FROM Question WHERE survey_id=?", (survey_id,))
    cursor.execute("DELETE FROM Survey WHERE survey_id=?", (survey_id,))
    conn.commit()
    conn.close()

    messagebox.showinfo("成功", f"问卷 {survey_id} 已删除")


# ----------------------------------------
# >>> 新增功能：弹窗查看自己创建/填写过的问卷 + 管理
# ----------------------------------------
def my_surveys_window(user_id: int):
    win = tk.Toplevel()
    win.title("我的问卷")
    win.geometry("500x450")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Survey WHERE created_by=?", (user_id,))
    created = cursor.fetchall()

    cursor.execute("""
        SELECT s.* FROM Survey s
        JOIN Answer_survey_history a ON s.survey_id=a.survey_id
        WHERE a.user_id=?
    """, (user_id,))
    filled = cursor.fetchall()

    conn.close()

    ttk.Label(win, text="我创建的问卷", font=("Arial", 12, "bold")).pack()

    for s in created:
        f = ttk.Frame(win)
        f.pack(fill='x', pady=2)
        ttk.Label(f, text=f"ID {s['survey_id']}  状态:{s['survey_status']}").pack(side='left')

        ttk.Button(f, text="详情", command=lambda sid=s['survey_id']: view_survey_detail(sid)).pack(side='right')
        ttk.Button(f, text="删除", command=lambda sid=s['survey_id']: delete_survey(sid, user_id)).pack(side='right')

    ttk.Label(win, text="\n我填写过的问卷", font=("Arial", 12, "bold")).pack()

    for s in filled:
        f = ttk.Frame(win)
        f.pack(fill='x', pady=2)
        ttk.Label(f, text=f"ID {s['survey_id']} 状态:{s['survey_status']}").pack(side='left')

        ttk.Button(f, text="查看内容", command=lambda sid=s['survey_id']: view_survey_detail(sid)).pack(side='right')


# ----------------------------------------
# 管理员查看用户列表（原有功能）
# ----------------------------------------
def admin_user_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id,user_name,phone,user_status,last_login FROM User")
    users = cursor.fetchall()
    conn.close()
    msg = f"用户列表({len(users)}):\n"
    for u in users:
        msg += f"ID:{u['user_id']} 名称:{u['user_name']} 手机:{u['phone']} 状态:{u['user_status']} 最后登录:{u['last_login']}\n"
    messagebox.showinfo("用户列表", msg)


# ----------------------------------------
# Tkinter界面
# ----------------------------------------
class UserSystemApp:
    def __init__(self, master):
        self.master = master
        self.master.title("用户系统")
        self.current_user_id = None
        self.is_admin = False

        # Tabs
        self.tab_control = ttk.Notebook(master)
        self.tab_login = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_login, text='登录/注册')
        self.tab_control.pack(expand=1, fill='both')

        self.create_login_tab()

    def create_login_tab(self):
        frame = self.tab_login
        ttk.Label(frame, text="用户名").grid(row=0, column=0, padx=5, pady=5)
        self.entry_name = ttk.Entry(frame)
        self.entry_name.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="密码").grid(row=1, column=0, padx=5, pady=5)
        self.entry_password = ttk.Entry(frame, show="*")
        self.entry_password.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(frame, text="登录", command=self.login_action).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(frame, text="注册", command=self.register_action).grid(row=2, column=1, padx=5, pady=5)

    def login_action(self):
        name = self.entry_name.get()
        pwd = self.entry_password.get()
        user_id = login(name, pwd)
        if user_id:
            self.current_user_id = user_id

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_status FROM User WHERE user_id=?", (user_id,))
            self.is_admin = cursor.fetchone()["user_status"] == "admin"
            conn.close()

            self.create_user_tab()

    def register_action(self):
        name = self.entry_name.get()
        pwd = self.entry_password.get()
        register(name, "", pwd)

    def create_user_tab(self):
        self.tab_control.destroy()
        self.tab_control = ttk.Notebook(self.master)
        self.tab_user = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_user, text='用户操作')
        self.tab_control.pack(expand=1, fill='both')

        ttk.Button(self.tab_user, text="查看我的问卷",
                   command=lambda: my_surveys_window(self.current_user_id)).pack(padx=5, pady=5)

        ttk.Button(self.tab_user, text="修改密码", command=self.change_password).pack(padx=5, pady=5)

        if self.is_admin:
            ttk.Button(self.tab_user, text="查看所有用户", command=admin_user_list).pack(padx=5, pady=5)

    def change_password(self):
        if self.current_user_id:
            new_pwd = tk.simpledialog.askstring("修改密码", "请输入新密码", show="*")
            if new_pwd:
                update_user(self.current_user_id, new_password=new_pwd)


# ----------------------------------------
# 启动应用
# ----------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = UserSystemApp(root)
    root.mainloop()
