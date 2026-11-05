# ChessLab

Chess game analysis app: import your games, analyze them with Stockfish, review mistakes on an interactive board.

## Status

- [x] Day 1: backend, PGN import, Chess.com import, SQLite storage
- [ ] Day 2: React board and move navigation
- [ ] Day 3: Stockfish analysis
- [ ] Day 4: move labels, accuracy, eval graph
- [ ] Day 5: AI explanations
- [ ] Days 6 to 7: polish and deploy

## Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API.

## API

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/games/import` | Body `{"pgn": "..."}`. Imports one or many games from PGN text |
| POST | `/games/import/chesscom/{username}?limit=20` | Pulls your newest games from Chess.com, skips ones already imported |
| GET | `/games` | Lists games, newest first (`offset`, `limit`) |
| GET | `/games/{id}` | One game with its PGN and SAN move list |
| DELETE | `/games/{id}` | Deletes a game |

## Tests

```bash
cd backend && pytest
```

Chess.com calls are mocked, so tests run offline.

## Layout

```
backend/
  app/
    main.py      routes
    pgn.py       PGN parsing (python-chess)
    chesscom.py  Chess.com public API client
    models.py    database table + request/response schemas
    db.py        SQLite engine and sessions
  tests/
```
