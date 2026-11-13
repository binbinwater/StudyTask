# StudyTask 个人学习任务管理系统

StudyTask 是一个可本地运行的单用户学习任务管理 Web 应用，按《软件工程》实验一附录 A 的 SRS 实现。用于记录课程作业、实验和考试准备，提供任务增删改查、状态管理、组合筛选、逾期提示和基础统计。

- GitHub 仓库：<https://github.com/binbinwater/StudyTask>
- 公网 Web 地址：<http://116.62.141.168/>
- 本地 Web 地址：<http://127.0.0.1:5000>

## 1. 技术栈与范围

- 后端：Python 3.11+、Flask 3.1
- 数据存储：SQLite（单文件，本地持久化）
- 前端：Jinja2 模板 + 原生 CSS，无外部 CDN，离线可用
- 测试：pytest

严格不实现：账号注册、登录、多用户权限、共享任务、邮件/短信、第三方日历同步、移动 App。课程要求在云服务器上提供访问，因此额外部署了 Nginx + Gunicorn 运行环境，但不改变应用功能范围。

## 2. 从零开始运行

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app run.py init-db
.\.venv\Scripts\python.exe run.py
```

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flask --app run.py init-db
.venv/bin/python run.py
```

打开浏览器访问：<http://127.0.0.1:5000>

数据库文件位于 `instance/studytask.sqlite3`，首次启动时也会自动创建表，`init-db` 可安全重复执行。应用启动时为空库，不注入演示数据。按 `Ctrl+C` 停止服务。

### 重置本地数据

先停止服务，删除 `instance/studytask.sqlite3`，再执行一次 `init-db` 或重新启动。删除数据库会永久丢失已有任务。

### 云端部署（公网演示）

公网地址：<http://116.62.141.168/>

云服务器为 Ubuntu 24.04，使用 Nginx 反向代理到 Gunicorn。应用目录为 `/opt/studytask`，systemd 服务名为 `studytask`，数据库位于 `/opt/studytask/instance/studytask.sqlite3`，服务器时区为 `Asia/Shanghai`。

```bash
# 登录服务器后执行
systemctl status studytask
systemctl restart studytask
nginx -t
systemctl restart nginx
```

Gunicorn 只监听 `127.0.0.1:8000`，Nginx 对外提供 80 端口。服务器账号和密码不写入仓库，请由项目所有者保管。公网版本无登录保护，仅用于课程演示。

## 3. 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

macOS / Linux：

```bash
.venv/bin/python -m pytest -q
```

当前自动化测试共 20 条，覆盖 SRS 的 FR-01 至 FR-10、T1–T10，以及 200 条任务的数据规模检查。测试使用独立临时数据库，不会修改 `instance/studytask.sqlite3`。

验收对照与逐条证据见 [docs/acceptance.md](docs/acceptance.md)。

## 4. 提交材料

| 材料 | 文件 |
| --- | --- |
| 可运行源代码 | `run.py`、`studytask/`、`tests/` |
| 运行与测试说明 | 本 README、`requirements.txt` |
| 需求验收表（T1–T10） | [docs/acceptance.md](docs/acceptance.md) |
| 实验报告（4 页） | [docs/StudyTask实验报告.docx](docs/StudyTask实验报告.docx)、[PDF 版](docs/StudyTask实验报告.pdf) |
| 演示 PPT | [docs/StudyTask演示.pptx](docs/StudyTask演示.pptx) |
| AI 协作日志 | [AI_DEV_LOG.md](AI_DEV_LOG.md) |

## 5. 功能与 SRS 对照

| 需求 | 实现 |
| --- | --- |
| FR-01 新建任务 | `/tasks/new` 表单；名称 1–100 字、课程 1–60 字、描述 ≤1000 字、日期 YYYY-MM-DD、优先级必填、状态默认“待完成” |
| FR-02 列表与详情 | 列表显示名称、课程、截止日期、状态、优先级和提醒；点击进入详情 |
| FR-03 修改 | `/tasks/<id>/edit` 修改全部字段，列表与详情读取同一数据库记录 |
| FR-04 删除 | 先进入独立确认页，取消返回详情，确认后 POST 删除 |
| FR-05 状态 | 待完成 / 进行中 / 已完成；详情页可调整状态 |
| FR-06 筛选 | 课程、状态、优先级三个条件按 AND 组合 |
| FR-07 提醒 | 未完成且截止日期早于今天：“逾期”；今天起 3 天内：“即将到期”；已完成不提醒 |
| FR-08 统计 | 首页显示全部任务总数、已完成数、完成率；0 条任务时显示 0% |
| FR-09 持久化 | SQLite 文件持久化；重启进程后数据仍可查询 |
| FR-10 中文与容错 | 中文界面、字段级错误提示、400/404 页面；非法输入不会写入数据库 |

日期提醒在每次渲染时按服务器本地日期动态计算，不写入数据库状态字段。

## 6. 项目结构

```text
.
├── run.py                     # 本地启动入口
├── requirements.txt           # Python 依赖
├── pytest.ini                 # pytest 配置
├── README.md
├── AI_DEV_LOG.md              # AI 协作过程记录
├── docs/
│   ├── acceptance.md          # T1–T10 验收记录
│   ├── StudyTask实验报告.docx  # 4 页实验报告
│   ├── StudyTask实验报告.pdf
│   └── StudyTask演示.pptx      # 演示用 PPT
├── instance/
│   └── studytask.sqlite3      # 运行时生成，已加入 .gitignore
├── studytask/
│   ├── __init__.py            # 应用工厂、当前日期
│   ├── db.py                  # SQLite 连接与初始化
│   ├── routes.py              # 页面路由
│   ├── tasks.py               # 校验、查询、提醒、统计
│   ├── schema.sql             # 表结构与索引
│   ├── templates/
│   └── static/style.css
└── tests/
    ├── conftest.py
    └── test_studytask.py
```

## 7. 数据表

`tasks` 表字段：`id`、`name`、`course`、`description`、`due_date`、`priority`、`status`、`created_at`、`updated_at`。数据库层也设置了名称/课程/描述长度、日期格式、优先级和状态枚举约束，并建立课程、状态、优先级、截止日期索引。

## 8. 已知限制

1. 公网版本使用 HTTP，无 HTTPS；应用没有登录、权限和 CSRF 防护，任何拿到地址的人都能修改任务，只适合课程演示，不要录入敏感信息。
2. SQLite 适合单机单写入者；公网环境为 Nginx + 2 个 Gunicorn worker，不支持高并发或多实例写入。
3. Flask 开发服务器只用于本地运行与验收；公网部署改用 Gunicorn。
4. 删除为物理删除，没有回收站、撤销、备份或导出功能；服务器故障或误删无法恢复。
5. 没有分页；目标规模为 200 条任务，当前实现一次渲染全部结果，更大数据量需要另行优化。
6. 截止日期是纯日期，不含时间和时区；“今天”取服务器本地日期，服务器已设置为 Asia/Shanghai。
7. 完成率保留一位小数，整数结果省略小数位（如 40%）；完成率按全部任务计算，不受列表筛选影响。
8. 数据库结构在启动时以 `CREATE TABLE IF NOT EXISTS` 保证存在，没有版本化迁移工具。
9. 无演示数据；首次启动为空列表，需要手动新建任务。
10. 公网演示环境没有自动备份；云服务器到期时间为 2026-12-13，到期后公网地址将不可用。