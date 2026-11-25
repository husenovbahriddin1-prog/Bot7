import json
import asyncpg
from datetime import datetime, timezone

class Database:
    def __init__(self, url: str):
        self.url = url
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.url, min_size=1, max_size=5)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def create_tables(self):
        async with self.pool.acquire() as c:
            await c.execute("""
            CREATE TABLE IF NOT EXISTS groups_info(
              chat_id BIGINT PRIMARY KEY, title TEXT NOT NULL,
              first_seen TIMESTAMPTZ DEFAULT NOW(), last_seen TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS messages(
              id BIGSERIAL PRIMARY KEY, chat_id BIGINT REFERENCES groups_info(chat_id),
              message_id BIGINT, user_id BIGINT, user_name TEXT, body TEXT,
              sent_at TIMESTAMPTZ, UNIQUE(chat_id, message_id)
            );
            CREATE TABLE IF NOT EXISTS issues(
              id BIGSERIAL PRIMARY KEY, chat_id BIGINT REFERENCES groups_info(chat_id),
              group_title TEXT, title TEXT, details TEXT, status TEXT DEFAULT 'Ochiq',
              raised_by TEXT, responsible TEXT, last_update TEXT,
              created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS questions(
              id BIGSERIAL PRIMARY KEY, chat_id BIGINT REFERENCES groups_info(chat_id),
              group_title TEXT, question TEXT, asked_by TEXT,
              status TEXT DEFAULT 'Javobsiz', created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS tasks(
              id BIGSERIAL PRIMARY KEY, chat_id BIGINT REFERENCES groups_info(chat_id),
              group_title TEXT, title TEXT, responsible TEXT, status TEXT DEFAULT 'Jarayonda',
              due_hint TEXT, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """)

    async def upsert_group(self, chat_id, title):
        async with self.pool.acquire() as c:
            await c.execute("""
              INSERT INTO groups_info(chat_id,title) VALUES($1,$2)
              ON CONFLICT(chat_id) DO UPDATE SET title=EXCLUDED.title,last_seen=NOW()
            """, chat_id, title)

    async def save_message(self, chat_id, message_id, user_id, user_name, text, sent_at):
        async with self.pool.acquire() as c:
            await c.execute("""
              INSERT INTO messages(chat_id,message_id,user_id,user_name,body,sent_at)
              VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(chat_id,message_id) DO NOTHING
            """, chat_id, message_id, user_id, user_name, text, sent_at)

    async def recent_messages(self, chat_id, limit=25):
        async with self.pool.acquire() as c:
            rows = await c.fetch("""
              SELECT user_name, body, sent_at FROM messages
              WHERE chat_id=$1 ORDER BY sent_at DESC LIMIT $2
            """, chat_id, limit)
        return [dict(r) for r in reversed(rows)]

    async def apply_analysis(self, chat_id, group_title, data, author):
        async with self.pool.acquire() as c:
            for item in data.get("issues", []):
                if item.get("action") == "resolve":
                    await c.execute("""
                      UPDATE issues SET status='Hal qilindi', last_update=$2, updated_at=NOW()
                      WHERE chat_id=$1 AND status <> 'Hal qilindi'
                      AND title ILIKE '%' || $3 || '%'
                    """, chat_id, item.get("evidence", ""), item.get("title", "")[:80])
                elif item.get("action") == "open":
                    await c.execute("""
                      INSERT INTO issues(chat_id,group_title,title,details,raised_by,responsible,last_update)
                      VALUES($1,$2,$3,$4,$5,$6,$7)
                    """, chat_id, group_title, item.get("title","Nomi aniqlanmagan"),
                         item.get("details",""), item.get("raised_by") or author,
                         item.get("responsible"), item.get("evidence",""))
                elif item.get("action") == "update":
                    await c.execute("""
                      UPDATE issues SET last_update=$2, updated_at=NOW(),
                      responsible=COALESCE($3,responsible)
                      WHERE chat_id=$1 AND status <> 'Hal qilindi'
                      AND title ILIKE '%' || $4 || '%'
                    """, chat_id, item.get("evidence",""), item.get("responsible"),
                         item.get("title","")[:80])

            for q in data.get("questions", []):
                if q.get("action") == "ask":
                    await c.execute("""
                      INSERT INTO questions(chat_id,group_title,question,asked_by)
                      VALUES($1,$2,$3,$4)
                    """, chat_id, group_title, q.get("question",""), q.get("asked_by") or author)
                elif q.get("action") == "answer":
                    await c.execute("""
                      UPDATE questions SET status='Javob berildi'
                      WHERE chat_id=$1 AND status='Javobsiz'
                      AND question ILIKE '%' || $2 || '%'
                    """, chat_id, q.get("question_hint",""))

            for t in data.get("tasks", []):
                if t.get("action") == "create":
                    await c.execute("""
                      INSERT INTO tasks(chat_id,group_title,title,responsible,due_hint)
                      VALUES($1,$2,$3,$4,$5)
                    """, chat_id, group_title, t.get("title",""), t.get("responsible"), t.get("due_hint"))
                elif t.get("action") == "complete":
                    await c.execute("""
                      UPDATE tasks SET status='Bajarildi',updated_at=NOW()
                      WHERE chat_id=$1 AND status <> 'Bajarildi'
                      AND title ILIKE '%' || $2 || '%'
                    """, chat_id, t.get("title_hint",""))

    async def list_groups(self):
        async with self.pool.acquire() as c:
            return await c.fetch("SELECT chat_id,title FROM groups_info ORDER BY title")

    async def list_open_issues(self):
        async with self.pool.acquire() as c:
            return await c.fetch("SELECT * FROM issues WHERE status <> 'Hal qilindi' ORDER BY updated_at")

    async def list_open_questions(self):
        async with self.pool.acquire() as c:
            return await c.fetch("SELECT * FROM questions WHERE status='Javobsiz' ORDER BY created_at")

    async def list_responsibilities(self):
        async with self.pool.acquire() as c:
            return await c.fetch("SELECT * FROM tasks WHERE status <> 'Bajarildi' ORDER BY created_at")

    async def report_data(self, days=1):
        async with self.pool.acquire() as c:
            groups = await c.fetch("SELECT * FROM groups_info ORDER BY title")
            issues = await c.fetch("""
              SELECT * FROM issues WHERE status <> 'Hal qilindi'
              AND updated_at > NOW() - ($1 * INTERVAL '1 day') ORDER BY updated_at
            """, days)
            questions = await c.fetch("""
              SELECT * FROM questions WHERE status='Javobsiz'
              AND created_at > NOW() - ($1 * INTERVAL '1 day') ORDER BY created_at
            """, days)
            solved = await c.fetch("""
              SELECT COUNT(*) AS n FROM issues WHERE status='Hal qilindi'
              AND updated_at > NOW() - ($1 * INTERVAL '1 day')
            """, days)
            tasks = await c.fetch("""
              SELECT * FROM tasks WHERE status <> 'Bajarildi'
              AND created_at > NOW() - ($1 * INTERVAL '1 day')
            """, days)
        return groups, issues, questions, solved[0]["n"], tasks
