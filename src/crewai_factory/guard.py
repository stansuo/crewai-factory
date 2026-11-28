"""Deterministic checks shared by draft review and future publish callers."""

import re
import unicodedata
from collections.abc import Sequence
from difflib import SequenceMatcher

# twitter/twitter-text config/v3.json and js/src/parseTweet.js.
# Recognize a limited set of common DNS suffixes and ASCII URL paths.
_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_DOMAIN = rf"(?:www\.)?{_LABEL}\.(?:com|org|net|edu|gov|io|dev|app|co|uk|tw|jp)"
# Discount only complete whitespace-delimited links. Limit paths/queries to
# forms with an unambiguous end; the final sentence period stays outside.
_PATH = r"(?:/|/[a-z0-9/_-]*[a-z0-9/])"
_QUERY = r"(?:\?[a-z0-9]+=[a-z0-9]+(?:&[a-z0-9]+=[a-z0-9]+)*)?"
_URL = re.compile(
    rf"(?<!\S)(?:https?://{_DOMAIN}{_PATH}?{_QUERY}|{_DOMAIN}{_PATH}?)"
    r"(?=\.?(?:\s|$))",
    re.IGNORECASE | re.ASCII,
)
# Every dotted hostname consumes at least one internal separator. For
# unparsed text, reserve a whole transformed URL per possible separator;
# this also covers partial recognition and several URLs inside one token.
_DOMAIN_SEPARATOR = re.compile(r"(?<=\S)[.。．｡](?=\S)")
# These sequences have weight two. Other emoji fall back to code-point weights.
_EMOJI = re.compile(
    r"🇹🇼|🇺🇸|🇯🇵|[0-9#*]\ufe0f?\u20e3|"
    r"[👩👨][🏻-🏿]?\u200d💻|[👍👎👋🙏][🏻-🏿]|❤\ufe0f"
)
_SINGLE = re.compile(r"[\x00-\u10ff\u2000-\u200d\u2010-\u201f\u2032-\u2037]")
_INVALID = re.compile(r"[\ufeff\ufffe\uffff\ud800-\udfff]")


def _text_weight(text: str) -> int:
    # Each recognized emoji has the same weight as a single CJK character.
    weighted_text = _EMOJI.sub("界", text)
    return 2 * len(weighted_text) - len(_SINGLE.findall(weighted_text))


def _literal_weight(text: str) -> int:
    expansion = 23 * len(_DOMAIN_SEPARATOR.findall(text))
    return _text_weight(text) + expansion


def _weighted_length(text: str) -> int:
    normalized = unicodedata.normalize("NFC", text)
    end = 0
    length = 0
    for url in _URL.finditer(normalized):
        # Leave ample room below twitter-text's maximum URL length, including
        # the implicit scheme on bare domains.
        # The canonical parser may wrap only the first segment of a t.co URL.
        host = url[0].lower().split("://")[-1].split("/")[0].split("?")[0]
        if host == "t.co" or len(url[0]) > 4000:
            continue
        length += _literal_weight(normalized[end : url.start()]) + 23
        end = url.end()
    return length + _literal_weight(normalized[end:])


_PLACEHOLDER = re.compile(
    r"(?-i:\b(?:TODO|TBD|FIXME)\b|"
    r"\[[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\])|\{\{[^{}\n]+\}\}|"
    r"\[(?:insert\b[^\]\n]*|(?:your )?(?:link|topic|name|placeholder)(?: here)?)\]"
    r"|<(?:insert [^<>\n]+|placeholder)>",
    re.IGNORECASE,
)
_META = re.compile(
    r"^\s*(?:(?:sure|certainly)[!,.:]?\s*)?"
    r"(?:here(?:['’]s| is) (?:your|a|the) (?:requested )?(?:draft|tweet|post)"
    r"(?: for you)?(?:\s*:|[.!]?\s*$)"
    r"|(?:draft (?:tweet|post)|final answer)\s*:|as an ai language model\b)",
    re.IGNORECASE | re.MULTILINE,
)


def _comparison_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def check_draft(
    text: str, max_length: int, recent_posts: Sequence[str] = ()
) -> list[str]:
    """Return revision notes in rule order. An empty list means all checks passed."""
    violations = []
    length = _weighted_length(text)
    if _INVALID.search(text):
        violations.append("Remove invalid Unicode characters.")
    if not any(unicodedata.category(c)[0] in "LNPS" for c in text):
        violations.append("Write a post with visible content.")
    elif length > max_length:
        violations.append(
            f"Shorten the post (guard estimate {length}, limit {max_length} X units)."
        )
    if _PLACEHOLDER.search(text):
        violations.append("Replace template placeholders with finished copy.")
    if _META.search(text):
        violations.append("Remove generation commentary and return only the post.")

    candidate = _comparison_text(text)
    for previous in recent_posts:
        normalized = _comparison_text(previous)
        if (
            normalized
            and SequenceMatcher(None, normalized, candidate, autojunk=False).ratio()
            >= 0.9
        ):
            violations.append("Rewrite the post to distinguish it from a recent post.")
            break
    return violations
