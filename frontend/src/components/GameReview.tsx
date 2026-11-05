import { useEffect, useMemo, useRef, useState } from "react";
import { Chessboard } from "react-chessboard";
import { api, type GameDetail } from "../api";
import { buildPositions } from "../positions";
import MoveList from "./MoveList";
import PlayerBar from "./PlayerBar";
import { formatPlayed, formatTimeControl, perspective } from "../format";
import { savedUsername } from "../storage";

// Board fills its column; the CSS grid decides how wide that column is.
function useBoardWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () =>
      setWidth(Math.floor(Math.min(el.clientWidth, 560)));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
    };
  });
  return [ref, width] as const;
}

const LAST_MOVE_STYLE = { backgroundColor: "rgba(255, 255, 51, 0.5)" };
const LIGHT_SQUARE = { backgroundColor: "#ebecd0" };
const DARK_SQUARE = { backgroundColor: "#739552" };

export default function GameReview({ id }: { id: number }) {
  const [game, setGame] = useState<GameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ply, setPly] = useState(0);
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    setGame(null);
    setError(null);
    setPly(0);
    api
      .getGame(id)
      .then((g) => {
        setGame(g);
        // Put your own pieces at the bottom, like Chess.com does.
        setFlipped(g.black.toLowerCase() === perspective(g, savedUsername()));
      })
      .catch((e: Error) => setError(e.message));
  }, [id]);

  const positions = useMemo(() => (game ? buildPositions(game.moves) : []), [game]);
  const lastPly = positions.length - 1;
  const [boardRef, boardWidth] = useBoardWidth();

  // Arrow keys: ← → step, ↑ / Home start, ↓ / End finish.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const step: Record<string, (p: number) => number> = {
        ArrowLeft: (p) => p - 1,
        ArrowRight: (p) => p + 1,
        ArrowUp: () => 0,
        Home: () => 0,
        ArrowDown: () => lastPly,
        End: () => lastPly,
      };
      if (e.key === "f") setFlipped((f) => !f);
      const fn = step[e.key];
      if (!fn) return;
      e.preventDefault();
      setPly((p) => Math.max(0, Math.min(lastPly, fn(p))));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lastPly]);

  if (error) return <p className="error">{error} <a href="#/">Back</a></p>;
  if (!game) return <p className="muted">Loading game…</p>;

  const position = positions[ply];
  const squareStyles = position.lastMove
    ? { [position.lastMove.from]: LAST_MOVE_STYLE, [position.lastMove.to]: LAST_MOVE_STYLE }
    : {};
  const me = perspective(game, savedUsername());
  const sides = (["white", "black"] as const).map((color) => ({
    color,
    name: color === "white" ? game.white : game.black,
    elo: color === "white" ? game.white_elo : game.black_elo,
  }));
  const [bottom, top] = flipped ? [sides[1], sides[0]] : sides;

  return (
    <div className="review">
      <div className="board-col" ref={boardRef}>
        <PlayerBar {...top} width={boardWidth} isYou={top.name.toLowerCase() === me} />
        <div className="board-frame">
          {boardWidth > 0 && (
          <Chessboard
            id="review-board"
            position={position.fen}
            boardOrientation={flipped ? "black" : "white"}
            arePiecesDraggable={false}
            customSquareStyles={squareStyles}
            customLightSquareStyle={LIGHT_SQUARE}
            customDarkSquareStyle={DARK_SQUARE}
            animationDuration={150}
            boardWidth={boardWidth}
          />
          )}
        </div>
        <PlayerBar {...bottom} width={boardWidth} isYou={bottom.name.toLowerCase() === me} />
      </div>

      <aside className="panel side">
        <div className="panel-header review-header">
          <a href="#/" className="back" title="Back to games">‹</a>
          <h2>
            <span className="star">★</span> Game Review
          </h2>
        </div>
        <div className="game-info">
          <div className="info-players">
            {game.white} <span className="muted">vs</span> {game.black}
            <span className="info-result">{game.result}</span>
          </div>
          <div className="muted">
            {[formatTimeControl(game.time_control), formatPlayed(game)].filter(Boolean).join(" · ")}
          </div>
          {game.opening && <div className="opening">{game.opening}</div>}
          {game.external_url && (
            <a href={game.external_url} target="_blank" rel="noreferrer" className="ext-link">
              View on Chess.com ↗
            </a>
          )}
        </div>
        <MoveList moves={game.moves} ply={ply} onSelect={setPly} />
        <div className="controls">
          <button onClick={() => setFlipped(!flipped)} title="Flip board (F)">⇅</button>
          <button onClick={() => setPly(0)} disabled={ply === 0} title="Start (↑)">⏮</button>
          <button onClick={() => setPly(ply - 1)} disabled={ply === 0} title="Previous (←)">◀</button>
          <button onClick={() => setPly(ply + 1)} disabled={ply === lastPly} title="Next (→)">▶</button>
          <button onClick={() => setPly(lastPly)} disabled={ply === lastPly} title="End (↓)">⏭</button>
        </div>
      </aside>
    </div>
  );
}
