import os
from collections.abc import Iterator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine, select

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chesslab.db")

# check_same_thread is a SQLite-only flag: FastAPI may use the session on a different thread.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def init_db() -> None:
    _add_missing_columns()
    SQLModel.metadata.create_all(engine)
    _backfill()


# Columns added after the first release. SQLite's create_all won't add columns to an
# existing table, so older databases get them here.
_NEW_COLUMNS = {
    "played_at": "DATETIME",
    "owner": "VARCHAR",
    "white_elo": "INTEGER",
    "black_elo": "INTEGER",
}


def _add_missing_columns() -> None:
    insp = inspect(engine)
    if not insp.has_table("game"):
        return
    existing = {c["name"] for c in insp.get_columns("game")}
    with engine.begin() as conn:
        for name, sql_type in _NEW_COLUMNS.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE game ADD COLUMN {name} {sql_type}"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_game_played_at ON game (played_at)"))


def _backfill() -> None:
    """Fill new columns for games imported before they existed."""
    from collections import Counter

    from app.models import Game
    from app.pgn import PgnError, parse_pgn

    with Session(engine) as session:
        # Fields read from PGN headers: re-read them for games that are missing any.
        stale = select(Game).where(
            (Game.played_at.is_(None)) | (Game.white_elo.is_(None)) | (Game.black_elo.is_(None))
        )
        for game in session.exec(stale).all():
            try:
                parsed = parse_pgn(game.pgn)[0]
            except PgnError:
                continue
            game.played_at = parsed.played_at
            game.white_elo = parsed.white_elo
            game.black_elo = parsed.black_elo
            game.opening = parsed.opening
            session.add(game)

        # Owner of old Chess.com games: the player who appears in the most of them,
        # i.e. the account that was imported.
        chesscom = session.exec(select(Game).where(Game.source == "chesscom")).all()
        counts = Counter(name.lower() for g in chesscom for name in (g.white, g.black))
        for game in chesscom:
            if not game.owner:
                game.owner = max((game.white, game.black), key=lambda n: counts[n.lower()])
                session.add(game)
        session.commit()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
