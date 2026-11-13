# StudyTask 验收记录

## 1. 测试环境

| 项目 | 值 |
| --- | --- |
| 验收日期 | 2026-11-09 |
| 操作系统 | Windows（本地） |
| Python | 3.12.14 |
| Flask | 3.1.3 |
| pytest | 9.2.0 |
| 数据库 | SQLite，`instance/studytask.sqlite3` |
| 测试命令 | `.venv\Scripts\python.exe -m pytest -q` |
| 测试结果 | `20 passed in 1.71s` |

自动化测试使用独立临时数据库，验收结束后生产数据库为空库，仅保留表结构。测试中的“今天”固定为 2026-11-09，避免日期边界导致结果漂移；运行中的应用使用服务器当天日期。

## 2. SRS 最低验收用例 T1–T10

| 用例 | 操作 / 输入 | 预期结果 | 实际结果 | 自动化证据 |
| --- | --- | --- | --- | --- |
| T1 | 新建：课程“数据结构”、明天截止、高优先级 | 列表显示新增任务 | 通过；列表和详情均显示新增记录 | `test_create_task_then_list_and_detail_show_required_fields` |
| T2 | 名称为空提交新任务 | 提示错误，不产生脏数据 | 通过；返回 400，数据库计数为 0 | `test_empty_name_is_rejected_without_creating_a_row` |
| T3 | 修改任务描述与优先级 | 修改成功且刷新后保留 | 通过；列表与详情读取同一更新记录 | `test_edit_updates_list_and_detail_consistently` |
| T4 | 待完成→进行中→已完成 | 状态逐次正确更新 | 通过；最终数据库状态为已完成 | `test_status_can_move_through_all_three_states_and_persists` |
| T5 | 分别筛选课程、状态和优先级 | 结果只包含匹配任务 | 通过；单项筛选与组合筛选均只返回 1 条匹配记录 | `test_each_filter_dimension_works_individually`、`test_combined_course_status_and_priority_filters` |
| T6 | 新增昨日到期且未完成的任务 | 显示逾期标识 | 通过；显示“逾期”，已完成旧任务不显示 | `test_overdue_and_due_soon_badges_respect_completion` |
| T7 | 新增明日到期且未完成的任务 | 显示即将到期标识 | 通过；显示“即将到期” | `test_overdue_and_due_soon_badges_respect_completion`、`test_reminder_boundary_is_today_through_three_days` |
| T8 | 创建 5 项、完成 2 项 | 总数 5、完成数 2、完成率 40% | 通过；页面统计为 5 / 2 / 40% | `test_statistics_show_total_completed_and_rate` |
| T9 | 删除一项任务并取消/确认操作 | 取消不删除、确认后删除 | 通过；确认页不删除，POST 确认后记录移除 | `test_delete_requires_confirmation_page_then_deletes` |
| T10 | 关闭并重新启动系统 | 已保存数据仍可查询 | 通过；自动测试用同一数据库重建应用后仍可查询 | `test_data_survives_application_restart` |

## 3. 补充验收

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| 无效日期（2026-02-30、2026/11/10）被拒绝 | 通过 | `test_invalid_form_values_are_rejected` |
| 非法优先级、空课程被拒绝 | 通过 | `test_invalid_form_values_are_rejected` |
| 名称超 100 字、描述超 1000 字被拒绝 | 通过 | `test_overlong_name_and_description_are_rejected` |
| 非法状态不修改记录 | 通过 | `test_invalid_status_does_not_change_task` |
| 0 条任务时统计为 0 / 0 / 0% | 通过 | `test_empty_statistics_show_zero_percent` |
| 200 条任务列表正常渲染，统计正确 | 通过 | `test_two_hundred_tasks_render_on_the_list_page` |
| 不存在的任务返回中文 404 | 通过 | `test_unknown_task_returns_chinese_404` |
| 真实进程重启后数据仍存在 | 通过 | 通过 HTTP 创建“启动自检任务”，停止并重启 `run.py` 后首页仍显示该记录，随后通过确认页删除并恢复空库 |

## 4. 人工运行验收记录

1. 执行 `.venv\Scripts\python.exe -m flask --app run.py init-db`，生成 `instance/studytask.sqlite3`，`tasks` 表存在且初始 0 条记录。
2. 执行 `.venv\Scripts\python.exe run.py`，访问 `http://127.0.0.1:5000/` 返回 HTTP 200，页面中文正常，统计为 0 / 0 / 0%，显示空状态。
3. 通过实际 HTTP POST 创建“启动自检任务”（课程“软件工程”，截止日期 2026-11-12，优先级“中”），返回 303 并跳转 `/tasks/1`，详情页显示名称和课程。
4. 停止进程并重新启动服务，首页仍显示“启动自检任务”，验证文件持久化。
5. 打开 `/tasks/1/delete` 确认页，页面显示任务信息和“确认删除”；POST 确认后返回列表，任务消失，空状态恢复。

## 5. 范围核对

未实现登录注册、多用户、权限、共享任务、邮件/短信、第三方日历、移动 App、云部署。应用只监听 `127.0.0.1`，所有页面资源均本地提供，运行时不依赖互联网。

## 6. 结论

SRS 附录 A 的 FR-01 至 FR-10 与第二章 2.5 节 T1–T10 均已实际验证通过。自动化测试可复现，实际运行结果与页面、数据库记录一致。