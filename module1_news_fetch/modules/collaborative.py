from collections import Counter

# In-memory user history (M.Tech simple collaborative system)
user_history = {}


# =========================
# SAVE USER INTERACTION
# =========================
def save_interaction(username, category):

    if username not in user_history:
        user_history[username] = []

    user_history[username].append(category)


# =========================
# COLLABORATIVE RECOMMENDATION
# =========================
def get_collaborative_recommendations(username):

    if username not in user_history:
        return []

    target_interests = set(user_history[username])
    scores = Counter()

    for user, interests in user_history.items():

        if user == username:
            continue

        common = len(target_interests.intersection(set(interests)))

        if common > 0:
            for item in interests:
                if item not in target_interests:
                    scores[item] += common

    return [x[0] for x in scores.most_common(5)]