/** 后端枚举 / 数值 → 中文展示文案。 */

export const LAND_SYSTEM_LABELS: Record<string, string> = {
  clan_communal: "氏族公有",
  noble_estate: "贵族庄园",
  state_grant: "国有授田",
  landlord_tenant: "地主租佃",
  yeoman_smallhold: "自耕农小农",
};

export const AUTHORITY_SOURCE_LABELS: Record<string, string> = {
  bloodline: "血统",
  military: "军功",
  election: "推举",
  theocratic: "神权",
};

export const DECISION_STRUCTURE_LABELS: Record<string, string> = {
  autocracy: "独裁",
  oligarchy: "寡头",
  council: "议事会",
  bureaucracy: "官僚体制",
};

export const SUCCESSION_LABELS: Record<string, string> = {
  hereditary: "世袭",
  abdication: "禅让",
  election: "选举",
  military_coup: "军事夺权",
};

export const LEGITIMACY_LABELS: Record<string, string> = {
  traditional: "传统",
  religious: "天命",
  performance: "绩效",
  legal: "法理",
};

const LABOR_LABELS: Record<string, string> = {
  free_citizens: "自由民",
  corvee: "徭役",
  serf: "农奴",
  slave: "奴隶",
};

export function labelOrRaw(
  map: Record<string, string>,
  key: string | null | undefined,
): string {
  if (!key) {
    return "—";
  }
  return map[key] ?? key;
}

export function formatBureaucracy(value: number): string {
  if (value < 0.15) return "无";
  if (value < 0.35) return "萌芽";
  if (value < 0.55) return "初级";
  if (value < 0.75) return "中级";
  return "完善";
}

export function formatPolitySummary(polity: {
  authority_source: string;
  decision_structure: string;
  succession: string;
}): string {
  const source = labelOrRaw(AUTHORITY_SOURCE_LABELS, polity.authority_source);
  const decision = labelOrRaw(
    DECISION_STRUCTURE_LABELS,
    polity.decision_structure,
  );
  const succession = labelOrRaw(SUCCESSION_LABELS, polity.succession);
  return `${source}·${decision}·${succession}`;
}

export function formatLaborSummary(labor: {
  free_citizens: number;
  corvee: number;
  serf: number;
  slave: number;
}): string {
  const ranked = (
    Object.entries(labor) as [string, number][]
  )
    .filter(([, share]) => share >= 0.12)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([key]) => LABOR_LABELS[key] ?? key);

  return ranked.length > 0 ? ranked.join("+") : "—";
}

export function formatLegitimacySummary(legitimacy: {
  traditional: number;
  religious: number;
  performance: number;
  legal: number;
}): string {
  const ranked = (
    Object.entries(legitimacy) as [string, number][]
  )
    .filter(([, strength]) => strength >= 0.35)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([key]) => LEGITIMACY_LABELS[key] ?? key);

  return ranked.length > 0 ? ranked.join("+") : "薄弱";
}

export type SocialSignal = {
  id: string;
  text: string;
  metricKey:
    | "stability"
    | "authority"
    | "class_tension"
    | "elite_cohesion";
  value: string;
};

function band(
  value: number,
  low: number,
  mid: number,
  high: number,
): "low" | "mid" | "high" | "peak" {
  if (value < low) return "low";
  if (value < mid) return "mid";
  if (value < high) return "high";
  return "peak";
}

export function buildSocialSignals(state: {
  stability: number;
  authority: number;
  class_tension: number | null;
  elite_cohesion: number | null;
}): SocialSignal[] {
  const signals: SocialSignal[] = [];

  const stabilityBand = band(state.stability, 30, 55, 75);
  signals.push({
    id: "stability",
    metricKey: "stability",
    value: String(Math.round(state.stability * 100) / 100),
    text:
      stabilityBand === "low"
        ? "朝野不安，民心浮动。"
        : stabilityBand === "mid"
          ? "局势尚稳，暗流偶现。"
          : stabilityBand === "high"
            ? "秩序大体安稳。"
            : "海晏河清，根基稳固。",
  });

  const authorityBand = band(state.authority, 30, 55, 75);
  signals.push({
    id: "authority",
    metricKey: "authority",
    value: String(Math.round(state.authority * 100) / 100),
    text:
      authorityBand === "low"
        ? "号令难行，威柄不张。"
        : authorityBand === "mid"
          ? "统治尚可，边鄙时有不从。"
          : authorityBand === "high"
            ? "王命通行，控制力充足。"
            : "乾纲独断，威加海内。",
  });

  if (state.class_tension !== null) {
    const tensionBand = band(state.class_tension, 0.25, 0.45, 0.7);
    signals.push({
      id: "class_tension",
      metricKey: "class_tension",
      value: String(Math.round(state.class_tension * 100) / 100),
      text:
        tensionBand === "low"
          ? "各阶层相安，张力尚轻。"
          : tensionBand === "mid"
            ? "贫富之间偶有怨言。"
            : tensionBand === "high"
              ? "阶级龃龉日显，需防激变。"
              : "矛盾尖锐，一触即发。",
    });
  }

  if (state.elite_cohesion !== null) {
    const cohesionBand = band(state.elite_cohesion, 0.3, 0.5, 0.7);
    signals.push({
      id: "elite_cohesion",
      metricKey: "elite_cohesion",
      value: String(Math.round(state.elite_cohesion * 100) / 100),
      text:
        cohesionBand === "low"
          ? "权贵离心，各怀心思。"
          : cohesionBand === "mid"
            ? "精英大体共事，偶有裂隙。"
            : cohesionBand === "high"
              ? "贵胄同心，朝堂齐整。"
              : "统治集团高度凝聚。",
    });
  }

  return signals;
}
