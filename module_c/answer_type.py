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
# 字体配置 (已修复优先级和 TTC 逻辑)
# =====================================================
def get_chinese_font():
    """获取系统中可用的中文字体"""
    system = platform.system()
    if system == "Windows":
        font_paths = [
            # 优先级调整，优先使用兼容性更好的字体
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/micross.ttf",
            "C:/Windows/Fonts/simhei.ttf",
        ]
    elif system == "Darwin":
        font_paths = [
            "/System/Library/Fonts/Supplemental/PingFang.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            # 规范化路径，避免路径格式问题
            return os.path.normpath(font_path)
    return None


# 获取原始字体路径
chinese_font_raw = get_chinese_font()

# 核心逻辑：生成 wordcloud 接受的 font_path 字符串
if chinese_font_raw and chinese_font_raw.lower().endswith('.ttc'):
    # 如果是 TTC 文件，WordCloud 要求格式为 "path/to/font.ttc,0"
    chinese_font_for_wc = f"{chinese_font_raw},0"
else:
    chinese_font_for_wc = chinese_font_raw

# Matplotlib 字体配置
if chinese_font_raw:
    font_name = os.path.basename(chinese_font_raw).split('.')[0]

    # 增加 Fallback 字体
    default_sans_serif = ['SimHei', 'Microsoft YaHei', 'SimSun']

    # 将找到的字体作为第一优先级
    plt.rcParams['font.sans-serif'] = [font_name] + [f for f in default_sans_serif if f not in font_name]
    plt.rcParams['axes.unicode_minus'] = False


def _fig_to_png(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    # 确保 bbox_inches="tight" 能够正确工作
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# =====================================================
# 数据适配层 (通过 db_utils 获取数据)
# ... (get_question_adapter, get_answers_list_adapter, get_options_adapter 保持不变)
# =====================================================
def get_question_adapter(survey_id: int, question_id: int):
    """
    通过 db_utils 获取问题详情。
    注意：db_utils.get_full_survey_detail 返回的是包含 questions 列表的字典。
    """
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
    """
    通过 db_utils 获取答案列表。
    注意：db_utils.get_survey_answers_summary 返回问卷的详细统计。
    """
    summary = db_utils.get_survey_answers_summary(survey_id)
    if not summary:
        return []

    target_answers = []
    for q in summary['questions']:
        if q['question_id'] == question_id:
            for ans_obj in q['answers']:
                # 过滤掉空答案
                if ans_obj['answer']:
                    target_answers.append(str(ans_obj['answer']).strip())
            break
    return target_answers


def get_options_adapter(question_id: int) -> List[Dict]:
    """
    通过 db_utils 获取选项。
    db_utils.get_question_options 返回 [(id, text), ...]
    """
    raw_options = db_utils.get_question_options(question_id)
    options = []
    for idx, (opt_id, opt_text) in enumerate(raw_options):
        options.append({
            "option_text": opt_text,
            "option_index": idx + 1
        })
    return options


# =====================================================
# 核心功能: 词云与分词 (已修复 A888 过滤问题)
# =====================================================

SIMPLE_STOPWORDS = set([
    '的', '是', '了', '和', '在', '我', '你', '它', '这', '那', '我们', '他们',
    '一个', '一种', '一些', '可以', '进行', '都', '也', '很', '非常', '没有'
])


def jieba_tokenizer(text: str) -> List[str]:
    words = jieba.lcut(text.lower())
    filtered_words = []
    for word in words:
        word = word.strip()

        # 1. 基础过滤：长度>1，不在停用词列表中
        if len(word) > 1 and word not in SIMPLE_STOPWORDS:

            # 2. 保留逻辑：满足以下任一条件则保留

            # a) 包含中文的词语，保留
            if any('\u4e00' <= char <= '\u9fa5' for char in word):
                filtered_words.append(word)

            # b) 字母/数字混合词或纯字母（例如：A888, apple）
            #    使用 isalnum() 检查字母数字，并排除纯数字
            elif word.isalnum() and not word.isdigit():
                filtered_words.append(word)

    return filtered_words


def calculate_tfidf_weights(survey_id: int, question_id: int) -> Dict[str, float]:
    answers = get_answers_list_adapter(survey_id, question_id)
    if not answers:
        return {}

    processed_answers = [" ".join(jieba_tokenizer(a)) for a in answers]
    # 检查是否所有答案都被过滤掉了
    if not any(processed_answers):
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
        # 兼容旧版本 scikit-learn
        feature_names = vectorizer.get_feature_names()

    if tfidf_matrix.shape[0] == 0:
        return {}

    tfidf_scores = tfidf_matrix.max(axis=0).toarray()[0]

    tfidf_dict = {}
    for word, score in zip(feature_names, tfidf_scores):
        if score > 0:
            tfidf_dict[word] = score

    return dict(sorted(tfidf_dict.items(), key=lambda item: item[1], reverse=True))


def generate_tfidf_wordcloud(survey_id: int, question_id: int) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    if not q:
        raise ValueError("问题不存在")

    tfidf_weights = calculate_tfidf_weights(survey_id, question_id)

    # 如果权重为空，生成一个包含提示信息的图片
    if not tfidf_weights:
        fig, ax = plt.subplots(figsize=(8, 4))
        # 依赖 plt.rcParams 设置的中文字体
        ax.text(0.5, 0.5, "数据不足或无有效文本，无法生成词云",
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        return _fig_to_png(fig)

    wc_params = {
        "width": 800,
        "height": 500,
        "background_color": "white",
        "max_words": 50,
        "prefer_horizontal": 0.9,
    }

    # 使用 wordcloud 专用的字体路径 (可能带 ,0 索引)
    if chinese_font_raw:
        wc_params["font_path"] = chinese_font_for_wc

    try:
        wc = WordCloud(**wc_params).generate_from_frequencies(tfidf_weights)
    except Exception as e:
        # 捕获字体配置错误，提供更清晰的提示
        if "TrueType" in str(e) or "resource" in str(e):
            raise RuntimeError(
                f"无法生成图表: 字体配置错误({chinese_font_for_wc})，请确认字体路径是否正确或尝试更换字体。") from e
        raise e

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(f"{q['question_text']} (TF-IDF 词云图)")
    plt.tight_layout()
    return _fig_to_png(fig)


# =====================================================
# 其他图表 (Pie, Bar, Line)
# =====================================================

def aggregate_choice_counts(survey_id: int, question_id: int):
    options = get_options_adapter(question_id)
    opt_map = {opt["option_text"]: opt["option_text"] for opt in options}

    counts = {opt["option_text"]: 0 for opt in options}
    counts["其他"] = 0

    answers = get_answers_list_adapter(survey_id, question_id)

    for a in answers:
        parts = [p.strip() for p in a.replace(";", ",").split(",") if p.strip()]
        matched_any = False
        for p in parts:
            if p in opt_map:
                counts[opt_map[p]] += 1
                matched_any = True

        if not matched_any and parts:
            counts["其他"] += 1

    if counts["其他"] == 0:
        del counts["其他"]
    return counts


def generate_pie_chart(survey_id: int, question_id: int) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    counts = aggregate_choice_counts(survey_id, question_id)
    non_zero = {k: v for k, v in counts.items() if v > 0}

    if not non_zero:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "暂无数据", ha='center', va='center')
        ax.axis('off')
        return _fig_to_png(fig)

    # 修复饼图尺寸和图例不显示的问题
    fig, ax = plt.subplots(figsize=(10, 8))

    wedges, texts, autotexts = ax.pie(
        non_zero.values(),
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.8,
        radius=0.7
    )

    ax.legend(
        wedges,
        non_zero.keys(),
        title="选项",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1)
    )

    ax.set_title(f"{q['question_text']} (饼图)", pad=20)
    ax.axis('equal')

    return _fig_to_png(fig)


def generate_bar_chart(survey_id: int, question_id: int, horizontal=False) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    counts = aggregate_choice_counts(survey_id, question_id)
    non_zero = {k: v for k, v in counts.items() if v > 0}

    if not non_zero:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "暂无数据", ha='center', va='center')
        ax.axis('off')
        return _fig_to_png(fig)

    labels = list(non_zero.keys())
    values = list(non_zero.values())

    # 调整figsize以容纳标签
    fig, ax = plt.subplots(figsize=(8, 5) if not horizontal else (10, 6))
    x = range(len(labels))

    if horizontal:
        ax.barh(x, values)
        ax.set_yticks(x)
        # 增加水平条形图的左侧空间，防止标签被截断
        ax.set_yticklabels(labels)
    else:
        ax.bar(x, values)
        ax.set_xticks(x)
        # 旋转标签以防止重叠
        ax.set_xticklabels(labels, rotation=45, ha='right')

    ax.set_title(f"{q['question_text']} (柱状图)")
    plt.tight_layout()
    return _fig_to_png(fig)


def generate_line_chart(survey_id: int, question_id: int) -> bytes:
    q = get_question_adapter(survey_id, question_id)
    options = get_options_adapter(question_id)

    if not options:
        # 如果不是选择题，不能生成 Line Answer
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "此题型不支持趋势图", ha='center')
        ax.axis('off')
        return _fig_to_png(fig)

    opt_texts = [o['option_text'] for o in options]
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

    if not has_data:
        ax.text(0.5, 0.5, "暂无数据", ha='center')
    else:
        ax.legend()

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
        q_type = q.get("question_type", "unknown").lower()
    else:
        q_type = "unknown"

    chart_type = chart_type.lower().strip()

    # 文本题 -> 词云
    if chart_type == "wordcloud":
        if q_type not in ("text", "textarea"):
            raise ValueError(f"类型 {q_type} 不支持词云，仅支持文本题")
        return generate_tfidf_wordcloud(survey_id, question_id)

    # 选择题 -> 统计图
    elif chart_type in ("pie", "bar", "bar_h", "line_answer"):
        if q_type not in ("choice", "radio", "checkbox", "slide"):
            raise ValueError(f"类型 {q_type} 不支持统计图，仅支持选择题")

        if chart_type == "pie":
            return generate_pie_chart(survey_id, question_id)
        elif chart_type == "bar":
            return generate_bar_chart(survey_id, question_id, horizontal=False)
        elif chart_type == "bar_h":
            return generate_bar_chart(survey_id, question_id, horizontal=True)
        elif chart_type == "line_answer":
            return generate_line_chart(survey_id, question_id)

    raise ValueError(f"不支持的图表类型: {chart_type}")