from collections import Counter

def get_muma_recommendations(interests):

    counter = Counter(interests)

    recommendations = []

    for topic, score in counter.most_common():

        recommendations.append(topic)

    return recommendations