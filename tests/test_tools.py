import tools

from tools import create_fit_card, search_listings, suggest_outfit


class _FakeGroqResponse:
    def __init__(self, content: str):
        self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]


class _FakeCompletions:
    def __init__(self, response: str):
        self.response = response
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeGroqResponse(self.response)


class _FakeChat:
    def __init__(self, response: str):
        self.completions = _FakeCompletions(response)


class _FakeClient:
    def __init__(self, response: str):
        self.chat = _FakeChat(response)


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


def test_suggest_outfit_empty_wardrobe(monkeypatch):
    fake_client = _FakeClient("Try a cropped tee and relaxed jeans.")
    monkeypatch.setattr(tools, "_get_groq_client", lambda: fake_client)

    result = suggest_outfit(
        {"title": "Graphic Tee", "category": "tops", "style_tags": ["vintage"], "colors": ["black"], "price": 24, "platform": "depop"},
        {"items": []},
    )

    assert result == "Try a cropped tee and relaxed jeans."
    assert "general styling advice" in fake_client.chat.completions.last_kwargs["messages"][1]["content"].lower()


def test_suggest_outfit_uses_wardrobe_items(monkeypatch):
    fake_client = _FakeClient("Style it with baggy jeans and chunky sneakers.")
    monkeypatch.setattr(tools, "_get_groq_client", lambda: fake_client)

    result = suggest_outfit(
        {"title": "Graphic Tee", "category": "tops", "style_tags": ["vintage"], "colors": ["black"], "price": 24, "platform": "depop"},
        {
            "items": [
                {"name": "Baggy Jeans", "category": "bottoms", "colors": ["blue"], "style_tags": ["streetwear"], "size": "M"},
                {"name": "Chunky Sneakers", "category": "shoes", "colors": ["white"], "style_tags": ["casual"], "size": "9"},
            ]
        },
    )

    assert result == "Style it with baggy jeans and chunky sneakers."
    prompt = fake_client.chat.completions.last_kwargs["messages"][1]["content"]
    assert "Baggy Jeans" in prompt
    assert "Chunky Sneakers" in prompt


def test_create_fit_card_empty_outfit():
    result = create_fit_card("   ", {"title": "Graphic Tee", "price": 24, "platform": "depop"})
    assert "missing or empty" in result.lower()


def test_create_fit_card_uses_item_and_outfit(monkeypatch):
    fake_client = _FakeClient("Soft layers, lived-in denim, and an easy weekend mood.")
    monkeypatch.setattr(tools, "_get_groq_client", lambda: fake_client)

    result = create_fit_card(
        "Style it with baggy jeans and chunky sneakers.",
        {"title": "Graphic Tee", "category": "tops", "style_tags": ["vintage"], "colors": ["black"], "price": 24, "platform": "depop"},
    )

    assert result == "Soft layers, lived-in denim, and an easy weekend mood."
    prompt = fake_client.chat.completions.last_kwargs["messages"][1]["content"]
    assert "Graphic Tee" in prompt
    assert "24" in prompt
    assert "depop" in prompt
    assert "Style it with baggy jeans and chunky sneakers." in prompt
    assert fake_client.chat.completions.last_kwargs["temperature"] >= 1.0
