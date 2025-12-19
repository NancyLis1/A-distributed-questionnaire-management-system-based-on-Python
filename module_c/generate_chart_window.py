import io
import sys
import os
from PIL import Image, ImageTk
from typing import Optional,Any  # 引入 Optional 用于类型注解

# 确保能引用到同级目录的 answer_type
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from answer_type import get_chart_bytes

# 配置常量：哪些图表需要 Question ID
CHART_TYPES_NEED_QUESTION_ID = {
    "pie", "bar", "bar_h", "line_answer", "text_answer"
}


def generate_chart_image(survey_id: int, question_id: int, chart_type: str,
                         sock: Optional[object] = None) -> Any:
    """
    修改后的函数：
    - 如果是 text_answer，直接返回字节流或字符串。
    - 如果是统计图，才返回 PhotoImage。
    """
    chart_type_lower = chart_type.lower().strip()

    # 1. 调用后端获取原始数据 (可能是 PNG 字节流，也可能是文本字节流)
    try:
        raw_data = get_chart_bytes(survey_id, question_id, chart_type_lower, sock=sock)
    except Exception as e:
        raise e

    # 2. 如果是文本报告，直接返回，不经过 PIL 处理
    if chart_type_lower == "text_answer":
        return raw_data  # 直接返回字节流，由前端 _display_chart_ui_flexible 去 decode

    # 3. 如果是图片类型，才走 PIL 的逻辑
    try:
        image_data_stream = io.BytesIO(raw_data)
        img = Image.open(image_data_stream)

        # 调整尺寸逻辑
        max_width = 700
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            resampling_filter = Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.Resampling.LANCZOS
            img = img.resize((max_width, new_height), resampling_filter)

        return ImageTk.PhotoImage(img)
    except Exception as e:
        # 如果虽然不是 text_answer 但图片解析失败，抛出错误
        raise Exception(f"图片解析失败: {e}")