import sqlite3
import math

DB = "news.db"


# =========================
# SAFE DB INIT (MTECH FIX)
# =========================
def init_tables():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_interests(
        username TEXT,
        category TEXT,
        count INTEGER DEFAULT 0,
        PRIMARY KEY(username, category)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS article_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        article_title TEXT,
        category TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS article_popularity(
        article_title TEXT PRIMARY KEY,
        views INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_graph(
        username TEXT,
        article_title TEXT
    )
    """)

    conn.commit()
    conn.close()


init_tables()


# =========================
# USER INTEREST MODEL
# =========================
def update_interest(username, category):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT count FROM user_interests
        WHERE username=? AND category=?
    """, (username, category))

    result = cur.fetchone()

    if result:
        cur.execute("""
            UPDATE user_interests
            SET count = count + 1
            WHERE username=? AND category=?
        """, (username, category))
    else:
        cur.execute("""
            INSERT INTO user_interests(username, category, count)
            VALUES (?, ?, 1)
        """, (username, category))

    conn.commit()
    conn.close()


# =========================
# USER PROFILE (NORMALIZED IMPORTANCE)
# =========================
def get_user_profile(username):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT category, count
        FROM user_interests
        WHERE username=?
        ORDER BY count DESC
        LIMIT 5
    """, (username,))

    data = cur.fetchall()
    conn.close()

    # Normalize scores (M.Tech improvement)
    total = sum([x[1] for x in data]) or 1

    profile = [
        (cat, round(cnt / total, 3))
        for cat, cnt in data
    ]

    return profile


# =========================
# ARTICLE TRACKING (GRAPH MODEL)
# =========================
def track_article(username, title, category):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO article_history(username, article_title, category)
        VALUES (?, ?, ?)
    """, (username, title, category))

    cur.execute("""
        INSERT INTO article_popularity(article_title, views)
        VALUES (?, 1)
        ON CONFLICT(article_title)
        DO UPDATE SET views = views + 1
    """, (title,))

    cur.execute("""
        INSERT INTO user_graph(username, article_title)
        VALUES (?, ?)
    """, (username, title))

    conn.commit()
    conn.close()


# =========================
# POPULARITY SCORE (IMPROVED NORMALIZATION)
# =========================
def get_popularity_score(title):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT views FROM article_popularity
        WHERE article_title=?
    """, (title,))

    result = cur.fetchone()
    conn.close()

    if result:
        # log scaling = M.Tech improvement
        return round(math.log(1 + result[0]), 3)

    return 0.0


# =========================
# EXPLAINABILITY ENGINE (NEW - MTECH FEATURE)
# =========================
def explain_recommendation(username, category, score):

    profile = get_user_profile(username)

    top_interest = profile[0][0] if profile else "general"

    explanation = (
        f"Recommended because you frequently read '{top_interest}' "
        f"and this article matches '{category}' category. "
        f"Relevance score: {score}"
    )

    return explanation