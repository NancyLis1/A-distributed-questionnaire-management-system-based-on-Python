import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# 让程序能找到根目录的 db_utils.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_utils as db

# ---------------------------
# 输入用户名窗口（替代登录）
# ---------------------------
class UsernameWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("问卷系统 - 输入用户名")
        self.master.geometry("400x200")

        ttk.Label(master, text="请输入用户名：", font=("Arial", 14)).pack(pady=20)

        self.username_entry = ttk.Entry(master, width=30)
        self.username_entry.pack()

        ttk.Button(master, text="开始", command=self.submit).pack(pady=20)

    def submit(self):
        username = self.username_entry.get().strip()

        if not username:
            messagebox.showerror("错误", "用户名不能为空")
            return

        user_id = db.get_user_id_by_name(username)
        if not user_id:
            messagebox.showerror("错误", "用户不存在，请检查用户名")
            return

        messagebox.showinfo("成功", f"欢迎你，{username}")

        # 隐藏登录窗口
        self.master.withdraw()

        # 打开问卷列表窗口
        MainWindow(self.master, user_id)


# ---------------------------
# 主窗口：问卷列表
# ---------------------------
class MainWindow:
    def __init__(self, master, user_id):
        self.master = master
        self.user_id = user_id

        self.win = tk.Toplevel(master)
        self.win.title("选择问卷")
        self.win.geometry("500x400")

        self.container = tk.Frame(self.win)
        self.container.pack(fill="both", expand=True)

        self.refresh()   # ← 初始化时直接调用

    def refresh(self):
        # 清空旧内容
        for widget in self.container.winfo_children():
            widget.destroy()

        surveys = db.get_public_surveys()
        filled_surveys = db.get_surveys_filled_by_user(self.user_id)

        tk.Label(self.container, text="请选择要填写的问卷：").pack(pady=10)

        for survey in surveys:
            sid = survey["survey_id"]
            title = survey["survey_title"]

            if sid in filled_surveys:
                display_name = f"{title} 【已填写】"
                btn = tk.Button(self.container, text=display_name, state="disabled")
            else:
                display_name = title
                btn = tk.Button(
                    self.container,
                    text=display_name,
                    command=lambda s=sid: self.open_fill_window(s)
                )

            btn.pack(pady=5, fill="x", padx=20)

    def open_fill_window(self, survey_id):
        # 传入两个参数：main_window_self（用于刷新）和 parent_win（用于层级）
        FillSurveyWindow(main_window=self, parent_win=self.win, user_id=self.user_id, survey_id=survey_id)


# ---------------------------
# 问卷填写窗口
# ---------------------------
class FillSurveyWindow:
    def __init__(self, main_window, parent_win, user_id, survey_id):
        self.main_window = main_window
        self.parent_win = parent_win
        self.user_id = user_id
        self.survey_id = survey_id

        self.win = tk.Toplevel(parent_win)
        self.win.title("填写问卷")
        self.win.geometry("600x600")

        survey_data = db.get_full_survey_detail(survey_id)
        self.survey_data = survey_data

        ttk.Label(self.win, text=survey_data["survey_title"], font=("Arial", 18)).pack(pady=10)

        # 创建可滚动区域
        canvas = tk.Canvas(self.win)
        scrollbar = ttk.Scrollbar(self.win, orient="vertical", command=canvas.yview)
        self.frame = ttk.Frame(canvas)

        self.frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.answer_widgets = {}

        # 显示每个题目
        for q in survey_data["questions"]:
            q_frame = ttk.LabelFrame(self.frame, text=f"第 {q['index']} 题")
            q_frame.pack(fill="x", padx=10, pady=10)

            ttk.Label(q_frame, text=q["text"], font=("Arial", 12)).pack(anchor="w", pady=5)

            if q["type"] == "choice":
                var = tk.StringVar()
                self.answer_widgets[q["question_id"]] = var

                for opt in q["options"]:
                    ttk.Radiobutton(q_frame, text=opt, variable=var, value=opt).pack(anchor="w")

            elif q["type"] == "checkbox":
                vars_list = []
                for opt in q["options"]:
                    v = tk.BooleanVar()
                    ttk.Checkbutton(q_frame, text=opt, variable=v).pack(anchor="w")
                    vars_list.append((opt, v))
                self.answer_widgets[q["question_id"]] = vars_list

            elif q["type"] == "text":
                entry = ttk.Entry(q_frame, width=50)
                entry.pack(anchor="w")
                self.answer_widgets[q["question_id"]] = entry

        ttk.Button(self.win, text="提交问卷", command=self.submit_answers).pack(pady=20)

    def submit_answers(self):
        # ========= 必填校验 ==========
        for q in self.survey_data["questions"]:
            qid = q["question_id"]
            widget = self.answer_widgets[qid]

            if q["type"] in ("choice", "radio"):
                # 单选题必须选
                if widget.get() == "":
                    messagebox.showwarning("未完成", f"第 {q['index']} 题尚未作答（单选题）。")
                    return

            elif q["type"] == "checkbox":
                # 多选题至少一个
                selected = [opt for opt, v in widget if v.get()]
                if len(selected) == 0:
                    messagebox.showwarning("未完成", f"第 {q['index']} 题尚未作答（多选题）。")
                    return

            elif q["type"] == "text":
                # 文本题不能为空（你可根据需求是否允许空）
                if widget.get().strip() == "":
                    messagebox.showwarning("未完成", f"第 {q['index']} 题尚未填写（文本题）。")
                    return

        # ========= 校验通过后才允许提交 ==========
        db.add_answer_survey_history(self.user_id, self.survey_id)

        for q in self.survey_data["questions"]:
            qid = q["question_id"]
            widget = self.answer_widgets[qid]

            if q["type"] in ("choice", "radio"):
                ans = widget.get()

            elif q["type"] == "checkbox":
                ans = ",".join(opt for opt, v in widget if v.get())

            else:  # text
                ans = widget.get().strip()

            db.add_answer(self.user_id, self.survey_id, qid, ans)

        messagebox.showinfo("成功", "问卷填写完成！")

        self.win.destroy()
        self.main_window.refresh()  # ← 刷新问卷列表

        self.parent_win.deiconify()


# ---------------------------
# 程序入口
# ---------------------------
if __name__ == "__main__":
    root = tk.Tk()  # 只创建一个 Tk 实例
    UsernameWindow(root)
    root.mainloop()
