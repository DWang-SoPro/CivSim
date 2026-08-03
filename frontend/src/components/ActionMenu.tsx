"use client";

import { useEffect, useRef, useState } from "react";

type ActionMenuItem = {
  id: string;
  name: string;
  label: string;
  domain: string;
  domain_label: string;
  description: string;
  difficulty_hint: string;
  suggested_input: string;
};

type ActionMenuProps = {
  items: ActionMenuItem[];
  loading?: boolean;
  disabled?: boolean;
  /** 当前输入框全文，用于在勾选切换时保留手动补充部分 */
  command: string;
  /** 父级在提交/新局后递增，用以清空勾选 */
  selectionResetKey?: number;
  onCompose: (text: string, selectedCount: number) => void;
};

const DOMAIN_ORDER = [
  "economic",
  "political",
  "military",
  "cultural",
  "technology",
  "composite",
];

/** 与后端 TaskSplitter 的「；」确定性拆分对齐 */
export const ACTION_MENU_SEP = "；";

const OVERSELECT_HINT_THRESHOLD = 4;

function difficultyClass(hint: string): string {
  switch (hint) {
    case "容易":
      return "difficulty--easy";
    case "中等":
      return "difficulty--medium";
    case "困难":
      return "difficulty--hard";
    case "极难":
      return "difficulty--extreme";
    default:
      return "difficulty--medium";
  }
}

function menuPrefixFromIds(
  items: ActionMenuItem[],
  selectedIds: string[],
): string {
  const byId = new Map(items.map((item) => [item.id, item]));
  return selectedIds
    .map((id) => byId.get(id)?.suggested_input)
    .filter((text): text is string => Boolean(text))
    .join(ACTION_MENU_SEP);
}

function extractManualSuffix(command: string, menuPrefix: string): string {
  if (!menuPrefix) {
    return command.trim();
  }
  if (command.startsWith(menuPrefix)) {
    return command.slice(menuPrefix.length).replace(/^[；;，,\s]+/, "").trim();
  }
  return command.trim();
}

function composeCommand(menuPrefix: string, manualSuffix: string): string {
  if (menuPrefix && manualSuffix) {
    return `${menuPrefix}${ACTION_MENU_SEP}${manualSuffix}`;
  }
  return menuPrefix || manualSuffix;
}

export function ActionMenu({
  items,
  loading = false,
  disabled = false,
  command,
  selectionResetKey = 0,
  onCompose,
}: ActionMenuProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const selectedIdsRef = useRef(selectedIds);
  const lastMenuPrefixRef = useRef("");
  const commandRef = useRef(command);
  const onComposeRef = useRef(onCompose);

  selectedIdsRef.current = selectedIds;
  commandRef.current = command;
  onComposeRef.current = onCompose;

  useEffect(() => {
    setSelectedIds([]);
    selectedIdsRef.current = [];
    lastMenuPrefixRef.current = "";
  }, [selectionResetKey]);

  // 菜单项刷新后剔除已不可用的勾选（副作用里更新父状态，不在 setState updater 内）
  useEffect(() => {
    const available = new Set(items.map((item) => item.id));
    const prev = selectedIdsRef.current;
    const next = prev.filter((id) => available.has(id));
    if (next.length === prev.length) {
      return;
    }

    const prefix = menuPrefixFromIds(items, next);
    const suffix = extractManualSuffix(
      commandRef.current,
      lastMenuPrefixRef.current,
    );
    lastMenuPrefixRef.current = prefix;
    const composed = composeCommand(prefix, suffix);
    commandRef.current = composed;
    selectedIdsRef.current = next;
    setSelectedIds(next);
    onComposeRef.current(composed, next.length);
  }, [items]);

  const grouped = DOMAIN_ORDER.map((domain) => ({
    domain,
    label: items.find((item) => item.domain === domain)?.domain_label ?? domain,
    items: items.filter((item) => item.domain === domain),
  })).filter((group) => group.items.length > 0);

  function toggleItem(item: ActionMenuItem) {
    if (disabled) {
      return;
    }

    const prev = selectedIdsRef.current;
    const exists = prev.includes(item.id);
    const next = exists
      ? prev.filter((id) => id !== item.id)
      : [...prev, item.id];
    const prefix = menuPrefixFromIds(items, next);
    const suffix = extractManualSuffix(
      commandRef.current,
      lastMenuPrefixRef.current,
    );
    lastMenuPrefixRef.current = prefix;
    const composed = composeCommand(prefix, suffix);

    // 先写 ref，保证连点时读到最新组合；再分别更新本组件与父组件状态
    commandRef.current = composed;
    selectedIdsRef.current = next;
    setSelectedIds(next);
    onCompose(composed, next.length);
  }

  const overselected = selectedIds.length > OVERSELECT_HINT_THRESHOLD;

  return (
    <details className="action-menu" open={false}>
      <summary className="action-menu-summary">
        可选政令
        <span className="action-menu-chevron" aria-hidden="true">
          ▸
        </span>
        {loading ? (
          <span className="action-menu-meta">载入中…</span>
        ) : (
          <span className="action-menu-meta">
            {items.length} 项
            {selectedIds.length > 0 ? ` · 已选 ${selectedIds.length}` : ""}
          </span>
        )}
      </summary>
      <div className="action-menu-body">
        {grouped.length === 0 && !loading && (
          <p className="action-menu-empty">暂无可用建议，可直接在下方输入。</p>
        )}
        {overselected && (
          <p className="action-menu-hint" role="status">
            一次推行过多政令，国力恐难兼顾
          </p>
        )}
        {grouped.map((group) => (
          <section key={group.domain} className="action-menu-domain">
            <h3 className="action-menu-domain-title">{group.label}</h3>
            <ul className="action-menu-list">
              {group.items.map((item) => {
                const selected = selectedIds.includes(item.id);
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      role="checkbox"
                      aria-checked={selected}
                      className={`action-menu-item${selected ? " action-menu-item--selected" : ""}`}
                      disabled={disabled}
                      title={item.description}
                      onClick={() => toggleItem(item)}
                    >
                      <span className="action-menu-item-check" aria-hidden="true">
                        {selected ? "☑" : "☐"}
                      </span>
                      <span className="action-menu-item-name">{item.name}</span>
                      <span
                        className={`action-menu-difficulty ${difficultyClass(
                          item.difficulty_hint,
                        )}`}
                      >
                        {item.difficulty_hint}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    </details>
  );
}

export type { ActionMenuItem };
