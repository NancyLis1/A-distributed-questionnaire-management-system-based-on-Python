import sys
import os

# 导入utils模块（包含新增的get_username_by_id函数）
try:
    from db_utils import (
        get_public_surveys, get_survey, update_survey_status,
        delete_survey, get_username_by_id  # 导入新增的函数
    )
except ImportError as e:
    print(f"导入失败！请确保utils.py与manager.py在同一目录。错误详情：{e}")
    sys.exit(1)

# 预设管理员账号和密码（仅校验账号密码，跳过数据库）
ADMIN_ACCOUNTS = {"manager1", "manager2", "manager3"}
ADMIN_PASSWORD_PLAIN = "management"  # 明文预设密码


def admin_login():
    """管理员登录验证（仅校验账号密码，跳过数据库）"""
    print("===== 问卷系统管理员登录 =====")
    max_attempts = 3
    attempts = 0

    while attempts < max_attempts:
        username = input("请输入管理员账号：").strip()
        password = input("请输入管理员密码：").strip()

        # 1. 验证账号是否在预设列表中
        if username not in ADMIN_ACCOUNTS:
            attempts += 1
            print(f"错误：无效的管理员账号！剩余尝试次数：{max_attempts - attempts}")
            continue

        # 2. 验证密码（仅明文对比）
        if password == ADMIN_PASSWORD_PLAIN:
            print(f"登录成功！欢迎 {username} 进入管理员界面。")
            return True
        else:
            attempts += 1
            print(f"错误：密码错误！剩余尝试次数：{max_attempts - attempts}")

    print("错误：登录尝试次数过多，程序退出。")
    sys.exit(1)


def list_all_surveys():
    """查看所有问卷及对应发布者信息（修复发布者显示问题）"""
    print("\n===== 系统所有问卷列表 =====")
    all_surveys = []
    active_surveys = get_public_surveys()

    for survey in active_surveys:
        # 1. 获取问卷基础信息
        survey_id = survey["survey_id"]
        survey_title = survey["survey_title"]
        creator_id = survey["created_by"]  # 发布者ID
        release_time = survey["release_time"] or "未设置"

        # 2. 核心修复：调用新增的get_username_by_id函数查询发布者名称
        creator_name = get_username_by_id(creator_id)

        # 3. 获取问卷最新状态
        survey_detail = get_survey(survey_id)
        survey_status = survey_detail["survey_status"] if survey_detail else "未知"

        # 4. 组装问卷信息
        all_surveys.append({
            "survey_id": survey_id,
            "title": survey_title,
            "creator_id": creator_id,
            "creator_name": creator_name,
            "status": survey_status,
            "release_time": release_time
        })

    # 格式化输出（显示问卷ID、标题、发布者ID、发布者名称、状态、发布时间）
    print(f"{'问卷ID':<10} {'问卷标题':<30} {'发布者ID':<10} {'发布者名称':<10} {'状态':<15} {'发布时间':<20}")
    print("-" * 100)
    if not all_surveys:
        print("暂无已发布的问卷")
    else:
        for survey in all_surveys:
            print(
                f"{survey['survey_id']:<10} {survey['title']:<30} {survey['creator_id']:<10} {survey['creator_name']:<10} {survey['status']:<15} {survey['release_time']:<20}")

    print("\n提示：状态说明 - active=已发布, banned=已封禁, draft=草稿")


def ban_survey():
    """封禁指定问卷（将状态改为banned）"""
    print("\n===== 封禁问卷 =====")
    try:
        survey_id = int(input("请输入要封禁的问卷ID：").strip())
        # 1. 验证问卷是否存在
        survey = get_survey(survey_id)
        if not survey:
            print(f"错误：问卷ID {survey_id} 不存在！")
            return

        # 2. 验证当前状态
        if survey["survey_status"] == "banned":
            print(f"提示：问卷ID {survey_id} 已处于封禁状态，无需重复操作。")
            return

        # 3. 执行封禁
        update_survey_status(survey_id, "banned")
        print(f"成功：问卷ID {survey_id}（{survey['survey_title']}）已封禁，用户无法填写。")
    except ValueError:
        print("错误：问卷ID必须是数字！")
    except Exception as e:
        print(f"错误：封禁问卷失败 - {str(e)}")


def delete_survey_confirm():
    """删除指定问卷（物理删除，需二次确认）"""
    print("\n===== 删除问卷 =====")
    try:
        survey_id = int(input("请输入要删除的问卷ID：").strip())
        # 1. 验证问卷是否存在
        survey = get_survey(survey_id)
        if not survey:
            print(f"错误：问卷ID {survey_id} 不存在！")
            return

        # 2. 二次确认（防止误删）
        confirm = input(
            f"警告：删除问卷「{survey['survey_title']}」将永久删除所有相关数据（题目/答案/历史），是否确认？(y/N)：").strip().lower()
        if confirm != "y":
            print("操作已取消。")
            return

        # 3. 执行删除
        delete_survey(survey_id)
        print(f"成功：问卷ID {survey_id}（{survey['survey_title']}）已永久删除。")
    except ValueError:
        print("错误：问卷ID必须是数字！")
    except Exception as e:
        print(f"错误：删除问卷失败 - {str(e)}")


def unban_survey():
    """解封指定问卷（将状态改回active）"""
    print("\n===== 解封问卷 =====")
    try:
        survey_id = int(input("请输入要解封的问卷ID：").strip())
        # 1. 验证问卷是否存在
        survey = get_survey(survey_id)
        if not survey:
            print(f"错误：问卷ID {survey_id} 不存在！")
            return

        # 2. 验证当前状态
        if survey["survey_status"] != "banned":
            print(f"提示：问卷ID {survey_id} 当前状态为「{survey['survey_status']}」，无需解封。")
            return

        # 3. 执行解封
        update_survey_status(survey_id, "active")
        print(f"成功：问卷ID {survey_id}（{survey['survey_title']}）已解封，用户可正常填写。")
    except ValueError:
        print("错误：问卷ID必须是数字！")
    except Exception as e:
        print(f"错误：解封问卷失败 - {str(e)}")


def show_admin_menu():
    """显示管理员主菜单"""
    while True:
        print("\n===== 问卷系统管理员菜单 =====")
        print("1. 查看所有问卷及发布者")
        print("2. 封禁指定问卷")
        print("3. 删除指定问卷")
        print("4. 解封指定问卷")
        print("0. 退出管理员界面")
        print("==============================")

        choice = input("请输入操作编号（0-4）：").strip()
        if choice == "1":
            list_all_surveys()
        elif choice == "2":
            ban_survey()
        elif choice == "3":
            delete_survey_confirm()
        elif choice == "4":
            unban_survey()
        elif choice == "0":
            print("正在退出管理员界面...")
            print("感谢使用，再见！")
            sys.exit(0)
        else:
            print("错误：无效的操作编号，请输入0-4之间的数字！")


def main():
    """程序主入口"""
    # 1. 管理员登录
    if not admin_login():
        sys.exit(1)

    # 2. 显示管理菜单
    show_admin_menu()


if __name__ == "__main__":
    main()