"""Turn raw PGN text into structured games using python-chess."""

import io
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import chess.pgn


class PgnError(ValueError):
    pass


@dataclass
class ParsedGame:
    white: str
    black: str
    result: str
    date: str | None
    time_control: str | None
    opening: str | None
    moves: list[str]
    played_at: datetime | None  # when the game ended (UTC), if the PGN says
    white_elo: int | None
    black_elo: int | None
    pgn: str  # normalized PGN, exported by python-chess


def _clean(value: str | None) -> str | None:
    # PGN uses "?" and "????.??.??" to mean unknown.
    if value is None or set(value) <= {"?", "."}:
        return None
    return value


def played_at(headers) -> datetime | None:
    """Best guess at when a game finished, in UTC.

    Chess.com writes EndDate/EndTime; Lichess and most tools write UTCDate/UTCTime
    (the start). Fall back to the plain Date header at midnight.
    """
    for date_key, time_key in (("EndDate", "EndTime"), ("UTCDate", "UTCTime"), ("Date", None)):
        date = _clean(headers.get(date_key))
        if not date:
            continue
        time = (_clean(headers.get(time_key)) if time_key else None) or "00:00:00"
        try:
            parsed = datetime.strptime(f"{date} {time[:8]}", "%Y.%m.%d %H:%M:%S")
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _elo(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def opening_name(headers) -> str | None:
    """Readable opening name. Chess.com only gives ECO plus a URL like
    .../openings/Sicilian-Defense-Najdorf-Variation-6.Be3, so take the words before
    the first move number."""
    if _clean(headers.get("Opening")):
        return headers["Opening"]
    url = headers.get("ECOUrl") or ""
    if "/openings/" in url:
        slug = url.rsplit("/", 1)[-1]
        # Cut at the first move: "-6.Be3" or "...6.c3".
        slug = re.split(r"\.\.\.|-(?=\d)|^(?=\d)", slug)[0]
        words = [w for w in slug.split("-") if w]
        while words and words[-1].lower() in {"with", "and"}:
            words.pop()
        if words:
            return " ".join(words)
    return _clean(headers.get("ECO"))


def parse_pgn(text: str) -> list[ParsedGame]:
    """Parse one or many games from a PGN string.

    Raises PgnError if no game could be read, or a game contains an illegal move.
    """
    stream = io.StringIO(text)
    games: list[ParsedGame] = []

    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        if game.errors:
            # python-chess keeps going past bad moves; we would rather reject loudly.
            raise PgnError(f"Game {len(games) + 1}: {game.errors[0]}")

        headers = game.headers
        moves = []
        board = game.board()
        for move in game.mainline_moves():
            moves.append(board.san(move))
            board.push(move)

        # python-chess fills missing headers with "?", so text like "hello" parses
        # as an empty game. No moves and no real player names means it isn't one.
        if not moves and _clean(headers.get("White")) is None and _clean(headers.get("Black")) is None:
            continue

        games.append(
            ParsedGame(
                white=headers.get("White", "?"),
                black=headers.get("Black", "?"),
                result=headers.get("Result", "*"),
                date=_clean(headers.get("Date")),
                time_control=_clean(headers.get("TimeControl")),
                opening=opening_name(headers),
                moves=moves,
                played_at=played_at(headers),
                white_elo=_elo(headers.get("WhiteElo")),
                black_elo=_elo(headers.get("BlackElo")),
                pgn=str(game),
            )
        )

    if not games:
        raise PgnError("No games found in the PGN text.")
    return games


def san_moves(pgn: str) -> list[str]:
    return parse_pgn(pgn)[0].moves
