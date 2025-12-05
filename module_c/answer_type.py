# survey_charts.py
"""
survey_charts.py

功能：
- 从 SQLite 数据库读取问卷回答数据并生成多类型图表（pie / bar / line）。
- 提供文件输出（PNG）和内存二进制输出（bytes）接口，方便 A/B 模块调用并返回图片。

依赖：
- matplotlib
- sqlite3
- typing
- io
- os
- datetime

说明：
- 适配数据库结构：Survey, Question, Option, Answer, Answer_survey_history
- 对选择题（有 Option 表）按选项统计；对文本题按文本频次统计。
- 折线图用于展示答卷随时间的变化（按日/小时聚合）。
"""

import sqlite3
from typing import List, Dict, Tuple, Optional
import os
import io
import matplotlib
# 使用无 GUI backend，便于服务器/无显示环境运行
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

# 默认数据库路径（根据你的项目位置调整）
DB_PATH = "database/survey_system.db"

# ========== 数据库读取辅助函数 ==========
def get_db(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # 启用外键（若未启）
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_question(survey_id: int, question_id: int, db_path: str = DB_PATH) -> Optional[sqlite3.Row]:
    conn = get_db(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM Question WHERE survey_id=? AND question_id=?", (survey_id, question_id))
    q = cur.fetchone()
    conn.close()
    return q

def get_options_for_question(question_id: int, db_path: str = DB_PATH) -> List[sqlite3.Row]:
    conn = get_db(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM Option WHERE question_id=? ORDER BY option_index", (question_id,))
    rows = cur.fetchall()
    conn.close()
    return list(rows)

def get_answers_for_question(survey_id: int, question_id: int, db_path: str = DB_PATH) -> List[str]:
    """
    返回该问题的所有 answer_content（原始文本）
    """
    conn = get_db(db_path)
    cur = conn.cursor()
    cur.execute("SELECT answer_content FROM Answer WHERE survey_id=? AND question_id=?", (survey_id, question_id))
    rows = cur.fetchall()
    conn.close()
    return [r["answer_content"] for r in rows]

def get_answer_history_counts_by_time(survey_id: int, db_path: str = DB_PATH, time_unit: str = "date") -> List[Tuple[str,int]]:
    """
    统计每个时间段（date/hour）收到答卷的数量，用于折线图。
    time_unit: "date" (YYYY-MM-DD) 或 "hour" (YYYY-MM-DD HH)
    返回按时间升序的 (time_str, count)
    """
    conn = get_db(db_path)
    cur = conn.cursor()
    if time_unit == "hour":
        cur.execute("""
            SELECT strftime('%Y-%m-%d %H', answered_at) as t, COUNT(*) as cnt
            FROM Answer_survey_history
            WHERE survey_id=?
            GROUP BY t
            ORDER BY t;
        """, (survey_id,))
    else:
        cur.execute("""
            SELECT strftime('%Y-%m-%d', answered_at) as t, COUNT(*) as cnt
            FROM Answer_survey_history
            WHERE survey_id=?
            GROUP BY t
            ORDER BY t;
        """, (survey_id,))
    rows = cur.fetchall()
    conn.close()
    return [(r["t"], r["cnt"]) for r in rows]

# ========== 数据聚合函数 ==========
def aggregate_choice_counts_by_option(survey_id: int, question_id: int, db_path: str = DB_PATH) -> Dict[str,int]:
    """
    如果 question 有 Option，则统计每个选项被选中的次数。
    返回：{option_text: count}
    注意：Answer.answer_content 可能是存 option_index 或 option_text（视你的写入方式）。
    这里做宽松匹配：优先匹配 option_index（字符串），否则匹配 option_text。
    """
    options = get_options_for_question(question_id, db_path)
    opt_map = {}  # map option_index_str -> option_text
    for opt in options:
        idx = str(opt["option_index"])
        opt_map[idx] = opt["option_text"]
        # also map full text to text (for exact-match storage)
        opt_map[opt["option_text"]] = opt["option_text"]

    answers = get_answers_for_question(survey_id, question_id, db_path)
    counts: Dict[str,int] = {opt["option_text"]: 0 for opt in options}

    for a in answers:
        if a is None:
            continue
        a_str = str(a).strip()
        # 多选场景：可能以逗号/分号/空格分隔多个选项 index 或文本
        parts = [p.strip() for p in a_str.replace(';', ',').split(',') if p.strip()]
        matched_any = False
        for p in parts:
            if p in opt_map:
                counts[opt_map[p]] = counts.get(opt_map[p], 0) + 1
                matched_any = True
            else:
                # 尝试按数字匹配
                if p.isdigit() and p in opt_map:
                    counts[opt_map[p]] = counts.get(opt_map[p], 0) + 1
                    matched_any = True
        if not matched_any:
            # 未匹配到选项，归类为 "其他"
            counts.setdefault("其他", 0)
            counts["其他"] += 1

    return counts

def aggregate_text_counts(survey_id: int, question_id: int, top_n: int = 10, db_path: str = DB_PATH) -> List[Tuple[str,int]]:
    """
    对文本题做词频/答案频率统计，返回 top_n 的 (answer_text, count)
    答案以原文完整匹配。若需要更细的文本处理（分词/归一化），可扩展。
    """
    answers = get_answers_for_question(survey_id, question_id, db_path)
    freq: Dict[str,int] = {}
    for a in answers:
        if a is None:
            continue
        key = a.strip()
        if key == "":
            continue
        freq[key] = freq.get(key, 0) + 1
    items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return items[:top_n]

# ========== 绘图函数 ==========
def _save_fig_to_path(fig: plt.Figure, out_path: str) -> str:
    directory = os.path.dirname(out_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    fig.savefig(out_path, bbox_inches='tight', dpi=150)
    plt.close(fig)
    return out_path

def _fig_to_png_bytes(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()

def generate_pie_chart_for_question(survey_id: int, question_id: int, out_path: Optional[str] = None,
                                    db_path: str = DB_PATH) -> bytes:
    """
    为指定问题生成饼图。若 out_path 提供，则会保存为文件并同时返回二进制。
    返回 PNG bytes（可供接口使用）。
    """
    q = get_question(survey_id, question_id, db_path)
    if not q:
        raise ValueError("问题不存在")

    # 若有选项，按选项统计；否则按文本统计 top N 并绘图
    opts = get_options_for_question(question_id, db_path)
    if opts:
        counts = aggregate_choice_counts_by_option(survey_id, question_id, db_path)
        labels = list(counts.keys())
        sizes = list(counts.values())
    else:
        items = aggregate_text_counts(survey_id, question_id, top_n=10, db_path=db_path)
        if not items:
            raise ValueError("没有可绘制的数据")
        labels = [it[0] for it in items]
        sizes = [it[1] for it in items]

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.set_title(f"{q['question_text']} (饼图)")

    if out_path:
        _save_fig_to_path(fig, out_path)
    return _fig_to_png_bytes(fig)

def generate_bar_chart_for_question(survey_id: int, question_id: int, out_path: Optional[str] = None,
                                    db_path: str = DB_PATH, horizontal: bool = False) -> bytes:
    """
    生成柱状图。返回 PNG bytes（并可保存文件）。
    """
    q = get_question(survey_id, question_id, db_path)
    if not q:
        raise ValueError("问题不存在")

    opts = get_options_for_question(question_id, db_path)
    if opts:
        counts = aggregate_choice_counts_by_option(survey_id, question_id, db_path)
        labels = list(counts.keys())
        values = list(counts.values())
    else:
        items = aggregate_text_counts(survey_id, question_id, top_n=15, db_path=db_path)
        if not items:
            raise ValueError("没有可绘制的数据")
        labels = [it[0] for it in items]
        values = [it[1] for it in items]

    fig, ax = plt.subplots(figsize=(8, max(4, len(labels)*0.4)))
    x = range(len(labels))
    if horizontal:
        ax.barh(x, values)
        ax.set_yticks(x)
        ax.set_yticklabels(labels)
        ax.set_xlabel("数量")
    else:
        ax.bar(x, values)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel("数量")
    ax.set_title(f"{q['question_text']} (柱状图)")

    plt.tight_layout()
    if out_path:
        _save_fig_to_path(fig, out_path)
    return _fig_to_png_bytes(fig)

def generate_line_chart_for_survey(survey_id: int, out_path: Optional[str] = None,
                                   db_path: str = DB_PATH, time_unit: str = "date") -> bytes:
    """
    生成问卷随时间的答卷数量折线图（按日或按小时）。
    time_unit: "date" 或 "hour"
    """
    data = get_answer_history_counts_by_time(survey_id, db_path=db_path, time_unit=time_unit)
    if not data:
        raise ValueError("没有答卷数据")

    times = [d[0] for d in data]
    counts = [d[1] for d in data]

    # x 轴为时间字符串，按顺序绘制折线
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(times, counts, marker='o')
    ax.set_xticks(times)
    ax.set_xticklabels(times, rotation=45, ha='right')
    ax.set_ylabel("答卷数量")
    ax.set_title(f"问卷 {survey_id} — 答卷数量随时间变化 ({time_unit})")
    plt.tight_layout()

    if out_path:
        _save_fig_to_path(fig, out_path)
    return _fig_to_png_bytes(fig)

# ========== 组合/便捷接口（A/B 模块可以直接调用） ==========
def save_chart_png_bytes(bytes_png: bytes, out_path: str) -> str:
    """把 PNG bytes 保存为文件并返回路径（便于复用）"""
    directory = os.path.dirname(out_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(bytes_png)
    return out_path

def get_chart_bytes(survey_id: int, question_id: Optional[int], chart_type: str,
                    out_path: Optional[str] = None, db_path: str = DB_PATH, **kwargs) -> bytes:
    """
    统一接口：根据 chart_type 生成图并返回 PNG bytes。
    - chart_type: "pie", "bar", "bar_h", "line_date", "line_hour"
    - question_id: 对于饼/柱图需要 question_id；对于 line 传 None
    - kwargs 传入额外参数（例如 top_n 等）
    如果 out_path 提供，生成后也会保存文件（并返回路径通过 save_chart_png_bytes）。
    """
    chart_type = chart_type.lower()
    if chart_type in ("pie",):
        if question_id is None:
            raise ValueError("pie chart requires question_id")
        png = generate_pie_chart_for_question(survey_id, question_id, out_path=out_path, db_path=db_path)
    elif chart_type in ("bar",):
        if question_id is None:
            raise ValueError("bar chart requires question_id")
        png = generate_bar_chart_for_question(survey_id, question_id, out_path=out_path, db_path=db_path, horizontal=False)
    elif chart_type in ("bar_h", "bar_horizontal"):
        if question_id is None:
            raise ValueError("bar_h chart requires question_id")
        png = generate_bar_chart_for_question(survey_id, question_id, out_path=out_path, db_path=db_path, horizontal=True)
    elif chart_type in ("line_date",):
        png = generate_line_chart_for_survey(survey_id, out_path=out_path, db_path=db_path, time_unit="date")
    elif chart_type in ("line_hour",):
        png = generate_line_chart_for_survey(survey_id, out_path=out_path, db_path=db_path, time_unit="hour")
    else:
        raise ValueError(f"未知 chart_type: {chart_type}")

    # 如果 out_path 指定但函数只返回 bytes（we already saved inside), return bytes anyhow.
    return png

# ========== 示例用法 ==========
if __name__ == "__main__":
    # 示例：请确保数据库路径正确，survey_id / question_id 存在
    survey_id_example = 1
    question_id_example = 1
    try:
        # 生成饼图并保存到 files/
        png = get_chart_bytes(survey_id_example, question_id_example, "pie")
        save_chart_png_bytes(png, "output/survey1_q1_pie.png")
        print("生成饼图：output/survey1_q1_pie.png")

        # 生成柱状图
        png = get_chart_bytes(survey_id_example, question_id_example, "bar")
        save_chart_png_bytes(png, "output/survey1_q1_bar.png")
        print("生成柱状图：output/survey1_q1_bar.png")

        # 生成折线图（按日）
        png = get_chart_bytes(survey_id_example, None, "line_date")
        save_chart_png_bytes(png, "output/survey1_line_date.png")
        print("生成折线图：output/survey1_line_date.png")
    except Exception as e:
        print("生成图表时出错：", e)
