// Thin client for the FastAPI backend.

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface GameSummary {
  id: number;
  source: string;
  white: string;
  black: string;
  result: string;
  date: string | null;
  played_at: string | null; // ISO, UTC
  owner: string | null; // the player this game was imported for
  white_elo: number | null;
  black_elo: number | null;
  time_control: string | null;
  opening: string | null;
  ply_count: number;
  external_url: string | null;
}

export interface GameDetail extends GameSummary {
  pgn: string;
  moves: string[]; // SAN
}

export interface ImportResult {
  imported: number;
  skipped_duplicates: number;
  games: GameSummary[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error(`Can't reach the backend at ${BASE}. Is it running?`);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    // FastAPI validation errors come back as a list of objects.
    const message = typeof detail === "string" ? detail : detail?.[0]?.msg;
    throw new Error(message ?? `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  listGames: () => request<GameSummary[]>("/games?limit=200"),
  getGame: (id: number) => request<GameDetail>(`/games/${id}`),
  deleteGame: (id: number) => request<void>(`/games/${id}`, { method: "DELETE" }),
  importPgn: (pgn: string) =>
    request<ImportResult>("/games/import", { method: "POST", body: JSON.stringify({ pgn }) }),
  importChessCom: (username: string, limit = 20, newOnly = false) =>
    request<ImportResult>(
      `/games/import/chesscom/${encodeURIComponent(username)}?limit=${limit}&new_only=${newOnly}`,
      { method: "POST" },
    ),
};
