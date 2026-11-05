# ChessLab Build Plan

Nov 5, 2026 · Yuusuf

## Overview

A working ChessLab MVP takes about **7 weeks at ~10 hours a week (~70 hours)**, or roughly 2 to 3 weeks full time. With AI help it drops to about 3 to 4 weeks at 10 hours a week, or **one focused week at 35 to 40 hours** (see the sprint below). The MVP matches Chess.com Game Review: import games, engine analysis, move labels, accuracy, an eval graph and a playable review board, plus AI explanations.

- **Stack:** React + TypeScript + Vite frontend, FastAPI + python-chess backend.
- **Free tooling only:** Stockfish (open source), the Chess.com public data API for fetching games, the Lichess Opening Explorer and tablebase APIs, react-chessboard (MIT) for the board, and a local or free tier LLM.
- **Build order:** backend first for each feature, then the UI for it, so every phase ends with something you can click through.
- **Estimates assume** school weeks at ~10 hours. Double the weekly hours and the calendar time roughly halves.

## One-week sprint (current)

About 5 to 6 hours a day. Openings, tablebases, caching polish and broad tests move to week two.

- [x] **Day 1:** setup, PGN paste, Chess.com import (FastAPI, SQLite, 8 tests passing)
- [x] **Day 2:** board, move list, navigation (React + Vite, react-chessboard, chess.js)
- [ ] **Day 3:** Stockfish analysis with stored evals and best moves (fallback: stockfish.js in the browser)
- [ ] **Day 4:** move labels, accuracy, eval bar and graph
- [ ] **Day 5:** AI explanations for blunders only
- [ ] **Days 6 to 7:** fix bugs, deploy, write the README

## Phases

Seven phases, each about one week at 10 hours, each ending in a demoable feature.

### Phase 1: Setup and game import (week 1, ~10 h)

- [x] Project with `backend/` (FastAPI); `frontend/` (Vite React TS) comes on Day 2
- [x] `POST /games/import` that accepts pasted PGN and parses it with python-chess
- [x] `POST /games/import/chesscom/{username}` that calls the Chess.com public API (archives list, then months, newest first) and stores the games
- [x] Store games in SQLite (move to Postgres later only if needed)

**Done when:** you can pull your last month of Chess.com games into ChessLab.

### Phase 2: Board and move navigation (week 2, ~10 h)

- [x] react-chessboard showing the game, with next, previous, start, end and arrow key controls
- [x] Clickable move list in SAN, synced with the board
- [x] Flip board, highlight last move

**Done when:** you can step through any imported game.

### Phase 3: Engine analysis (week 3, ~12 h)

- [ ] Install the Stockfish binary and drive it with `chess.engine.SimpleEngine` from python-chess
- [ ] Analyze every position at a fixed depth (start at 16 to 18), store eval and best move per ply
- [ ] Run analysis as a background task, with a status endpoint the frontend polls
- [ ] Cache results so a game is only analyzed once

**Done when:** every move has a stored eval and best move.

### Phase 4: Classification, accuracy and eval graph (week 4, ~12 h)

- [ ] Convert centipawns (and mate scores) to win probability
- [ ] Label each move by win % lost: Best, Good, Inaccuracy, Mistake, Blunder
- [ ] Per player accuracy score from the win % losses
- [ ] Eval bar beside the board and an eval graph you can click to jump to a move
- [ ] Arrow on the board for the engine's best move

**Done when:** a game review screen looks like Chess.com Game Review.

### Phase 5: Openings and endgames (week 5, ~8 h)

- [ ] Name the opening and mark where you left theory, using the Lichess Opening Explorer API
- [ ] For 7 pieces or fewer, check moves against the Lichess tablebase API
- [ ] Cache API responses and respect rate limits

**Done when:** reviews show the opening name and theory exit point.

### Phase 6: AI explanations (week 6, ~10 h)

- [ ] For each Mistake or Blunder, build a prompt from the FEN, the move played, the engine's best line and the eval drop
- [ ] Run the model locally with Ollama, or use a free API tier, behind one `explain()` function so you can swap providers
- [ ] Show the explanation in a side panel, cache it per move

**Done when:** clicking a blunder shows a short explanation that matches the engine line.

### Phase 7: Polish and deploy (week 7, ~8 h)

- [ ] Loading states, error handling, empty states, mobile layout
- [ ] Tests for PGN parsing, classification thresholds and the API routes
- [ ] Frontend on Vercel or Netlify free tier; backend in Docker (Stockfish included) on a free tier host
- [ ] README with screenshots and an architecture diagram for your portfolio

**Done when:** a public link you can put on your resume.

## Timeline

| Week | Phase | Hours |
| --- | --- | --- |
| 1 | Setup and import | ~10 |
| 2 | Board and navigation | ~10 |
| 3 | Engine analysis | ~12 |
| 4 | Labels and accuracy (Game Review parity) | ~12 |
| 5 | Openings and endgames | ~8 |
| 6 | AI explanations | ~10 |
| 7 | Polish and deploy (MVP live) | ~8 |
| | **Total** | **~70** |

By the end of week 4 you have the core Game Review experience; weeks 5 to 7 add openings, AI explanations and a public deploy.

## Risks and stretch goals

The biggest risk is analysis speed on a free host, so plan for running Stockfish in the browser if the server is too slow.

| Risk | Fallback |
| --- | --- |
| Free tier backend is slow or sleeps, so analysis takes minutes | Run stockfish.js (WASM) in the browser; the backend only stores results |
| Chess.com or Lichess API rate limits | Cache every response; fetch one month of games at a time |
| LLM explains the wrong idea | Only explain what the engine line shows; never let it invent moves |
| Exam weeks cut your hours | Phases 5 and 6 can slip without breaking the MVP |

**Stretch goals after the MVP:**

- Puzzles generated from your own blunders
- Stats across many games: weakest openings, blunder rate by game phase
- Accounts so friends can import their games
- Lichess game import alongside Chess.com