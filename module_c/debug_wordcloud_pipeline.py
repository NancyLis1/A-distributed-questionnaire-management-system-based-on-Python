"""
专用调试：检查词云为什么生成不了
不会影响主程序
"""

from answer_type import (
    get_answers_list_adapter,
    jieba_tokenizer,
    calculate_tfidf_weights
)


def debug_wordcloud(survey_id: int, question_id: int):
    print("=" * 60)
    print(f"[DEBUG] survey_id={survey_id}, question_id={question_id}")
    print("=" * 60)

    # 1️⃣ 原始答案
    answers = get_answers_list_adapter(survey_id, question_id)
    print(f"\n[1] 原始答案数量: {len(answers)}")
    for i, a in enumerate(answers[:10], 1):
        print(f"  {i}. {repr(a)}")

    # 2️⃣ 分词结果
    print("\n[2] 分词 & 过滤结果:")
    processed = []
    for a in answers:
        tokens = jieba_tokenizer(a)
        processed.append(tokens)
        print(f"  原文: {repr(a)}")
        print(f"  分词: {tokens}")

    # 3️⃣ TF-IDF 输入文本
    joined = [" ".join(t) for t in processed]
    print("\n[3] TF-IDF 实际输入:")
    for j in joined:
        print(f"  {repr(j)}")

    # 4️⃣ 是否全部为空
    empty_count = sum(1 for j in joined if not j.strip())
    print(f"\n[4] 空文本条数: {empty_count}/{len(joined)}")

    # 5️⃣ TF-IDF 权重
    weights = calculate_tfidf_weights(survey_id, question_id)
    print("\n[5] TF-IDF 权重 Top 20:")
    if not weights:
        print("  ❌ 权重为空")
    else:
        for i, (k, v) in enumerate(list(weights.items())[:20], 1):
            print(f"  {i}. {k} -> {v:.4f}")

    print("\n[DEBUG END]")
    print("=" * 60)


if __name__ == "__main__":
    # 🔴 把这里换成你实际的 survey_id / question_id
    debug_wordcloud(survey_id=1, question_id=1)
