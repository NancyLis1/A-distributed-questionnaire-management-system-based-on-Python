import io
import sys
import os
from PIL import Image, ImageTk
from typing import Optional  # 引入 Optional 用于类型注解

# 确保能引用到同级目录的 answer_type
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from answer_type import get_chart_bytes

# 配置常量：哪些图表需要 Question ID
CHART_TYPES_NEED_QUESTION_ID = {
    "pie", "bar", "bar_h", "line_answer", "wordcloud"
}


def generate_chart_image(survey_id: int, question_id: int, chart_type: str,
                         sock: Optional[object] = None) -> ImageTk.PhotoImage:
    """
    生成图表并返回 Tkinter 可用的 PhotoImage 对象。
    接受 sock 参数并将其传递给 get_chart_bytes。
    """
    chart_type_lower = chart_type.lower().strip()

    # 动态确定是否需要 question_id
    chart_need_qid = chart_type_lower in CHART_TYPES_NEED_QUESTION_ID
    qid = question_id if chart_need_qid else None

    # 调用 answer_type 获取 PNG 字节流
    try:
        # -----------------------------------------------
        # 关键修正：将 sock 参数传递给 get_chart_bytes
        # -----------------------------------------------
        png_bytes = get_chart_bytes(survey_id, qid, chart_type_lower, sock=sock)
    except Exception as e:
        # 如果生成失败，抛出异常让 UI 层处理显示
        raise e

    # 从内存加载图片
    image_data_stream = io.BytesIO(png_bytes)
    img = Image.open(image_data_stream)

    # 可以在这里做 resize，防止图表过大撑爆界面
    # 例如限制最大宽度 700
    max_width = 700
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        # 兼容新版本 PIL/Pillow
        resampling_filter = Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.Resampling.LANCZOS
        img = img.resize((max_width, new_height), resampling_filter)

    photo = ImageTk.PhotoImage(img)
    return photo