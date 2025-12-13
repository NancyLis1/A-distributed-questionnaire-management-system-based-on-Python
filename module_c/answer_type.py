import sys
import os
import io
import platform
import matplotlib
import matplotlib.pyplot as plt
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud
from typing import List, Dict, Optional

matplotlib.use("Agg")

# =====================================================
# 路径配置：添加上级目录以导入 db_utils
# =====================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import db_utils


# =====================================================
# 【统一字体策略】Matplotlib + WordCloud 多平台兜底
# =====================================================

# Matplotlib：简单、稳定
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False


def get_wc_font_path():
    """
    WordCloud 专用字体路径，多平台兜底
    """
    candidates = []

    system = platform.system()
    if system == "Windows":
        candidates = [
            r"C:/Windows/Fonts/simhei.ttf",
            r"C:/Windows/Fonts/msyh.ttc",
        ]
    elif system == "Darwin":
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
        ]
    else:  # Linux / Docker
        candidates = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        ]

    for p in candidates:
        if os.path.exists(p):
            return p
    return None


WC_FONT_PATH = get_wc_font_path()


def _fig_to_png(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# =====================================================
# 数据适配层
# =====================================================

def get_question_adapter(survey_id: int, question_id: int):
    full_data = db_utils.get_full_survey_detail(survey_id)
    if not full_data:
        return None

    for q in full_data['questions']:
        if q['question_id'] == question_id:
            return {
                "question_text": q['text'],
                "question_type": q['type']
            }
    return None


def get_answers_list_adapter(survey_id: int, question_id: int) -> List[str]:
    summary = db_utils.get_survey_answers_summary(survey_id)
    if not summary:
        return []

    answers = []
    for q in summary['questions']:
        if q['question_id'] == question_id:
            for a in q['answers']:
                if a['answer']:
                    answers.append(str(a['answer']).strip())
            break
    return answers


def get_options_adapter(question_id: int) -> List[Dict]:
    raw = db_utils.get_question_options(question_id)
    return [{"option_text": t, "option_index": i + 1} for i, (_, t) in enumerate(raw)]


# =====================================================
# 词云 / TF-IDF 核心逻辑（已彻底修复）
# =====================================================

SIMPLE_STOPWORDS = {
    '的', '是', '了', '和', '在', '我', '你', '它', '这', '那',
    '我们', '他们', '一个', '一种', '一些', '可以', '进行',
    '都', '也', '很', '非常', '没有'
}


def jieba_tokenizer(text: str) -> List[str]:
    words = jieba.lcut(text.lower())
    results = []

    for w in words:
        w = w.strip()
        if len(w) <= 1 or w in SIMPLE_STOPWORDS:
            continue

        # 中文
        if any('\u4e00' <= c <= '\u9fa5' for c in w):
            results.append(w)

        # 字母 / 字母数字混合（如 A888）
        elif w.isalnum() and not w.isdigit():
            results.append(w)

    return results


def calculate_tfidf_weights(survey_id: int, question_id: int) -> Dict[str, float]:
    answers = get_answers_list_adapter(survey_id, question_id)
    if not answers:
        return {}

    processed = [" ".join(jieba_tokenizer(a)) for a in answers]

    # ⭐ 关键修复 1：过滤空文本
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
        # ⭐ 关键修复 2：过滤空 token
        if word and score > 0:
            tfidf_dict[word] = score

    return dict(sorted(tfidf_dict.items(), key=lambda x: x[1], reverse=True))


def generate_tfidf_wordcloud(survey_id: int, question_id: int) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    answers = get_answers_list_adapter(survey_id, question_id)

    # 无人作答
    if not answers:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "暂无作答，无法生成词云", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    tfidf_weights = calculate_tfidf_weights(survey_id, question_id)

    # 作答存在，但无语义内容
    if not tfidf_weights:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(
            0.5, 0.5,
            "回答内容过于简短或无语义，无法生成词云",
            ha="center", va="center"
        )
        ax.axis("off")
        return _fig_to_png(fig)

    wc_params = dict(
        width=800,
        height=500,
        background_color="white",
        max_words=50,
        prefer_horizontal=0.9,
    )

    if WC_FONT_PATH:
        wc_params["font_path"] = WC_FONT_PATH

    wc = WordCloud(**wc_params).generate_from_frequencies(tfidf_weights)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(f"{q['question_text']}（词云）")
    return _fig_to_png(fig)


# =====================================================
# 选择题统计图
# =====================================================

def aggregate_choice_counts(survey_id: int, question_id: int):
    options = get_options_adapter(question_id)
    counts = {o["option_text"]: 0 for o in options}
    counts["其他"] = 0

    answers = get_answers_list_adapter(survey_id, question_id)

    for a in answers:
        parts = [p.strip() for p in a.replace(";", ",").split(",") if p.strip()]
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


def generate_pie_chart(survey_id: int, question_id: int) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    counts = {k: v for k, v in aggregate_choice_counts(survey_id, question_id).items() if v > 0}

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


def generate_bar_chart(survey_id: int, question_id: int, horizontal=False) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    counts = {k: v for k, v in aggregate_choice_counts(survey_id, question_id).items() if v > 0}

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


def generate_line_chart(survey_id: int, question_id: int) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    options = get_options_adapter(question_id)
    answers = get_answers_list_adapter(survey_id, question_id)

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
# 统一入口
# =====================================================

def get_chart_bytes(survey_id: int, question_id: Optional[int], chart_type: str) -> bytes:
    q = get_question_adapter(survey_id, question_id) if question_id else None
    q_type = q["question_type"].lower() if q else "unknown"

    chart_type = chart_type.lower()

    if chart_type == "wordcloud":
        if q_type not in ("text", "textarea"):
            raise ValueError("仅文本题支持词云")
        return generate_tfidf_wordcloud(survey_id, question_id)

    if chart_type in ("pie", "bar", "bar_h", "line_answer"):
        if q_type not in ("choice", "radio", "checkbox", "slide"):
            raise ValueError("仅选择题支持统计图")

        if chart_type == "pie":
            return generate_pie_chart(survey_id, question_id)
        if chart_type == "bar":
            return generate_bar_chart(survey_id, question_id, False)
        if chart_type == "bar_h":
            return generate_bar_chart(survey_id, question_id, True)
        if chart_type == "line_answer":
            return generate_line_chart(survey_id, question_id)

    raise ValueError(f"不支持的图表类型：{chart_type}")
