export interface Decree {
  id: string
  title: string
  text: string
  domain?: string
  domainLabel?: string
  description: string
  difficulty?: string
  available?: boolean
  unmetReason?: string | null
}
export interface GameSummary {
  gameId: string
  templateId: string
  name: string
  turn: number
  year: number
  updatedAt: string
}
export interface Stat {
  id: string
  label: string
  value: number
  unit: string
  norm?: number
  warn?: boolean
  inverse?: boolean
  before?: number
  delta?: number
  good?: boolean
}
export interface AccumulationStat {
  id: string
  label: string
  value: number
  before?: number
  delta?: number
  good?: boolean
}
export interface DeepPanel {
  indicators: Stat[]
  structure: {
    territoryCore: number
    territoryFrontier: number
    territoryTotal?: number
    territoryBefore?: number
    territoryDelta?: number
    landSystem: string
    landSystemBefore?: string
    polity: string
    polityBefore?: string
    extractions: string[]
    labor: { label: string; pct: number }[]
  }
  accumulations: AccumulationStat[]
}
export interface Change {
  id: string
  label: string
  before: number
  after: number
  delta?: number
  good?: boolean
  group?: 'core' | 'deep'
  unit: string
}
export interface TurnOutcome {
  name: string
  scale: 'small' | 'medium' | 'large' | string
  scaleLabel?: string
  tier: 'great' | 'success' | 'partial' | 'failure' | 'disaster' | 'blocked' | string
  tierLabel: string
  met: boolean
}
export interface UnlockBadge {
  id: string
  targetNodeId: string
  kind: 'tech' | 'land' | 'polity' | 'tax' | string
  kindLabel: string
  branchId?: string
  branchName: string
  name: string
  subtitle: string
  art: string
  effect: string
}
export interface TechReq {
  key: string
  label: string
  current: number
  target: number
  currentText: string
  targetText: string
  met: boolean
  ratio: number
}
export interface TechNode {
  id: string
  branchId: string
  branchName: string
  stage: number
  era: string
  name: string
  subtitle: string
  art: string
  effect: string
  chronicleNote: string
  status: 'unlocked' | 'next' | 'locked'
  unlocked: boolean
  progress: number
  reqs: TechReq[]
  suggestedDecrees: string[]
}
export interface TechBranch {
  id: 'agriculture' | 'engineering' | 'knowledge' | string
  name: string
  metricKey: string
  accent: string
  level: number
  levelText: string
  unlockedCount: number
  totalCount: number
  nodes: TechNode[]
}
export interface InstitutionNode {
  id: string
  name: string
  summary: string
  triggerHint: string
  suggestedDecrees: string[]
  active: boolean
  unlocked: boolean
  status: 'active' | 'unlocked' | 'locked'
}
export interface InstitutionGroup {
  title: string
  currentId?: string
  activeIds?: string[]
  nodes: InstitutionNode[]
}
export interface Progression {
  unlockedCount: number
  totalNodes: number
  focusNodeId: string
  recentUnlocks: UnlockBadge[]
  branches: TechBranch[]
  institutions: {
    land: InstitutionGroup
    polity: InstitutionGroup
    tax: InstitutionGroup
  }
}
export interface Entry {
  turn: number
  year: number
  years?: number
  decree: string
  narrative: string
  outcomes?: TurnOutcome[]
  changes: Change[]
  unlocks?: UnlockBadge[]
}
export interface Game extends GameSummary {
  status: 'active' | 'game_over'
  ending?: string | null
  stats: Stat[]
  panel?: DeepPanel
  progression?: Progression
  availableDecrees?: Decree[]
  history: Entry[]
  clarification?: string
}
export interface Catalog {
  mode?: 'offline' | 'model'
  preferredMode?: 'auto' | 'model' | 'offline'
  canToggleModel?: boolean
  hostManaged?: boolean
  slotsEnabled?: boolean
  modelName?: string
  templates: { id: string; name: string; description: string }[]
  decrees: Decree[]
}
export interface ConsultResponse {
  gameId: string
  turn: number
  answer: string
  source: 'model' | 'local'
}
export interface Context {
  page: 'list' | 'record'
  recordId?: string
  title: string
  summary?: string
  targets: { id: string; title: string }[]
}
type Command =
  | { type: 'input'; text: string; recordId: string | null }
  | { type: 'navigate'; recordId: string | null }
  | { type: 'result'; recordId: string | null }
export type Action =
  | 'catalog'
  | 'list'
  | 'get'
  | 'new'
  | 'turn'
  | 'delete'
  | 'consult'
  | 'mode'

declare global {
  interface Window {
    wanxiang?: {
      gameRequest?: (
        action: Action,
        payload: Record<string, unknown>
      ) => Promise<unknown>
      publishContext?: (context: Context) => void
      onCommand?: (
        listener: (command: Command) => boolean | void | Promise<boolean>
      ) => () => void
    }
  }
}

export function request<T>(
  action: Action,
  payload: Record<string, unknown> = {}
): Promise<T> {
  if (!window.wanxiang?.gameRequest) {
    return Promise.reject(new Error('请在万相内打开已安装的文明灵。'))
  }
  return window.wanxiang.gameRequest(action, payload) as Promise<T>
}

export function requestId() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64
  bytes[8] = (bytes[8] & 63) | 128
  const hex = [...bytes].map(byte => byte.toString(16).padStart(2, '0')).join('')
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20),
  ].join('-')
}

export function historicalYear(year: number) {
  const rounded = Math.round(year)
  return rounded < 0 ? '公元前 ' + Math.abs(rounded) + ' 年' : '公元 ' + rounded + ' 年'
}

const numberFormat = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 })
export function valueText(value: number) {
  return numberFormat.format(value)
}

export function changeDelta(change: Change): number {
  return typeof change.delta === 'number'
    ? change.delta
    : Number((change.after - change.before).toFixed(2))
}

export function isGoodChange(change: Change): boolean {
  if (typeof change.good === 'boolean') return change.good
  const d = changeDelta(change)
  return change.id === 'class_tension' ? d < 0 : d > 0
}

export function changeText(change: Change) {
  const delta = changeDelta(change)
  return (delta > 0 ? '+' : '') + valueText(delta) + change.unit
}

export function signedNumberText(delta: number, unit = '') {
  return (delta > 0 ? '+' : '') + valueText(delta) + unit
}

/** Fallback client-side archive lookup if backend consult is unreachable. */
export function consultHistory(question: string, game: Game): string {
  const specifiedTurn = question.match(/第\s*(\d+)\s*(?:回合|轮)/)
  const entry = specifiedTurn
    ? game.history.find(row => row.turn === Number(specifiedTurn[1]))
    : game.history.at(-1)
  if (!entry) {
    return specifiedTurn ? '当前可见的史卷里没有这一回合。' : '此卷尚未记事。'
  }
  const stat = game.stats.find(
    row => question.includes(row.label) || (row.id === 'food' && question.includes('粮'))
  )
  if (!specifiedTurn && stat) {
    const movement = entry.changes.find(row => row.id === stat.id)
    return (
      stat.label +
      '现为 ' +
      valueText(stat.value) +
      stat.unit +
      '。' +
      (movement
        ? '最近一次结算由 ' +
          valueText(movement.before) +
          movement.unit +
          ' 变为 ' +
          valueText(movement.after) +
          movement.unit +
          '。'
        : '本回合没有记载这一项的变动。') +
      (entry.decree ? '当时的政令是「' + entry.decree + '」。' : '')
    )
  }
  const changes = entry.changes
    .slice(0, 4)
    .map(row => row.label + ' ' + changeText(row))
    .join('、')
  return (
    historicalYear(entry.year) +
    '，' +
    (entry.turn === 0 ? '开国' : '第 ' + entry.turn + ' 回合') +
    '。' +
    entry.narrative +
    (changes ? ' 国势记录：' + changes + '。' : '')
  )
}
