import sqlite3


def save_bookmark(username, title, url, source):

    conn = sqlite3.connect("news.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO bookmarks(username,title,url,source)
        VALUES(?,?,?,?)
        """,
        (username, title, url, source)
    )

    conn.commit()
    conn.close()


def get_bookmarks(username):

    conn = sqlite3.connect("news.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id,title,url,source
        FROM bookmarks
        WHERE username=?
        """,
        (username,)
    )

    data = cursor.fetchall()

    conn.close()

    return data


def delete_bookmark(bookmark_id):

    conn = sqlite3.connect("news.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM bookmarks
        WHERE id=?
        """,
        (bookmark_id,)
    )

    conn.commit()
    conn.close()