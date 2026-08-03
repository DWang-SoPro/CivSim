"use client";

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
  onPick: (suggestedInput: string) => void;
};

const DOMAIN_ORDER = ["economic", "political", "military", "cultural", "technology", "composite"];

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

export function ActionMenu({
  items,
  loading = false,
  disabled = false,
  onPick,
}: ActionMenuProps) {
  const grouped = DOMAIN_ORDER.map((domain) => ({
    domain,
    label: items.find((item) => item.domain === domain)?.domain_label ?? domain,
    items: items.filter((item) => item.domain === domain),
  })).filter((group) => group.items.length > 0);

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
          <span className="action-menu-meta">{items.length} 项</span>
        )}
      </summary>
      <div className="action-menu-body">
        {grouped.length === 0 && !loading && (
          <p className="action-menu-empty">暂无可用建议，可直接在下方输入。</p>
        )}
        {grouped.map((group) => (
          <section key={group.domain} className="action-menu-domain">
            <h3 className="action-menu-domain-title">{group.label}</h3>
            <ul className="action-menu-list">
              {group.items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="action-menu-item"
                    disabled={disabled}
                    title={item.description}
                    onClick={() => onPick(item.suggested_input)}
                  >
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
              ))}
            </ul>
          </section>
        ))}
      </div>
    </details>
  );
}

export type { ActionMenuItem };
