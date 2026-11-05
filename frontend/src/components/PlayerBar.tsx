interface Props {
  name: string;
  elo: number | null;
  color: "white" | "black";
  width?: number;
  isYou?: boolean;
}

/** Name strip above/below the board: avatar square, name, rating. */
export default function PlayerBar({ name, elo, color, width, isYou }: Props) {
  return (
    <div className="player-bar" style={{ width: width || undefined }}>
      <span className={`avatar ${color}`}>♟</span>
      <span className="player-name">{name}</span>
      {elo && <span className="player-elo">({elo})</span>}
      {isYou && <span className="you-tag">You</span>}
    </div>
  );
}
