from app.storage import cosine_similarity


def test_cosine_similarity_direction():
    assert cosine_similarity([1, 0], [1, 0]) == 1
    assert cosine_similarity([1, 0], [0, 1]) == 0
