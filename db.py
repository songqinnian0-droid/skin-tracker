"""
数据库模块：负责皮肤数据的存储与"新上皮肤"的判定
用 SQLite（一个文件，无需安装数据库软件）
"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "skins.db"


def get_conn():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 让查询结果可以按列名访问
    return conn


def init_db():
    """初始化表结构。首次运行会自动建表。"""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skins (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            game         TEXT NOT NULL,       -- 游戏名，如 "CS2"
            category     TEXT NOT NULL,       -- "枪械皮肤" 或 "时装皮肤"
            name         TEXT NOT NULL,       -- 皮肤名
            image_url    TEXT,                -- 图片链接
            source_url   TEXT,                -- 来源页链接
            rarity       TEXT DEFAULT '',     -- 品质名（原始游戏内名称，如"隐秘"/"Premium"）
            rarity_color TEXT DEFAULT '',     -- 品质颜色 hex，如 "#eb4b4b"
            first_seen   TEXT NOT NULL,       -- 第一次爬到的时间（ISO 格式）
            is_new       INTEGER DEFAULT 1,   -- 1=本周新增，0=旧数据
            UNIQUE(game, category, name)      -- 同游戏同类型同名视为同一条
        )
    """)
    # 兼容旧库：如果表已存在但没有 rarity 列，补上
    cols = {r[1] for r in conn.execute("PRAGMA table_info(skins)").fetchall()}
    if "rarity" not in cols:
        conn.execute("ALTER TABLE skins ADD COLUMN rarity TEXT DEFAULT ''")
    if "rarity_color" not in cols:
        conn.execute("ALTER TABLE skins ADD COLUMN rarity_color TEXT DEFAULT ''")
    conn.commit()
    conn.close()


def mark_all_as_old():
    """
    每次爬取前调用：把所有数据的 is_new 置为 0。
    爬取过程中新插入的会是 1，用来区分"本周新上"。
    """
    conn = get_conn()
    conn.execute("UPDATE skins SET is_new = 0")
    conn.commit()
    conn.close()


def upsert_skin(game: str, category: str, name: str,
                image_url: str = "", source_url: str = "",
                rarity: str = "", rarity_color: str = "") -> bool:
    """
    插入或更新一条皮肤。
    返回 True 表示是"新皮肤"（数据库里之前没有），False 表示已存在。
    对已存在的记录，会补齐缺失的 rarity / rarity_color（用于旧数据回填）。
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, rarity, rarity_color FROM skins WHERE game=? AND category=? AND name=?",
        (game, category, name)
    )
    row = cur.fetchone()

    if row:
        # 已存在：若原来 rarity 为空但本次爬到了，就补上（不改 is_new）
        if (not row["rarity"]) and rarity:
            cur.execute(
                "UPDATE skins SET rarity=?, rarity_color=? WHERE id=?",
                (rarity, rarity_color, row["id"])
            )
            conn.commit()
        conn.close()
        return False
    else:
        cur.execute("""
            INSERT INTO skins (game, category, name, image_url, source_url,
                               rarity, rarity_color, first_seen, is_new)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (game, category, name, image_url, source_url,
              rarity, rarity_color, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True


def get_all_skins():
    """获取全部皮肤，按 game / category / first_seen 排序"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM skins
        ORDER BY game, category, first_seen DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_new_skins():
    """只获取本周新增的皮肤"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM skins WHERE is_new = 1
        ORDER BY game, category, first_seen DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def stats():
    """返回统计信息：每个游戏 / 类型下的数量"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT game, category, COUNT(*) as total,
               SUM(is_new) as new_count
        FROM skins GROUP BY game, category
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    # 直接运行本文件时，初始化数据库并打印统计
    init_db()
    print(f"数据库已初始化：{DB_PATH}")
    for s in stats():
        print(s)
