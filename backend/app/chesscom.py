"""Fetch a player's games from the Chess.com public data API (no key needed).

The API has no "latest N games" endpoint. It has:
  GET /pub/player/{user}/games/archives  -> {"archives": [month_url, ...]}, oldest first
  GET /pub/player/{user}/games/{YYYY}/{MM} -> {"games": [...]}, oldest first within the month

The archives list is cached by Chess.com for ~60 s, but the current month is only
cached for ~5 s, so finished games show up within seconds. We therefore read the
current month directly and only touch the archives list when we need older games.
Only finished games are listed; games in progress never appear.
"""

from collections import OrderedDict
from datetime import datetime, timezone

import httpx

BASE_URL = "https://api.chess.com/pub"
# Chess.com asks API clients to identify themselves with a User-Agent.
HEADERS = {"User-Agent": "ChessLab/0.1 (personal game analysis project)"}

# url -> (etag, body). Lets frequent syncs send If-None-Match and get a cheap 304 back.
_ETAG_CACHE: "OrderedDict[str, tuple[str, dict]]" = OrderedDict()
_ETAG_CACHE_SIZE = 256


class ChessComError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def current_month() -> tuple[int, int]:
    # Chess.com archives are split by UTC month.
    now = datetime.now(timezone.utc)
    return now.year, now.month


async def _get_json(client: httpx.AsyncClient, url: str) -> dict:
    headers = dict(HEADERS)
    cached = _ETAG_CACHE.get(url)
    if cached:
        headers["If-None-Match"] = cached[0]
    try:
        response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise ChessComError(f"Could not reach Chess.com: {exc}") from exc
    if response.status_code == 304 and cached:
        _ETAG_CACHE.move_to_end(url)
        return cached[1]
    if response.status_code == 404:
        raise ChessComError("Chess.com user not found.", status_code=404)
    if response.status_code == 429:
        raise ChessComError("Chess.com rate limit hit, try again shortly.", status_code=429)
    if response.status_code != 200:
        raise ChessComError(f"Chess.com returned {response.status_code}.")

    body = response.json()
    etag = response.headers.get("ETag")
    if etag:
        _ETAG_CACHE[url] = (etag, body)
        _ETAG_CACHE.move_to_end(url)
        if len(_ETAG_CACHE) > _ETAG_CACHE_SIZE:
            _ETAG_CACHE.popitem(last=False)
    return body


async def fetch_recent_games(
    username: str,
    limit: int,
    client: httpx.AsyncClient,
    stop_at: set[str] | None = None,
) -> list[dict]:
    """Return up to `limit` of the user's most recent games, newest first.

    If `stop_at` is given, stop at the first game whose URL is in it: everything older
    is already imported, so a sync usually costs a single request.
    Each item is the raw Chess.com game object (has "pgn", "url", "time_class", ...).
    """
    user_url = f"{BASE_URL}/player/{username.lower()}/games"
    year, month = current_month()
    this_month = f"{user_url}/{year}/{month:02d}"

    collected: list[dict] = []

    def take(month_body: dict) -> bool:
        """Add a month's games newest first. Returns True when we should stop."""
        games = [g for g in month_body.get("games", []) if g.get("pgn")]
        for game in reversed(games):
            if stop_at is not None and game.get("url") in stop_at:
                return True
            collected.append(game)
            if len(collected) >= limit:
                return True
        return False

    try:
        if take(await _get_json(client, this_month)):
            return collected
    except ChessComError as exc:
        # No games yet this month can come back as 404; the archives call below
        # tells us whether the user exists at all.
        if exc.status_code != 404:
            raise

    archives = (await _get_json(client, f"{user_url}/archives")).get("archives", [])
    for month_url in reversed(archives):  # newest month first
        if month_url == this_month:
            continue  # already read above
        if take(await _get_json(client, month_url)):
            break
    return collected
