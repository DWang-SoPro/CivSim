<script setup lang="ts">
import { computed } from 'vue'
import type { Game } from './game'

const props = defineProps<{
  game: Game
}>()

defineEmits<{
  (e: 'open-tree'): void
}>()

function branchLevel(branchId: string, fallback = 1): number {
  const b = props.game.progression?.branches.find((item) => item.id === branchId)
  return b ? b.level : fallback
}

function statNorm(id: string, fallback = 0.5): number {
  const inStats = props.game.stats.find((s) => s.id === id)
  if (inStats && typeof inStats.norm === 'number') return inStats.norm
  const inPanel = props.game.panel?.indicators.find((s) => s.id === id)
  if (inPanel && typeof inPanel.norm === 'number') return inPanel.norm
  return fallback
}

const agri = computed(() => branchLevel('agriculture', 1.2))
const eng = computed(() => branchLevel('engineering', 1.0))
const know = computed(() => branchLevel('knowledge', 1.0))
const grain = computed(() => statNorm('grain_reserve', 0.2))
const stability = computed(() => statNorm('stability', 0.6))
const tension = computed(() => statNorm('class_tension', 0.2))
const terr = computed(() => {
  const s = props.game.panel?.structure
  const core = s?.territoryCore ?? 1
  const frontier = s?.territoryFrontier ?? 0
  const total = Math.max(1, core + frontier)
  return {
    core,
    frontier,
    corePct: Math.round((core / total) * 100),
  }
})
const summaryCounts = computed(() => ({
  unlocked: props.game.progression?.unlockedCount ?? 0,
  total: props.game.progression?.totalNodes ?? 15,
  recent: props.game.progression?.recentUnlocks.length ?? 0,
}))
</script>

<template>
  <button
    type="button"
    class="diorama-card"
    data-testid="civsim-realm-diorama"
    @click="$emit('open-tree')"
  >
    <div class="diorama-head">
      <span class="diorama-title">疆域气象</span>
      <span class="diorama-meta">
        <span>天工 {{ summaryCounts.unlocked }}/{{ summaryCounts.total }}</span>
        <span v-if="summaryCounts.recent > 0" class="diorama-new">+{{ summaryCounts.recent }} 新脉</span>
      </span>
    </div>

    <svg class="diorama-svg" viewBox="0 0 360 84" fill="none" aria-hidden="true">
      <!-- 远山线稿 -->
      <path
        d="M0 54 Q38 35 76 48 Q116 26 164 44 Q212 29 258 46 Q308 30 360 49"
        stroke="#2a241e"
        stroke-opacity="0.24"
        stroke-width="1.3"
      />
      <!-- 社会张力乌云警兆（仅当阶级矛盾偏高或稳定偏低时显现） -->
      <g v-if="tension >= 0.5 || stability < 0.45">
        <path
          d="M28 16 Q42 9 58 15 Q68 10 82 16"
          stroke="#9e3223"
          stroke-width="1.6"
          stroke-linecap="round"
        />
        <path
          d="M276 18 Q292 11 308 17 Q319 12 332 18"
          stroke="#9e3223"
          stroke-width="1.4"
          stroke-opacity="0.7"
          stroke-linecap="round"
        />
      </g>

      <!-- 地平与河渠灌网（随农业等级演进） -->
      <path d="M4 66 Q90 61 178 66 Q268 71 356 64" stroke="#241e18" stroke-width="1.6" />
      <path
        d="M8 73 Q55 68 95 73 Q138 78 188 73"
        stroke="#4f6c68"
        stroke-width="2"
        stroke-opacity="0.65"
        stroke-linecap="round"
      />
      <g v-if="agri >= 1.55">
        <path d="M40 66 L48 73 M62 66 L70 73 M84 66 L92 73" stroke="#4f6c68" stroke-width="1.2" />
      </g>
      <g v-if="agri >= 2.2">
        <rect x="20" y="54" width="24" height="10" stroke="#241e18" stroke-width="1.1" stroke-opacity="0.7" />
        <line x1="32" y1="54" x2="32" y2="64" stroke="#4f6c68" stroke-width="1" />
        <line x1="20" y1="59" x2="44" y2="59" stroke="#4f6c68" stroke-width="1" />
      </g>

      <!-- 官仓余粮贮备图（左侧） -->
      <g transform="translate(88 37)">
        <path d="M0 13 L18 3 L36 13 Z" fill="#9e3223" fill-opacity="0.16" stroke="#241e18" stroke-width="1.4" />
        <rect x="4" y="13" width="28" height="16" stroke="#241e18" stroke-width="1.4" fill="#fbf7ee" />
        <rect
          x="6"
          :y="27 - Math.round(Math.min(1, Math.max(0.08, grain)) * 12)"
          width="24"
          :height="Math.round(Math.min(1, Math.max(0.08, grain)) * 12)"
          fill="#9e3223"
          fill-opacity="0.34"
        />
      </g>

      <!-- 都邑城防与工坊（中景，随工程等级升阶） -->
      <g transform="translate(152 24)">
        <!-- 基础城垣 -->
        <rect x="8" y="25" width="76" height="17" stroke="#241e18" stroke-width="1.6" fill="#f7f1e3" />
        <path
          d="M8 25 V21 H16 V25 H24 V21 H32 V25 H40 V21 H48 V25 H56 V21 H64 V25 H72 V21 H84 V25"
          stroke="#241e18"
          stroke-width="1.4"
        />
        <path d="M40 42 V32 C40 29, 50 29, 50 32 V42" stroke="#241e18" stroke-width="1.4" />
        <!-- Lv >= 1.5 青铜冶铸高台 + 重门 -->
        <g v-if="eng >= 1.5">
          <rect x="28" y="11" width="34" height="14" stroke="#241e18" stroke-width="1.4" fill="#f2ead9" />
          <path d="M24 11 L45 1 L66 11 Z" fill="#9e3223" fill-opacity="0.2" stroke="#241e18" stroke-width="1.5" />
        </g>
        <!-- Lv >= 2.7 坚壁望楼旌旗 -->
        <g v-if="eng >= 2.7">
          <line x1="72" y1="21" x2="72" y2="5" stroke="#241e18" stroke-width="1.3" />
          <path d="M72 5 L84 8.5 L72 12 Z" fill="#9e3223" />
        </g>
      </g>

      <!-- 太学典籍重檐与石碑（右侧，随知识等级升阶） -->
      <g transform="translate(268 32)">
        <rect x="10" y="19" width="38" height="15" stroke="#241e18" stroke-width="1.4" fill="#f9f4e8" />
        <path d="M4 19 L29 7 L54 19 Z" stroke="#241e18" stroke-width="1.5" fill="#241e18" fill-opacity="0.08" />
        <g v-if="know >= 1.4">
          <line x1="20" y1="21" x2="20" y2="33" stroke="#9e3223" stroke-width="1.3" />
          <line x1="38" y1="21" x2="38" y2="33" stroke="#9e3223" stroke-width="1.3" />
        </g>
        <g v-if="know >= 2.2">
          <path d="M10 10 L29 1 L48 10" stroke="#9e3223" stroke-width="1.4" stroke-linejoin="round" />
        </g>
      </g>
    </svg>

    <div class="diorama-foot">
      <span class="terr-bar">
        <span class="terr-core" :style="{ width: terr.corePct + '%' }" />
      </span>
      <span class="diorama-foot-text">核心 {{ terr.core.toLocaleString() }} · 边疆 {{ terr.frontier.toLocaleString() }} km²</span>
      <span class="diorama-link">图谱 →</span>
    </div>
  </button>
</template>

<style scoped>
.diorama-card {
  display: grid;
  gap: 3px;
  width: 100%;
  padding: 6px 9px;
  border: 1px solid rgba(36, 30, 24, 0.16);
  border-radius: 6px;
  background: linear-gradient(180deg, rgba(251, 247, 238, 0.96), rgba(244, 237, 223, 0.92));
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}
.diorama-card:hover {
  border-color: rgba(158, 50, 35, 0.45);
  box-shadow: 0 2px 8px rgba(42, 30, 20, 0.08);
}
.diorama-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
}
.diorama-title {
  font-weight: 700;
  color: #2c241d;
  letter-spacing: 0.04em;
}
.diorama-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #6b5e50;
}
.diorama-new {
  padding: 1px 5px;
  border-radius: 999px;
  background: rgba(158, 50, 35, 0.12);
  color: #9e3223;
  font-weight: 600;
}
.diorama-svg {
  display: block;
  width: 100%;
  height: auto;
  max-height: 56px;
}
.diorama-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10.5px;
  color: #6d6256;
}
.terr-bar {
  flex: none;
  width: 44px;
  height: 5px;
  border-radius: 999px;
  background: rgba(158, 50, 35, 0.25);
  overflow: hidden;
}
.terr-core {
  display: block;
  height: 100%;
  background: #2c241d;
}
.diorama-foot-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.diorama-link {
  flex: none;
  color: #9e3223;
  font-weight: 600;
}
@media (max-height: 750px) {
  .diorama-card {
    padding: 5px 8px;
    gap: 3px;
  }
  .diorama-svg {
    max-height: 58px;
  }
}
</style>
