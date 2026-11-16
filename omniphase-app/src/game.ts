export interface Decree { id: string; title: string; text: string; description: string }
export interface GameSummary { gameId: string; templateId: string; name: string; turn: number; year: number; updatedAt: string }
export interface Stat { id: string; label: string; value: number; unit: string }
export interface Change { id: string; label: string; before: number; after: number; unit: string }
export interface Entry { turn: number; year: number; decree: string; narrative: string; changes: Change[] }
export interface Game extends GameSummary {
  status: 'active' | 'game_over'
  stats: Stat[]
  history: Entry[]
  clarification?: string
}
export interface Catalog { mode?: 'offline' | 'model'; modelName?: string; templates: { id: string; name: string; description: string }[]; decrees: Decree[] }
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
type Action = 'catalog' | 'list' | 'get' | 'new' | 'turn'
declare global {
  interface Window {
    wanxiang?: {
      gameRequest?: (action: Action, payload: Record<string, unknown>) => Promise<unknown>
      publishContext?: (context: Context) => void
      onCommand?: (listener: (command: Command) => boolean | void | Promise<boolean>) => (() => void)
    }
  }
}
export function request<T>(action: Action, payload: Record<string, unknown> = {}): Promise<T> {
  if (!window.wanxiang?.gameRequest) return Promise.reject(new Error('请在万相内打开已安装的文明灵。'))
  return window.wanxiang.gameRequest(action, payload) as Promise<T>
}
export function requestId() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64
  bytes[8] = (bytes[8] & 63) | 128
  const hex = [...bytes].map(byte => byte.toString(16).padStart(2, '0')).join('')
  return [hex.slice(0,8), hex.slice(8,12), hex.slice(12,16), hex.slice(16,20), hex.slice(20)].join('-')
}
export function historicalYear(year: number) {
  return year < 0 ? '公元前 ' + Math.abs(year) + ' 年' : '公元 ' + year + ' 年'
}
const numberFormat = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 })
export function valueText(value: number) { return numberFormat.format(value) }
export function changeText(change: Change) {
  const delta = change.after - change.before
  return (delta > 0 ? '+' : '') + valueText(delta) + change.unit
}

/** Read only the settled archive. Answers never dispatch a game action. */
export function consultHistory(question: string, game: Game): string {
  const specifiedTurn = question.match(/第\s*(\d+)\s*(?:回合|轮)/)
  const entry = specifiedTurn ? game.history.find(row => row.turn === Number(specifiedTurn[1])) : game.history.at(-1)
  if (!entry) return specifiedTurn ? '当前可见的史卷里没有这一回合。' : '此卷尚未记事。'
  const stat = game.stats.find(row => question.includes(row.label) || (row.id === 'food' && question.includes('粮')))
  if (!specifiedTurn && stat) {
    const movement = entry.changes.find(row => row.id === stat.id)
    return stat.label + '现为 ' + valueText(stat.value) + stat.unit + '。' + (movement ? '最近一次结算由 ' + valueText(movement.before) + movement.unit + ' 变为 ' + valueText(movement.after) + movement.unit + '。' : '本回合没有记载这一项的变动。') + (entry.decree ? '当时的政令是「' + entry.decree + '」。' : '')
  }
  const changes = entry.changes.slice(0, 3).map(row => row.label + ' ' + changeText(row)).join('、')
  return historicalYear(entry.year) + '，' + (entry.turn === 0 ? '开国' : '第 ' + entry.turn + ' 回合') + '。' + entry.narrative + (changes ? ' 国势记录：' + changes + '。' : '')
}
