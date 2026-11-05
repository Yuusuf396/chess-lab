import { useEffect, useState } from "react";
import Home from "./components/Home";
import GameReview from "./components/GameReview";

// Tiny hash router: "#/game/12" opens a game, anything else is home.
function parseHash(): number | null {
  const match = window.location.hash.match(/^#\/game\/(\d+)$/);
  return match ? Number(match[1]) : null;
}

export default function App() {
  const [gameId, setGameId] = useState<number | null>(parseHash);

  useEffect(() => {
    const onHashChange = () => setGameId(parseHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <a href="#/" className="logo">
          <span className="logo-icon">♞</span> ChessLab
        </a>
        <nav>
          <a href="#/" className={gameId === null ? "active" : ""}>Games</a>
        </nav>
      </header>
      <main>{gameId === null ? <Home /> : <GameReview id={gameId} />}</main>
    </div>
  );
}
