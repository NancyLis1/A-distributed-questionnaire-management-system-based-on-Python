# admin_sqlite_browser.py
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import List, Tuple, Optional

DB_PATH_DEFAULT = None

class AdminSQLiteBrowser:
    def __init__(self, db_path: str = DB_PATH_DEFAULT):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

        # 初始化 GUI
        self.root = tk.Tk()
        self.root.title("SQLite 管理浏览器")
        self.root.geometry("1000x700")

        # 顶部按钮
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(top_frame, text="打开数据库", command=self.open_db).pack(side=tk.LEFT)
        tk.Button(top_frame, text="刷新表列表", command=self.refresh_tables).pack(side=tk.LEFT)
        tk.Button(top_frame, text="添加行", command=self.add_row).pack(side=tk.LEFT)
        tk.Button(top_frame, text="编辑选中行", command=self.edit_row).pack(side=tk.LEFT)
        tk.Button(top_frame, text="删除选中行", command=self.delete_row).pack(side=tk.LEFT)
        tk.Button(top_frame, text="执行SQL", command=self.exec_sql_dialog).pack(side=tk.LEFT)

        # 左侧表列表
        left_frame = tk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        tk.Label(left_frame, text="表列表").pack()
        self.table_listbox = tk.Listbox(left_frame, width=30)
        self.table_listbox.pack(fill=tk.Y, expand=True)
        self.table_listbox.bind("<<ListboxSelect>>", self.show_table_data)

        # 右侧表数据
        right_frame = tk.Frame(self.root)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        header = tk.Label(right_frame, text="表数据", font=("Arial", 12, "bold"))
        header.pack(anchor="w")
        self.tree = ttk.Treeview(right_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)
        # 允许多列水平滚动
        self.hscroll = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.hscroll.pack(fill=tk.X)
        self.tree.configure(xscrollcommand=self.hscroll.set)

        # 状态栏
        self.status_var = tk.StringVar(value="未连接数据库")
        status_bar = tk.Label(self.root, textvariable=self.status_var, anchor="w")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.root.mainloop()

    # ---------- DB 操作 ----------
    def open_db(self):
        path = filedialog.askopenfilename(title="选择 SQLite 数据库文件", filetypes=[("SQLite DB", "*.db;*.sqlite;*.sqlite3"), ("All files", "*.*")])
        if path:
            self.db_path = path
            try:
                if self.conn:
                    self.conn.close()
                self.conn = sqlite3.connect(self.db_path)
                # 使用 row factory 以便更容易处理列
                self.conn.row_factory = sqlite3.Row
                self.status_var.set(f"已连接: {self.db_path}")
                messagebox.showinfo("成功", f"已连接数据库: {self.db_path}")
                self.refresh_tables()
            except Exception as e:
                messagebox.showerror("错误", str(e))

    def refresh_tables(self):
        if not self.conn:
            return
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        self.table_listbox.delete(0, tk.END)
        for t in tables:
            self.table_listbox.insert(tk.END, t)

    def get_table_columns(self, table_name: str) -> List[Tuple]:
        """返回 PRAGMA table_info 结果的列表（cid, name, type, notnull, dflt_value, pk）"""
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        return cursor.fetchall()

    def get_primary_key_column(self, table_name: str) -> Optional[str]:
        cols = self.get_table_columns(table_name)
        for col in cols:
            # col[5] 是 pk 标志（0/1/序号）
            if col[5] and col[5] > 0:
                return col[1]
        return None

    # ---------- 显示数据 ----------
    def show_table_data(self, event=None):
        if not self.conn:
            return
        selection = self.table_listbox.curselection()
        if not selection:
            return
        table_name = self.table_listbox.get(selection[0])
        cols_info = self.get_table_columns(table_name)
        columns = [col[1] for col in cols_info]

        # 清空旧数据并设置新列
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns
        self.tree["show"] = "headings"

        # 设置列头
        for col in columns:
            self.tree.heading(col, text=col)
            # 以文本形式显示列
            self.tree.column(col, width=120, anchor="w")

        # 查询数据并插入
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1000;")
            rows = cursor.fetchall()
            for r in rows:
                values = [r[col] for col in columns]
                self.tree.insert("", tk.END, values=values)
            self.status_var.set(f"表 {table_name} 共 {len(rows)} 条（显示最多1000条）")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # ---------- 添加行 ----------
    def add_row(self):
        if not self.conn:
            messagebox.showwarning("未连接", "请先打开数据库。")
            return
        selection = self.table_listbox.curselection()
        if not selection:
            messagebox.showwarning("未选择表", "请先选择一个表。")
            return
        table_name = self.table_listbox.get(selection[0])
        cols_info = self.get_table_columns(table_name)

        # 构造输入对话框
        dlg = RowEditorDialog(self.root, title=f"添加到 {table_name}", cols_info=cols_info, is_edit=False)
        if dlg.result is None:
            return  # 取消
        col_names, values = dlg.result

        placeholders = ", ".join(["?"] * len(values))
        cols_sql = ", ".join(col_names)
        sql = f"INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders});"

        try:
            cur = self.conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute(sql, values)
            self.conn.commit()
            messagebox.showinfo("成功", "添加完成")
            self.show_table_data()
        except Exception as e:
            messagebox.showerror("插入错误", str(e))
            self.conn.rollback()

    # ---------- 编辑行 ----------
    def edit_row(self):
        if not self.conn:
            messagebox.showwarning("未连接", "请先打开数据库。")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("未选择行", "请先在右侧选择一行需要编辑的记录。")
            return
        selection = self.table_listbox.curselection()
        table_name = self.table_listbox.get(selection[0])
        cols_info = self.get_table_columns(table_name)
        columns = [col[1] for col in cols_info]

        # 取选中行的值
        item = self.tree.item(sel[0])
        values = item["values"]

        # 找到主键列，以便作为 WHERE 条件（如果没有主键，将使用整行匹配）
        pk_col = self.get_primary_key_column(table_name)
        pk_value = None
        if pk_col:
            try:
                pk_index = columns.index(pk_col)
                pk_value = values[pk_index]
            except ValueError:
                pk_value = None

        dlg = RowEditorDialog(self.root, title=f"编辑 {table_name}", cols_info=cols_info, is_edit=True, initial_values=values)
        if dlg.result is None:
            return
        col_names, new_values = dlg.result

        # 构建更新 SQL
        set_parts = ", ".join([f"{c}=?" for c in col_names])
        if pk_col and pk_value is not None:
            sql = f"UPDATE {table_name} SET {set_parts} WHERE {pk_col} = ?;"
            params = tuple(new_values) + (pk_value,)
        else:
            # 如果没有主键，只能用全部列匹配原值来定位（风险较高）
            where_parts = " AND ".join([f"{c} IS ?" for c in columns])
            sql = f"UPDATE {table_name} SET {set_parts} WHERE {where_parts};"
            params = tuple(new_values) + tuple(values)

        try:
            cur = self.conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute(sql, params)
            self.conn.commit()
            messagebox.showinfo("成功", "更新完成")
            self.show_table_data()
        except Exception as e:
            messagebox.showerror("更新错误", str(e))
            self.conn.rollback()

    # ---------- 删除行 ----------
    def delete_row(self):
        if not self.conn:
            messagebox.showwarning("未连接", "请先打开数据库。")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("未选择行", "请先在右侧选择一行需要删除的记录。")
            return
        selection = self.table_listbox.curselection()
        table_name = self.table_listbox.get(selection[0])
        cols_info = self.get_table_columns(table_name)
        columns = [col[1] for col in cols_info]

        # 取选中行的值
        item = self.tree.item(sel[0])
        values = item["values"]

        pk_col = self.get_primary_key_column(table_name)
        if pk_col:
            pk_index = columns.index(pk_col)
            pk_value = values[pk_index]
            confirm = messagebox.askyesno("确认删除", f"确认删除 {table_name} 中主键 {pk_col}={pk_value} 的记录？")
            if not confirm:
                return
            sql = f"DELETE FROM {table_name} WHERE {pk_col} = ?;"
            params = (pk_value,)
        else:
            # 没有主键则用整行匹配（谨慎）
            confirm = messagebox.askyesno("确认删除", f"表 {table_name} 无显式主键，将根据整行匹配删除。继续？")
            if not confirm:
                return
            where_parts = " AND ".join([f"{c} IS ?" for c in columns])
            sql = f"DELETE FROM {table_name} WHERE {where_parts};"
            params = tuple(values)

        try:
            cur = self.conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute(sql, params)
            self.conn.commit()
            messagebox.showinfo("成功", "删除完成")
            self.show_table_data()
        except Exception as e:
            messagebox.showerror("删除错误", str(e))
            self.conn.rollback()

    # ---------- 执行任意 SQL（管理员） ----------
    def exec_sql_dialog(self):
        if not self.conn:
            messagebox.showwarning("未连接", "请先打开数据库。")
            return
        sql = simpledialog.askstring("执行 SQL", "输入要执行的 SQL（仅限 DML/DDL）:")
        if not sql:
            return
        try:
            cur = self.conn.cursor()
            cur.executescript(sql)
            self.conn.commit()
            messagebox.showinfo("执行完成", "SQL 已执行")
            self.refresh_tables()
            self.show_table_data()
        except Exception as e:
            messagebox.showerror("执行错误", str(e))
            self.conn.rollback()

# ---------- 行编辑对话框 ----------
class RowEditorDialog(tk.Toplevel):
    def __init__(self, parent, title: str, cols_info: List[sqlite3.Row], is_edit: bool = False, initial_values: List = None):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.cols_info = cols_info
        self.is_edit = is_edit
        self.initial_values = initial_values or []

        self.inputs = []  # (col_name, entry_widget, readonly_flag)

        frm = tk.Frame(self)
        frm.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        for idx, col in enumerate(cols_info):
            cid, name, ctype, notnull, dflt_value, pk = col
            # 跳过自增主键（如果是 pk 且没有默认值且通常是 autoincrement）
            skip = False
            if pk and pk > 0:
                # 如果是主键且没有默认值，通常不需要手动填写
                skip = True

            if skip and not self.is_edit:
                continue

            lbl = tk.Label(frm, text=f"{name} ({ctype})")
            lbl.grid(row=len(self.inputs), column=0, sticky="w", pady=3)
            ent = tk.Entry(frm, width=60)
            ent.grid(row=len(self.inputs), column=1, pady=3, padx=5)
            # 填初始值（编辑时）
            if self.is_edit and self.initial_values:
                try:
                    ent.insert(0, str(self.initial_values[idx]))
                except Exception:
                    # 索引可能不匹配（因为跳过了主键），就按顺序填
                    pass
            self.inputs.append((name, ent, bool(pk)))

        btn_frm = tk.Frame(self)
        btn_frm.pack(fill=tk.X, pady=5)
        tk.Button(btn_frm, text="确认", command=self.on_confirm).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frm, text="取消", command=self.on_cancel).pack(side=tk.LEFT, padx=5)

        self.grab_set()
        self.wait_window(self)

    def on_confirm(self):
        col_names = []
        values = []
        for name, ent, is_pk in self.inputs:
            col_names.append(name)
            values.append(ent.get() if ent.get() != "" else None)
        self.result = (col_names, values)
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

if __name__ == "__main__":
    AdminSQLiteBrowser()
