from datetime import date

import pytest

from studytask import create_app
from studytask.db import get_db
from studytask.tasks import reminder_for


def task_count(app):
    with app.app_context():
        return get_db().execute("SELECT COUNT(*) FROM tasks").fetchone()[0]


def test_create_task_then_list_and_detail_show_required_fields(client, create_task):
    task_id = create_task(name="线性表作业", course="数据结构", priority="高", due_date="2026-11-10")

    page = client.get("/").get_data(as_text=True)
    assert f'data-task-id="{task_id}"' in page
    assert "线性表作业" in page
    assert "数据结构" in page
    assert "2026-11-10" in page
    assert "待完成" in page
    assert ">高<" in page

    detail = client.get(f"/tasks/{task_id}").get_data(as_text=True)
    assert "线性表作业" in detail
    assert "完成单链表与双链表实验。" in detail
    assert "编辑任务" in detail
    assert "删除任务" in detail


def test_empty_name_is_rejected_without_creating_a_row(client, app):
    response = client.post(
        "/tasks",
        data={
            "name": "   ",
            "course": "数据结构",
            "description": "",
            "due_date": "2026-11-10",
            "priority": "中",
        },
    )

    assert response.status_code == 400
    assert "任务名称不能为空" in response.get_data(as_text=True)
    assert task_count(app) == 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("due_date", "2026-02-30", "截止日期不是有效日期"),
        ("due_date", "2026/11/10", "截止日期格式应为 YYYY-MM-DD"),
        ("priority", "紧急", "优先级必须是高、中或低"),
        ("course", "   ", "所属课程不能为空"),
    ],
)
def test_invalid_form_values_are_rejected(client, app, field, value, message):
    data = {
        "name": "数据库练习",
        "course": "数据库原理",
        "description": "",
        "due_date": "2026-11-11",
        "priority": "中",
    }
    data[field] = value

    response = client.post("/tasks", data=data)

    assert response.status_code == 400
    assert message in response.get_data(as_text=True)
    assert task_count(app) == 0


def test_overlong_name_and_description_are_rejected(client, app):
    response = client.post(
        "/tasks",
        data={
            "name": "任" * 101,
            "course": "软件工程",
            "description": "描" * 1001,
            "due_date": "2026-11-12",
            "priority": "低",
        },
    )

    page = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "任务名称不能超过 100 个字符" in page
    assert "任务描述不能超过 1000 个字符" in page
    assert task_count(app) == 0


def test_edit_updates_list_and_detail_consistently(client, create_task):
    task_id = create_task()

    response = client.post(
        f"/tasks/{task_id}/edit",
        data={
            "name": "链表实验报告（修订）",
            "course": "数据结构与算法",
            "description": "补充复杂度分析。",
            "due_date": "2026-11-20",
            "priority": "低",
            "status": "进行中",
        },
    )
    assert response.status_code == 303

    detail = client.get(f"/tasks/{task_id}").get_data(as_text=True)
    assert "链表实验报告（修订）" in detail
    assert "数据结构与算法" in detail
    assert "补充复杂度分析。" in detail
    assert "2026-11-20" in detail
    assert "低" in detail
    assert "进行中" in detail

    page = client.get("/").get_data(as_text=True)
    assert "链表实验报告（修订）" in page
    assert "数据结构与算法" in page
    assert "2026-11-20" in page


def test_status_can_move_through_all_three_states_and_persists(client, app, create_task):
    task_id = create_task()

    for status in ("进行中", "已完成"):
        response = client.post(f"/tasks/{task_id}/status", data={"status": status}, follow_redirects=True)
        assert response.status_code == 200
        assert f">{status}<" in response.get_data(as_text=True)

    with app.app_context():
        stored = get_db().execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
    assert stored["status"] == "已完成"


def test_invalid_status_does_not_change_task(client, app, create_task):
    task_id = create_task()

    response = client.post(
        f"/tasks/{task_id}/status",
        data={"status": "已归档"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "状态必须是待完成、进行中或已完成" in response.get_data(as_text=True)
    with app.app_context():
        stored = get_db().execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
    assert stored["status"] == "待完成"


def test_each_filter_dimension_works_individually(client, create_task):
    create_task(name="数据结构待办", course="数据结构", due_date="2026-11-10", priority="高")
    create_task(name="数据库已完成", course="数据库原理", due_date="2026-11-11", priority="中")
    create_task(name="操作系统低优先级", course="操作系统", due_date="2026-11-12", priority="低")
    with client.application.app_context():
        done_id = get_db().execute(
            "SELECT id FROM tasks WHERE name = '数据库已完成'"
        ).fetchone()["id"]
    client.post(f"/tasks/{done_id}/status", data={"status": "已完成"})

    cases = [
        ({"course": "操作系统"}, "操作系统低优先级", ["数据结构待办", "数据库已完成"]),
        ({"status": "已完成"}, "数据库已完成", ["数据结构待办", "操作系统低优先级"]),
        ({"priority": "高"}, "数据结构待办", ["数据库已完成", "操作系统低优先级"]),
    ]
    for query, expected, excluded in cases:
        page = client.get("/", query_string=query).get_data(as_text=True)
        body = page.split("<tbody>")[1].split("</tbody>")[0]
        assert body.count("data-task-id=") == 1
        assert expected in body
        for name in excluded:
            assert name not in body


def test_combined_course_status_and_priority_filters(client, app, create_task):
    target = create_task(name="目标任务", course="数据结构", due_date="2026-11-10", priority="高")
    create_task(name="同课已完成", course="数据结构", due_date="2026-11-11", priority="高")
    create_task(name="同课低优先级", course="数据结构", due_date="2026-11-12", priority="低")
    create_task(name="其他课程", course="操作系统", due_date="2026-11-13", priority="高")

    # Complete the second task so that all three filter dimensions differ.
    with app.app_context():
        second_id = get_db().execute(
            "SELECT id FROM tasks WHERE name = '同课已完成'"
        ).fetchone()["id"]
    client.post(f"/tasks/{second_id}/status", data={"status": "已完成"})

    page = client.get(
        "/",
        query_string={"course": "数据结构", "status": "待完成", "priority": "高"},
    ).get_data(as_text=True)
    body = page.split("<tbody>")[1].split("</tbody>")[0]

    assert body.count("data-task-id=") == 1
    assert f'data-task-id="{target}"' in body
    assert "目标任务" in body
    assert "同课低优先级" not in body
    assert "其他课程" not in body


def test_overdue_and_due_soon_badges_respect_completion(client, create_task):
    overdue_id = create_task(name="逾期任务", due_date="2026-11-08")
    soon_id = create_task(name="即将到期任务", due_date="2026-11-10")
    completed_id = create_task(name="已完成旧任务", due_date="2026-11-08")
    client.post(f"/tasks/{completed_id}/status", data={"status": "已完成"})

    page = client.get("/").get_data(as_text=True)
    overdue_row = page.split(f'data-task-id="{overdue_id}"')[1].split("</tr>")[0]
    soon_row = page.split(f'data-task-id="{soon_id}"')[1].split("</tr>")[0]
    completed_row = page.split(f'data-task-id="{completed_id}"')[1].split("</tr>")[0]

    assert "reminder-overdue" in overdue_row
    assert "逾期" in overdue_row
    assert "reminder-soon" in soon_row
    assert "即将到期" in soon_row
    assert "reminder-overdue" not in completed_row
    assert "reminder-soon" not in completed_row


def test_reminder_boundary_is_today_through_three_days():
    today = date(2026, 11, 9)
    assert reminder_for({"status": "待完成", "due_date": "2026-11-09"}, today) == "即将到期"
    assert reminder_for({"status": "进行中", "due_date": "2026-11-12"}, today) == "即将到期"
    assert reminder_for({"status": "待完成", "due_date": "2026-11-13"}, today) is None
    assert reminder_for({"status": "已完成", "due_date": "2026-11-01"}, today) is None


def test_statistics_show_total_completed_and_rate(client, create_task):
    ids = [create_task(name=f"统计任务{i}", due_date=f"2026-11-{10 + i}") for i in range(1, 6)]
    client.post(f"/tasks/{ids[0]}/status", data={"status": "已完成"})
    client.post(f"/tasks/{ids[1]}/status", data={"status": "已完成"})

    page = client.get("/").get_data(as_text=True)
    assert 'data-stat="total">5</strong>' in page
    assert 'data-stat="completed">2</strong>' in page
    assert 'data-stat="rate">40%</strong>' in page


def test_empty_statistics_show_zero_percent(client):
    page = client.get("/").get_data(as_text=True)
    assert 'data-stat="total">0</strong>' in page
    assert 'data-stat="completed">0</strong>' in page
    assert 'data-stat="rate">0%</strong>' in page
    assert "暂无任务" in page


def test_delete_requires_confirmation_page_then_deletes(client, app, create_task):
    task_id = create_task(name="待删除任务")

    confirmation = client.get(f"/tasks/{task_id}/delete")
    confirmation_page = confirmation.get_data(as_text=True)
    assert confirmation.status_code == 200
    assert "确定要删除这项任务吗" in confirmation_page
    assert "取消" in confirmation_page
    assert task_count(app) == 1

    response = client.post(f"/tasks/{task_id}/delete", follow_redirects=True)
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "任务已删除" in page
    assert "待删除任务" not in page
    assert task_count(app) == 0


def test_data_survives_application_restart(db_path, create_task, app):
    task_id = create_task(name="重启后仍存在", due_date="2026-12-01")

    restarted_app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(db_path),
            "SECRET_KEY": "test-only-key",
            "TODAY_OVERRIDE": date(2026, 11, 9),
        }
    )
    page = restarted_app.test_client().get("/").get_data(as_text=True)

    assert f'data-task-id="{task_id}"' in page
    assert "重启后仍存在" in page
    assert "2026-12-01" in page


def test_two_hundred_tasks_render_on_the_list_page(client, app):
    with app.app_context():
        database = get_db()
        database.executemany(
            """
            INSERT INTO tasks (name, course, description, due_date, priority, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    f"批量任务{i}",
                    "批量课程",
                    "",
                    "2026-12-01",
                    "中",
                    "待完成" if i % 2 else "已完成",
                )
                for i in range(200)
            ],
        )
        database.commit()

    response = client.get("/")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert page.count("data-task-id=") == 200
    assert 'data-stat="total">200</strong>' in page
    assert 'data-stat="completed">100</strong>' in page
    assert 'data-stat="rate">50%</strong>' in page


def test_unknown_task_returns_chinese_404(client):
    response = client.get("/tasks/9999")

    assert response.status_code == 404
    assert "没有找到这个页面" in response.get_data(as_text=True)