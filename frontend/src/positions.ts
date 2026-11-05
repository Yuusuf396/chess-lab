import { Chess, type Square } from "chess.js";

export interface Position {
  fen: string;
  // The move that led here; null for the starting position.
  lastMove: { from: Square; to: Square } | null;
}

/** Replay SAN moves and return one position per ply, starting with the initial one. */
export function buildPositions(moves: string[]): Position[] {
  const chess = new Chess();
  const positions: Position[] = [{ fen: chess.fen(), lastMove: null }];
  for (const san of moves) {
    const move = chess.move(san);
    positions.push({ fen: chess.fen(), lastMove: { from: move.from, to: move.to } });
  }
  return positions;
}
