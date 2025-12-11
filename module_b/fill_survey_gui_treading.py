import json
import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from typing import List, Dict, Any, Optional

# 让程序能找到根目录的 db_proxy.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_proxy as db


# ======== 违规词检查（使用 module_a/banned_words.txt） ========
class AnswerViolationChecker:
    def __init__(self):
        self.banned_words = []
        self.load_banned_words()

    def load_banned_words(self):
        """
        加载 python-project/module_a/banned_words.txt
        """
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
        """
        检查单个文本是否包含敏感词
        """
        if not text:
            return False, None

        for word in self.banned_words:
            if word in text:
                return True, word
        return False, None


# ---------------------------
# 输入用户名窗口（保持不变）
# ---------------------------
class UsernameWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("问卷系统 - 输入用户名")
        self.master.geometry("400x200")

        self.submit_btn = ttk.Button(master, text="开始", command=self.submit)

        ttk.Label(master, text="请输入用户名：", font=("Arial", 14)).pack(pady=20)
        self.username_entry = ttk.Entry(master, width=30)
        self.username_entry.pack()
        self.submit_btn.pack(pady=20)

        self.loading_overlay = None

    def show_loading_state(self, message="⏳ 登录中，请稍候..."):
        self.submit_btn.config(state="disabled")
        self.username_entry.config(state="disabled")

        if self.loading_overlay and self.loading_overlay.winfo_exists():
            return

        self.loading_overlay = tk.Toplevel(self.master)
        self.loading_overlay.transient(self.master)
        self.loading_overlay.grab_set()
        self.loading_overlay.wm_overrideredirect(True)

        try:
            w = self.master.winfo_width()
            h = self.master.winfo_height()
            x = self.master.winfo_x()
            y = self.master.winfo_y()
            if w < 10 or h < 10: w, h = 400, 200
            self.loading_overlay.geometry(f"{w}x{h}+{x}+{y}")
        except:
            self.loading_overlay.geometry("400x200+100+100")

        loading_frame = tk.Frame(self.loading_overlay, bg="#333333", bd=1, relief="solid")
        loading_frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(loading_frame, text=message, bg="#333333", fg="white", font=("Arial", 12, "bold")).pack(padx=20,
                                                                                                         pady=10)
        self.master.update_idletasks()

    def hide_loading_state(self):
        self.submit_btn.config(state="normal")
        self.username_entry.config(state="normal")
        if self.loading_overlay and self.loading_overlay.winfo_exists():
            self.loading_overlay.grab_release()
            self.loading_overlay.destroy()
            self.loading_overlay = None

    def submit(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("错误", "用户名不能为空")
            return

        self.show_loading_state()
        threading.Thread(target=self._login_in_thread, args=(username,), daemon=True).start()

    def _login_in_thread(self, username):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", 5000))
            user_id = db.get_user_id_by_name(sock, username)

            if not user_id:
                self.master.after(0, self._handle_login_failure, "用户不存在，请检查用户名")
                return

            login_msg = {"action": "login", "params": {"user_id": user_id}}
            sock.sendall(json.dumps(login_msg).encode("utf-8"))

            self.master.after(0, self._handle_login_success, username, user_id, sock)

        except ConnectionRefusedError:
            self.master.after(0, self._handle_login_failure, "无法连接到服务器，请确保服务器已运行。")
            if sock: sock.close()
        except Exception as e:
            self.master.after(0, self._handle_login_failure, f"登录失败: {e}")
            if sock: sock.close()

    def _handle_login_failure(self, message):
        self.hide_loading_state()
        messagebox.showerror("登录错误", message)

    def _handle_login_success(self, username, user_id, sock):
        self.hide_loading_state()
        messagebox.showinfo("成功", f"欢迎你，{username}")
        self.master.withdraw()

        def listen_server():
            try:
                while True:
                    sock.settimeout(0.5)
                    try:
                        data = sock.recv(4096)
                        if not data: break
                        msg = json.loads(data.decode("utf-8"))
                        if msg.get("action") == "force_logout":
                            messagebox.showinfo("提示", "你的账号在另一界面登录，你已被强制退出")
                            self.master.destroy()
                            break
                    except socket.timeout:
                        continue
            except:
                pass
            finally:
                sock.close()

        threading.Thread(target=listen_server, daemon=True).start()

        MainWindow(self.master, user_id, sock)


# ---------------------------
# 主窗口：问卷列表
# ---------------------------
class MainWindow:
    def __init__(self, master, user_id, sock):
        self.master = master
        self.user_id = user_id
        self.sock = sock

        self.win = tk.Toplevel(master)
        self.win.title("选择问卷")
        self.master.update_idletasks()
        w = self.master.winfo_width()
        h = self.master.winfo_height()
        x = self.master.winfo_x()
        y = self.master.winfo_y()

        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.configure(bg="#F0F2F5")

        # 使用 Canvas 实现列表滚动
        self.canvas = tk.Canvas(self.win, bg="#F0F2F5")
        scrollbar = ttk.Scrollbar(self.win, orient="vertical", command=self.canvas.yview)

        # 容器 Frame 放在 Canvas 内部
        self.container = tk.Frame(self.canvas, bg="#F0F2F5")

        # 初始宽度绑定
        self.canvas.create_window((0, 0), window=self.container, anchor="nw", width=w)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.container.bind("<Configure>", lambda e: self.canvas.config(scrollregion=self.canvas.bbox("all")))

        # 绑定 Canvas 宽度变化以同步 container 宽度
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # 鼠标滚轮支持 (绑定到 Canvas)
        def _on_mousewheel(event):
            if sys.platform.startswith('win') or sys.platform == 'darwin':
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")

        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.canvas.bind("<Button-4>", _on_mousewheel)
        self.canvas.bind("<Button-5>", _on_mousewheel)

        self.canvas.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 内部状态
        self.loading_overlay = None
        self.filter_type = None
        self.filter_value = None
        self.filled_surveys = set()
        self.search_bar_frame = None  # 存储搜索栏的引用

        # 1. 创建搜索栏 (必须在 refresh 之前创建)
        self.create_search_bar()
        # 2. 加载问卷列表
        self.refresh()

        self.back_btn = ttk.Button(
            self.win,
            text="返回上一个界面",
            command=self.back_to_previous
        )
        self.back_btn.place(relx=0.98, rely=0.96, anchor="se")

    def _on_canvas_configure(self, event):
        """同步容器 Frame 的宽度到 Canvas 的宽度"""
        if self.canvas.winfo_children():
            self.canvas.itemconfig(self.canvas.winfo_children()[0], width=event.width)

    def show_loading_state(self, message="⏳ 数据加载中，请稍候..."):
        if self.loading_overlay and self.loading_overlay.winfo_exists(): return
        self.loading_overlay = tk.Toplevel(self.win)
        self.loading_overlay.transient(self.win)
        self.loading_overlay.grab_set()
        self.loading_overlay.wm_overrideredirect(True)
        try:
            w = self.win.winfo_width()
            h = self.win.winfo_height()
            x = self.win.winfo_x()
            y = self.win.winfo_y()
            if w < 10 or h < 10: w, h = 800, 600
            self.loading_overlay.geometry(f"{w}x{h}+{x}+{y}")
        except:
            self.loading_overlay.geometry("400x150+100+100")
        loading_frame = tk.Frame(self.loading_overlay, bg="#333333", bd=1, relief="solid")
        loading_frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(loading_frame, text=message, bg="#333333", fg="white", font=("Arial", 14, "bold")).pack(padx=30,
                                                                                                         pady=20)
        self.win.update_idletasks()

    def hide_loading_state(self):
        if self.loading_overlay and self.loading_overlay.winfo_exists():
            self.loading_overlay.grab_release()
            self.loading_overlay.destroy()
            self.loading_overlay = None

    # 🚀 新增：判断是否为网络错误
    def is_network_error(self, message: str) -> bool:
        """检查错误信息是否包含瞬时网络错误关键词"""
        return "网络超时" in message or "网络错误" in message or "连接已关闭" in message or "接收服务器响应超时" in message

    def _handle_error(self, message):
        self.hide_loading_state()
        messagebox.showerror("操作失败", message, parent=self.win)

    def refresh(self):
        # 清除旧的列表项
        for widget in self.container.winfo_children():
            # ⚠️ 关键修复：判断是否是搜索栏，如果是则保留
            if widget is not self.search_bar_frame:
                widget.destroy()

        # 重新创建 "请选择要填写的问卷：" 标签
        tk.Label(self.container, text="请选择要填写的问卷：", bg="#F0F2F5").pack(pady=5)

        self.show_loading_state()
        threading.Thread(target=self._load_surveys_in_thread, daemon=True).start()

    def _load_surveys_in_thread(self):
        """
        工作线程：进行网络I/O获取数据
        """
        try:
            # 1. 获取所有公开问卷
            all_surveys = db.get_public_surveys(self.sock)

            # 2. 过滤逻辑（与原来一致）
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
                    surveys = db.get_public_surveys_by_username(self.sock, self.filter_value)
                elif self.filter_type == "user_id":
                    try:
                        uid = int(self.filter_value)
                        surveys = db.get_public_surveys_by_user_id(self.sock, uid)
                    except:
                        surveys = []

            # 3. 获取用户已填写的问卷ID
            filled_surveys = db.get_surveys_filled_by_user(self.sock, self.user_id)

            # 4. 返回主线程，一次性绘制
            self.win.after(0, self._update_gui_with_data, surveys, filled_surveys)

        except Exception as e:
            error_message = f"刷新列表失败: {e}"
            if self.is_network_error(error_message):
                # 🚀 自动刷新，不弹窗，重新尝试加载
                self.win.after(0, self.refresh)
            else:
                self.win.after(0, self._handle_error, error_message)

    # =======================================================
    # 一次性绘制所有问卷列表
    # =======================================================
    def _update_gui_with_data(self, surveys, filled_surveys):
        try:
            for survey in surveys:
                self._create_single_survey_item(survey, filled_surveys)

            # 确保 canvas 滚动区域更新
            self.container.update_idletasks()
            self.canvas.config(scrollregion=self.canvas.bbox("all"))

        finally:
            self.hide_loading_state()

    def _create_single_survey_item(self, survey, filled_surveys):
        """创建单个问卷列表按钮"""
        sid = survey["survey_id"]
        title = survey["survey_title"]

        if sid in filled_surveys:
            display_name = f"{title} 【已填写】"
            btn = tk.Button(self.container, text=display_name, bg="#EEEEEE", fg="gray", relief="flat",
                            state="disabled", font=("Arial", 11), anchor="w", padx=12)
        else:
            display_name = title
            btn = tk.Button(self.container, text=display_name, bg="white", relief="flat", font=("Arial", 11),
                            anchor="w", padx=12, command=lambda s=sid: self.open_fill_window(s))

        # 确保新创建的按钮排在搜索栏和标签之后
        btn.pack(pady=5, fill="x", padx=20)

    # =======================================================

    def back_to_previous(self):
        self.win.destroy()
        self.master.deiconify()

    def create_search_bar(self):
        # 搜索栏放在 container 的第一个位置
        bar = tk.Frame(self.container, bg="#F0F2F5")
        bar.pack(fill="x", pady=10, padx=10)
        self.search_bar_frame = bar  # 存储搜索栏 Frame 的引用

        self.search_entry = tk.Entry(bar, width=18, bg="white", bd=0, font=("Arial", 11))
        self.search_entry.pack(side="left", padx=6, ipady=5)

        self.search_mode = ttk.Combobox(bar, values=["按问卷ID", "按用户名", "按用户ID"], state="readonly", width=10)
        self.search_mode.current(0)
        self.search_mode.pack(side="left", padx=6)

        search_btn = tk.Button(bar, text="搜索", bg="#2196F3", fg="white", relief="flat", command=self.apply_filter)
        search_btn.pack(side="left", padx=6, ipadx=10)

        reset_btn = tk.Button(bar, text="重置", bg="#E0E0E0", relief="flat", command=self.reset_filter)
        reset_btn.pack(side="left", padx=6, ipadx=10)

    def apply_filter(self):
        value = self.search_entry.get().strip()
        mode = self.search_mode.get()
        if value == "":
            messagebox.showwarning("提示", "请输入搜索内容", parent=self.win)
            return
        self.filter_value = value
        if mode == "按问卷ID":
            self.filter_type = "survey_id"
        elif mode == "按用户名":
            self.filter_type = "username"
        elif mode == "按用户ID":
            self.filter_type = "user_id"
        self.refresh()

    def reset_filter(self):
        self.filter_type = None
        self.filter_value = None
        self.search_entry.delete(0, tk.END)
        self.search_mode.current(0)  # 重置搜索模式为默认
        self.refresh()

    def open_fill_window(self, survey_id):
        self.win.withdraw()
        FillSurveyWindow(main_window=self, parent_win=self.win,
                         user_id=self.user_id, survey_id=survey_id, sock=self.sock)


# ---------------------------
# 问卷填写窗口
# ---------------------------
class FillSurveyWindow:
    def __init__(self, main_window, parent_win, user_id, survey_id, sock):
        self.sock = sock
        self.main_window = main_window
        self.parent_win = parent_win
        self.user_id = user_id
        self.survey_id = survey_id
        self.loading_overlay = None
        self.survey_data = None
        self.questions_data = None  # 存储问题数据
        self.answer_widgets = {}

        self.win = tk.Toplevel(parent_win)
        self.win.configure(bg="#F0F2F5")
        self.win.title("填写问卷")

        self.parent_win.update_idletasks()
        w = self.parent_win.winfo_width()
        h = self.parent_win.winfo_height()
        x = self.parent_win.winfo_x()
        y = self.parent_win.winfo_y()
        self.win.geometry(f"{w}x{h}+{x}+{y}")

        self.violation_checker = AnswerViolationChecker()

        self.show_loading_state("正在获取问卷详情...")

        threading.Thread(target=self._load_survey_data, daemon=True).start()

    def show_loading_state(self, message="⏳ 处理中，请稍候..."):
        if self.loading_overlay and self.loading_overlay.winfo_exists(): return
        self.loading_overlay = tk.Toplevel(self.win)
        self.loading_overlay.transient(self.win)
        self.loading_overlay.grab_set()
        self.loading_overlay.wm_overrideredirect(True)
        try:
            w = self.win.winfo_width()
            h = self.win.winfo_height()
            x = self.win.winfo_x()
            y = self.win.winfo_y()
            if w < 10 or h < 10: w, h = 800, 600
            self.loading_overlay.geometry(f"{w}x{h}+{x}+{y}")
        except:
            self.loading_overlay.geometry("400x150+100+100")
        loading_frame = tk.Frame(self.loading_overlay, bg="#333333", bd=1, relief="solid")
        loading_frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(loading_frame, text=message, bg="#333333", fg="white", font=("Arial", 14, "bold")).pack(padx=30,
                                                                                                         pady=20)
        self.win.update_idletasks()

    def hide_loading_state(self):
        if self.loading_overlay and self.loading_overlay.winfo_exists():
            self.loading_overlay.grab_release()
            self.loading_overlay.destroy()
            self.loading_overlay = None

    def is_network_error(self, message: str) -> bool:
        """检查错误信息是否包含瞬时网络错误关键词"""
        return "网络超时" in message or "网络错误" in message or "连接已关闭" in message or "接收服务器响应超时" in message

    def _handle_error(self, message, is_fatal=False):
        self.hide_loading_state()
        messagebox.showerror("操作失败", message, parent=self.win)
        if is_fatal:
            self.back_to_main(skip_confirm=True)

    def _handle_loading_network_failure(self):
        """处理加载问卷时的网络错误：直接返回主界面并刷新"""
        self.hide_loading_state()
        messagebox.showinfo("提示", "网络连接异常，已自动刷新问卷列表。", parent=self.win)
        self.back_to_main(skip_confirm=True)

    def _load_survey_data(self):
        try:
            survey_data = db.get_full_survey_detail(self.sock, self.survey_id)
            self.win.after(0, self._build_ui, survey_data)
        except Exception as e:
            error_message = f"获取问卷详情失败: {e}"
            if self.is_network_error(error_message):
                # 🚀 网络错误，自动返回并刷新主列表
                self.win.after(0, self._handle_loading_network_failure)
            else:
                # 其他错误（如问卷不存在），弹窗并返回主列表
                self.win.after(0, self._handle_error, error_message, is_fatal=True)

    def _build_ui(self, survey_data):
        self.hide_loading_state()
        self.survey_data = survey_data
        self.questions_data = survey_data["questions"]

        ttk.Label(self.win, text=survey_data["survey_title"], font=("Arial", 18, "bold"), foreground="#2196F3",
                  background="#F0F2F5").pack(pady=15)

        canvas = tk.Canvas(self.win)
        scrollbar = ttk.Scrollbar(self.win, orient="vertical", command=canvas.yview)
        self.frame = ttk.Frame(canvas)

        self.frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=self.frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            if sys.platform.startswith('win') or sys.platform == 'darwin':
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_mousewheel)
        canvas.bind("<Button-5>", _on_mousewheel)
        self.frame.bind("<MouseWheel>", _on_mousewheel)
        self.frame.bind("<Button-4>", _on_mousewheel)
        self.frame.bind("<Button-5>", _on_mousewheel)

        # 一次性绘制所有问题
        for q in self.questions_data:
            self._create_single_question_widget(q)
        # 确保 canvas 滚动区域更新
        self.frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        self.submit_btn = tk.Button(self.win, text="提交问卷", bg="#2196F3", fg="white", font=("Arial", 12, "bold"),
                                    relief="flat", command=self.submit_answers)
        self.submit_btn.pack(pady=(25, 10), ipadx=20, ipady=6)
        self.back_btn = tk.Button(self.win, text="返回主界面（不保存）", bg="#E0E0E0", relief="flat", font=("Arial", 11),
                                  command=self.back_to_main)
        self.back_btn.pack(pady=(0, 20), ipadx=20, ipady=6)

    def _create_single_question_widget(self, q):
        """
        负责创建单个问题的控件。
        """
        q_frame = ttk.LabelFrame(self.frame, text=f"第 {q['index']} 题")
        q_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(q_frame, text=q["text"], font=("Arial", 12)).pack(anchor="w", pady=5)

        qid = q["question_id"]

        if q["type"] == "choice":
            var = tk.StringVar()
            self.answer_widgets[qid] = var
            for opt in q["options"]:
                ttk.Radiobutton(q_frame, text=opt, variable=var, value=opt).pack(anchor="w")
        elif q["type"] == "checkbox":
            vars_list = []
            for opt in q["options"]:
                v = tk.BooleanVar()
                ttk.Checkbutton(q_frame, text=opt, variable=v).pack(anchor="w")
                vars_list.append((opt, v))
            self.answer_widgets[qid] = vars_list
        elif q["type"] == "text":
            entry = ttk.Entry(q_frame, width=50)
            entry.pack(anchor="w")
            self.answer_widgets[qid] = entry
        elif q["type"] == "slider":
            # 创建滑块和值显示标签
            slider_frame = tk.Frame(q_frame)
            slider_frame.pack(fill="x", pady=5)

            # 值显示标签
            val_label = tk.Label(slider_frame, text="5", font=("Arial", 12, "bold"),
                                 width=3, bd=1, relief="solid")
            val_label.pack(side="left", padx=(0, 10))

            # 创建滑块 (1-10)
            scale = tk.Scale(slider_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                             length=300, showvalue=0)
            scale.set(5)  # 默认值为5
            scale.pack(side="left", fill="x", expand=True)

            # 创建数字标签
            scale_nums = tk.Frame(q_frame, bg="white")
            scale_nums.pack(fill="x", padx=55, pady=5)
            for i in range(1, 11):
                tk.Label(scale_nums, text=str(i), bg="white", fg="gray").pack(side="left", expand=True)

            # 存储滑块和标签的引用
            self.answer_widgets[qid] = {
                'scale': scale,
                'value_label': val_label
            }

            # 绑定滑块值变化事件
            def update_label(val, label=val_label):
                label.config(text=str(int(float(val))))

            scale.config(command=update_label)

    def back_to_main(self, skip_confirm=False):
        """
        返回主界面，不保存进度。
        """
        if not skip_confirm:
            confirm = messagebox.askyesno("确认返回",
                                          "返回主界面将不会保存当前作答内容。\n确定要返回吗？",
                                          parent=self.win)
            if not confirm:
                return

        self.main_window.refresh()
        self.win.destroy()
        self.parent_win.deiconify()

    def submit_answers(self):
        # 1. 前端校验
        for q in self.survey_data["questions"]:
            qid = q["question_id"]
            widget = self.answer_widgets[qid]
            ans = ""
            if q["type"] in ("choice", "radio"):
                if widget.get() == "":
                    messagebox.showwarning("未完成", f"第 {q['index']} 题尚未作答（单选题）。", parent=self.win)
                    return
                ans = widget.get()
            elif q["type"] == "checkbox":
                selected = [opt for opt, v in widget if v.get()]
                if len(selected) == 0:
                    messagebox.showwarning("未完成", f"第 {q['index']} 题尚未作答（多选题）。", parent=self.win)
                    return
                ans = ",".join(selected)
            elif q["type"] == "text":
                if widget.get().strip() == "":
                    messagebox.showwarning("未完成", f"第 {q['index']} 题尚未填写（文本题）。", parent=self.win)
                    return
                ans = widget.get().strip()
                # 新增：滑动条校验
            elif q["type"] == "slider":
                # 滑动条总是有值（默认值为5），所以不需要校验是否为空
                ans = str(widget['scale'].get())

            is_bad, bad_word = self.violation_checker.check_text(ans)
            if is_bad:
                messagebox.showerror("违规内容", f"第 {q['index']} 题答案包含敏感词【{bad_word}】\n请修改后再提交。",
                                     parent=self.win)
                return

        # 2. 禁用按钮，显示加载状态
        self.submit_btn.config(state="disabled")
        self.back_btn.config(state="disabled")
        self.show_loading_state("正在提交答案...")

        # 3. 提交操作在工作线程中进行
        threading.Thread(target=self._submit_answers_in_thread, daemon=True).start()

    def _submit_answers_in_thread(self):
        try:
            # 1. 整理答案
            answers_to_submit = []
            for q in self.survey_data["questions"]:
                qid = q["question_id"]
                widget = self.answer_widgets[qid]
                if q["type"] in ("choice", "radio"):
                    ans = widget.get()
                elif q["type"] == "checkbox":
                    ans = ",".join(opt for opt, v in widget if v.get())
                elif q["type"] == "text":
                    ans = widget.get().strip()
                    # 新增：滑动条答案获取
                elif q["type"] == "slider":
                    ans = str(widget['scale'].get())

                # 整理成新接口需要的格式
                answers_to_submit.append({'question_id': qid, 'answer_text': ans})

            # 2. 关键优化：只调用一次合并的提交接口
            db.add_full_survey_submission(
                self.sock,
                self.user_id,
                self.survey_id,
                answers_to_submit  # 包含所有问题的列表
            )

            # 3. 成功后返回主线程处理 UI
            self.win.after(0, self._submission_success)

        except Exception as e:
            # 4. 失败后返回主线程处理 UI
            error_message = f"提交答案失败: {e}"
            cleanup_successful = False

            if self.is_network_error(error_message):
                try:
                    # 尝试清除数据库中的记录（即“回滚”）
                    db.undo_survey_submission(self.sock, self.user_id, self.survey_id)
                    cleanup_successful = True
                except:
                    # 清理操作本身也失败了，我们只能尽力了
                    pass

                # 4. 失败后返回主线程处理 UI
            self.win.after(0, self._submission_failure_handler, error_message, cleanup_successful)


    def _submission_success(self):
        self.hide_loading_state()
        messagebox.showinfo("成功", "问卷填写完成！", parent=self.win)
        self.main_window.refresh()
        self.parent_win.deiconify()
        self.win.destroy()

    def _submission_failure_handler(self, message, cleanup_successful=False):
        """处理提交问卷时的失败，如果是网络错误则重置按钮并根据清理结果给出提示"""
        self.hide_loading_state()

        # 重新启用按钮
        self.submit_btn.config(state="normal", bg="#2196F3", fg="white")
        self.back_btn.config(state="normal", bg="#E0E0E0")

        if self.is_network_error(message):
            if cleanup_successful:
                # 🚀 已经成功清除，用户可以重新填写
                messagebox.showinfo("提交失败", "网络连接超时，已**成功清除**本次作答记录，请检查网络后重试。",
                                    parent=self.win)
            else:
                # 🚀 清除失败，数据可能已存入，提示用户刷新主页查看
                messagebox.showinfo("提交失败",
                                    "网络连接不稳定，请稍后点击'提交问卷'按钮重试。（注意：由于网络原因，本次作答记录可能已部分存入，建议返回主页刷新查看问卷是否标记为'已填写'）",
                                    parent=self.win)
        else:
            # 业务逻辑错误/其他：弹出错误
            messagebox.showerror("提交失败", message, parent=self.win)

# ---------------------------
# 程序入口
# ---------------------------
if __name__ == "__main__":
    root = tk.Tk()
    UsernameWindow(root)
    root.mainloop()