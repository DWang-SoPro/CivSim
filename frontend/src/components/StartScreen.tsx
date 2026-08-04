"use client";

import type { SaveListItem } from "@/components/SaveLoadModal";

type StartScreenProps = {
  creating?: boolean;
  error?: string | null;
  latestSave?: SaveListItem | null;
  onNewGame: () => void;
  onLoadSaves: () => void;
  onContinue?: () => void;
};

function formatYear(year: number): string {
  if (year < 0) {
    return `公元前${Math.abs(Math.round(year))}年`;
  }
  if (year === 0) {
    return "公元元年";
  }
  return `公元${Math.round(year)}年`;
}

export function StartScreen({
  creating = false,
  error = null,
  latestSave = null,
  onNewGame,
  onLoadSaves,
  onContinue,
}: StartScreenProps) {
  return (
    <main className="app-shell app-shell--landing">
      <div className="start-stage parchment">
        <div className="start-seal" aria-hidden="true">
          史
        </div>
        <h1 className="landing-brand">文明灵</h1>
        <p className="landing-sub">CivSim · 史官卷轴</p>
        <div className="gold-divider start-divider" aria-hidden="true">
          <span className="gold-divider-mark" />
          <span className="gold-divider-mark" />
        </div>
        <p className="start-tagline">择一文明，执笔记国运兴衰。</p>

        {error && (
          <p className="banner banner--error" role="alert">
            {error}
          </p>
        )}

        <div className="start-actions">
          {latestSave && onContinue && (
            <button
              type="button"
              className="btn-primary start-action-primary"
              onClick={onContinue}
              disabled={creating}
            >
              继续上一局
              <span className="start-action-meta">
                {latestSave.civ_name} · {formatYear(latestSave.year)} · 第
                {latestSave.turn}回合
                {latestSave.is_autosave ? " · 自动" : ""}
              </span>
            </button>
          )}
          <button
            type="button"
            className="btn-primary"
            onClick={onNewGame}
            disabled={creating}
          >
            {creating ? "开局中……" : "开新局"}
          </button>
          <button
            type="button"
            className="btn-ghost start-action-secondary"
            onClick={onLoadSaves}
            disabled={creating}
          >
            读取存档
          </button>
        </div>
      </div>
    </main>
  );
}
