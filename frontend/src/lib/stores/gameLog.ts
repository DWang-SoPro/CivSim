import { writable } from 'svelte/store';

export let idCounter = 0;

export interface LogEntry {
  id: number;
  timestamp: string;
  message: string;
}

const PERSIST_KEY = 'gameLog';

function loadInitial(): LogEntry[] {
  try {
    const raw = localStorage.getItem(PERSIST_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        const entries = parsed.filter((e) => typeof e?.timestamp === 'string' && typeof e?.message === 'string');
        idCounter = entries.length;
        return entries;
      }
    }
  } catch {
    // ignore
  }
  return [];
}

export const gameLog = writable<LogEntry[]>(loadInitial());

if (typeof window !== 'undefined') {
  gameLog.subscribe((entries) => {
    try {
      localStorage.setItem(PERSIST_KEY, JSON.stringify(entries));
    } catch {
      // ignore
    }
  });
}

export function resetGameLog() {
  idCounter = 0;
  gameLog.set([]);
  try {
    localStorage.removeItem(PERSIST_KEY);
  } catch {
    // ignore
  }
}

export function log(message: string) {
  const entry: LogEntry = {
    id: idCounter++,
    timestamp: new Date().toISOString(),
    message,
  };
  gameLog.update((arr) => [...arr, entry]);
}
