# sqlite_gui_browser.py
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class SQLiteBrowser:
    def __init__(self, db_path=None):
        self.db_path = db_path
        self.conn = None

        # 初始化 GUI
        self.root = tk.Tk()
        self.root.title("SQLite 浏览器")
        self.root.geometry("800x600")

        # 顶部按钮
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(top_frame, text="打开数据库", command=self.open_db).pack(side=tk.LEFT)
        tk.Button(top_frame, text="刷新表列表", command=self.refresh_tables).pack(side=tk.LEFT)

        # 左侧表列表
        left_frame = tk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        tk.Label(left_frame, text="表列表").pack()
        self.table_listbox = tk.Listbox(left_frame)
        self.table_listbox.pack(fill=tk.Y, expand=True)
        self.table_listbox.bind("<<ListboxSelect>>", self.show_table_data)

        # 右侧表数据
        right_frame = tk.Frame(self.root)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        tk.Label(right_frame, text="表数据").pack()
        self.tree = ttk.Treeview(right_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.root.mainloop()

    def open_db(self):
        path = filedialog.askopenfilename(title="选择 SQLite 数据库文件", filetypes=[("SQLite DB", "*.db")])
        if path:
            self.db_path = path
            try:
                if self.conn:
                    self.conn.close()
                self.conn = sqlite3.connect(self.db_path)
                messagebox.showinfo("成功", f"已连接数据库: {self.db_path}")
                self.refresh_tables()
            except Exception as e:
                messagebox.showerror("错误", str(e))

    def refresh_tables(self):
        if not self.conn:
            return
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        self.table_listbox.delete(0, tk.END)
        for t in tables:
            self.table_listbox.insert(tk.END, t)

    def show_table_data(self, event):
        if not self.conn:
            return
        selection = self.table_listbox.curselection()
        if not selection:
            return
        table_name = self.table_listbox.get(selection[0])
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [col[1] for col in cursor.fetchall()]

        # 清空旧数据
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns
        self.tree["show"] = "headings"
        for col in columns:
            self.tree.heading(col, text=col)

        try:
            cursor.execute(f"SELECT * FROM {table_name};")
            for row in cursor.fetchall():
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("错误", str(e))

if __name__ == "__main__":
    SQLiteBrowser()
