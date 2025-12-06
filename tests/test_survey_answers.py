import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_utils as db
import pprint

def main():
    # 假设 survey_id = 1
    survey_id = 1

    summary = db.get_survey_answers_summary(survey_id)
    if summary is None:
        print(f"问卷 {survey_id} 不存在")
        return

    print("问卷答案情况：")
    pprint.pprint(summary)

if __name__ == "__main__":
    main()
