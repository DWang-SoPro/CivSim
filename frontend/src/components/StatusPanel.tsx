"use client";

import type { ReactNode } from "react";

import { CivEmblem } from "@/components/CivEmblem";
import {
  buildSocialSignals,
  formatBureaucracy,
  formatLaborSummary,
  formatLegitimacySummary,
  formatPolitySummary,
  labelOrRaw,
  LAND_SYSTEM_LABELS,
} from "@/lib/labels";

export type DimensionChanges = Record<string, string>;

export type ChangeableStateKey =
  | "population"
  | "stability"
  | "authority"
  | "class_tension"
  | "elite_cohesion"
  | "bureaucratization"
  | "tech_agriculture"
  | "tech_engineering"
  | "tech_knowledge";

export type CivStateView = {
  civ_name: string;
  template_id: string;
  turn: number;
  year: number;
  population: number;
  tech_agriculture: number;
  tech_engineering: number;
  tech_knowledge: number;
  territory_core: number;
  territory_frontier: number;
  bureaucratization: number;
  stability: number;
  authority: number;
  class_tension: number | null;
  elite_cohesion: number | null;
  land_system: string;
  labor_distribution: {
    free_citizens: number;
    corvee: number;
    serf: number;
    slave: number;
  };
  polity: {
    authority_source: string;
    decision_structure: string;
    succession: string;
  };
  legitimacy: {
    traditional: number;
    religious: number;
    performance: number;
    legal: number;
  };
};

const dimensionChangeKeys: Record<ChangeableStateKey, readonly string[]> = {
  // food 单独成行展示，不并入人口变化。
  population: ["population"],
  stability: ["stability"],
  authority: ["authority"],
  class_tension: ["class_tension"],
  elite_cohesion: ["elite_cohesion"],
  bureaucratization: ["bureaucratization"],
  tech_agriculture: ["tech_agriculture"],
  tech_engineering: ["tech_engineering"],
  tech_knowledge: ["tech_knowledge"],
};

function getDimensionChange(
  changes: DimensionChanges,
  stateKey: ChangeableStateKey,
): string | undefined {
  for (const changeKey of dimensionChangeKeys[stateKey]) {
    const change = changes[changeKey];
    if (typeof change === "string" && change.trim()) {
      return change.trim();
    }
  }
  return undefined;
}

type ChangeDirection = "up" | "down" | "zero";

function getChangeDirection(change: string): ChangeDirection {
  const normalized = change.trim();
  if (/^[+＋\-−－]?0(?:\.0+)?%?$/.test(normalized)) {
    return "zero";
  }
  if (/^[+＋↑]/.test(normalized)) {
    return "up";
  }
  if (/^[\-−－↓]/.test(normalized)) {
    return "down";
  }
  return "zero";
}

function formatChangeAmount(change: string): string {
  return change.trim().replace(/^[+＋\-−－↑↓]\s*/, "");
}

function formatMetric(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return String(Math.round(value * 100) / 100);
}

function StateMetric({
  value,
  change,
  textStyle = false,
}: {
  value: string | number;
  change?: string;
  textStyle?: boolean;
}) {
  if (!change) {
    return (
      <span className={textStyle ? "metric-value--text" : undefined}>
        {value}
      </span>
    );
  }

  const direction = getChangeDirection(change);
  const arrow = direction === "up" ? "↑" : direction === "down" ? "↓" : "→";
  const amount = formatChangeAmount(change);
  const directionLabel =
    direction === "up" ? "上升" : direction === "down" ? "下降" : "无变化";

  return (
    <>
      <span className={textStyle ? "metric-value--text" : undefined}>
        {value}
      </span>
      <span
        className={`dimension-change dimension-change--${direction}`}
        aria-label={`${directionLabel} ${amount}`}
      >
        {arrow}
        {amount}
      </span>
    </>
  );
}

function MetricRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="metric-row">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{children}</span>
    </div>
  );
}

function PanelSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details className="status-section" open={defaultOpen}>
      <summary className="status-section-summary">
        <span className="status-section-chevron" aria-hidden="true" />
        {title}
      </summary>
      <div className="status-section-card">{children}</div>
    </details>
  );
}

export function StatusPanel({
  state,
  dimensionChanges,
}: {
  state: CivStateView;
  dimensionChanges: DimensionChanges;
}) {
  const foodChange = dimensionChanges.food?.trim();
  const signals = buildSocialSignals(state);

  return (
    <aside className="status-panel" aria-label="文明状态">
      <div className="status-panel-header">
        <CivEmblem
          templateId={state.template_id}
          civName={state.civ_name}
          size={56}
        />
        <div className="status-panel-header-text">
          <h2 className="status-panel-civ">{state.civ_name}</h2>
          <span className="status-panel-label">国势</span>
        </div>
      </div>
      <div className="status-panel-body">
        <PanelSection title="物质基底" defaultOpen>
          <MetricRow label="人口">
            <StateMetric
              value={state.population.toLocaleString("zh-CN")}
              change={getDimensionChange(dimensionChanges, "population")}
            />
          </MetricRow>
          {foodChange ? (
            <MetricRow label="粮食">
              <StateMetric value="见趋势" change={foodChange} textStyle />
            </MetricRow>
          ) : null}
          <MetricRow label="农业技术">
            <StateMetric
              value={formatMetric(state.tech_agriculture)}
              change={getDimensionChange(dimensionChanges, "tech_agriculture")}
            />
          </MetricRow>
          <MetricRow label="工程技术">
            <StateMetric
              value={formatMetric(state.tech_engineering)}
              change={getDimensionChange(dimensionChanges, "tech_engineering")}
            />
          </MetricRow>
          <MetricRow label="知识技术">
            <StateMetric
              value={formatMetric(state.tech_knowledge)}
              change={getDimensionChange(dimensionChanges, "tech_knowledge")}
            />
          </MetricRow>
          <MetricRow label="核心领土">
            {state.territory_core.toLocaleString("zh-CN")} km²
          </MetricRow>
          <MetricRow label="边疆领土">
            {state.territory_frontier.toLocaleString("zh-CN")} km²
          </MetricRow>
        </PanelSection>

        <PanelSection title="生产关系">
          <MetricRow label="土地">
            <span className="metric-value--text">
              {labelOrRaw(LAND_SYSTEM_LABELS, state.land_system)}
            </span>
          </MetricRow>
          <MetricRow label="劳动">
            <span className="metric-value--text">
              {formatLaborSummary(state.labor_distribution)}
            </span>
          </MetricRow>
        </PanelSection>

        <PanelSection title="上层建筑">
          <MetricRow label="政体">
            <span className="metric-value--text">
              {formatPolitySummary(state.polity)}
            </span>
          </MetricRow>
          <MetricRow label="官僚化">
            <StateMetric
              value={formatBureaucracy(state.bureaucratization)}
              change={getDimensionChange(
                dimensionChanges,
                "bureaucratization",
              )}
              textStyle
            />
          </MetricRow>
          <MetricRow label="合法性">
            <span className="metric-value--text">
              {formatLegitimacySummary(state.legitimacy)}
            </span>
          </MetricRow>
        </PanelSection>

        <PanelSection title="社会信号">
          <ul className="signal-list">
            {signals.map((signal) => (
              <li key={signal.id} className="signal-item">
                {signal.text}
                <span className="signal-item-meta">
                  <StateMetric
                    value={signal.value}
                    change={getDimensionChange(
                      dimensionChanges,
                      signal.metricKey,
                    )}
                  />
                </span>
              </li>
            ))}
          </ul>
        </PanelSection>
      </div>
    </aside>
  );
}
