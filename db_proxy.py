# db_proxy.py
from module_b.client_socket import send_request
from typing import Optional, Dict, Any, List

# ==============================
# 用户相关接口
# ==============================
def add_user(sock, user_name: str, password: str, user_status: str = "active", unban_time: Optional[str] = None) -> int:
    return send_request("add_user", {
        "user_name": user_name,
        "password": password,
        "user_status": user_status,
        "unban_time": unban_time
    }, sock=sock)

def get_user_by_login(sock, identifier: str) -> Optional[Dict[str, Any]]:
    return send_request("get_user_by_login", {"identifier": identifier}, sock=sock)

def get_user_id_by_name(sock, user_name: str) -> Optional[int]:
    return send_request("get_user_id_by_name", {"user_name": user_name}, sock=sock)

# ==============================
# 问卷相关接口
# ==============================
def add_survey(sock, created_by: int, survey_title: str, survey_status: str = "draft", release_time: Optional[str] = None) -> int:
    return send_request("add_survey", {
        "created_by": created_by,
        "survey_title": survey_title,
        "survey_status": survey_status,
        "release_time": release_time
    }, sock=sock)

def get_survey(sock, survey_id: int) -> Optional[Dict[str, Any]]:
    return send_request("get_survey", {"survey_id": survey_id}, sock=sock)

def get_full_survey_detail(sock, survey_id: int) -> Optional[Dict[str, Any]]:
    return send_request("get_full_survey_detail", {"survey_id": survey_id}, sock=sock)

def get_public_surveys(sock) -> List[Dict[str, Any]]:
    return send_request("get_public_surveys", sock=sock)

def get_public_surveys_by_user_id(sock, user_id: int) -> List[Dict[str, Any]]:
    return send_request("get_public_surveys_by_user_id", {"user_id": user_id}, sock=sock)

def get_public_surveys_by_username(sock, username: str) -> List[Dict[str, Any]]:
    return send_request("get_public_surveys_by_username", {"username": username}, sock=sock)

def get_surveys_filled_by_user(sock, user_id: int) -> List[int]:
    return send_request("get_surveys_filled_by_user", {"user_id": user_id}, sock=sock)

def has_user_answered_survey(sock, user_id: int, survey_id: int) -> bool:
    return send_request("has_user_answered_survey", {"user_id": user_id, "survey_id": survey_id}, sock=sock)


# ==============================
# 问题和选项相关接口
# ==============================
def add_question(sock, survey_id: int, question_index: int, question_text: str, question_type: str) -> int:
    return send_request("add_question", {
        "survey_id": survey_id,
        "question_index": question_index,
        "question_text": question_text,
        "question_type": question_type
    }, sock=sock)

def add_option(sock, question_id: int, option_index: int, option_text: str) -> int:
    return send_request("add_option", {
        "question_id": question_id,
        "option_index": option_index,
        "option_text": option_text
    }, sock=sock)

# 【新增】获取指定题目的选项列表 (供编辑器使用)
def get_question_options(sock, question_id: int) -> List[Any]:
    return send_request("get_question_options", {"question_id": question_id}, sock=sock)

# 【新增】复制题目 (供编辑器使用)
def copy_question(sock, survey_id: int, source_question_id: int):
    return send_request("copy_question", {
        "survey_id": survey_id,
        "source_question_id": source_question_id
    }, sock=sock)

def add_answer(sock, user_id: int, survey_id: int, question_id: int, answer_content: str) -> int:
    return send_request("add_answer", {
        "user_id": user_id,
        "survey_id": survey_id,
        "question_id": question_id,
        "answer_content": answer_content
    }, sock=sock)

def add_answer_survey_history(sock, user_id: int, survey_id: int) -> int:
    return send_request("add_answer_survey_history", {
        "user_id": user_id,
        "survey_id": survey_id
    }, sock=sock)

def update_survey_title(sock, survey_id: int, new_title: str):
    return send_request("update_survey_title", {"survey_id": survey_id, "new_title": new_title}, sock=sock)

def update_question_text(sock, question_id: int, new_text: str):
    return send_request("update_question_text", {"question_id": question_id, "new_text": new_text}, sock=sock)

def update_option_text(sock, option_id: int, new_text: str):
    return send_request("update_option_text", {"option_id": option_id, "new_text": new_text}, sock=sock)

def delete_survey(sock, survey_id: int):
    return send_request("delete_survey", {"survey_id": survey_id}, sock=sock)

def delete_question(sock, question_id: int):
    return send_request("delete_question", {"question_id": question_id}, sock=sock)

def delete_option(sock, option_id: int):
    return send_request("delete_option", {"option_id": option_id}, sock=sock)

def publish_survey(sock, survey_id: int):
    return send_request("publish_survey", {"survey_id": survey_id}, sock=sock)

def update_survey_status(sock, survey_id: int, new_status: str):
    return send_request("update_survey_status", {"survey_id": survey_id, "new_status": new_status}, sock=sock)

# ==============================
# 违规管理接口
# ==============================
def add_violation(sock, survey_id: int, reason: str, status: str = 'pending', handled_by: Optional[int] = None) -> int:
    return send_request("add_violation", {
        "survey_id": survey_id,
        "reason": reason,
        "status": status,
        "handled_by": handled_by
    }, sock=sock)

def get_all_violations(sock) -> List[Dict[str, Any]]:
    return send_request("get_all_violations", sock=sock)

def add_full_survey_submission(sock, user_id: int, survey_id: int, answers: List[Dict[str, Any]]):
    """
    一次性提交问卷历史和所有答案
    :param answers: 格式为 [{'question_id': qid, 'answer_text': ans}, ...]
    """
    return send_request("add_full_survey_submission", {
        "user_id": user_id,
        "survey_id": survey_id,
        "answers": answers
    }, sock=sock)

# 🚀 新增函数：用于在网络失败时清除可能存在的半成品提交记录
def undo_survey_submission(sock, user_id: int, survey_id: int):
    """
    清除指定用户对指定问卷的提交记录（用于处理超时）。
    需要服务器端实现对应的 db_utils.undo_survey_submission 函数。
    """
    return send_request("undo_survey_submission", {"user_id": user_id, "survey_id": survey_id}, sock=sock)