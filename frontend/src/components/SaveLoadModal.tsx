"use client";

type SaveListItem = {
  save_id: string;
  slot_name: string | null;
  civ_name: string;
  template_id: string;
  turn: number;
  year: number;
  saved_at: string;
  is_autosave: boolean;
};

type SaveLoadModalProps = {
  open: boolean;
  mode: "save" | "load";
  saves: SaveListItem[];
  loading?: boolean;
  message?: string | null;
  onClose: () => void;
  onConfirmSave?: () => void;
  onLoad?: (saveId: string) => void;
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

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("zh-CN", { hour12: false });
  } catch {
    return iso;
  }
}

export function SaveLoadModal({
  open,
  mode,
  saves,
  loading = false,
  message = null,
  onClose,
  onConfirmSave,
  onLoad,
}: SaveLoadModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-panel parchment"
        role="dialog"
        aria-modal="true"
        aria-labelledby="save-load-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-header">
          <h2 id="save-load-title" className="modal-title">
            {mode === "save" ? "存档" : "读档"}
          </h2>
          <button type="button" className="btn-ghost modal-close" onClick={onClose}>
            关闭
          </button>
        </header>

        {message && (
          <p className="modal-message" role="status">
            {message}
          </p>
        )}

        {mode === "save" ? (
          <div className="modal-body">
            <p className="modal-hint">
              将当前国势与史册写入新档。每回合结束后仍会自动覆盖「自动存档」。
            </p>
            <button
              type="button"
              className="btn-primary"
              disabled={loading}
              onClick={onConfirmSave}
            >
              {loading ? "保存中…" : "确认存档"}
            </button>
          </div>
        ) : (
          <div className="modal-body">
            {loading && <p className="modal-hint">载入列表…</p>}
            {!loading && saves.length === 0 && (
              <p className="modal-hint">尚无存档。</p>
            )}
            <ul className="save-list">
              {saves.map((save) => (
                <li key={save.save_id}>
                  <button
                    type="button"
                    className="save-list-item"
                    disabled={loading}
                    onClick={() => onLoad?.(save.save_id)}
                  >
                    <span className="save-list-title">
                      {save.slot_name || save.civ_name}
                      {save.is_autosave ? " · 自动" : ""}
                    </span>
                    <span className="save-list-meta">
                      {save.civ_name} · {formatYear(save.year)} · 第{save.turn}
                      回合
                    </span>
                    <span className="save-list-time">{formatTime(save.saved_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export type { SaveListItem };
