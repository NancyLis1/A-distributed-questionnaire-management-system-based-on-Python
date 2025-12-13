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
# WordCloud 专用字体（Windows）
WC_FONT_PATH = r"C:/Windows/Fonts/simhei.ttf"


# =====================================================
# 路径配置：添加上级目录以导入 db_utils
# =====================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import db_utils  # 从上级目录导入

matplotlib.use("Agg")

# =====================================================
# 字体配置（简化版）
# =====================================================
# 设置中文显示
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False


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

    target_answers = []
    for q in summary['questions']:
        if q['question_id'] == question_id:
            for ans_obj in q['answers']:
                if ans_obj['answer']:
                    target_answers.append(str(ans_obj['answer']).strip())
            break
    return target_answers


def get_options_adapter(question_id: int) -> List[Dict]:
    raw_options = db_utils.get_question_options(question_id)
    options = []
    for idx, (opt_id, opt_text) in enumerate(raw_options):
        options.append({
            "option_text": opt_text,
            "option_index": idx + 1
        })
    return options


# =====================================================
# 词云与 TF-IDF
# =====================================================
SIMPLE_STOPWORDS = {
    '的', '是', '了', '和', '在', '我', '你', '它', '这', '那',
    '我们', '他们', '一个', '一种', '一些', '可以', '进行',
    '都', '也', '很', '非常', '没有'
}


def jieba_tokenizer(text: str) -> List[str]:
    words = jieba.lcut(text.lower())
    result = []

    for word in words:
        word = word.strip()
        if len(word) <= 1 or word in SIMPLE_STOPWORDS:
            continue

        if any('\u4e00' <= c <= '\u9fa5' for c in word):
            result.append(word)
        elif word.isalnum() and not word.isdigit():
            result.append(word)

    return result


def calculate_tfidf_weights(survey_id: int, question_id: int) -> Dict[str, float]:
    answers = get_answers_list_adapter(survey_id, question_id)
    if not answers:
        return {}

    # 1️⃣ 分词 + 拼接
    processed_answers = [" ".join(jieba_tokenizer(a)) for a in answers]

    # 2️⃣ 【关键修复点 1】
    # 过滤掉空字符串文档（否则会产生空 token）
    processed_answers = [p for p in processed_answers if p.strip()]

    # 如果过滤后已经没有任何有效文本，直接返回
    if not processed_answers:
        return {}

    vectorizer = TfidfVectorizer(
        tokenizer=lambda x: x.split(' '),
        lowercase=False,
        token_pattern=None
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(processed_answers)
    except ValueError:
        return {}

    if hasattr(vectorizer, 'get_feature_names_out'):
        feature_names = vectorizer.get_feature_names_out()
    else:
        feature_names = vectorizer.get_feature_names()

    if tfidf_matrix.shape[0] == 0:
        return {}

    tfidf_scores = tfidf_matrix.max(axis=0).toarray()[0]

    tfidf_dict = {}
    for word, score in zip(feature_names, tfidf_scores):
        # 3️⃣ 【关键修复点 2】
        # 显式过滤空特征名
        if word and score > 0:
            tfidf_dict[word] = score

    return dict(sorted(tfidf_dict.items(), key=lambda item: item[1], reverse=True))

def generate_tfidf_wordcloud(survey_id: int, question_id: int) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    if not q:
        raise ValueError("问题不存在")

    weights = calculate_tfidf_weights(survey_id, question_id)

    if not weights:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "数据不足或无有效文本，无法生成词云",
                ha="center", va="center", fontsize=12)
        ax.axis("off")
        return _fig_to_png(fig)

    wc = WordCloud(
        width=800,
        height=500,
        background_color="white",
        max_words=50,
        prefer_horizontal=0.9,
        font_path=WC_FONT_PATH  # 依赖 matplotlib 全局字体
    ).generate_from_frequencies(weights)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(f"{q['question_text']} (TF-IDF 词云图)")
    plt.tight_layout()
    return _fig_to_png(fig)


# =====================================================
# 选择题统计图
# =====================================================
def aggregate_choice_counts(survey_id: int, question_id: int):
    options = get_options_adapter(question_id)
    opt_map = {o["option_text"]: o["option_text"] for o in options}

    counts = {o["option_text"]: 0 for o in options}
    counts["其他"] = 0

    answers = get_answers_list_adapter(survey_id, question_id)

    for a in answers:
        parts = [p.strip() for p in a.replace(";", ",").split(",") if p.strip()]
        matched = False
        for p in parts:
            if p in opt_map:
                counts[p] += 1
                matched = True
        if not matched and parts:
            counts["其他"] += 1

    if counts["其他"] == 0:
        del counts["其他"]
    return counts


def generate_pie_chart(survey_id: int, question_id: int) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    counts = aggregate_choice_counts(survey_id, question_id)
    data = {k: v for k, v in counts.items() if v > 0}

    if not data:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "暂无数据", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    fig, ax = plt.subplots(figsize=(10, 8))
    wedges, _, _ = ax.pie(
        data.values(),
        autopct="%1.1f%%",
        startangle=90,
        radius=0.7
    )

    ax.legend(
        wedges,
        data.keys(),
        title="选项",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1)
    )

    ax.set_title(f"{q['question_text']} (饼图)")
    ax.axis("equal")
    return _fig_to_png(fig)


def generate_bar_chart(survey_id: int, question_id: int, horizontal=False) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    counts = aggregate_choice_counts(survey_id, question_id)
    data = {k: v for k, v in counts.items() if v > 0}

    if not data:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "暂无数据", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    labels = list(data.keys())
    values = list(data.values())
    x = range(len(labels))

    fig, ax = plt.subplots(figsize=(10, 6))
    if horizontal:
        ax.barh(x, values)
        ax.set_yticks(x)
        ax.set_yticklabels(labels)
    else:
        ax.bar(x, values)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")

    ax.set_title(f"{q['question_text']} (柱状图)")
    plt.tight_layout()
    return _fig_to_png(fig)


def generate_line_chart(survey_id: int, question_id: int) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    options = get_options_adapter(question_id)

    if not options:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "此题型不支持趋势图", ha="center")
        ax.axis("off")
        return _fig_to_png(fig)

    opt_texts = [o["option_text"] for o in options]
    answers = get_answers_list_adapter(survey_id, question_id)

    cumulative = {t: [0] for t in opt_texts}
    current = {t: 0 for t in opt_texts}

    for ans in answers:
        for t in opt_texts:
            if t in ans:
                current[t] += 1
            cumulative[t].append(current[t])

    fig, ax = plt.subplots(figsize=(10, 5))
    x_axis = range(len(answers) + 1)

    has_data = False
    for t in opt_texts:
        if max(cumulative[t]) > 0:
            ax.plot(x_axis, cumulative[t], label=t)
            has_data = True

    if has_data:
        ax.legend()
    else:
        ax.text(0.5, 0.5, "暂无数据", ha="center")

    ax.set_title(f"{q['question_text']} (趋势图)")
    ax.set_xlabel("答卷顺序")
    ax.set_ylabel("累计数量")
    plt.tight_layout()
    return _fig_to_png(fig)


# =====================================================
# 统一入口
# =====================================================
def get_chart_bytes(survey_id: int, question_id: Optional[int], chart_type: str) -> bytes:
    if question_id:
        q = get_question_adapter(survey_id, question_id)
        if not q:
            raise ValueError("问题不存在")
        q_type = q.get("question_type", "").lower()
    else:
        q_type = ""

    chart_type = chart_type.lower().strip()

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
            return generate_bar_chart(survey_id, question_id)
        if chart_type == "bar_h":
            return generate_bar_chart(survey_id, question_id, horizontal=True)
        if chart_type == "line_answer":
            return generate_line_chart(survey_id, question_id)

    raise ValueError(f"不支持的图表类型: {chart_type}")
