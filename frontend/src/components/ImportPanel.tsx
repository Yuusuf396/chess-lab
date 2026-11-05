import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, type ImportResult } from "../api";
import { load, save, USERNAME_KEY } from "../storage";

const SYNC_EVERY_MS = 10_000;

export default function ImportPanel({ onImported }: { onImported: () => void }) {
  const [tab, setTab] = useState<"chesscom" | "pgn">("chesscom");
  const [username, setUsername] = useState(() => load(USERNAME_KEY, ""));
  const [autoSync, setAutoSync] = useState(() => load("chesslab.autoSync", "") === "1");
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [pgn, setPgn] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; error?: boolean } | null>(null);

  async function run(action: () => Promise<ImportResult>) {
    setBusy(true);
    setMessage(null);
    try {
      const r = await action();
      const skipped = r.skipped_duplicates ? `, skipped ${r.skipped_duplicates}` : "";
      setMessage({ text: `Imported ${r.imported} game${r.imported === 1 ? "" : "s"}${skipped}.` });
      onImported();
      return true;
    } catch (e) {
      setMessage({ text: (e as Error).message, error: true });
      return false;
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (tab === "chesscom") {
      const name = username.trim();
      if (!name) return;
      save(USERNAME_KEY, name);
      run(() => api.importChessCom(name));
    } else if (pgn.trim()) {
      run(() => api.importPgn(pgn)).then((ok) => ok && setPgn(""));
    }
  }

  // Auto-sync: every 10 s, pull only games newer than the newest one we have.
  // Keep the latest callback in a ref so the interval doesn't restart on every render.
  const onImportedRef = useRef(onImported);
  onImportedRef.current = onImported;
  const syncName = username.trim();

  useEffect(() => {
    save("chesslab.autoSync", autoSync ? "1" : "");
    if (!autoSync || !syncName) return;
    let inFlight = false;

    async function sync() {
      if (inFlight || document.hidden) return; // skip while the tab is in the background
      inFlight = true;
      try {
        const r = await api.importChessCom(syncName, 20, true);
        setLastSync(new Date());
        if (r.imported > 0) {
          setMessage({ text: `Synced ${r.imported} new game${r.imported === 1 ? "" : "s"}.` });
          onImportedRef.current();
        }
      } catch (e) {
        setMessage({ text: (e as Error).message, error: true });
      } finally {
        inFlight = false;
      }
    }

    sync();
    const timer = setInterval(sync, SYNC_EVERY_MS);
    document.addEventListener("visibilitychange", sync);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", sync);
    };
  }, [autoSync, syncName]);

  return (
    <section className="panel import-panel">
      <div className="tabs">
        <button className={tab === "chesscom" ? "active" : ""} onClick={() => setTab("chesscom")}>
          Chess.com
        </button>
        <button className={tab === "pgn" ? "active" : ""} onClick={() => setTab("pgn")}>
          Paste PGN
        </button>
      </div>
      <form onSubmit={submit} className="import-form">
        {tab === "chesscom" ? (
          <input
            placeholder="Chess.com username"
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
              save(USERNAME_KEY, e.target.value.trim());
            }}
          />
        ) : (
          <textarea
            placeholder={'[White "..."]\n\n1. e4 e5 2. Nf3 ...'}
            rows={6}
            value={pgn}
            onChange={(e) => setPgn(e.target.value)}
          />
        )}
        <button type="submit" className="btn-green" disabled={busy}>
          {busy ? "Importing…" : "Import"}
        </button>
      </form>
      {tab === "chesscom" && (
        <label className="sync">
          <input
            type="checkbox"
            checked={autoSync}
            disabled={!syncName}
            onChange={(e) => setAutoSync(e.target.checked)}
          />
          Auto-sync new games every 10 s
          {autoSync && lastSync && (
            <span className="muted"> · last checked {lastSync.toLocaleTimeString()}</span>
          )}
        </label>
      )}
      {message && <p className={message.error ? "error" : "success"}>{message.text}</p>}
    </section>
  );
}
