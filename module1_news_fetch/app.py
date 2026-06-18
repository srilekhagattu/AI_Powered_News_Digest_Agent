from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from textblob import TextBlob
import requests
import os
import uuid
from gtts import gTTS
import sqlite3
import re

from modules.bookmarks import save_bookmark, get_bookmarks, delete_bookmark
from modules.translator import translate_text
from modules.rgrec import get_rgrec_recommendations
from modules.muma import get_muma_recommendations
from modules.hybrid import hybrid_recommendations
from modules.summarizer import summarize
from modules.recommendation import (
    update_interest,
    get_user_profile,
    track_article,
    get_popularity_score
)

# ✅ SAFE IMPORT (fix crash)
try:
    from modules.collaborative import save_interaction, get_collaborative_recommendations
except:
    def save_interaction(*args, **kwargs):
        pass

    def get_collaborative_recommendations(username):
        return []

app = Flask(__name__)
app.secret_key = "secret123"

API_KEY = "9ffdc75e97b241e383f9f2b367de3218"

# =========================
# INIT DB
# =========================
def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# =========================
# SENTIMENT
# =========================
def get_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0:
        return "positive"
    elif polarity < 0:
        return "negative"
    return "neutral"

# =========================
# CATEGORY MAP
# =========================
CATEGORY_MAP = {
    "technology": "technology OR AI OR software OR gadgets OR programming",
    "business": "business OR economy OR stock market OR startups OR finance",
    "sports": "cricket OR football OR IPL OR sports",
    "health": "health OR fitness OR medicine",
    "entertainment": "movies OR celebrity OR bollywood OR hollywood",
    "science": "science OR space OR NASA OR research",
    "politics": "politics OR government OR election OR parliament OR policy OR minister"
}

TELANGANA_KEYWORDS = "telangana OR hyderabad OR kcr OR revanth reddy OR brs OR congress"

# =========================
# QUERY BUILDER
# =========================
def build_query(category, subcategory, search, username, location):

    if category:

        interest = subcategory or category
        update_interest(username, interest)
        save_interaction(username, interest)

        if search:
            query = search

        elif subcategory:
            query = subcategory

        else:
            query = CATEGORY_MAP.get(category, category)

    else:

        profile = get_user_profile(username)

        if profile:

            interests = [i[0] for i in profile]

            rgrec = get_rgrec_recommendations(interests)
            muma = get_muma_recommendations(interests)
            collab = get_collaborative_recommendations(username)

            final = hybrid_recommendations(muma + rgrec, collab)

            query = " OR ".join(list(set(final)))

        else:
            query = "technology OR business OR sports"

    # LOCATION FILTER
    if location == "india":

        if category:
            query = f"India AND ({query})"
        else:
            query = "India"

    elif location == "telangana":

        if category:
            query = f"(Telangana OR Hyderabad) AND ({query})"
        else:
            query = "Telangana OR Hyderabad"

    print("FINAL QUERY =", query)

    return query.strip()

# =========================
# FETCH NEWS
# =========================
def fetch_news(query):

    url = (
        "https://newsapi.org/v2/everything?"
        f"q={query}"
        "&language=en"
        "&sortBy=publishedAt"
        "&pageSize=30"
        f"&apiKey={API_KEY}"
    )

    print(url)

    try:

        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get("status") != "ok":
            print(data)
            return []

        return data.get("articles", [])

    except Exception as e:
        print("ERROR:", e)
        return []

# =========================
# FILTER TELANGANA FIX
# =========================
def filter_telangana(articles, location):
    if location != "telangana":
        return articles

    keywords = ["telangana", "hyderabad", "kcr", "revanth", "brs", "congress"]
    filtered = []

    for a in articles:
        text = ((a.get("title") or "") + " " + (a.get("description") or "")).lower()
        if any(k in text for k in keywords):
            filtered.append(a)

    return filtered

# =========================
# ROOT
# =========================
@app.route("/")
def index():

    category = request.args.get("category")
    subcategory = request.args.get("subcategory", "")
    search = request.args.get("query", "")
    location = request.args.get("location", "world")
    language = request.args.get("language", "en")

    query = "technology OR AI OR business OR sports"

    articles = fetch_news(query)

    news_list = []

    for article in articles:

        title = article.get("title") or ""
        desc = article.get("description") or ""

        news_list.append({
            "title": title,
            "summary": summarize(title + " " + desc),
            "source": article.get("source", {}).get("name"),
            "image": article.get("urlToImage"),
            "url": article.get("url"),
            "score": get_popularity_score(title),
            "sentiment": get_sentiment(title + " " + desc),
            "reason": "Trending News"
        })

    return render_template(
        "index.html",
        news=news_list,
        user="Guest",
        category=category,
        subcategory=subcategory,
        location=location,
        language=language
    )

# =========================
# HOME
# =========================
@app.route("/home")
def home():

    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]

    category = request.args.get("category")
    subcategory = request.args.get("subcategory", "")
    search = request.args.get("query", "")
    location = request.args.get("location", "world")
    language = request.args.get("language", "en")

    print("CATEGORY =", category)
    print("SUBCATEGORY =", subcategory)
    print("LOCATION =", location)

    query = build_query(
        category,
        subcategory,
        search,
        username,
        location
    )

    print("QUERY =", query)

    articles = fetch_news(query)
    articles = filter_telangana(articles, location)

    news_list = []

    profile = get_user_profile(username)
    interests = [i[0].lower() for i in profile] if profile else []

    for article in articles:

        title = article.get("title") or ""
        desc = article.get("description") or ""
        full_text = title + " " + desc

        summary_en = summarize(full_text)

        try:
            if language != "en":
                title_final = translate_text(title, language)
                summary_final = translate_text(summary_en, language)
            else:
                title_final = title
                summary_final = summary_en
        except:
            title_final = title
            summary_final = summary_en

        reason = "Trending News"

        for interest in interests:
            if interest.lower() in full_text.lower():
                reason = f"Matched your interest: {interest.title()}"
                break

        news_list.append({
            "title": title_final,
            "summary": summary_final,
            "source": article.get("source", {}).get("name"),
            "image": article.get("urlToImage"),
            "url": article.get("url"),
            "score": get_popularity_score(title),
            "sentiment": get_sentiment(full_text),
            "reason": reason
        })

    news_list.sort(key=lambda x: x["score"], reverse=True)

    return render_template(
        "index.html",
        news=news_list,
        user=username,
        category=category,
        subcategory=subcategory,
        location=location,
        language=language
    )
# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    msg = ""

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            msg = "All fields required"

        elif " " in username:
            msg = "Spaces not allowed in email"

        elif len(username) < 5:
            msg = "Email too short"

        elif len(password) < 6:
            msg = "Password too short"

        else:
            conn = sqlite3.connect("users.db")
            cur = conn.cursor()

            cur.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username, password)
            )

            user = cur.fetchone()
            conn.close()

            if user:
                session["user"] = username
                return redirect(url_for("home"))
            else:
                msg = "Incorrect email or password"

    return render_template("login.html", message=msg)
# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():

    msg = ""

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not username or not password or not confirm_password:
            msg = "All fields required"

        elif not re.match(r"^[a-zA-Z0-9_.+-]+@gmail\.com$", username):
            msg = "Only Gmail allowed"

        elif " " in username:
            msg = "Spaces not allowed in email"

        elif len(username) < 8:
            msg = "Email too short"

        elif password != confirm_password:
            msg = "Passwords do not match"

        elif len(password) < 6:
            msg = "Password must be at least 6 characters"

        elif not any(char.isupper() for char in password):
            msg = "Password must contain one uppercase letter"

        elif not any(char.islower() for char in password):
            msg = "Password must contain one lowercase letter"

        elif not any(char.isdigit() for char in password):
            msg = "Password must contain one number"

        elif not any(char in "@$!%*#?&" for char in password):
            msg = "Password must contain one special character"

        else:

            conn = sqlite3.connect("users.db")
            cur = conn.cursor()

            cur.execute(
                "SELECT * FROM users WHERE username=?",
                (username,)
            )

            if cur.fetchone():
                msg = "User already exists"

            else:
                cur.execute(
                    "INSERT INTO users(username,password) VALUES(?,?)",
                    (username, password)
                )

                conn.commit()
                conn.close()

                return redirect(url_for("login"))

    return render_template("register.html", message=msg)

# =========================
# NAVBAR FIX ROUTES
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/explore")
def explore():
    if "user" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("home"))

@app.route("/trending")
def trending():
    if "user" not in session:
        return redirect(url_for("login"))

    articles = fetch_news("technology OR business OR sports")

    news_list = []
    for article in articles:
        title = article.get("title") or ""
        desc = article.get("description") or ""

        news_list.append({
            "title": title,
            "summary": summarize(title + " " + desc),
            "source": article.get("source", {}).get("name"),
            "image": article.get("urlToImage"),
            "url": article.get("url"),
            "score": get_popularity_score(title),
            "sentiment": get_sentiment(title + " " + desc)
        })

    news_list.sort(key=lambda x: x["score"], reverse=True)

    return render_template("trending.html", news=news_list)

# =========================
# BOOKMARK
# =========================
@app.route("/bookmark")
def bookmark():
    if "user" not in session:
        return redirect(url_for("login"))

    save_bookmark(
        session["user"],
        request.args.get("title"),
        request.args.get("url"),
        request.args.get("source")
    )
    return redirect(url_for("home"))

@app.route("/bookmarks")
def bookmarks():
    if "user" not in session:
        return redirect(url_for("login"))

    data = get_bookmarks(session["user"])
    return render_template("bookmarks.html", bookmarks=data)

# =========================
# TRACK
# =========================
@app.route("/track")
def track():
    if "user" not in session:
        return redirect(url_for("login"))

    track_article(
        session["user"],
        request.args.get("title"),
        request.args.get("category")
    )
    return redirect(request.args.get("url"))

# =========================
# VOICE
# =========================
@app.route("/voice")
def voice():
    try:
        text = request.args.get("text", "").strip()
        lang = request.args.get("lang", "en")

        filename = f"{uuid.uuid4().hex}.mp3"
        path = os.path.join("static", filename)

        gTTS(text=text[:300], lang=lang).save(path)

        return jsonify({"audio": f"/static/{filename}"})

    except Exception as e:
        return jsonify({"error": str(e)})

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)