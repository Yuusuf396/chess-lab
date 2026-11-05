from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app import chesscom
from app.db import get_session, init_db
from app.models import (
    Game,
    GameDetail,
    GameSummary,
    ImportResult,
    PgnImportRequest,
)
from app.pgn import ParsedGame, PgnError, parse_pgn, san_moves


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ChessLab API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_http_client() -> httpx.AsyncClient:
    # Overridden in tests with a mock transport.
    return httpx.AsyncClient(timeout=15)


def _owner(parsed: ParsedGame, username: str | None) -> str | None:
    """Return the player name from the PGN that matches `username` (any case)."""
    if not username:
        return None
    for name in (parsed.white, parsed.black):
        if name.lower() == username.lower():
            return name
    return None


def _to_game(
    parsed: ParsedGame,
    source: str,
    external_url: str | None = None,
    owner: str | None = None,
) -> Game:
    return Game(
        owner=_owner(parsed, owner),
        source=source,
        white=parsed.white,
        black=parsed.black,
        result=parsed.result,
        date=parsed.date,
        time_control=parsed.time_control,
        opening=parsed.opening,
        ply_count=len(parsed.moves),
        played_at=parsed.played_at,
        white_elo=parsed.white_elo,
        black_elo=parsed.black_elo,
        pgn=parsed.pgn,
        external_url=external_url,
    )


def _summary(game: Game) -> GameSummary:
    return GameSummary.model_validate(game, from_attributes=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/games/import", response_model=ImportResult, status_code=201)
def import_pgn(body: PgnImportRequest, session: Session = Depends(get_session)):
    try:
        parsed_games = parse_pgn(body.pgn)
    except PgnError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    games = [_to_game(p, source="pgn") for p in parsed_games]
    session.add_all(games)
    session.commit()
    for g in games:
        session.refresh(g)
    return ImportResult(
        imported=len(games), skipped_duplicates=0, games=[_summary(g) for g in games]
    )


@app.post("/games/import/chesscom/{username}", response_model=ImportResult, status_code=201)
async def import_chesscom(
    username: str,
    limit: int = Query(20, ge=1, le=100),
    new_only: bool = Query(
        False, description="Stop at the first game already imported (fast sync)."
    ),
    session: Session = Depends(get_session),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    stop_at = None
    if new_only:
        stop_at = set(
            session.exec(select(Game.external_url).where(Game.source == "chesscom")).all()
        )
    try:
        async with client:
            raw_games = await chesscom.fetch_recent_games(username, limit, client, stop_at)
    except chesscom.ChessComError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    existing = set(
        session.exec(
            select(Game.external_url).where(
                Game.external_url.in_([g.get("url") for g in raw_games])
            )
        ).all()
    )

    new_games: list[Game] = []
    skipped = 0
    for raw in raw_games:
        url = raw.get("url")
        if url in existing:
            skipped += 1
            continue
        try:
            parsed = parse_pgn(raw["pgn"])[0]
        except PgnError:
            skipped += 1  # odd variants (e.g. chess960 edge cases); skip rather than fail the batch
            continue
        new_games.append(_to_game(parsed, source="chesscom", external_url=url, owner=username))
        existing.add(url)

    session.add_all(new_games)
    session.commit()
    for g in new_games:
        session.refresh(g)
    return ImportResult(
        imported=len(new_games),
        skipped_duplicates=skipped,
        games=[_summary(g) for g in new_games],
    )


@app.get("/games", response_model=list[GameSummary])
def list_games(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    games = session.exec(
        select(Game)
        .order_by(Game.played_at.desc().nulls_last(), Game.id.desc())
        .offset(offset).limit(limit)
    ).all()
    return [_summary(g) for g in games]


@app.get("/games/{game_id}", response_model=GameDetail)
def get_game(game_id: int, session: Session = Depends(get_session)):
    game = session.get(Game, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return GameDetail(
        **_summary(game).model_dump(), pgn=game.pgn, moves=san_moves(game.pgn)
    )


@app.delete("/games/{game_id}", status_code=204)
def delete_game(game_id: int, session: Session = Depends(get_session)):
    game = session.get(Game, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    session.delete(game)
    session.commit()
