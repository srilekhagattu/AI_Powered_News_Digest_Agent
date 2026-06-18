RELATED_TOPICS = {

    "Cricket": [
        "Football",
        "Olympics",
        "Fitness"
    ],

    "AI": [
        "Cybersecurity",
        "Data Science",
        "Cloud Computing"
    ],

    "Cloud Computing": [
        "DevOps",
        "Cybersecurity",
        "AI"
    ],

    "Business": [
        "Economy",
        "Startups",
        "Stock Market"
    ]
}


def get_rgrec_recommendations(interests):

    recommendations = []

    for item in interests:

        recommendations.append(item)

        if item in RELATED_TOPICS:

            recommendations.extend(
                RELATED_TOPICS[item]
            )

    return list(set(recommendations))