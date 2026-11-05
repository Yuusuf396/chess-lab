import type { GameSummary } from "./api";

/** When a game was played, in local time: "Today 4:16 PM", "Yesterday 9:02 PM", "Nov 3, 2026 8:15 PM". */
export function formatPlayed(g: GameSummary): string | null {
  if (!g.played_at) return g.date;
  const d = new Date(g.played_at);
  const time = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return `Today ${time}`;
  if (d.toDateString() === yesterday.toDateString()) return `Yesterday ${time}`;
  return `${d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })} ${time}`;
}

/** PGN time control to something readable: "600" -> "10 min", "180+2" -> "3+2", "1/86400" -> "Daily". */
export function formatTimeControl(tc: string | null): string | null {
  if (!tc || tc === "-") return null;
  if (tc.includes("/")) return "Daily";
  const [base, inc] = tc.split("+").map(Number);
  if (Number.isNaN(base)) return tc;
  const mins = base >= 60 ? `${+(base / 60).toFixed(1)}` : `${base}s`;
  return inc ? `${mins}+${inc}` : base >= 60 ? `${mins} min` : mins;
}

export type Outcome = "win" | "loss" | "draw" | null;

/** Whose side to show: the player the game was imported for, else the saved username. */
export function perspective(g: GameSummary, fallbackUsername: string): string {
  return (g.owner ?? fallbackUsername).toLowerCase();
}

/** The game's result from `username`'s side, or null if they didn't play in it. */
export function outcomeFor(g: GameSummary, fallbackUsername: string): Outcome {
  const username = perspective(g, fallbackUsername);
  const side =
    g.white.toLowerCase() === username ? "white" : g.black.toLowerCase() === username ? "black" : null;
  if (!side || !username) return null;
  if (g.result === "1/2-1/2") return "draw";
  if (g.result === "1-0") return side === "white" ? "win" : "loss";
  if (g.result === "0-1") return side === "black" ? "win" : "loss";
  return null;
}
