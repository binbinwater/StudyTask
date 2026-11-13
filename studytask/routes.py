from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from . import current_date
from .tasks import (
    PRIORITIES,
    STATUSES,
    create_task,
    decorate_task,
    delete_task,
    get_stats,
    get_task,
    list_courses,
    list_tasks,
    set_task_status,
    update_task,
    validate_task_form,
)

bp = Blueprint("tasks", __name__)

STATUS_CLASSES = {
    "待完成": "status-pending",
    "进行中": "status-progress",
    "已完成": "status-done",
}
PRIORITY_CLASSES = {"高": "priority-high", "中": "priority-medium", "低": "priority-low"}
REMINDER_CLASSES = {"逾期": "reminder-overdue", "即将到期": "reminder-soon"}


@bp.app_template_filter("status_class")
def status_class(status):
    return STATUS_CLASSES.get(status, "")


@bp.app_template_filter("priority_class")
def priority_class(priority):
    return PRIORITY_CLASSES.get(priority, "")


@bp.app_template_filter("reminder_class")
def reminder_class(reminder):
    return REMINDER_CLASSES.get(reminder, "")


@bp.app_errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@bp.route("/")
def index():
    filters = {
        "course": request.args.get("course", "").strip(),
        "status": request.args.get("status", "").strip(),
        "priority": request.args.get("priority", "").strip(),
    }
    today = current_date()
    rows = list_tasks(filters)
    tasks = [decorate_task(row, today) for row in rows]
    stats = get_stats()
    return render_template(
        "index.html",
        tasks=tasks,
        filters=filters,
        courses=list_courses(),
        statuses=STATUSES,
        priorities=PRIORITIES,
        stats=stats,
        today=today,
    )


@bp.route("/tasks/new")
def new_task():
    form = {
        "name": "",
        "course": "",
        "description": "",
        "due_date": "",
        "priority": "中",
        "status": "待完成",
    }
    return render_template(
        "task_form.html",
        mode="create",
        task=None,
        form=form,
        errors={},
        statuses=STATUSES,
        priorities=PRIORITIES,
    )


@bp.post("/tasks")
def create():
    data, errors = validate_task_form(request.form, require_status=False)
    if errors:
        return (
            render_template(
                "task_form.html",
                mode="create",
                task=None,
                form=data,
                errors=errors,
                statuses=STATUSES,
                priorities=PRIORITIES,
            ),
            400,
        )

    task_id = create_task(data)
    flash("任务已创建。", "success")
    return redirect(url_for("tasks.detail", task_id=task_id), code=303)


@bp.route("/tasks/<int:task_id>")
def detail(task_id):
    task = get_task(task_id)
    if task is None:
        abort(404)
    return render_template(
        "task_detail.html",
        task=decorate_task(task, current_date()),
        statuses=STATUSES,
    )


@bp.route("/tasks/<int:task_id>/edit")
def edit(task_id):
    task = get_task(task_id)
    if task is None:
        abort(404)
    return render_template(
        "task_form.html",
        mode="edit",
        task=task,
        form=task,
        errors={},
        statuses=STATUSES,
        priorities=PRIORITIES,
    )


@bp.post("/tasks/<int:task_id>/edit")
def update(task_id):
    task = get_task(task_id)
    if task is None:
        abort(404)

    data, errors = validate_task_form(request.form, require_status=True)
    if errors:
        return (
            render_template(
                "task_form.html",
                mode="edit",
                task=task,
                form=data,
                errors=errors,
                statuses=STATUSES,
                priorities=PRIORITIES,
            ),
            400,
        )

    update_task(task_id, data)
    flash("任务已更新。", "success")
    return redirect(url_for("tasks.detail", task_id=task_id), code=303)


@bp.post("/tasks/<int:task_id>/status")
def change_status(task_id):
    if get_task(task_id) is None:
        abort(404)
    status = (request.form.get("status") or "").strip()
    if status not in STATUSES:
        flash("状态必须是待完成、进行中或已完成。", "error")
    else:
        set_task_status(task_id, status)
        flash("任务状态已更新。", "success")
    return redirect(url_for("tasks.detail", task_id=task_id), code=303)


@bp.route("/tasks/<int:task_id>/delete")
def delete_confirmation(task_id):
    task = get_task(task_id)
    if task is None:
        abort(404)
    return render_template(
        "delete_confirm.html",
        task=decorate_task(task, current_date()),
    )


@bp.post("/tasks/<int:task_id>/delete")
def delete(task_id):
    if get_task(task_id) is None:
        abort(404)
    delete_task(task_id)
    flash("任务已删除。", "success")
    return redirect(url_for("tasks.index"), code=303)