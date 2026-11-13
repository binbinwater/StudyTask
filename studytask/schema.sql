CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
        CHECK (length(trim(name)) BETWEEN 1 AND 100),
    course TEXT NOT NULL
        CHECK (length(trim(course)) BETWEEN 1 AND 60),
    description TEXT NOT NULL DEFAULT ''
        CHECK (length(description) <= 1000),
    due_date TEXT NOT NULL
        CHECK (due_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    priority TEXT NOT NULL DEFAULT '中'
        CHECK (priority IN ('高', '中', '低')),
    status TEXT NOT NULL DEFAULT '待完成'
        CHECK (status IN ('待完成', '进行中', '已完成')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks (due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_course ON tasks (course);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority);