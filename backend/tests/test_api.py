import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app import chesscom
from app.db import get_session
from app.main import app, get_http_client

SCHOLARS_MATE = """[Event "Casual"]
[White "alice"]
[Black "bob"]
[Result "1-0"]
[Date "2026.11.01"]

1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7# 1-0
"""

TWO_GAMES = SCHOLARS_MATE + "\n" + """[White "carol"]
[Black "dave"]
[Result "1/2-1/2"]

1. d4 d5 1/2-1/2
"""


def chesscom_game(n: int) -> dict:
    return {
        "url": f"https://www.chess.com/game/live/{n}",
        "pgn": f'[White "me"]\n[Black "opp{n}"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n',
    }


ARCHIVES = {
    "https://api.chess.com/pub/player/me/games/archives": {
        "archives": [
            "https://api.chess.com/pub/player/me/games/2026/10",
            "https://api.chess.com/pub/player/me/games/2026/11",
        ]
    },
    "https://api.chess.com/pub/player/me/games/2026/10": {
        "games": [chesscom_game(1), chesscom_game(2), chesscom_game(3)]
    },
    "https://api.chess.com/pub/player/me/games/2026/11": {
        "games": [chesscom_game(4), chesscom_game(5)]
    },
}


def mock_chesscom(request: httpx.Request) -> httpx.Response:
    assert "User-Agent" in request.headers
    body = ARCHIVES.get(str(request.url))
    return httpx.Response(200, json=body) if body else httpx.Response(404)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(chesscom, "current_month", lambda: (2026, 11))
    chesscom._ETAG_CACHE.clear()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def session_override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_http_client] = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(mock_chesscom)
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_import_single_pgn(client):
    r = client.post("/games/import", json={"pgn": SCHOLARS_MATE})
    assert r.status_code == 201
    game = r.json()["games"][0]
    assert (game["white"], game["black"], game["result"]) == ("alice", "bob", "1-0")
    assert game["ply_count"] == 7

    detail = client.get(f"/games/{game['id']}").json()
    assert detail["moves"] == ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7#"]


def test_import_multiple_games(client):
    r = client.post("/games/import", json={"pgn": TWO_GAMES})
    assert r.json()["imported"] == 2
    assert len(client.get("/games").json()) == 2


def test_illegal_move_rejected(client):
    r = client.post("/games/import", json={"pgn": "1. e4 e5 2. Ke3 Ke6 3. Qh8 *"})
    assert r.status_code == 422


def test_garbage_rejected(client):
    r = client.post("/games/import", json={"pgn": "hello"})
    assert r.status_code == 422


def test_chesscom_import_newest_first_and_limit(client):
    r = client.post("/games/import/chesscom/me?limit=3")
    assert r.status_code == 201
    urls = [g["external_url"] for g in r.json()["games"]]
    # Games 5 and 4 from November, then 3 from October.
    assert urls == [f"https://www.chess.com/game/live/{n}" for n in (5, 4, 3)]


def test_chesscom_import_skips_duplicates(client):
    client.post("/games/import/chesscom/me?limit=2")
    r = client.post("/games/import/chesscom/me?limit=4")
    body = r.json()
    assert body["imported"] == 2
    assert body["skipped_duplicates"] == 2


def test_chesscom_unknown_user(client):
    r = client.post("/games/import/chesscom/nobody")
    assert r.status_code == 404


def test_get_missing_game(client):
    assert client.get("/games/999").status_code == 404


def test_chesscom_reads_current_month_without_archives(client):
    calls = []

    def tracking(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return mock_chesscom(request)

    app.dependency_overrides[get_http_client] = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(tracking)
    )
    r = client.post("/games/import/chesscom/me?limit=2")
    assert r.json()["imported"] == 2
    assert calls == ["https://api.chess.com/pub/player/me/games/2026/11"]


def test_chesscom_new_only_stops_at_known_game(client):
    client.post("/games/import/chesscom/me?limit=1")  # imports game 5
    ARCHIVES["https://api.chess.com/pub/player/me/games/2026/11"]["games"].append(
        chesscom_game(6)
    )
    try:
        r = client.post("/games/import/chesscom/me?limit=20&new_only=true")
    finally:
        ARCHIVES["https://api.chess.com/pub/player/me/games/2026/11"]["games"].pop()
    body = r.json()
    assert [g["external_url"] for g in body["games"]] == ["https://www.chess.com/game/live/6"]
    assert body["skipped_duplicates"] == 0


def test_chesscom_uses_etag(client):
    month = "https://api.chess.com/pub/player/me/games/2026/11"
    seen_if_none_match = []

    def etag_server(request: httpx.Request) -> httpx.Response:
        if str(request.url) == month:
            seen_if_none_match.append(request.headers.get("If-None-Match"))
            if request.headers.get("If-None-Match") == '"v1"':
                return httpx.Response(304)
            return httpx.Response(200, json=ARCHIVES[month], headers={"ETag": '"v1"'})
        return mock_chesscom(request)

    app.dependency_overrides[get_http_client] = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(etag_server)
    )
    client.post("/games/import/chesscom/me?limit=2")
    r = client.post("/games/import/chesscom/me?limit=2")
    assert seen_if_none_match == [None, '"v1"']
    assert r.json()["skipped_duplicates"] == 2  # cached body was reused


def test_games_listed_by_when_played_not_import_order(client):
    def game(name: str, end: str) -> str:
        return f'[White "{name}"]\n[Black "x"]\n[EndDate "2026.11.0{end[0]}"]\n[EndTime "{end[2:]}"]\n\n1. e4 *\n'

    # Import newest first, like the Chess.com import does.
    client.post("/games/import", json={"pgn": game("newest", "5 20:16:34")})
    client.post("/games/import", json={"pgn": game("oldest", "4 09:00:00")})
    client.post("/games/import", json={"pgn": game("middle", "5 08:30:00")})
    client.post("/games/import", json={"pgn": SCHOLARS_MATE.replace("2026.11.01", "????.??.??")})

    games = client.get("/games").json()
    assert [g["white"] for g in games] == ["newest", "middle", "oldest", "alice"]
    assert games[0]["played_at"].startswith("2026-11-05T20:16:34")


def test_chesscom_games_record_owner(client):
    r = client.post("/games/import/chesscom/ME?limit=1")
    assert r.json()["games"][0]["owner"] == "me"  # name as written in the PGN
    r = client.post("/games/import", json={"pgn": SCHOLARS_MATE})
    assert r.json()["games"][0]["owner"] is None


def test_ratings_and_opening_name_from_chesscom_headers(client):
    pgn = (
        '[White "a"]\n[Black "b"]\n[WhiteElo "1210"]\n[BlackElo "1185"]\n[ECO "B06"]\n'
        '[ECOUrl "https://www.chess.com/openings/Modern-Defense-with-1-e4-2.d4-Bg7"]\n\n1. e4 g6 *\n'
    )
    game = client.post("/games/import", json={"pgn": pgn}).json()["games"][0]
    assert (game["white_elo"], game["black_elo"]) == (1210, 1185)
    assert game["opening"] == "Modern Defense"
