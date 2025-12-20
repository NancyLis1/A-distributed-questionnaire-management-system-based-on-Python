import sys
import os
import io
import platform
import matplotlib
import matplotlib.pyplot as plt
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List, Dict, Optional
import socket # 引入 socket 类型提示，虽然是 Optional[object]

matplotlib.use("Agg")

# =====================================================
# 路径配置：添加上级目录以导入 db_proxy
# =====================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# -----------------------------------------------
# 关键修正 1: 替换导入 db_utils 为 db_proxy
# -----------------------------------------------
try:
    import db_proxy
except ImportError:
    print("导入 db_proxy 失败，请确保 db_proxy.py 文件存在于正确的路径。")
    sys.exit(1)


# =====================================================
# 【统一字体策略】Matplotlib + WordCloud 多平台兜底 (保持不变)
# =====================================================

# Matplotlib：简单、稳定
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

def _fig_to_png(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# =====================================================
# 数据适配层 - 【关键修正 2: 添加 sock 参数，修改调用】
# =====================================================

def get_question_adapter(survey_id: int, question_id: int, sock: Optional[socket.socket] = None):
    # -----------------------------------------------
    # 关键修正 3: 使用 db_proxy
    # -----------------------------------------------
    full_data = db_proxy.get_full_survey_detail(sock, survey_id)
    if not full_data:
        return None

    for q in full_data['questions']:
        if q['question_id'] == question_id:
            return {
                "question_text": q['text'],
                "question_type": q['type']
            }
    return None


def get_answers_list_adapter(survey_id: int, question_id: int, sock: Optional[socket.socket] = None) -> List[str]:
    # -----------------------------------------------
    # 关键修正 3: 使用 db_proxy
    # -----------------------------------------------
    summary = db_proxy.get_survey_answers_summary(sock, survey_id)
    if not summary:
        return []

    answers = []
    for q in summary['questions']:
        if q['question_id'] == question_id:
            for a in q['answers']:
                # 兼容可能的键名或结构
                answer_content = a.get('answer', a.get('answer_content'))
                if answer_content:
                    answers.append(str(answer_content).strip())
            break
    return answers


def get_options_adapter(question_id: int, sock: Optional[socket.socket] = None) -> List[Dict]:
    raw = db_proxy.get_question_options(sock, question_id)
    if not raw:
        return []

    processed_options = []
    for i, item in enumerate(raw):
        option_text = ""

        # 情况 1: 元组格式 (id, text)
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            option_text = item[1]

        # 情况 2: 字典格式 (最可能出问题的地方)
        elif isinstance(item, dict):
            # 尝试所有可能的后端字段名
            option_text = (item.get('option_text') or
                           item.get('content') or
                           item.get('text') or
                           item.get('option_content') or "")

        # 情况 3: 直接是字符串
        elif isinstance(item, str):
            option_text = item

        if option_text:
            processed_options.append({
                "option_text": str(option_text).strip(),
                "option_index": i + 1
            })

    return processed_options
# =====================================================
# TF-IDF 核心逻辑
# =====================================================

SIMPLE_STOPWORDS = {
    '的', '是', '了', '和', '在', '我', '你', '它', '这', '那',
    '我们', '他们', '一个', '一种', '一些', '可以', '进行',
    '都', '也', '很', '非常', '没有'
}


def jieba_tokenizer(text: str) -> List[str]:
    # 1. 清洗数据：去除首尾空格
    clean_text = text.strip()

    # 2. 过滤掉空字符串（防止空回答干扰统计）
    if not clean_text:
        return []

    # 3. 返回包含完整文本的列表，不再拆分“付”和“美育”
    return [clean_text]


def calculate_tfidf_weights(survey_id: int, question_id: int, sock: Optional[socket.socket] = None) -> Dict[str, float]:
    """计算 TF-IDF 权重"""
    answers = get_answers_list_adapter(survey_id, question_id, sock=sock)
    if not answers:
        return {}

    processed = [" ".join(jieba_tokenizer(a)) for a in answers]

    processed = [p for p in processed if p.strip()]
    if not processed:
        return {}

    vectorizer = TfidfVectorizer(
        tokenizer=lambda x: x.split(" "),
        lowercase=False,
        token_pattern=None
    )

    try:
        tfidf = vectorizer.fit_transform(processed)
    except ValueError:
        return {}

    feature_names = (
        vectorizer.get_feature_names_out()
        if hasattr(vectorizer, "get_feature_names_out")
        else vectorizer.get_feature_names()
    )

    scores = tfidf.max(axis=0).toarray()[0]

    tfidf_dict = {}
    for word, score in zip(feature_names, scores):
        if word and score > 0:
            tfidf_dict[word] = score

    return dict(sorted(tfidf_dict.items(), key=lambda x: x[1], reverse=True))

def get_text_tfidf_list(survey_id: int, question_id: int, sock: Optional[socket.socket] = None) -> str:
    """
    计算文本题的 TF-IDF 权重，并返回格式化的纯文本报告。
    """
    tfidf_weights = calculate_tfidf_weights(survey_id, question_id, sock=sock)
    answers = get_answers_list_adapter(survey_id, question_id, sock=sock)

    if not answers:
        return "暂无作答内容。"

    if not tfidf_weights:
        return "回答内容过于简短或无语义，无法生成分析报告。"

    # 格式化输出为字符串
    output_lines = ["--- 文本题词频分析报告 (TF-IDF 权重降序) ---"]
    output_lines.append(f"总有效回答数: {len(answers)}")
    output_lines.append("------------------------------------------------")

    for i, (word, score) in enumerate(tfidf_weights.items()):
        if i >= 50:  # 限制输出前 50 个高频词
            break
        output_lines.append(f"【{word}】: 权重 {score:.4f}")

    report_str = "\n".join(output_lines)
    return report_str.encode('utf-8')


# =====================================================
# 选择题统计图 (修改调用)
# =====================================================

def aggregate_choice_counts(survey_id: int, question_id: int, sock: Optional[socket.socket] = None):
    # 1. 获取问题类型
    q = get_question_adapter(survey_id, question_id, sock=sock)
    q_type = q["question_type"].lower() if q else "unknown"

    # 2. 获取选项列表
    options_text_list = []
    if q_type == "slider":
        # 针对 Slider 题型，强制使用 1 到 10 的选项文本
        options_text_list = [str(i) for i in range(1, 11)]
    else:
        # 其他题型，从数据库获取选项
        options = get_options_adapter(question_id, sock=sock)
        options_text_list = [o["option_text"] for o in options]
        for o in options:
            # 兼容多种可能的字段名：option_text, content, text
            text = o.get("option_text") or o.get("content") or o.get("text")
            if text:
                options_text_list.append(str(text).strip())

    # 3. 初始化计数器
    counts = {o: 0 for o in options_text_list}
    counts["其他"] = 0

    answers = get_answers_list_adapter(survey_id, question_id, sock=sock)
    for a in answers:
        parts = [p.strip() for p in a.replace(";", ",").split(",") if p.strip()]

        if q_type == "slider" and len(parts) == 1 and parts[0] in counts:
            counts[parts[0]] += 1
            continue  # 处理下一个回答

        # 兼容 choice/checkbox 的逻辑
        matched = False
        for p in parts:
            if p in counts:
                counts[p] += 1
                matched = True
        if not matched and parts:
            counts["其他"] += 1

    if counts["其他"] == 0:
        del counts["其他"]
    return counts

def generate_pie_chart(survey_id: int, question_id: int, sock: Optional[socket.socket] = None) -> bytes:
    # -----------------------------------------------
    # 关键修正 3: 传递 sock
    # -----------------------------------------------
    q = get_question_adapter(survey_id, question_id, sock=sock)
    counts = {k: v for k, v in aggregate_choice_counts(survey_id, question_id, sock=sock).items() if v > 0}
    if not counts:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "暂无数据", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    fig, ax = plt.subplots(figsize=(10, 8))
    wedges, *_ = ax.pie(counts.values(), autopct="%1.1f%%", startangle=90)
    ax.legend(wedges, counts.keys(), loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    ax.set_title(f"{q['question_text']}（饼图）")
    ax.axis("equal")
    return _fig_to_png(fig)


def generate_bar_chart(survey_id: int, question_id: int, horizontal: bool = False, sock: Optional[socket.socket] = None) -> bytes:
    # -----------------------------------------------
    # 关键修正 3: 传递 sock
    # -----------------------------------------------
    q = get_question_adapter(survey_id, question_id, sock=sock)
    counts = {k: v for k, v in aggregate_choice_counts(survey_id, question_id, sock=sock).items() if v > 0}

    if not counts:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "暂无数据", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    labels = list(counts.keys())
    values = list(counts.values())

    fig, ax = plt.subplots(figsize=(10, 6))
    if horizontal:
        ax.barh(labels, values)
    else:
        ax.bar(labels, values)
        ax.set_xticklabels(labels, rotation=45, ha="right")

    ax.set_title(f"{q['question_text']}（柱状图）")
    plt.tight_layout()
    return _fig_to_png(fig)


def generate_line_chart(survey_id: int, question_id: int, sock: Optional[socket.socket] = None) -> bytes:
    # -----------------------------------------------
    # 关键修正 3: 传递 sock
    # -----------------------------------------------
    q = get_question_adapter(survey_id, question_id, sock=sock)
    options = get_options_adapter(question_id, sock=sock)
    answers = get_answers_list_adapter(survey_id, question_id, sock=sock)

    if not options:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "此题型不支持趋势图", ha="center")
        ax.axis("off")
        return _fig_to_png(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(answers) + 1)

    for o in options:
        t = o["option_text"]
        y = [0]
        c = 0
        for a in answers:
            if t in a:
                c += 1
            y.append(c)
        if max(y) > 0:
            ax.plot(x, y, label=t)

    if ax.lines:
        ax.legend()
    else:
        ax.text(0.5, 0.5, "暂无数据", ha="center")

    ax.set_title(f"{q['question_text']}（趋势图）")
    return _fig_to_png(fig)


# =====================================================
# 统一入口 - 【关键修正 4: 添加 sock 参数】
# =====================================================

def get_chart_bytes(survey_id: int, question_id: Optional[int], chart_type: str, sock: Optional[socket.socket] = None) -> bytes:

    q = get_question_adapter(survey_id, question_id, sock=sock) if question_id else None
    q_type = q["question_type"].lower() if q else "unknown"

    chart_type = chart_type.lower()

    if chart_type == "text_answer":
        if q_type not in ("text", "textarea"):
            raise ValueError("仅文本题支持text_answer")
        return get_text_tfidf_list(survey_id, question_id, sock=sock)
        return result.encode('utf-8') if isinstance(result, str) else result

    if chart_type in ("pie", "bar", "bar_h", "line_answer"):
        if q_type not in ("choice", "radio", "checkbox", "slider"):
            raise ValueError("仅选择题支持统计图")

        if chart_type == "pie":
            return generate_pie_chart(survey_id, question_id, sock=sock)
        if chart_type == "bar":
            return generate_bar_chart(survey_id, question_id, False, sock=sock)
        if chart_type == "bar_h":
            return generate_bar_chart(survey_id, question_id, True, sock=sock)
        if chart_type == "line_answer":
            return generate_line_chart(survey_id, question_id, sock=sock)

    raise ValueError(f"不支持的图表类型：{chart_type}")