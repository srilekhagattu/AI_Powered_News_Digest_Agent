def hybrid_recommendations(content_based, collaborative):

    combined = []

    # Content-based first priority
    for item in content_based:
        if item not in combined:
            combined.append(item)

    # Collaborative second priority
    for item in collaborative:
        if item not in combined:
            combined.append(item)

    # Return top results (M.Tech ranking logic)
    return combined[:10]