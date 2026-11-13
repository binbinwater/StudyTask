import re
from datetime import date, timedelta

from .db import get_db

PRIORITIES = ("高", "中", "低")
STATUSES = ("待完成", "进行中", "已完成")
MAX_NAME_LENGTH = 100
MAX_COURSE_LENGTH = 60
MAX_DESCRIPTION_LENGTH = 1000
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_task_form(form, *, require_status):
    """Validate and normalize task form data.

    Returns ``(data, errors)``. ``data`` is always populated so the template can
    echo what the user submitted after a validation failure.
    """
    name = (form.get("name") or "").strip()
    course = (form.get("course") or "").strip()
    description = (form.get("description") or "").strip()
    due_date_raw = (form.get("due_date") or "").strip()
    priority = (form.get("priority") or "中").strip()
    status = (form.get("status") or "").strip()
    if not require_status:
        status = "待完成"

    data = {
        "name": name,
        "course": course,
        "description": description,
        "due_date": due_date_raw,
        "priority": priority,
        "status": status,
    }
    errors = {}

    if not name:
        errors["name"] = "任务名称不能为空。"
    elif len(name) > MAX_NAME_LENGTH:
        errors["name"] = f"任务名称不能超过 {MAX_NAME_LENGTH} 个字符。"

    if not course:
        errors["course"] = "所属课程不能为空。"
    elif len(course) > MAX_COURSE_LENGTH:
        errors["course"] = f"所属课程不能超过 {MAX_COURSE_LENGTH} 个字符。"

    if len(description) > MAX_DESCRIPTION_LENGTH:
        errors["description"] = f"任务描述不能超过 {MAX_DESCRIPTION_LENGTH} 个字符。"

    if not due_date_raw:
        errors["due_date"] = "截止日期不能为空。"
    elif not DATE_PATTERN.match(due_date_raw):
        errors["due_date"] = "截止日期格式应为 YYYY-MM-DD。"
    else:
        try:
            parsed_date = date.fromisoformat(due_date_raw)
        except ValueError:
            errors["due_date"] = "截止日期不是有效日期。"
        else:
            if parsed_date.isoformat() != due_date_raw:
                errors["due_date"] = "截止日期格式应为 YYYY-MM-DD。"
            else:
                data["due_date"] = parsed_date.isoformat()

    if priority not in PRIORITIES:
        errors["priority"] = "优先级必须是高、中或低。"

    if require_status and status not in STATUSES:
        errors["status"] = "状态必须是待完成、进行中或已完成。"

    return data, errors


def decorate_task(row, today):
    task = dict(row)
    task["reminder"] = reminder_for(task, today)
    return task


def reminder_for(task, today):
    """Return the reminder badge for a task, or ``None``."""
    if task["status"] == "已完成":
        return None
    try:
        due = date.fromisoformat(task["due_date"])
    except (TypeError, ValueError):
        return None
    if due < today:
        return "逾期"
    if due <= today + timedelta(days=3):
        return "即将到期"
    return None


def list_tasks(filters=None):
    filters = filters or {}
    clauses = []
    parameters = []

    course = (filters.get("course") or "").strip()
    status = (filters.get("status") or "").strip()
    priority = (filters.get("priority") or "").strip()

    if course:
        clauses.append("course = ?")
        parameters.append(course)
    if status:
        clauses.append("status = ?")
        parameters.append(status)
    if priority:
        clauses.append("priority = ?")
        parameters.append(priority)

    sql = "SELECT * FROM tasks"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY due_date ASC, id DESC"

    return [dict(row) for row in get_db().execute(sql, parameters).fetchall()]


def get_task(task_id):
    row = get_db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row is not None else None


def list_courses():
    rows = get_db().execute(
        "SELECT DISTINCT course FROM tasks ORDER BY course ASC"
    ).fetchall()
    return [row["course"] for row in rows]


def get_stats():
    row = get_db().execute(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN status = '已完成' THEN 1 ELSE 0 END), 0) AS completed
        FROM tasks
        """
    ).fetchone()
    total = row["total"]
    completed = row["completed"]
    rate = (completed * 100 / total) if total else 0
    return {
        "total": total,
        "completed": completed,
        "completion_rate": _format_rate(rate),
    }


def _format_rate(rate):
    formatted = f"{rate:.1f}"
    if formatted.endswith(".0"):
        formatted = formatted[:-2]
    return formatted


def create_task(data):
    database = get_db()
    cursor = database.execute(
        """
        INSERT INTO tasks (name, course, description, due_date, priority, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"],
            data["course"],
            data["description"],
            data["due_date"],
            data["priority"],
            data["status"],
        ),
    )
    database.commit()
    return cursor.lastrowid


def update_task(task_id, data):
    database = get_db()
    cursor = database.execute(
        """
        UPDATE tasks
        SET name = ?, course = ?, description = ?, due_date = ?,
            priority = ?, status = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            data["name"],
            data["course"],
            data["description"],
            data["due_date"],
            data["priority"],
            data["status"],
            task_id,
        ),
    )
    database.commit()
    return cursor.rowcount > 0


def set_task_status(task_id, status):
    database = get_db()
    cursor = database.execute(
        """
        UPDATE tasks
        SET status = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (status, task_id),
    )
    database.commit()
    return cursor.rowcount > 0


def delete_task(task_id):
    database = get_db()
    cursor = database.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    database.commit()
    return cursor.rowcount > 0