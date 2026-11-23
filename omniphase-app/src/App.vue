<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { CIV_TEMPLATES, getCivTemplate } from './civilizations'
import Atlas from './Atlas.vue'
import ArtifactArt from './ArtifactArt.vue'
import RealmDiorama from './RealmDiorama.vue'
import TechTree from './TechTree.vue'
import {
  changeDelta,
  changeText,
  consultHistory,
  historicalYear,
  isGoodChange,
  request,
  requestId,
  signedNumberText,
  valueText,
} from './game'
import type {
  Catalog,
  Change,
  ConsultResponse,
  Context,
  Decree,
  Game,
  GameSummary,
} from './game'
import emblem from '../icon.svg'

const DOMAINS = [
  { id: 'all', label: '全部' },
  { id: 'economic', label: '经济' },
  { id: 'political', label: '政治' },
  { id: 'military', label: '军事' },
  { id: 'cultural', label: '文化' },
  { id: 'technology', label: '科技' },
  { id: 'composite', label: '综合' },
]

const CONSULT_PRESETS = [
  { short: '隐忧与建议', text: '当前国势有何隐忧与施政建议？' },
  { short: '粮仓与供需', text: '最近粮食与仓储怎样变化？' },
  { short: '田制与政体', text: '现行田制、政体与赋税如何？' },
]

const LABOR_COLORS: Record<string, string> = {
  自由民: '#3c6e57',
  徭役: '#b08344',
  农奴: '#7e6651',
  奴隶: '#984836',
}

const game = ref<Game | null>(null)
const saves = ref<GameSummary[]>([])
const catalog = ref<Catalog>({ templates: [], decrees: [] })
const selected = ref('zhou')
const selectedCiv = computed(() => getCivTemplate(selected.value) ?? CIV_TEMPLATES[0])
const library = ref(true)
const activeTab = ref<'court' | 'tree' | 'archive'>('court')
const focusedNodeId = ref<string | null>(null)
const openComposer = ref(false)
const moreDecrees = ref(false)
const domainFilter = ref('all')
const showDeepPanel = ref(true)
const showAllChanges = ref(false)
const confirmingDelete = ref<string | null>(null)
const lockedHint = ref('')
const draft = ref('')
const authoring = ref<'decree' | 'consult'>('decree')
const busy = ref(false)
const connected = ref(false)
const hasBridge = typeof window.wanxiang?.gameRequest === 'function'
const loading = ref(true)
const error = ref('')
const clarification = ref('')
const reply = ref('')
const inputEl = ref<HTMLTextAreaElement | null>(null)
const settledPulse = ref(false)
let pulseTimer: ReturnType<typeof setTimeout> | undefined

const latest = computed(() => game.value?.history.at(-1))
const visibleChanges = computed(() => {
  const list = latest.value?.changes ?? []
  if (showAllChanges.value || list.length <= 8) return list
  return list.slice(0, 8)
})
const entries = computed(() => [...(game.value?.history ?? [])].reverse())

const activeDecrees = computed<Decree[]>(() => {
  return game.value?.availableDecrees?.length
    ? game.value.availableDecrees
    : catalog.value.decrees
})

const availableDecreeCount = computed(
  () => activeDecrees.value.filter(d => d.available !== false).length
)

const filteredDecrees = computed<Decree[]>(() => {
  if (domainFilter.value === 'all') return activeDecrees.value
  return activeDecrees.value.filter(d => d.domain === domainFilter.value)
})

const activeScale = computed<'small' | 'medium' | 'large'>(() => {
  const trimmed = draft.value.trim()
  if (/^(?:小规模|试行)/.test(trimmed)) return 'small'
  if (/^(?:大规模|举国)/.test(trimmed)) return 'large'
  return 'medium'
})

const draftedParts = computed(() =>
  draft.value
    .trim()
    .replace(/^(?:小规模|大规模|举国|试行)\s*/, '')
    .split(/\s*[、，,；;]\s*/)
    .filter(Boolean)
)

function isDecreeDrafted(d: Decree): boolean {
  if (!openComposer.value || authoring.value !== 'decree') return false
  return draftedParts.value.includes(d.text) || draftedParts.value.includes(d.title)
}

const starterActions = computed<Decree[]>(() => {
  const pool = activeDecrees.value.filter(d => d.available !== false)
  const food = game.value?.stats.find(s => s.id === 'food')?.value ?? 1.1
  const tension =
    game.value?.panel?.indicators.find(s => s.id === 'class_tension')?.value ?? 35
  const preferred =
    food < 1.0
      ? ['开垦荒地', '兴修水利', '改进农具', '赈济饥民']
      : tension >= 60
        ? ['赈济饥民', '编纂律令', '巡狩四方', '兴修水利']
        : ['兴修水利', '修建粮仓', '开垦荒地', '设立学宫']
  const chosen = preferred
    .map(title => pool.find(d => d.title === title))
    .filter((d): d is Decree => Boolean(d))
  return [
    ...new Map([...chosen, ...pool].map(d => [d.id, d])).values(),
  ].slice(0, 4)
})

const activeLabor = computed(() =>
  (game.value?.panel?.structure.labor ?? []).filter(item => item.pct > 0)
)

const modeBadge = computed(() => {
  if (catalog.value.mode === 'model') {
    const label = catalog.value.modelName ? ` · ${catalog.value.modelName}` : ''
    return catalog.value.hostManaged ? `万相史官${label}` : `模型政令${label}`
  }
  return '本机单人 · 28 项国策'
})

const pendingTurns = reactive(
  new Map<string, { gameId: string; turn: number; text: string; key: string }>()
)
const pendingTurn = computed(() =>
  game.value ? pendingTurns.get(game.value.gameId) : undefined
)
let pendingNew: { id: string; key: string } | undefined
let unsubscribe: (() => void) | undefined
let mounted = true

function explainError(e: unknown) {
  return e instanceof Error ? e.message : String(e)
}

function triggerSettlePulse() {
  settledPulse.value = false
  clearTimeout(pulseTimer)
  requestAnimationFrame(() => {
    settledPulse.value = true
    pulseTimer = setTimeout(() => {
      settledPulse.value = false
    }, 1500)
  })
}

function deltaArrow(change: Change): string {
  return changeDelta(change) > 0 ? '▲' : '▼'
}

function updateSaves(data: Game) {
  const { gameId, templateId, name, year, turn, updatedAt } = data
  saves.value = [
    { gameId, templateId, name, year, turn, updatedAt },
    ...saves.value.filter(s => s.gameId !== gameId),
  ]
}

function resetInput() {
  moreDecrees.value = false
  showAllChanges.value = false
  lockedHint.value = ''
  draft.value = ''
  openComposer.value = false
  authoring.value = 'decree'
  clarification.value = ''
  reply.value = ''
}

function showGame(data: Game) {
  const previous = pendingTurns.get(data.gameId)
  if (previous && previous.turn !== data.turn) pendingTurns.delete(data.gameId)
  game.value = data
  selected.value = data.templateId
  library.value = false
  activeTab.value = 'court'
  focusedNodeId.value = data.progression?.focusNodeId ?? null
  confirmingDelete.value = null
  updateSaves(data)
  resetInput()
  if (previous && previous.turn === data.turn) {
    draft.value = previous.text
    openComposer.value = true
    error.value = '上道政令尚无回执，可重读国史或按相同请求重试。'
  }
}

function openTechTree(nodeId?: string) {
  if (nodeId) focusedNodeId.value = nodeId
  else if (game.value?.progression?.focusNodeId) {
    focusedNodeId.value = game.value.progression.focusNodeId
  }
  activeTab.value = 'tree'
}

function stageFromTree(decrees: string[]) {
  activeTab.value = 'court'
  const picked = decrees.slice(0, 3)
  void compose('decree', picked.length ? picked.join('、') : undefined)
}

async function getGame(id: string) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    showGame(await request<Game>('get', { gameId: id }))
  } catch (e) {
    error.value = explainError(e)
  } finally {
    busy.value = false
  }
}

async function boot() {
  if (!hasBridge) {
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    const [catalogData, list] = await Promise.all([
      request<Catalog>('catalog'),
      request<{ games: GameSummary[] }>('list'),
    ])
    if (!mounted) return
    catalog.value = catalogData
    saves.value = list.games
    connected.value = true
    if (saves.value.length) await getGame(saves.value[0].gameId)
  } catch (e) {
    error.value = explainError(e)
    connected.value = false
  } finally {
    loading.value = false
  }
}

async function toggleMode() {
  if (!connected.value || busy.value || !catalog.value.canToggleModel) return
  const target = catalog.value.mode === 'model' ? 'offline' : 'auto'
  busy.value = true
  error.value = ''
  try {
    catalog.value = await request<Catalog>('mode', { mode: target })
  } catch (e) {
    error.value = explainError(e)
  } finally {
    busy.value = false
  }
}

async function newGame() {
  if (!connected.value || busy.value || loading.value) return
  const id = selected.value
  if (pendingNew?.id !== id) pendingNew = { id, key: requestId() }
  busy.value = true
  error.value = ''
  try {
    showGame(
      await request<Game>('new', { templateId: id, requestId: pendingNew.key })
    )
    pendingNew = undefined
  } catch (e) {
    error.value = explainError(e)
  } finally {
    busy.value = false
  }
}

async function removeSave(id: string) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const res = await request<{ games: GameSummary[] }>('delete', {
      gameId: id,
      requestId: requestId(),
    })
    saves.value = res.games
    pendingTurns.delete(id)
    if (game.value?.gameId === id) {
      game.value = null
      library.value = true
    }
    confirmingDelete.value = null
  } catch (e) {
    error.value = explainError(e)
  } finally {
    busy.value = false
  }
}

async function openLibrary() {
  if (busy.value) return
  library.value = true
  activeTab.value = 'court'
  confirmingDelete.value = null
  error.value = ''
  if (!connected.value) return
  try {
    const [catalogData, list] = await Promise.all([
      request<Catalog>('catalog'),
      request<{ games: GameSummary[] }>('list'),
    ])
    catalog.value = catalogData
    saves.value = list.games
  } catch (e) {
    error.value = explainError(e)
  }
}

function pickDecree(d: Decree) {
  if (busy.value) return
  if (d.available === false) {
    lockedHint.value = `「${d.title}」尚未具备条件：${d.unmetReason || '请先夯实国势基础'}。`
    return
  }
  lockedHint.value = ''
  if (openComposer.value && authoring.value === 'decree' && draft.value.trim()) {
    const scalePrefix =
      activeScale.value === 'small'
        ? '小规模'
        : activeScale.value === 'large'
          ? '大规模'
          : ''
    const parts = [...draftedParts.value]
    const idx = parts.findIndex(p => p === d.text || p === d.title)
    if (idx >= 0) {
      parts.splice(idx, 1)
      draft.value = parts.length ? `${scalePrefix}${parts.join('、')}` : ''
      return
    }
    if (parts.length >= 3) {
      lockedHint.value = '单回合最多并举 3 项政令，以免民力过度分薄。可先点已选国策取消一项。'
      return
    }
    parts.push(d.text)
    draft.value = `${scalePrefix}${parts.join('、')}`
    return
  }
  void compose('decree', d.text)
}

function applyScalePrefix(scale: 'small' | 'medium' | 'large') {
  const cleaned = draft.value
    .trim()
    .replace(/^(?:小规模|大规模|举国|试行)\s*/, '')
  if (!cleaned) return
  draft.value =
    scale === 'small'
      ? `小规模${cleaned}`
      : scale === 'large'
        ? `大规模${cleaned}`
        : cleaned
}

function toggleMoreDecrees() {
  moreDecrees.value = !moreDecrees.value
  if (moreDecrees.value) {
    reply.value = ''
  }
}

async function compose(mode: 'decree' | 'consult', text?: string) {
  if (busy.value) return
  authoring.value = mode
  openComposer.value = true
  if (mode === 'consult') moreDecrees.value = false
  error.value = ''
  clarification.value = ''
  lockedHint.value = ''
  if (text !== undefined) draft.value = text
  else if (mode === 'consult') draft.value = ''
  await nextTick()
  inputEl.value?.focus()
}

function publish() {
  const current = library.value ? null : game.value
  const targets = saves.value
    .slice(0, 10)
    .map(s => ({ id: s.gameId, title: s.name }))
  if (current && !targets.some(s => s.id === current.gameId)) {
    targets.unshift({ id: current.gameId, title: current.name })
  }
  const context: Context = current
    ? {
        page: 'record',
        recordId: current.gameId,
        title: current.name,
        summary: historicalYear(current.year) + '，第 ' + current.turn + ' 回合',
        targets,
      }
    : { page: 'list', title: '文明与存档', targets }
  window.wanxiang?.publishContext?.(context)
}
watch([game, library, saves], publish)

async function submit(text: string, mode = authoring.value): Promise<boolean> {
  const active = game.value,
    value = text.trim()
  if (!active || busy.value || library.value || !value) return false
  error.value = ''
  clarification.value = ''
  lockedHint.value = ''
  if (mode === 'consult') {
    busy.value = true
    try {
      const res = await request<ConsultResponse>('consult', {
        gameId: active.gameId,
        question: value.slice(0, 500),
      })
      reply.value = res.answer
    } catch {
      reply.value = consultHistory(value, active)
    } finally {
      busy.value = false
    }
    draft.value = ''
    openComposer.value = false
    activeTab.value = 'court'
    return true
  }
  if (active.status === 'game_over') {
    error.value = '此局已终，可进入国史查看记录。'
    return false
  }
  if ([...value].length > 2000) {
    error.value = '政令请控制在 2000 字以内。'
    return false
  }
  const prior = pendingTurn.value
  if (
    prior &&
    (prior.gameId !== active.gameId ||
      prior.turn !== active.turn ||
      prior.text !== value)
  ) {
    error.value = '上道政令的结果尚待核对，请先重读本局。'
    return false
  }
  const operation = prior ?? {
    gameId: active.gameId,
    turn: active.turn,
    text: value,
    key: requestId(),
  }
  pendingTurns.set(active.gameId, operation)
  busy.value = true
  reply.value = ''
  try {
    const prevTurn = active.turn
    const data = await request<Game>('turn', {
      gameId: operation.gameId,
      expectedTurn: operation.turn,
      input: value,
      requestId: operation.key,
    })
    if (!mounted) return false
    game.value = data
    updateSaves(data)
    pendingTurns.delete(active.gameId)
    activeTab.value = 'court'
    if (data.turn > prevTurn) triggerSettlePulse()
    if (data.clarification) {
      clarification.value = data.clarification
      draft.value = value
      openComposer.value = true
    } else resetInput()
    return true
  } catch (e) {
    draft.value = value
    openComposer.value = true
    error.value = explainError(e)
    return false
  } finally {
    busy.value = false
  }
}

async function reconcile() {
  const prior = pendingTurn.value
  if (!prior || busy.value) return
  busy.value = true
  try {
    const data = await request<Game>('get', { gameId: prior.gameId })
    game.value = data
    updateSaves(data)
    activeTab.value = 'court'
    if (data.turn !== prior.turn) {
      pendingTurns.delete(prior.gameId)
      resetInput()
      triggerSettlePulse()
      error.value = '已重读最新国史，请核对纪年后继续。'
    } else {
      draft.value = prior.text
      openComposer.value = true
      error.value = '服务端仍为原回合。再次颁令将沿用同一请求编号。'
    }
  } catch (e) {
    error.value = explainError(e)
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  unsubscribe = window.wanxiang?.onCommand?.(command => {
    if (command.type === 'navigate') {
      if (busy.value) return false
      if (command.recordId === null) void openLibrary()
      else if (saves.value.some(s => s.gameId === command.recordId)) {
        void getGame(command.recordId)
      }
    }
    if (command.type === 'input') {
      if (
        command.recordId !== game.value?.gameId ||
        library.value ||
        busy.value ||
        !command.text?.trim()
      ) {
        return false
      }
      const asking = /^(问史官|问史|查史)[：:\s]*/.exec(command.text.trim())
      return submit(
        asking
          ? command.text.trim().slice(asking[0].length) || '当前国势有何隐忧与建议？'
          : command.text,
        asking ? 'consult' : 'decree'
      )
    }
  })
  publish()
  void boot()
})
onUnmounted(() => {
  mounted = false
  clearTimeout(pulseTimer)
  unsubscribe?.()
})
</script>

<template>
  <main class="ledger" :class="{ settling: settledPulse }">
    <header class="mast">
      <div class="identity">
        <img :src="emblem" alt="" width="30" height="30" />
        <strong>文明灵</strong>
        <span>CivSim</span>
      </div>
      <div class="mast-right">
        <button
          v-if="catalog.canToggleModel"
          type="button"
          class="mode-pill interactive"
          data-testid="civsim-mode-toggle"
          :disabled="busy"
          :title="catalog.mode === 'model' ? '点击切换为离线规则引擎' : '点击启用万相智能史官与自由政令'"
          @click="toggleMode"
        >
          <span class="dot" :class="{ active: catalog.mode === 'model' }" />
          {{ modeBadge }}
        </button>
        <span v-else class="mode-pill">
          <span class="dot" :class="{ active: catalog.mode === 'model' }" />
          {{ modeBadge }}
        </span>
        <div v-if="game && !library" class="nav">
          <button type="button" :aria-pressed="activeTab === 'court'" @click="activeTab = 'court'">朝堂</button>
          <button
            v-if="game.progression"
            type="button"
            data-testid="civsim-tree-tab"
            :aria-pressed="activeTab === 'tree'"
            @click="openTechTree()"
          >
            天工图谱
            <span
              class="nav-badge"
              :class="{ 'is-new': game.progression.recentUnlocks.length > 0 }"
            >
              {{ game.progression.unlockedCount }}/{{ game.progression.totalNodes }}
            </span>
          </button>
          <button
            type="button"
            data-testid="civsim-history"
            :aria-pressed="activeTab === 'archive'"
            @click="activeTab = 'archive'"
          >
            国史 ({{ game.history.length }})
          </button>
          <button
            type="button"
            data-testid="civsim-library"
            :disabled="busy"
            @click="openLibrary"
          >
            文明与存档 <span aria-hidden="true">↗</span>
          </button>
        </div>
      </div>
    </header>

    <!-- 一、开局与存档视图（一屏自适应，存档区独立局部滚动） -->
    <section v-if="library || !game" class="library">
      <div class="atlas-hero">
        <Atlas :selected="selected" @select="selected = $event" />
        <div class="hero-caption">
          <p>文明发源地</p>
          <h1>{{ selectedCiv.name }}</h1>
          <span>{{ selectedCiv.region }} · {{ selectedCiv.era }}</span>
        </div>
      </div>
      <div class="library-body">
        <section class="selection">
          <h2>选择开局文明</h2>
          <div class="civilizations" role="group" aria-label="开局文明">
            <button
              v-for="civ in CIV_TEMPLATES"
              :key="civ.id"
              type="button"
              :data-testid="'civsim-template-' + civ.id"
              :aria-pressed="civ.id === selected"
              :disabled="busy"
              @click="selected = civ.id"
            >
              {{ civ.shortName }}
            </button>
          </div>
          <p class="blurb">{{ selectedCiv.blurb }}</p>
          <button
            type="button"
            class="primary"
            data-testid="civsim-start"
            :disabled="!connected || busy || loading"
            @click="newGame"
          >
            {{ busy ? '正在入局…' : '从' + selectedCiv.shortName + '开局' }}
            <span aria-hidden="true">→</span>
          </button>
          <p v-if="!hasBridge" class="notice">
            当前为预览。请在已连接本机游戏服务的万相内打开。
          </p>
          <p v-if="loading" class="notice" role="status">正在读取本机存档…</p>
          <div v-if="error" class="notice error" role="alert">
            {{ error }}
            <button v-if="!connected" type="button" @click="boot">重新连接</button>
          </div>
        </section>

        <section class="saves">
          <div class="section-head">
            <h2>本机存档</h2>
            <small v-if="saves.length">{{ saves.length }} 份记录</small>
          </div>
          <p v-if="!saves.length" class="muted">开局后将自动保存进度。</p>
          <div v-else class="saves-scroll">
            <div v-for="(save, index) in saves" :key="save.gameId" class="save-row">
              <button
                type="button"
                :data-testid="index === 0 ? 'civsim-resume' : undefined"
                class="save"
                :disabled="busy"
                @click="getGame(save.gameId)"
              >
                <span>
                  <b>{{ save.name }}</b>
                  <small>{{ historicalYear(save.year) }} · 第 {{ save.turn }} 回合</small>
                </span>
                <i aria-hidden="true">→</i>
              </button>
              <div class="save-actions">
                <template v-if="confirmingDelete === save.gameId">
                  <button
                    type="button"
                    class="danger-link"
                    :data-testid="'civsim-confirm-delete-' + index"
                    :disabled="busy"
                    @click="removeSave(save.gameId)"
                  >
                    确认删除
                  </button>
                  <button
                    type="button"
                    class="muted-link"
                    :disabled="busy"
                    @click="confirmingDelete = null"
                  >
                    取消
                  </button>
                </template>
                <button
                  v-else
                  type="button"
                  class="muted-link"
                  :data-testid="'civsim-delete-' + index"
                  :disabled="busy"
                  title="删除此局存档"
                  @click="confirmingDelete = save.gameId"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </section>

    <!-- 二、朝堂与国史视图（整屏固定，绝不触发外层纵向滚动） -->
    <section v-else class="court">
      <header class="court-title">
        <div class="court-heading">
          <h1 data-testid="civsim-game-title">{{ game.name }}</h1>
          <p class="court-sub">
            <span>{{ getCivTemplate(game.templateId)?.region }}</span>
            <i>·</i>
            <span>{{ historicalYear(game.year) }}</span>
            <template v-if="game.panel">
              <i>·</i>
              <span :class="{ shifted: game.panel.structure.landSystemBefore }">
                {{ game.panel.structure.landSystem }}
                <em v-if="game.panel.structure.landSystemBefore" class="shift-tag">
                  原：{{ game.panel.structure.landSystemBefore }}
                </em>
              </span>
              <i>·</i>
              <span :class="{ shifted: game.panel.structure.polityBefore }">
                {{ game.panel.structure.polity }}
              </span>
            </template>
          </p>
        </div>
        <div class="turn-seal">
          <span>{{ game.turn === 0 ? '开国' : '纪年' }}</span>
          <strong data-testid="civsim-turn">{{ game.turn }}</strong>
        </div>
      </header>

      <p v-if="error" class="notice error compact-notice" role="alert">
        <span>{{ error }}</span>
        <button v-if="pendingTurn" type="button" :disabled="busy" @click="reconcile">
          重读本局
        </button>
      </p>

      <!-- 2A. 朝堂双栏驾驶舱 -->
      <div v-if="activeTab === 'court'" class="court-grid">
        <div class="court-left">
          <article class="chronicle" :class="{ condensed: moreDecrees }">
            <div class="section-head">
              <div class="chronicle-title-group">
                <h2>史官记事</h2>
                <div v-if="latest?.outcomes?.length" class="outcome-seals">
                  <span
                    v-for="(out, idx) in latest.outcomes"
                    :key="idx"
                    class="outcome-seal"
                    :class="'tier-' + out.tier"
                  >
                    <small v-if="out.scale !== 'medium'">{{ out.scaleLabel }}·</small>{{ out.name }}
                    <b>{{ out.tierLabel }}</b>
                  </span>
                </div>
                <span v-else-if="latest?.decree && latest.turn > 0" class="decree-chip">
                  政令 · {{ latest.decree }}
                </span>
              </div>
              <small class="turn-caption">
                {{ latest?.turn === 0 ? '开篇' : '第 ' + latest?.turn + ' 回合' }}
                <template v-if="latest?.years"> · 历 {{ latest.years }} 载</template>
              </small>
            </div>

            <p data-testid="civsim-narrative" class="narrative">
              {{ latest?.narrative || '尚无记载。' }}
            </p>

            <!-- 本回合新突破：点击直达天工·典章图谱对应节点 -->
            <div
              v-if="game.progression?.recentUnlocks.length && !moreDecrees"
              class="unlock-strip"
              data-testid="civsim-unlock-strip"
            >
              <button
                v-for="unlock in game.progression.recentUnlocks"
                :key="unlock.id"
                type="button"
                class="unlock-chip"
                @click="openTechTree(unlock.targetNodeId)"
              >
                <ArtifactArt :art="unlock.art" :kind="unlock.kind" :size="28" />
                <span class="unlock-text">
                  <em>{{ unlock.kindLabel }} · {{ unlock.branchName }}</em>
                  <strong>{{ unlock.name }}</strong>
                </span>
                <i aria-hidden="true">展阅 →</i>
              </button>
            </div>

            <!-- 本轮结算数值变动看板（默认完整展示前 8 项核心变动，不截半行；展开国策谱时折叠为单行摘要以腾出空间） -->
            <div
              v-if="latest?.changes.length"
              class="delta-board"
              data-testid="civsim-delta-board"
            >
              <div class="delta-board-head">
                <span>
                  本轮国势变动（{{ latest.changes.length }} 项）
                  <em v-if="moreDecrees" class="folded-hint">· 已收合明细以便选策</em>
                </span>
                <div class="delta-head-actions">
                  <button
                    v-if="!moreDecrees && latest.changes.length > 8"
                    type="button"
                    class="delta-expand-btn"
                    @click="showAllChanges = !showAllChanges"
                  >
                    {{ showAllChanges ? '仅看要项 (8)' : `展开全部 (${latest.changes.length})` }}
                  </button>
                  <small v-else>绿为利好 · 红为示警</small>
                </div>
              </div>
              <div v-if="!moreDecrees" class="changes" :class="{ expanded: showAllChanges }">
                <div
                  v-for="item in visibleChanges"
                  :key="game.turn + '-' + item.id"
                  class="delta-card"
                  :class="isGoodChange(item) ? 'pos' : 'neg'"
                >
                  <div class="delta-card-top">
                    <span class="delta-name">{{ item.label }}</span>
                    <strong class="delta-badge">
                      <i aria-hidden="true">{{ deltaArrow(item) }}</i>
                      {{ changeText(item) }}
                    </strong>
                  </div>
                  <div class="delta-route">
                    <span>{{ valueText(item.before) }}</span>
                    <i aria-hidden="true">→</i>
                    <b>{{ valueText(item.after) }}{{ item.unit }}</b>
                  </div>
                </div>
              </div>
            </div>
          </article>

          <!-- 施政与问史工作台（共享受限高度，展开国策谱或拟诏绝不撑长页面） -->
          <div class="orders">
            <div class="orders-bar">
              <div class="orders-bar-left">
                <h2>{{ game.status === 'game_over' ? '终局' : '施政' }}</h2>
                <div v-if="game.status !== 'game_over'" class="suggestions">
                  <button
                    v-for="d in starterActions"
                    :key="d.id"
                    type="button"
                    :class="{ picked: isDecreeDrafted(d) }"
                    :disabled="busy"
                    :title="d.description"
                    @click="pickDecree(d)"
                  >
                    {{ d.title }}
                  </button>
                </div>
              </div>
              <div class="orders-bar-right">
                <button
                  v-if="game.status !== 'game_over' && activeDecrees.length > starterActions.length"
                  type="button"
                  class="tool-btn"
                  :class="{ active: moreDecrees }"
                  data-testid="civsim-more-decrees"
                  :aria-expanded="moreDecrees"
                  @click="toggleMoreDecrees"
                >
                  {{ moreDecrees ? '收起国策谱' : `全部国策 (${activeDecrees.length})` }}
                </button>
                <button
                  v-if="game.status !== 'game_over'"
                  type="button"
                  class="tool-btn"
                  :class="{ active: openComposer && authoring === 'decree' }"
                  data-testid="civsim-compose"
                  :disabled="busy"
                  @click="compose('decree')"
                >
                  自拟政令
                </button>
                <button
                  type="button"
                  class="text-button"
                  data-testid="civsim-consult"
                  :disabled="busy"
                  @click="compose('consult')"
                >
                  问史官
                </button>
              </div>
            </div>

            <!-- 紧凑横排拟诏 / 问史官栏 -->
            <form
              v-if="openComposer"
              class="composer-box"
              @submit.prevent="submit(draft)"
            >
              <div class="composer-bar">
                <label for="civsim-input">
                  {{
                    authoring === 'consult'
                      ? '垂询史官（只读复盘，不推进回合）'
                      : '拟定诏书（可点选最多 3 项国策组合施政）'
                  }}
                </label>
                <div v-if="authoring === 'decree'" class="scale-picks">
                  <span>规模：</span>
                  <button
                    type="button"
                    :aria-pressed="activeScale === 'small'"
                    @click="applyScalePrefix('small')"
                  >
                    试办
                  </button>
                  <button
                    type="button"
                    :aria-pressed="activeScale === 'medium'"
                    @click="applyScalePrefix('medium')"
                  >
                    常制
                  </button>
                  <button
                    type="button"
                    :aria-pressed="activeScale === 'large'"
                    @click="applyScalePrefix('large')"
                  >
                    举国
                  </button>
                  <button
                    v-if="draft.trim()"
                    type="button"
                    class="clear-btn"
                    @click="draft = ''"
                  >
                    清空
                  </button>
                </div>
                <div v-else class="scale-picks">
                  <button
                    v-for="preset in CONSULT_PRESETS"
                    :key="preset.text"
                    type="button"
                    @click="draft = preset.text"
                  >
                    {{ preset.short }}
                  </button>
                </div>
              </div>
              <div class="composer-row">
                <textarea
                  id="civsim-input"
                  ref="inputEl"
                  v-model="draft"
                  data-testid="civsim-policy"
                  maxlength="2000"
                  :disabled="busy"
                  rows="1"
                  :placeholder="
                    authoring === 'consult'
                      ? '例如：当前国势有何隐忧与建议？或：第 1 回合发生了什么？'
                      : catalog.mode === 'model'
                        ? '例如：清丈王畿周边隐匿田亩，并在关隘设常平仓备荒'
                        : '例如：兴修水利、操练士卒（回车直接颁布）'
                  "
                  @keydown.enter.exact.prevent="submit(draft)"
                  @keydown.ctrl.enter.prevent="submit(draft)"
                  @keydown.meta.enter.prevent="submit(draft)"
                />
                <div class="composer-actions">
                  <button
                    type="submit"
                    class="primary compact-primary"
                    data-testid="civsim-submit"
                    :disabled="busy || !draft.trim()"
                  >
                    {{
                      busy
                        ? '办理中…'
                        : authoring === 'consult'
                          ? '查阅实录'
                          : '颁布政令'
                    }}
                  </button>
                  <button
                    type="button"
                    class="secondary compact-secondary"
                    :disabled="busy"
                    @click="openComposer = false"
                  >
                    收起
                  </button>
                </div>
              </div>
            </form>

            <!-- 反馈提示栏（未备提示 / 澄清 / 史官奏对 / 结算中） -->
            <div v-if="lockedHint" class="notice compact-notice" role="status">
              <span>{{ lockedHint }}</span>
              <button type="button" class="muted-link" @click="lockedHint = ''">知道了</button>
            </div>
            <div
              v-if="clarification"
              class="notice compact-notice"
              data-testid="civsim-clarification"
              role="status"
            >
              <span>{{ clarification }}</span>
            </div>
            <div
              v-if="reply"
              class="notice reply-box"
              data-testid="civsim-answer"
              role="status"
            >
              <div class="reply-text">{{ reply }}</div>
              <button type="button" class="muted-link" @click="reply = ''">收起</button>
            </div>
            <div v-if="busy && !openComposer" class="notice compact-notice" role="status">
              <span>{{ catalog.mode === 'model' ? '史官正在推演国势并执笔纪事…' : '正在结算国势…' }}</span>
            </div>

            <!-- 28 项国策谱（占满剩余高度并在框内平滑滚动） -->
            <div
              v-if="moreDecrees && game.status !== 'game_over'"
              class="decree-drawer"
              data-testid="civsim-decree-drawer"
            >
              <div class="drawer-head">
                <div class="domain-tabs" role="tablist" aria-label="政令分类">
                  <button
                    v-for="tab in DOMAINS"
                    :key="tab.id"
                    type="button"
                    :aria-pressed="domainFilter === tab.id"
                    @click="domainFilter = tab.id"
                  >
                    {{ tab.label }}
                  </button>
                </div>
                <small>可施政 {{ availableDecreeCount }} / {{ activeDecrees.length }}</small>
              </div>
              <div class="decree-grid">
                <button
                  v-for="d in filteredDecrees"
                  :key="d.id"
                  type="button"
                  class="decree-card"
                  :class="{
                    locked: d.available === false,
                    selected: isDecreeDrafted(d),
                  }"
                  :disabled="busy"
                  :title="d.available === false ? d.unmetReason || '' : d.description"
                  @click="pickDecree(d)"
                >
                  <div class="decree-card-head">
                    <strong>{{ d.title }}</strong>
                    <small>{{
                      isDecreeDrafted(d)
                        ? '已入诏'
                        : d.available === false
                          ? '未备'
                          : d.difficulty || d.domainLabel
                    }}</small>
                  </div>
                  <p>{{ d.available === false ? d.unmetReason : d.description }}</p>
                </button>
              </div>
            </div>

            <p v-else-if="!openComposer && !reply && !clarification && !lockedHint" class="guide">
              {{
                game.status === 'game_over'
                  ? '本局已收卷，可切换右上「国史」查阅完整兴衰编年。'
                  : catalog.mode === 'model'
                    ? '万相史官已就绪：可点选上方国策，或直接在底部万相框自由拟诏、输入「问史官：……」。'
                    : '点选推荐国策或展开「全部国策」可组合至多 3 项施政；也可在底部万相框直接下令。'
              }}
            </p>
          </div>
        </div>

        <!-- 右栏：国势原位涨跌仪表盘（双列紧凑卡片 + 进度警戒线） -->
        <aside class="state">
          <div class="section-head">
            <h2>国势总览</h2>
            <button
              v-if="game.panel"
              type="button"
              class="text-button"
              data-testid="civsim-toggle-deep"
              @click="showDeepPanel = !showDeepPanel"
            >
              {{ showDeepPanel ? '收起肌理' : '制度肌理' }}
            </button>
          </div>

          <RealmDiorama
            v-if="game.progression"
            :game="game"
            @open-tree="openTechTree()"
          />

          <div class="stat-cards">
            <div
              v-for="s in game.stats"
              :key="s.id"
              class="stat-card"
              :class="{
                warn: s.warn,
                'changed-pos': s.delta !== undefined && s.good !== false,
                'changed-neg': s.delta !== undefined && s.good === false,
              }"
            >
              <div class="stat-card-top">
                <span class="stat-label">{{ s.label }}</span>
                <em
                  v-if="s.delta !== undefined"
                  class="inline-delta"
                  :class="s.good !== false ? 'pos' : 'neg'"
                >
                  {{ s.delta > 0 ? '▲ ' : '▼ ' }}{{ signedNumberText(s.delta, s.unit) }}
                </em>
              </div>
              <div class="stat-card-mid">
                <strong class="stat-val">
                  {{ valueText(s.value) }}<small>{{ s.unit }}</small>
                </strong>
                <span v-if="s.before !== undefined" class="stat-prev">
                  前 {{ valueText(s.before) }}
                </span>
              </div>
              <div class="stat-meter">
                <span
                  class="stat-meter-fill"
                  :class="{ warn: s.warn }"
                  :style="{ width: Math.round((s.norm ?? 0.45) * 100) + '%' }"
                />
                <i
                  v-if="s.id === 'food'"
                  class="meter-threshold"
                  title="1.0 倍温饱基准线"
                />
              </div>
            </div>
          </div>

          <div
            v-if="game.panel && showDeepPanel"
            class="deep-panel"
            data-testid="civsim-deep-panel"
          >
            <div class="sub-head">
              <h3>治理与张力</h3>
              <small>阶级矛盾下降为利好</small>
            </div>
            <div class="ind-grid">
              <div
                v-for="ind in game.panel.indicators"
                :key="ind.id"
                class="ind-cell"
                :class="{
                  warn: ind.warn,
                  'changed-pos': ind.delta !== undefined && ind.good !== false,
                  'changed-neg': ind.delta !== undefined && ind.good === false,
                }"
              >
                <div class="ind-top">
                  <span class="ind-label">{{ ind.label }}</span>
                  <div class="ind-nums">
                    <strong>{{ valueText(ind.value) }}<small>{{ ind.unit }}</small></strong>
                    <em
                      v-if="ind.delta !== undefined"
                      class="inline-delta tiny"
                      :class="ind.good !== false ? 'pos' : 'neg'"
                    >
                      {{ ind.delta > 0 ? '▲+' : '▼' }}{{ valueText(ind.delta) }}
                    </em>
                  </div>
                </div>
                <div class="ind-meter">
                  <span
                    :class="{ warn: ind.warn, inverse: ind.inverse }"
                    :style="{ width: Math.round((ind.norm ?? 0.3) * 100) + '%' }"
                  />
                </div>
              </div>
            </div>

            <div class="struct-section">
              <div class="sub-head">
                <h3>版图、劳役与五维底蕴</h3>
                <span class="terr-summary">
                  畿甸 <b>{{ valueText(game.panel.structure.territoryCore) }}</b> · 边疆
                  <b>{{ valueText(game.panel.structure.territoryFrontier) }}</b> km²
                  <em
                    v-if="game.panel.structure.territoryDelta"
                    class="inline-delta tiny"
                    :class="game.panel.structure.territoryDelta > 0 ? 'pos' : 'neg'"
                  >
                    {{ signedNumberText(game.panel.structure.territoryDelta, ' km²') }}
                  </em>
                </span>
              </div>

              <div v-if="activeLabor.length" class="labor-wrap">
                <div class="labor-bar" aria-label="劳役阶层构成">
                  <span
                    v-for="seg in activeLabor"
                    :key="seg.label"
                    :style="{
                      width: seg.pct + '%',
                      background: LABOR_COLORS[seg.label] || '#6b705c',
                    }"
                    :title="seg.label + ' ' + seg.pct + '%'"
                  />
                </div>
                <div class="labor-legend">
                  <span v-for="seg in activeLabor" :key="seg.label">
                    <i :style="{ background: LABOR_COLORS[seg.label] || '#6b705c' }" />
                    {{ seg.label }} {{ seg.pct }}%
                  </span>
                  <span class="tax-inline">
                    赋税：{{ game.panel.structure.extractions.join(' / ') }}
                  </span>
                </div>
              </div>

              <div class="accum-pills">
                <span
                  v-for="acc in game.panel.accumulations"
                  :key="acc.id"
                  :class="{
                    pos: acc.delta !== undefined && acc.delta >= 0.02,
                    neg: acc.delta !== undefined && acc.delta <= -0.06,
                  }"
                >
                  {{ acc.label }} <b>{{ valueText(acc.value) }}</b>
                  <em v-if="acc.delta !== undefined && (acc.delta >= 0.02 || acc.delta <= -0.06)">
                    {{ signedNumberText(acc.delta) }}
                  </em>
                </span>
              </div>
            </div>
          </div>
        </aside>
      </div>

      <!-- 2B. 天工·典章演进图谱（单屏分栏展示科技树、典章流转与文物线稿） -->
      <TechTree
        v-else-if="activeTab === 'tree' && game.progression"
        :game="game"
        :progression="game.progression"
        :focused-id="focusedNodeId"
        @select-node="focusedNodeId = $event"
        @stage-decrees="stageFromTree"
      />

      <!-- 2C. 国史编年视图（内部平滑滚动，外层页面不滚动） -->
      <section v-else class="archive">
        <div class="section-head archive-head">
          <h2>国史实录</h2>
          <div class="archive-head-right">
            <small>共 {{ game.history.length }} 篇记事</small>
            <button type="button" class="secondary compact-secondary" @click="activeTab = 'court'">
              返回朝堂
            </button>
          </div>
        </div>
        <div class="archive-scroll">
          <article
            v-for="entry in entries"
            :key="entry.turn"
            class="archive-entry"
          >
            <div class="date">
              {{ historicalYear(entry.year) }}
              <small>
                {{ entry.turn === 0 ? '开国' : '第 ' + entry.turn + ' 回合' }}
                <template v-if="entry.years"> · 历 {{ entry.years }} 载</template>
              </small>
            </div>
            <div class="archive-body">
              <div class="archive-title-row">
                <h3>{{ entry.turn === 0 ? '立国' : entry.decree }}</h3>
                <div v-if="entry.outcomes?.length" class="outcome-seals">
                  <span
                    v-for="(out, idx) in entry.outcomes"
                    :key="idx"
                    class="outcome-seal"
                    :class="'tier-' + out.tier"
                  >
                    {{ out.name }} <b>{{ out.tierLabel }}</b>
                  </span>
                </div>
              </div>
              <p>{{ entry.narrative }}</p>
              <div v-if="entry.unlocks?.length" class="archive-unlocks">
                <button
                  v-for="u in entry.unlocks"
                  :key="u.id"
                  type="button"
                  class="archive-unlock-pill"
                  @click="openTechTree(u.targetNodeId)"
                >
                  ✦ {{ u.kindLabel }}：{{ u.name }}
                </button>
              </div>
              <div v-if="entry.changes.length" class="archive-changes">
                <span
                  v-for="change in entry.changes"
                  :key="change.id"
                  class="archive-change-pill"
                  :class="isGoodChange(change) ? 'pos' : 'neg'"
                >
                  {{ change.label }}
                  <em>{{ valueText(change.before) }} → {{ valueText(change.after) }}{{ change.unit }}</em>
                  <b>({{ changeText(change) }})</b>
                </span>
              </div>
            </div>
          </article>
        </div>
      </section>
    </section>
  </main>
</template>
