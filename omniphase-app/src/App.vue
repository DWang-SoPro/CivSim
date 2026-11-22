<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { CIV_TEMPLATES, getCivTemplate } from './civilizations'
import Atlas from './Atlas.vue'
import {
  changeText,
  consultHistory,
  historicalYear,
  request,
  requestId,
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
  '当前国势有何隐忧与施政建议？',
  '最近粮食与仓储怎样变化？',
  '现行田制、政体与赋税如何？',
]

const game = ref<Game | null>(null)
const saves = ref<GameSummary[]>([])
const catalog = ref<Catalog>({ templates: [], decrees: [] })
const selected = ref('zhou')
const selectedCiv = computed(() => getCivTemplate(selected.value) ?? CIV_TEMPLATES[0])
const library = ref(true)
const archive = ref(false)
const openComposer = ref(false)
const moreDecrees = ref(false)
const domainFilter = ref('all')
const showDeepPanel = ref(true)
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
const historyCount = ref(8)

const latest = computed(() => game.value?.history.at(-1))
const entries = computed(() =>
  (game.value?.history ?? []).slice(-historyCount.value).reverse()
)

const activeDecrees = computed<Decree[]>(() => {
  return game.value?.availableDecrees?.length
    ? game.value.availableDecrees
    : catalog.value.decrees
})

const filteredDecrees = computed<Decree[]>(() => {
  if (domainFilter.value === 'all') return activeDecrees.value
  return activeDecrees.value.filter(d => d.domain === domainFilter.value)
})

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

function isPositiveChange(item: Change): boolean {
  const delta = item.after - item.before
  return delta > 0
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
  archive.value = false
  confirmingDelete.value = null
  historyCount.value = 8
  updateSaves(data)
  resetInput()
  if (previous && previous.turn === data.turn) {
    draft.value = previous.text
    openComposer.value = true
    error.value = '上道政令尚无回执，可重读国史或按相同请求重试。'
  }
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
  archive.value = false
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
    lockedHint.value = `「${d.title}」当前尚未具备条件：${d.unmetReason || '请先夯实国势基础'}。`
    return
  }
  lockedHint.value = ''
  if (openComposer.value && authoring.value === 'decree' && draft.value.trim()) {
    const existing = draft.value.trim()
    if (!existing.includes(d.text)) {
      draft.value = `${existing}、${d.text}`
      return
    }
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

async function compose(mode: 'decree' | 'consult', text?: string) {
  if (busy.value) return
  authoring.value = mode
  openComposer.value = true
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
    archive.value = false
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
    archive.value = false
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
    archive.value = false
    if (data.turn !== prior.turn) {
      pendingTurns.delete(prior.gameId)
      resetInput()
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
  unsubscribe?.()
})
</script>

<template>
  <main class="ledger">
    <header class="mast">
      <div class="identity">
        <img :src="emblem" alt="" width="35" height="35" />
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
          <button :aria-pressed="!archive" @click="archive = false">朝堂</button>
          <button
            data-testid="civsim-history"
            :aria-pressed="archive"
            @click="archive = true"
          >
            国史
          </button>
          <button
            data-testid="civsim-library"
            :disabled="busy"
            @click="openLibrary"
          >
            文明与存档 <span aria-hidden="true">↗</span>
          </button>
        </div>
      </div>
    </header>

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
        </section>

        <section class="saves">
          <div class="section-head">
            <h2>本机存档</h2>
            <small v-if="saves.length">{{ saves.length }} 份记录</small>
          </div>
          <p v-if="!saves.length" class="muted">开局后将自动保存进度。</p>
          <div v-for="(save, index) in saves" :key="save.gameId" class="save-row">
            <button
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
        </section>
      </div>
      <div v-if="error" class="notice error" role="alert">
        {{ error }}
        <button v-if="!connected" @click="boot">重新连接</button>
      </div>
    </section>

    <section v-else class="court">
      <header class="court-title">
        <div>
          <p>
            {{ getCivTemplate(game.templateId)?.region }} ·
            {{ historicalYear(game.year) }}
            <template v-if="game.panel">
              · {{ game.panel.structure.landSystem }} ·
              {{ game.panel.structure.polity }}
            </template>
          </p>
          <h1 data-testid="civsim-game-title">{{ game.name }}</h1>
        </div>
        <div class="turn-seal">
          {{ game.turn === 0 ? '开国' : '纪年' }}
          <strong data-testid="civsim-turn">{{ game.turn }}</strong>
        </div>
      </header>

      <div v-if="!archive" class="court-grid">
        <div>
          <article class="chronicle">
            <div class="section-head">
              <h2>史官记事</h2>
              <small>{{
                latest?.turn === 0 ? '开篇' : '第 ' + latest?.turn + ' 回合'
              }}</small>
            </div>
            <p v-if="latest?.decree && latest.turn > 0" class="decree-line">
              政令 · {{ latest.decree }}
            </p>
            <p data-testid="civsim-narrative" class="narrative">
              {{ latest?.narrative || '尚无记载。' }}
            </p>
            <div v-if="latest?.changes.length" class="changes">
              <span
                v-for="item in latest.changes"
                :key="item.id"
                :class="isPositiveChange(item) ? 'pos' : 'neg'"
              >
                {{ item.label }} <b>{{ changeText(item) }}</b>
              </span>
            </div>
          </article>

          <div class="orders">
            <div class="section-head">
              <h2>{{ game.status === 'game_over' ? '终局' : '发布政令' }}</h2>
              <button
                type="button"
                class="text-button"
                data-testid="civsim-consult"
                @click="compose('consult')"
              >
                问史官
              </button>
            </div>

            <template v-if="game.status !== 'game_over'">
              <div class="suggestions">
                <button
                  v-for="d in starterActions"
                  :key="d.id"
                  :disabled="busy"
                  :title="d.description"
                  @click="pickDecree(d)"
                >
                  {{ d.title }}
                </button>
                <button
                  v-if="activeDecrees.length > starterActions.length"
                  type="button"
                  data-testid="civsim-more-decrees"
                  :aria-expanded="moreDecrees"
                  @click="moreDecrees = !moreDecrees"
                >
                  {{ moreDecrees ? '收起国策谱' : `全部国策 (${activeDecrees.length})` }}
                </button>
                <button
                  type="button"
                  data-testid="civsim-compose"
                  :disabled="busy"
                  @click="compose('decree')"
                >
                  自拟政令
                </button>
              </div>

              <div v-if="moreDecrees" class="decree-drawer" data-testid="civsim-decree-drawer">
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
                <div class="decree-grid">
                  <button
                    v-for="d in filteredDecrees"
                    :key="d.id"
                    type="button"
                    class="decree-card"
                    :class="{ locked: d.available === false }"
                    :disabled="busy"
                    :title="d.available === false ? d.unmetReason || '' : d.description"
                    @click="pickDecree(d)"
                  >
                    <div class="decree-card-head">
                      <strong>{{ d.title }}</strong>
                      <small>{{ d.available === false ? '未备' : d.difficulty || d.domainLabel }}</small>
                    </div>
                    <p>{{ d.available === false ? d.unmetReason : d.description }}</p>
                  </button>
                </div>
              </div>

              <p v-if="!openComposer" class="guide">
                {{
                  catalog.mode === 'model'
                    ? '万相史官已就绪：可自由输入任意历史政令，由模型解析意图并执笔史书。'
                    : '本地规则引擎：支持 6 大领域 28 项国策及顿号组合施政（如「兴修水利、操练士卒」）。'
                }}也可直接在万相底部悬浮框下令或输入「问史官：……」。
              </p>
            </template>
            <p v-else class="guide">本局已收卷，国史与存档仍可随时查阅。</p>

            <p v-if="lockedHint" class="notice" role="status">{{ lockedHint }}</p>
            <p
              v-if="clarification"
              class="notice"
              data-testid="civsim-clarification"
              role="status"
            >
              {{ clarification }}
            </p>

            <form v-if="openComposer" @submit.prevent="submit(draft)">
              <div class="composer-bar">
                <label for="civsim-input">
                  {{
                    authoring === 'consult'
                      ? '垂询史官（只读复盘，不推进回合）'
                      : '向' + game.name + '颁诏'
                  }}
                </label>
                <div v-if="authoring === 'decree'" class="scale-picks">
                  <span>动员规模：</span>
                  <button type="button" @click="applyScalePrefix('small')">试办</button>
                  <button type="button" @click="applyScalePrefix('medium')">常制</button>
                  <button type="button" @click="applyScalePrefix('large')">举国</button>
                </div>
                <div v-else class="scale-picks">
                  <button
                    v-for="preset in CONSULT_PRESETS"
                    :key="preset"
                    type="button"
                    @click="draft = preset"
                  >
                    {{ preset.slice(0, 6) }}…
                  </button>
                </div>
              </div>
              <textarea
                id="civsim-input"
                ref="inputEl"
                v-model="draft"
                data-testid="civsim-policy"
                maxlength="2000"
                :disabled="busy"
                rows="2"
                :placeholder="
                  authoring === 'consult'
                    ? '例如：当前国势有何隐忧与建议？或：第 1 回合发生了什么？'
                    : catalog.mode === 'model'
                      ? '例如：清丈王畿周边隐匿田亩，并在关隘设常平仓备荒'
                      : '例如：兴修水利、操练士卒（最多组合 3 项国策）'
                "
                @keydown.ctrl.enter.prevent="submit(draft)"
                @keydown.meta.enter.prevent="submit(draft)"
              />
              <div class="composer-actions">
                <button
                  class="primary"
                  data-testid="civsim-submit"
                  :disabled="busy || !draft.trim()"
                >
                  {{
                    busy
                      ? '正在结算…'
                      : authoring === 'consult'
                        ? '查阅实录'
                        : '颁布政令'
                  }}
                </button>
                <button
                  type="button"
                  class="secondary"
                  :disabled="busy"
                  @click="openComposer = false"
                >
                  收起
                </button>
              </div>
            </form>

            <p v-if="reply" class="notice" data-testid="civsim-answer" role="status">
              {{ reply }}
            </p>
            <p v-if="busy && !openComposer" class="notice" role="status">
              {{ catalog.mode === 'model' ? '史官正在推演国势并执笔纪事…' : '正在结算国势…' }}
            </p>
          </div>
        </div>

        <aside class="state">
          <div class="section-head">
            <h2>国势</h2>
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
          <dl>
            <div v-for="s in game.stats" :key="s.id">
              <dt>{{ s.label }}</dt>
              <dd>
                {{ valueText(s.value) }}<small>{{ s.unit }}</small>
              </dd>
            </div>
          </dl>

          <div v-if="game.panel && showDeepPanel" class="deep-panel" data-testid="civsim-deep-panel">
            <h3>治理与张力</h3>
            <dl class="compact-dl">
              <div
                v-for="ind in game.panel.indicators"
                :key="ind.id"
                :class="{ warn: ind.warn }"
              >
                <dt>{{ ind.label }}</dt>
                <dd>
                  {{ valueText(ind.value) }}<small>{{ ind.unit }}</small>
                </dd>
              </div>
            </dl>

            <h3>版图与赋役</h3>
            <p class="meta-line">
              核心畿甸 <b>{{ valueText(game.panel.structure.territoryCore) }}</b> km² ·
              边疆 <b>{{ valueText(game.panel.structure.territoryFrontier) }}</b> km²
            </p>
            <p class="meta-line">
              赋税：{{ game.panel.structure.extractions.join('、') }}
            </p>
            <div class="accum-pills">
              <span v-for="acc in game.panel.accumulations" :key="acc.id">
                {{ acc.label }} {{ valueText(acc.value) }}
              </span>
            </div>
          </div>
        </aside>
      </div>

      <section v-else class="archive">
        <div class="section-head">
          <h2>国史</h2>
          <small>{{ (game.history[0]?.turn ?? 0) > 0 ? '最近' : '共' }} {{ game.history.length }} 篇记事</small>
        </div>
        <article
          v-for="entry in entries"
          :key="entry.turn"
          class="archive-entry"
        >
          <div class="date">
            {{ historicalYear(entry.year) }}
            <small>{{ entry.turn === 0 ? '开国' : '第 ' + entry.turn + ' 回合' }}</small>
          </div>
          <div>
            <h3>{{ entry.turn === 0 ? '立国' : entry.decree }}</h3>
            <p>{{ entry.narrative }}</p>
            <div v-if="entry.changes.length" class="changes">
              <span
                v-for="change in entry.changes"
                :key="change.id"
                :class="isPositiveChange(change) ? 'pos' : 'neg'"
              >
                {{ change.label }} {{ changeText(change) }}
              </span>
            </div>
          </div>
        </article>
        <button
          v-if="entries.length < game.history.length"
          class="secondary"
          @click="historyCount += 8"
        >
          更早的记事
        </button>
      </section>

      <p v-if="error" class="notice error" role="alert">
        {{ error }}
        <button v-if="pendingTurn" :disabled="busy" @click="reconcile">
          重读本局
        </button>
      </p>
    </section>
  </main>
</template>
