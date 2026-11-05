import { useEffect, useRef } from "react";

interface Props {
  moves: string[];
  ply: number; // 0 = start position, n = after move n
  onSelect: (ply: number) => void;
}

export default function MoveList({ moves, ply, onSelect }: Props) {
  const activeRef = useRef<HTMLButtonElement>(null);

  // Keep the current move in view as you step through a long game.
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest" });
  }, [ply]);

  if (!moves.length) return <p className="muted pad">No moves.</p>;

  const rows = [];
  for (let i = 0; i < moves.length; i += 2) {
    rows.push(
      <div className="move-row" key={i}>
        <span className="move-number">{i / 2 + 1}.</span>
        {[i, i + 1].map((idx) =>
          idx < moves.length ? (
            <button
              key={idx}
              ref={ply === idx + 1 ? activeRef : undefined}
              className={`move ${ply === idx + 1 ? "active" : ""}`}
              onClick={() => onSelect(idx + 1)}
            >
              {moves[idx]}
            </button>
          ) : (
            <span key={idx} />
          ),
        )}
      </div>,
    );
  }
  return <div className="move-list">{rows}</div>;
}
