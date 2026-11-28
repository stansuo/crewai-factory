import pytest

from crewai_factory.guard import check_draft


@pytest.mark.parametrize(
    ("text", "units"),
    [
        ("abcd", 4),
        ("🧑‍💻", 5),
        ("https://example.com?x=1", 23),
        ("https://example.com/", 23),
        ("🇦🇦" * 71, 284),
        ("A\u10ff\u1100", 4),
        ("A\u200d\u200e\u2010\u2020\u2032\u2038", 10),
        ("🇹🇼1️⃣👍🏽❤️", 8),
        ("example.org https://example.net", 47),
        ("泡茶a", 5),
        ("e\u0301", 1),
        ("👩‍💻", 2),
        ("Visit https://example.com/a/long/path.", 30),
        ("example.com", 23),
    ],
)
def test_length_boundary(text: str, units: int) -> None:
    assert check_draft(text, units) == []
    assert len(check_draft(text, units - 1)) == 1


@pytest.mark.parametrize("text", ["[insert link here]", "{{topic}}", "TBD", "  "])
def test_unfinished_copy(text: str) -> None:
    assert check_draft(text, 280)


def test_recent_fixture_and_multiple_violations() -> None:
    post = "Here's your post: add [link] before heading into the mountains."
    recent = ["A different topic.", post.upper().replace("HEADING", "HIKING")]
    assert len(check_draft(post, 20, recent)) == 4
    assert (
        check_draft(
            "Today's reading [1] covers how a language model works.", 280, recent
        )
        == []
    )


@pytest.mark.parametrize(
    "text",
    [
        "\ufeff",
        "hello\ufffe",
        "\uffff!",
        " \u200d\u2060\ufe0f ",
        "Download [PRODUCT_NAME] today.",
        "Here is your requested tweet: Coffee first.",
    ],
)
def test_rejected_drafts(text: str) -> None:
    assert check_draft(text, 280)


def test_spanish_todo_is_prose() -> None:
    assert check_draft("Mañana todo cambia.", 280) == []


@pytest.mark.parametrize("prefix", ["#", "@", "user@", "label:", "茶"])
def test_adjacent_long_domain_keeps_literal_weight(prefix: str) -> None:
    domain = "b" * 50 + ".com"
    literal_weight = 54 + (2 if prefix == "茶" else len(prefix))
    assert check_draft(prefix + domain, 280) == []
    assert check_draft(prefix + domain, literal_weight - 1)


def test_oversized_url_keeps_literal_weight() -> None:
    assert check_draft("https://example.com/" + "a" * 4100, 280)


@pytest.mark.parametrize(
    ("text", "canonical"),
    [
        ("https://t.co/a/long/path", 33),
        ("café.com", 23),
        ("x.中国", 23),
        ("é.fr", 23),
        ("a.co,b.io", 47),
        ("example.com?x=1", 27),
        ("a。com", 6),
        ("a．com", 6),
        ("a｡com", 6),
        ("x.ai", 23),
        ("me@example.com", 14),
    ],
)
def test_uncertain_urls_do_not_undercount(text: str, canonical: int) -> None:
    assert check_draft(text, canonical - 1)
    assert check_draft(text, 280) == []
