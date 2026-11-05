// localStorage can throw (private mode, blocked storage); it's only a convenience here.
export function load(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

export function save(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
}

export const USERNAME_KEY = "chesslab.username";
export const savedUsername = () => load(USERNAME_KEY, "").trim().toLowerCase();
