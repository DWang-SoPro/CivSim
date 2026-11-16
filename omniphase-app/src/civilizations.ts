/** 开局文明模板目录（与 backend/templates/civilizations.py 对齐）。 */

export type CivTemplateMeta = {
  id: string;
  name: string;
  shortName: string;
  era: string;
  region: string;
  blurb: string;
  year: number;
};

export const CIV_TEMPLATES: CivTemplateMeta[] = [
  {
    id: "sumer",
    name: "苏美尔城邦联盟",
    shortName: "苏美尔",
    era: "约公元前 3000 年",
    region: "两河流域南部",
    blurb: "神庙城邦林立，灌溉农业与城邦守护神信仰奠定早期文明秩序。",
    year: -3000,
  },
  {
    id: "egypt",
    name: "早王朝埃及",
    shortName: "埃及",
    era: "约公元前 3000 年",
    region: "尼罗河流域",
    blurb: "法老神权与国有授田并行，官僚萌芽维系长河两岸的统一。",
    year: -3000,
  },
  {
    id: "harappa",
    name: "哈拉帕联盟",
    shortName: "哈拉帕",
    era: "约公元前 2000 年",
    region: "印度河流域",
    blurb: "城市规划精巧而军事色彩淡薄，贸易与氏族共治维持高稳定。",
    year: -2000,
  },
  {
    id: "babylon",
    name: "古巴比伦王国",
    shortName: "巴比伦",
    era: "约公元前 2000 年",
    region: "两河流域中部",
    blurb: "军功王权与法典传统并重，行政积累较高，吞吐四方贡赋。",
    year: -2000,
  },
  {
    id: "zhou",
    name: "西周王朝",
    shortName: "西周",
    era: "约公元前 1000 年",
    region: "黄河中游",
    blurb: "宗法封建与天命信仰交织，授田徭役支撑广阔疆域。",
    year: -1000,
  },
  {
    id: "greece",
    name: "古希腊城邦",
    shortName: "希腊",
    era: "约公元前 500 年",
    region: "爱琴海沿岸",
    blurb: "议事会与公民政治活跃，知识与商业积累突出，山地农耕拮据。",
    year: -500,
  },
];

export function getCivTemplate(id: string): CivTemplateMeta | undefined {
  return CIV_TEMPLATES.find((item) => item.id === id);
}
