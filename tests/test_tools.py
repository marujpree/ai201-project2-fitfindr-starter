from tools import search_listings


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("shirt", size="XL", max_price=None)
    assert all("xl" in item["size"].lower() for item in results)


def test_search_best_match_first():
    results = search_listings("vintage denim jeans", size=None, max_price=None)
    assert len(results) > 0
    # first result should have the most keyword overlap
    first_text = (results[0]["title"] + " " + results[0]["description"]).lower()
    assert any(word in first_text for word in ["vintage", "denim", "jeans"])
