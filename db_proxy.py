# db_proxy.py
from module_b.client_socket import send_request
from typing import Optional, Dict, Any, List

# ==============================
# 用户相关接口
# ==============================

def add_user(user_name: str, password: str, user_status: str = "active", unban_time: Optional[str] = None) -> int:
    return send_request("add_user", {
        "user_name": user_name,
        "password": password,
        "user_status": user_status,
        "unban_time": unban_time
    })

def get_user_by_login(identifier: str) -> Optional[Dict[str, Any]]:
    return send_request("get_user_by_login", {"identifier": identifier})

def get_user_id_by_name(user_name: str) -> Optional[int]:
    return send_request("get_user_id_by_name", {"user_name": user_name})

# ==============================
# 问卷相关接口
# ==============================

def add_survey(created_by: int, survey_title: str, survey_status: str = "draft", release_time: Optional[str] = None) -> int:
    return send_request("add_survey", {
        "created_by": created_by,
        "survey_title": survey_title,
        "survey_status": survey_status,
        "release_time": release_time
    })

def get_survey(survey_id: int) -> Optional[Dict[str, Any]]:
    return send_request("get_survey", {"survey_id": survey_id})

def get_full_survey_detail(survey_id: int) -> Optional[Dict[str, Any]]:
    return send_request("get_full_survey_detail", {"survey_id": survey_id})

def get_public_surveys() -> List[Dict[str, Any]]:
    return send_request("get_public_surveys")

def get_public_surveys_by_user_id(user_id: int) -> List[Dict[str, Any]]:
    return send_request("get_public_surveys_by_user_id", {"user_id": user_id})

def get_public_surveys_by_username(username: str) -> List[Dict[str, Any]]:
    return send_request("get_public_surveys_by_username", {"username": username})

def get_surveys_filled_by_user(user_id: int) -> List[int]:
    return send_request("get_surveys_filled_by_user", {"user_id": user_id})

def has_user_answered_survey(user_id: int, survey_id: int) -> bool:
    return send_request("has_user_answered_survey", {"user_id": user_id, "survey_id": survey_id})

# ==============================
# 问题和选项相关接口
# ==============================

def add_question(survey_id: int, question_index: int, question_text: str, question_type: str) -> int:
    return send_request("add_question", {
        "survey_id": survey_id,
        "question_index": question_index,
        "question_text": question_text,
        "question_type": question_type
    })

def add_option(question_id: int, option_index: int, option_text: str) -> int:
    return send_request("add_option", {
        "question_id": question_id,
        "option_index": option_index,
        "option_text": option_text
    })

def add_answer(user_id: int, survey_id: int, question_id: int, answer_content: str) -> int:
    return send_request("add_answer", {
        "user_id": user_id,
        "survey_id": survey_id,
        "question_id": question_id,
        "answer_content": answer_content
    })

def add_answer_survey_history(user_id: int, survey_id: int) -> int:
    return send_request("add_answer_survey_history", {
        "user_id": user_id,
        "survey_id": survey_id
    })

def update_survey_title(survey_id: int, new_title: str):
    return send_request("update_survey_title", {"survey_id": survey_id, "new_title": new_title})

def update_question_text(question_id: int, new_text: str):
    return send_request("update_question_text", {"question_id": question_id, "new_text": new_text})

def update_option_text(option_id: int, new_text: str):
    return send_request("update_option_text", {"option_id": option_id, "new_text": new_text})

def delete_survey(survey_id: int):
    return send_request("delete_survey", {"survey_id": survey_id})

def delete_question(question_id: int):
    return send_request("delete_question", {"question_id": question_id})

def delete_option(option_id: int):
    return send_request("delete_option", {"option_id": option_id})

def publish_survey(survey_id: int):
    return send_request("publish_survey", {"survey_id": survey_id})

def update_survey_status(survey_id: int, new_status: str):
    return send_request("update_survey_status", {"survey_id": survey_id, "new_status": new_status})

# ==============================
# 违规管理接口
# ==============================

def add_violation(survey_id: int, reason: str, status: str = 'pending', handled_by: Optional[int] = None) -> int:
    return send_request("add_violation", {
        "survey_id": survey_id,
        "reason": reason,
        "status": status,
        "handled_by": handled_by
    })

def get_all_violations() -> List[Dict[str, Any]]:
    return send_request("get_all_violations")
