<script setup lang="ts">
import { computed, nextTick, reactive, onMounted, onUnmounted, ref, watch } from 'vue'
import { CIV_TEMPLATES, getCivTemplate } from './civilizations'
import Atlas from './Atlas.vue'
import { changeText, consultHistory, historicalYear, request, requestId, valueText } from './game'
import type { Catalog, Context, Game, GameSummary } from './game'
import emblem from '../icon.svg'

const game = ref<Game | null>(null)
const saves = ref<GameSummary[]>([])
const catalog = ref<Catalog>({ templates: [], decrees: [] })
const selected = ref('zhou')
const selectedCiv = computed(() => getCivTemplate(selected.value) ?? CIV_TEMPLATES[0])
const library = ref(true)
const archive = ref(false)
const openComposer = ref(false)
const moreDecrees = ref(false)
const draft = ref('')
const authoring = ref<'decree'|'consult'>('decree')
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
const entries = computed(() => (game.value?.history ?? []).slice(-historyCount.value).reverse())
const starterActions = computed(() => {
  const preferred = ['兴修水利','修建粮仓','开垦农田']
  const chosen = preferred.map(title => catalog.value.decrees.find(d => d.title === title)).filter(Boolean)
  return [...new Map([...chosen, ...catalog.value.decrees].filter(d => !!d).map(d => [d!.id, d!])).values()].slice(0, 3)
})
const pendingTurns = reactive(new Map<string, { gameId: string; turn: number; text: string; key: string }>())
const pendingTurn = computed(() => game.value ? pendingTurns.get(game.value.gameId) : undefined)
let pendingNew: { id: string; key: string } | undefined
let unsubscribe: (()=>void) | undefined
let mounted = true

function explainError(e: unknown) { return e instanceof Error ? e.message : String(e) }
function updateSaves(data: Game) {
  const { gameId, templateId, name, year, turn, updatedAt } = data
  saves.value = [{gameId,templateId,name,year,turn,updatedAt},...saves.value.filter(s => s.gameId !== gameId)]
}
function resetInput() { moreDecrees.value = false; draft.value = ''; openComposer.value = false; authoring.value='decree'; clarification.value=''; reply.value='' }
function showGame(data: Game) {
  const previous=pendingTurns.get(data.gameId)
  if(previous && previous.turn!==data.turn) pendingTurns.delete(data.gameId)
  game.value = data
  selected.value = data.templateId
  library.value = false
  archive.value = false
  historyCount.value = 8
  updateSaves(data)
  resetInput()
  if(previous && previous.turn===data.turn) {
    draft.value=previous.text; openComposer.value=true
    error.value='上道政令尚无回执，可重读国史或按相同请求重试。'
  }
}
async function getGame(id: string) {
  if(busy.value) return
  busy.value=true; error.value=''
  try { showGame(await request<Game>('get', {gameId:id})) }
  catch(e) { error.value=explainError(e) } finally {busy.value=false}
}
async function boot() {
  if(!hasBridge) {loading.value=false; return}
  loading.value=true; error.value=''
  try {
    const [catalogData, list] = await Promise.all([request<Catalog>('catalog'),request<{games:GameSummary[]}>('list')])
    if(!mounted) return
    catalog.value=catalogData; saves.value=list.games; connected.value=true
    if(saves.value.length) await getGame(saves.value[0].gameId)
  } catch(e) {error.value=explainError(e); connected.value=false} finally {loading.value=false}
}
async function newGame() {
  if(!connected.value || busy.value || loading.value) return
  const id=selected.value
  if(pendingNew?.id!==id) pendingNew={id,key:requestId()}
  busy.value=true; error.value=''
  try { showGame(await request<Game>('new',{templateId:id, requestId:pendingNew.key})); pendingNew=undefined }
  catch(e) {error.value=explainError(e)} finally {busy.value=false}
}
async function openLibrary() {
  if(busy.value) return
  library.value=true; archive.value=false; error.value=''
  if(!connected.value) return
  try { saves.value=(await request<{games:GameSummary[]}>('list')).games }
  catch(e) {error.value=explainError(e)}
}
async function compose(mode:'decree'|'consult', text?:string) {
  if(busy.value) return
  authoring.value=mode; openComposer.value=true; error.value=''; clarification.value=''
  if(text!==undefined) draft.value=text
  else if(mode==='consult') draft.value=''
  await nextTick(); inputEl.value?.focus()
}
function publish() {
  const current = library.value ? null : game.value
  const targets=saves.value.slice(0,10).map(s=>({id:s.gameId,title:s.name}))
  if(current && !targets.some(s=>s.id===current.gameId)) targets.unshift({id:current.gameId,title:current.name})
  const context:Context=current ? {page:'record',recordId:current.gameId,title:current.name,summary:historicalYear(current.year)+'，第 '+current.turn+' 回合',targets}
    : {page:'list',title:'文明与存档',targets}
  window.wanxiang?.publishContext?.(context)
}
watch([game,library,saves],publish)
async function submit(text: string, mode = authoring.value):Promise<boolean> {
  const active=game.value, value=text.trim()
  if(!active || busy.value || library.value || !value) return false
  error.value=''; clarification.value=''
  if(mode==='consult') {
    reply.value=consultHistory(value,active); draft.value=''; openComposer.value=false; archive.value=false; return true
  }
  if(active.status==='game_over') {error.value='此局已终，可进入国史查看记录。';return false}
  if([...value].length>2000) {error.value='政令请控制在 2000 字以内。';return false}
  const prior=pendingTurn.value
  if(prior && (prior.gameId!==active.gameId || prior.turn!==active.turn || prior.text!==value)) {
    error.value='上道政令的结果尚待核对，请先重读本局。'; return false
  }
  const operation=prior ?? {gameId:active.gameId,turn:active.turn,text:value,key:requestId()}
  pendingTurns.set(active.gameId,operation)
  busy.value=true; reply.value=''
  try {
    const data=await request<Game>('turn',{gameId:operation.gameId,expectedTurn:operation.turn,input:value,requestId:operation.key})
    if(!mounted) return false
    game.value=data; updateSaves(data); pendingTurns.delete(active.gameId); archive.value=false
    if(data.clarification){clarification.value=data.clarification;draft.value=value;openComposer.value=true}
    else resetInput()
    return true
  } catch(e) {
    draft.value=value; openComposer.value=true; error.value=explainError(e)
    return false
  } finally {busy.value=false}
}
async function reconcile() {
  const prior=pendingTurn.value
  if(!prior || busy.value)return
  busy.value=true
  try {
    const data=await request<Game>('get',{gameId:prior.gameId})
    game.value=data; updateSaves(data); archive.value=false
    if(data.turn!==prior.turn) {pendingTurns.delete(prior.gameId);resetInput();error.value='已重读最新国史，请核对纪年后继续。'}
    else {draft.value=prior.text;openComposer.value=true;error.value='服务端仍为原回合。再次颁令将沿用同一请求编号。'}
  } catch(e) {error.value=explainError(e)} finally {busy.value=false}
}
onMounted(()=>{
  unsubscribe=window.wanxiang?.onCommand?.(command=>{
    if(command.type==='navigate') {
      if(busy.value) return false
      if(command.recordId===null) void openLibrary()
      else if(saves.value.some(s=>s.gameId===command.recordId)) void getGame(command.recordId)
    }
    if(command.type==='input'){
      if(command.recordId!==game.value?.gameId || library.value || busy.value || !command.text?.trim()) return false
      const asking=/^(问史官|问史|查史)[：:\s]*/.exec(command.text.trim())
      return submit(asking ? command.text.trim().slice(asking[0].length) || '本回合' : command.text,asking?'consult':'decree')
    }
  })
  publish()
  void boot()
})
onUnmounted(()=>{mounted=false;unsubscribe?.()})
</script>

<template>
  <main class="ledger">
    <header class="mast">
      <div class="identity"><img :src="emblem" alt="" width="35" height="35"><strong>文明灵</strong><span>CivSim</span></div>
      <div v-if="game && !library" class="nav">
        <button :aria-pressed="!archive" @click="archive=false">朝堂</button>
        <button data-testid="civsim-history" :aria-pressed="archive" @click="archive=true">国史</button>
        <button data-testid="civsim-library" :disabled="busy" @click="openLibrary">文明与存档 <span aria-hidden="true">↗</span></button>
      </div>
      <span v-else class="local-label">{{ catalog.mode==='model'?'本机单人 · 模型政令':'本机单人 · 本地政令' }}</span>
    </header>
    <section v-if="library || !game" class="library">
      <div class="atlas-hero">
        <Atlas :selected="selected" @select="selected=$event"/>
        <div class="hero-caption"><p>文明发源地</p><h1>{{ selectedCiv.name }}</h1><span>{{ selectedCiv.region }} · {{ selectedCiv.era }}</span></div>
      </div>
      <div class="library-body">
        <section class="selection">
          <h2>选择开局文明</h2>
          <div class="civilizations" role="group" aria-label="开局文明">
            <button v-for="civ in CIV_TEMPLATES" :key="civ.id" :data-testid="'civsim-template-'+civ.id" :aria-pressed="civ.id===selected" :disabled="busy" @click="selected=civ.id">{{ civ.shortName }}</button>
          </div>
          <p class="blurb">{{ selectedCiv.blurb }}</p>
          <button class="primary" data-testid="civsim-start" :disabled="!connected || busy || loading" @click="newGame">{{ busy?'正在入局…':'从'+selectedCiv.shortName+'开局' }} <span aria-hidden="true">→</span></button>
          <p v-if="!hasBridge" class="notice">当前为预览。请在已连接本机游戏服务的万相内打开。</p>
          <p v-if="loading" class="notice" role="status">正在读取本机存档…</p>
        </section>
        <section class="saves"><h2>本机存档</h2>
          <p v-if="!saves.length" class="muted">开局后将自动保存进度。</p>
          <button v-for="(save,index) in saves" :key="save.gameId" :data-testid="index===0?'civsim-resume':undefined" class="save" :disabled="busy" @click="getGame(save.gameId)">
            <span><b>{{ save.name }}</b><small>{{ historicalYear(save.year) }} · 第 {{ save.turn }} 回合</small></span><i aria-hidden="true">→</i>
          </button>
        </section>
      </div>
      <div v-if="error" class="notice error" role="alert">{{ error }} <button v-if="!connected" @click="boot">重新连接</button></div>
    </section>

    <section v-else class="court">
      <header class="court-title"><div><p>{{ getCivTemplate(game.templateId)?.region }} · {{ historicalYear(game.year) }}</p><h1 data-testid="civsim-game-title">{{ game.name }}</h1></div>
        <div class="turn-seal">{{ game.turn===0?'开国':'纪年' }}<strong data-testid="civsim-turn">{{ game.turn }}</strong></div>
      </header>
      <div v-if="!archive" class="court-grid">
        <div>
          <article class="chronicle">
            <div class="section-head"><h2>史官记事</h2><small>{{ latest?.turn===0?'开篇':'第 '+latest?.turn+' 回合' }}</small></div>
            <p v-if="latest?.decree && latest.turn>0" class="decree-line">政令 · {{ latest.decree }}</p>
            <p data-testid="civsim-narrative" class="narrative">{{ latest?.narrative || '尚无记载。' }}</p>
            <div v-if="latest?.changes.length" class="changes"><span v-for="item in latest.changes" :key="item.id">{{ item.label }} <b>{{ changeText(item) }}</b></span></div>
          </article>
          <div class="orders">
            <div class="section-head"><h2>{{ game.status==='game_over'?'终局':'发布政令' }}</h2><button class="text-button" @click="compose('consult')">问史官</button></div>
            <template v-if="game.status!=='game_over'">
              <div class="suggestions"><button v-for="d in (moreDecrees ? catalog.decrees : starterActions)" :key="d.id" :disabled="busy" :title="d.description" @click="compose('decree',d.text)">{{ d.title }}</button>
                <button v-if="catalog.decrees.length>starterActions.length" :aria-expanded="moreDecrees" @click="moreDecrees=!moreDecrees">{{ moreDecrees?'收起':'更多政令' }}</button>
                <button data-testid="civsim-compose" :disabled="busy" @click="compose('decree')">自拟政令</button>
              </div>
              <p v-if="!openComposer" class="guide">{{ catalog.mode==='model' ? '模型政令：本轮输入将交给已配置的模型。' : '本地政令：按已收录的施政方向结算。' }}也可在万相底部输入框直接下令。</p>
            </template>
            <p v-else class="guide">本局已结束，国史和存档仍可回看。</p>
            <p v-if="clarification" class="notice" data-testid="civsim-clarification" role="status">{{ clarification }}</p>
            <form v-if="openComposer" @submit.prevent="submit(draft)">
              <label for="civsim-input">{{ authoring==='consult'?'查阅已结算国史（不推进回合）':'向'+game.name+'下令' }}</label>
              <textarea id="civsim-input" ref="inputEl" v-model="draft" data-testid="civsim-policy" maxlength="2000" :disabled="busy" rows="2" :placeholder="authoring==='consult'?'例如：上回合的粮食怎样变化？':'例如：同时兴修水利、修建粮仓'" @keydown.ctrl.enter.prevent="submit(draft)" @keydown.meta.enter.prevent="submit(draft)"></textarea>
              <button class="primary" data-testid="civsim-submit" :disabled="busy||!draft.trim()">{{ busy?'正在结算…':authoring==='consult'?'查阅':'颁令' }}</button>
            </form>
            <p v-if="reply" class="notice" data-testid="civsim-answer" role="status">{{ reply }}</p>
            <p v-if="busy && !openComposer" class="notice" role="status">正在读取国势…</p>
          </div>
        </div>
        <aside class="state"><h2>国势</h2><dl><div v-for="s in game.stats" :key="s.id"><dt>{{ s.label }}</dt><dd>{{ valueText(s.value) }}<small>{{ s.unit }}</small></dd></div></dl></aside>
      </div>
      <section v-else class="archive">
        <div class="section-head"><h2>国史</h2><small>{{ (game.history[0]?.turn ?? 0)>0?'最近':'共' }} {{ game.history.length }} 篇记事</small></div>
        <article v-for="entry in entries" :key="entry.turn" class="archive-entry"><div class="date">{{ historicalYear(entry.year) }}<small>{{ entry.turn===0?'开国':'第 '+entry.turn+' 回合' }}</small></div><div>
          <h3>{{ entry.turn===0?'立国':entry.decree }}</h3><p>{{ entry.narrative }}</p>
          <div class="changes" v-if="entry.changes.length"><span v-for="change in entry.changes" :key="change.id">{{ change.label }} {{ changeText(change) }}</span></div></div></article>
        <button class="secondary" v-if="entries.length<game.history.length" @click="historyCount+=8">更早的记事</button>
      </section>
      <p v-if="error" class="notice error" role="alert">{{ error }} <button v-if="pendingTurn" @click="reconcile" :disabled="busy">重读本局</button></p>
    </section>
  </main>
</template>
