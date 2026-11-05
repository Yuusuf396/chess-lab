from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class GameBase(SQLModel):
    source: str = "pgn"  # "pgn" or "chesscom"
    white: str = "?"
    black: str = "?"
    result: str = "*"
    date: str | None = None  # PGN date as written, e.g. "2026.11.05"
    time_control: str | None = None
    opening: str | None = None
    ply_count: int = 0
    played_at: datetime | None = Field(default=None, index=True)  # UTC
    # The player this game was imported for (their side goes at the bottom of the board).
    owner: str | None = None
    white_elo: int | None = None
    black_elo: int | None = None


class Game(GameBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    pgn: str
    # Chess.com game URL; unique so re-importing the same month never duplicates games.
    external_url: str | None = Field(default=None, index=True, unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GameSummary(GameBase):
    id: int
    external_url: str | None = None


class GameDetail(GameSummary):
    pgn: str
    moves: list[str]  # SAN, e.g. ["e4", "e5", "Nf3"]


class PgnImportRequest(SQLModel):
    pgn: str = Field(min_length=1)


class ImportResult(SQLModel):
    imported: int
    skipped_duplicates: int
    games: list[GameSummary]
