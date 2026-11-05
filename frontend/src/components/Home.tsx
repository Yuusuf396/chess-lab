import { useCallback, useEffect, useState } from "react";
import { api, type GameSummary } from "../api";
import ImportPanel from "./ImportPanel";
import { formatPlayed, formatTimeControl, outcomeFor, type Outcome } from "../format";
import { savedUsername } from "../storage";

const OUTCOME_ICON: Record<NonNullable<Outcome>, string> = { win: "+", loss: "−", draw: "=" };

function ResultBadge({ game, me }: { game: GameSummary; me: string }) {
  const outcome = outcomeFor(game, me);
  const [w, b] = game.result === "1/2-1/2" ? ["½", "½"] : game.result.split("-");
  return (
    <span className="result-cell">
      <span className="score">
        <span>{w}</span>
        <span>{b}</span>
      </span>
      {outcome && <span className={`result-icon ${outcome}`}>{OUTCOME_ICON[outcome]}</span>}
    </span>
  );
}

export default function Home() {
  const [games, setGames] = useState<GameSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [me, setMe] = useState(savedUsername);

  const load = useCallback(() => {
    setMe(savedUsername());
    api.listGames().then(setGames).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  async function remove(id: number) {
    if (!confirm("Delete this game?")) return;
    try {
      await api.deleteGame(id);
      setGames((gs) => gs?.filter((g) => g.id !== id) ?? null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="home">
      <ImportPanel onImported={load} />

      <section className="panel">
        <div className="panel-header">
          <h2>Game History</h2>
          {games && <span className="muted">{games.length} games</span>}
        </div>
        {error && <p className="error pad">{error}</p>}
        {games === null && !error && <p className="muted pad">Loading…</p>}
        {games?.length === 0 && <p className="muted pad">No games yet. Import some above.</p>}
        {games && games.length > 0 && (
          <div className="history">
            <div className="history-row history-head">
              <span />
              <span>Players</span>
              <span>Result</span>
              <span className="hide-sm">Moves</span>
              <span className="hide-sm">Date</span>
              <span />
            </div>
            {games.map((g) => (
              <a key={g.id} href={`#/game/${g.id}`} className="history-row">
                <span className="tc" title="Time control">
                  {formatTimeControl(g.time_control) ?? "–"}
                </span>
                <span className="players-cell">
                  {(["white", "black"] as const).map((color) => (
                    <span key={color} className="player-line">
                      <span className={`sq ${color}`} />
                      <span className="pname">{color === "white" ? g.white : g.black}</span>
                      <span className="muted">
                        {(color === "white" ? g.white_elo : g.black_elo) ?? ""}
                      </span>
                    </span>
                  ))}
                  {g.opening && <span className="opening">{g.opening}</span>}
                </span>
                <ResultBadge game={g} me={me} />
                <span className="hide-sm muted">{Math.ceil(g.ply_count / 2)}</span>
                <span className="hide-sm muted date">{formatPlayed(g)}</span>
                <button
                  className="icon-btn"
                  title="Delete game"
                  onClick={(e) => {
                    e.preventDefault();
                    remove(g.id);
                  }}
                >
                  ✕
                </button>
              </a>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
