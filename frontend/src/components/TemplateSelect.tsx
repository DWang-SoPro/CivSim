"use client";

import { emblemSrc } from "@/components/CivEmblem";
import { CIV_TEMPLATES, type CivTemplateMeta } from "@/lib/civTemplates";

type TemplateSelectProps = {
  creating?: boolean;
  error?: string | null;
  selectedId?: string | null;
  onSelect: (template: CivTemplateMeta) => void;
  onConfirm: () => void;
  onBack: () => void;
};

export function TemplateSelect({
  creating = false,
  error = null,
  selectedId = null,
  onSelect,
  onConfirm,
  onBack,
}: TemplateSelectProps) {
  const selected = CIV_TEMPLATES.find((item) => item.id === selectedId) ?? null;

  return (
    <main className="app-shell app-shell--landing app-shell--templates">
      <div className="template-stage parchment">
        <header className="template-header">
          <button
            type="button"
            className="btn-ghost"
            onClick={onBack}
            disabled={creating}
          >
            返回
          </button>
          <div className="template-heading">
            <h1 className="landing-brand template-title">择定文明</h1>
            <p className="landing-sub">开新局 · 选择初始模板</p>
          </div>
          <span className="template-header-spacer" aria-hidden="true" />
        </header>

        {error && (
          <p className="banner banner--error" role="alert">
            {error}
          </p>
        )}

        <ul className="template-grid" role="listbox" aria-label="文明模板">
          {CIV_TEMPLATES.map((template) => {
            const selected = template.id === selectedId;
            return (
              <li key={template.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  className={`template-card${selected ? " template-card--selected" : ""}`}
                  disabled={creating}
                  onClick={() => onSelect(template)}
                >
                  <img
                    className="template-emblem"
                    src={emblemSrc(template.id)}
                    alt=""
                    width={56}
                    height={56}
                    draggable={false}
                  />
                  <span className="template-card-body">
                    <span className="template-name">{template.shortName}</span>
                    <span className="template-era">
                      {template.era} · {template.region}
                    </span>
                    <span className="template-blurb">{template.blurb}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>

        <footer className="template-footer">
          {selected ? (
            <p className="template-selected-hint">
              已选：{selected.name}
            </p>
          ) : (
            <p className="template-selected-hint">请选择一个文明</p>
          )}
          <button
            type="button"
            className="btn-primary"
            disabled={!selectedId || creating}
            onClick={onConfirm}
          >
            {creating ? "开局中……" : "以此开局"}
          </button>
        </footer>
      </div>
    </main>
  );
}
