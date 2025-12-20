#module_b\fill_survey_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# 让程序能找到根目录的 db_utils.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_utils as db

# ======== 违规词检查（使用 module_a/banned_words.txt） ========
import os

class AnswerViolationChecker:
    def __init__(self):
        self.banned_words = []
        self.load_banned_words()

    def load_banned_words(self):
        #加载 python-project/module_a/banned_words.txt

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        file_path = os.path.join(project_root, "module_a", "banned_words.txt")

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.banned_words = [line.strip() for line in f if line.strip()]
            except:
                self.banned_words = ["暴力", "赌博", "诈骗"]
        else:
            print(f"⚠ 未找到敏感词库：{file_path}")
            self.banned_words = ["暴力", "赌博", "诈骗"]

    def check_text(self, text: str):
        #检查单个文本是否包含敏感词
        if not text:
            return False, None

        for word in self.banned_words:
            if word in text:
                return True, word
        return False, None


# 输入用户名窗口（替代登录）
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


# 主窗口：问卷列表
class MainWindow:
    def __init__(self, master, user_id):
        self.master = master
        self.user_id = user_id

        self.win = tk.Toplevel(master)
        self.win.title("选择问卷")
        self.master.update_idletasks()  # 确保 master 尺寸是最新的
        w = self.master.winfo_width()
        h = self.master.winfo_height()
        x = self.master.winfo_x()
        y = self.master.winfo_y()

        self.win.geometry(f"{w}x{h}+{x}+{y}")

        self.win.configure(bg="#F0F2F5")

        self.container = tk.Frame(self.win, bg="#F0F2F5")
        self.container.pack(fill="both", expand=True)

        # 保存当前过滤条件（None 表示不过滤）
        self.filter_type = None
        self.filter_value = None

        self.create_search_bar()
        self.refresh()

        self.back_btn = ttk.Button(
            self.win,
            text="返回上一个界面",
            command=self.back_to_previous
        )

        # 右下角定位
        self.back_btn.place(relx=0.98, rely=0.96, anchor="se")

    def back_to_previous(self):
        """返回上一个界面，并关闭当前窗口"""
        self.win.destroy()  # 关闭当前 MainWindow
        self.master.deiconify()  # 显示上一个窗口

    # 搜索区（新增）
    def create_search_bar(self):
        bar = tk.Frame(self.container, bg="#F0F2F5")
        bar.pack(fill="x", pady=10, padx=10)

        self.search_entry = tk.Entry(
            bar, width=18,
            bg="white", bd=0, font=("Arial", 11)
        )
        self.search_entry.pack(side="left", padx=6, ipady=5)

        self.search_mode = ttk.Combobox(
            bar,
            values=["按问卷ID", "按用户名", "按用户ID"],
            state="readonly",
            width=10
        )
        self.search_mode.current(0)
        self.search_mode.pack(side="left", padx=6)

        search_btn = tk.Button(
            bar,
            text="搜索",
            bg="#2196F3",
            fg="white",
            relief="flat",
            command=self.apply_filter
        )
        search_btn.pack(side="left", padx=6, ipadx=10)

        reset_btn = tk.Button(
            bar,
            text="重置",
            bg="#E0E0E0",
            relief="flat",
            command=self.reset_filter
        )
        reset_btn.pack(side="left", padx=6, ipadx=10)

    # 执行搜索
    def apply_filter(self):
        value = self.search_entry.get().strip()
        mode = self.search_mode.get()

        if value == "":
            messagebox.showwarning("提示", "请输入搜索内容")
            return

        # 保存过滤条件
        self.filter_value = value

        if mode == "按问卷ID":
            self.filter_type = "survey_id"

        elif mode == "按用户名":
            self.filter_type = "username"

        elif mode == "按用户ID":
            self.filter_type = "user_id"

        self.refresh()

    # 清除过滤
    def reset_filter(self):
        self.filter_type = None
        self.filter_value = None
        self.search_entry.delete(0, tk.END)
        self.refresh()

    # 刷新问卷列表
    def refresh(self):
        # 清空旧内容（保留搜索栏）
        for widget in self.container.winfo_children()[1:]:
            widget.destroy()

        tk.Label(self.container, text="请选择要填写的问卷：").pack(pady=5)

        # 获取所有 public 问卷
        all_surveys = db.get_public_surveys()

        # 根据过滤条件做筛选
        surveys = []

        if self.filter_type is None:
            surveys = all_surveys

        else:
            if self.filter_type == "survey_id":
                try:
                    sid = int(self.filter_value)
                    surveys = [s for s in all_surveys if s["survey_id"] == sid]
                except:
                    surveys = []

            elif self.filter_type == "username":
                surveys = db.get_public_surveys_by_username(self.filter_value)

            elif self.filter_type == "user_id":
                try:
                    uid = int(self.filter_value)
                    surveys = db.get_public_surveys_by_user_id(uid)
                except:
                    surveys = []

        filled_surveys = db.get_surveys_filled_by_user(self.user_id)

        # 显示问卷列表
        for survey in surveys:
            sid = survey["survey_id"]
            title = survey["survey_title"]

            if sid in filled_surveys:
                display_name = f"{title} 【已填写】"
                btn = tk.Button(
                    self.container,
                    text=display_name,
                    bg="#EEEEEE",
                    fg="gray",
                    relief="flat",
                    state="disabled",
                    font=("Arial", 11),
                    anchor="w",
                    padx=12
                )
            else:
                display_name = title
                btn = tk.Button(
                    self.container,
                    text=display_name,
                    bg="white",
                    relief="flat",
                    font=("Arial", 11),
                    anchor="w",
                    padx=12,
                    command=lambda s=sid: self.open_fill_window(s)
                )

            btn.pack(pady=5, fill="x", padx=20)

    def open_fill_window(self, survey_id):
        self.win.withdraw()
        FillSurveyWindow(main_window=self, parent_win=self.win,
                         user_id=self.user_id, survey_id=survey_id)

# 问卷填写窗口
class FillSurveyWindow:
    def __init__(self, main_window, parent_win, user_id, survey_id):

        self.main_window = main_window
        self.parent_win = parent_win
        self.user_id = user_id
        self.survey_id = survey_id

        self.win = tk.Toplevel(parent_win)
        self.win.configure(bg="#F0F2F5")

        self.win.title("填写问卷")
        self.parent_win.update_idletasks()  # 确保 master 尺寸是最新的
        w = self.parent_win.winfo_width()
        h = self.parent_win.winfo_height()
        x = self.parent_win.winfo_x()
        y = self.parent_win.winfo_y()

        self.win.geometry(f"{w}x{h}+{x}+{y}")

        survey_data = db.get_full_survey_detail(survey_id)
        self.survey_data = survey_data

        self.violation_checker = AnswerViolationChecker()

        ttk.Label(
            self.win,
            text=survey_data["survey_title"],
            font=("Arial", 18, "bold"),
            foreground="#2196F3",
            background="#F0F2F5"
        ).pack(pady=15)

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

        submit_btn = tk.Button(
            self.win,
            text="提交问卷",
            bg="#2196F3",
            fg="white",
            font=("Arial", 12, "bold"),
            relief="flat",
            command=self.submit_answers
        )
        submit_btn.pack(pady=(25, 10), ipadx=20, ipady=6)

        back_btn = tk.Button(
            self.win,
            text="返回主界面（不保存）",
            bg="#E0E0E0",
            relief="flat",
            font=("Arial", 11),
            command=self.back_to_main
        )
        back_btn.pack(pady=(0, 20), ipadx=20, ipady=6)

    def back_to_main(self):
        """
        返回主界面，不保存进度。
        """
        confirm = messagebox.askyesno("确认返回",
                                      "返回主界面将不会保存当前作答内容。\n确定要返回吗？")
        if not confirm:
            return

        # 恢复 MainWindow
        self.parent_win.deiconify()
        self.main_window.refresh()  # 刷新问卷列表（可选）

        # 关闭填写窗口
        self.win.destroy()

    def submit_answers(self):
        #必填校验
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

        # 新增：答案敏感词检查
        for q in self.survey_data["questions"]:
            qid = q["question_id"]
            widget = self.answer_widgets[qid]

            if q["type"] in ("choice", "radio"):
                ans = widget.get()

            elif q["type"] == "checkbox":
                ans = ",".join(opt for opt, v in widget if v.get())

            else:  # text
                ans = widget.get().strip()

            is_bad, bad_word = self.violation_checker.check_text(ans)
            if is_bad:
                messagebox.showerror(
                    "违规内容",
                    f"第 {q['index']} 题答案包含敏感词\n"
                    f"请修改后再提交。"
                )
                return


        #校验通过后才允许提交
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

        self.main_window.refresh()  # 刷新问卷列表

        self.parent_win.deiconify()
        self.win.destroy()

# 程序入口
if __name__ == "__main__":
    root = tk.Tk()  # 只创建一个 Tk 实例
    UsernameWindow(root)
    root.mainloop()
