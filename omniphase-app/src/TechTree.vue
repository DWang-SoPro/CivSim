<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ArtifactArt from './ArtifactArt.vue'
import type { Decree, Game, InstitutionNode, Progression, TechNode } from './game'

const props = defineProps<{
  game: Game
  progression: Progression
  focusedId?: string | null
}>()

const emit = defineEmits<{
  (e: 'stage-decrees', decrees: string[]): void
  (e: 'select-node', nodeId: string): void
}>()

const selectedId = ref<string>(props.focusedId || props.progression.focusNodeId)

watch(
  () => [props.focusedId, props.progression.focusNodeId],
  ([focused, fallback]) => {
    if (focused) {
      selectedId.value = focused
    } else if (!selectedEntry.value && fallback) {
      selectedId.value = fallback
    }
  }
)

type SelectedEntry =
  | { kind: 'tech'; node: TechNode }
  | { kind: 'inst'; instKind: 'land' | 'polity' | 'tax'; groupTitle: string; node: InstitutionNode }

const selectedEntry = computed<SelectedEntry | null>(() => {
  for (const branch of props.progression.branches) {
    const found = branch.nodes.find((n) => n.id === selectedId.value)
    if (found) return { kind: 'tech', node: found }
  }
  const instGroups: Array<{ key: 'land' | 'polity' | 'tax'; group: Progression['institutions']['land'] }> = [
    { key: 'land', group: props.progression.institutions.land },
    { key: 'polity', group: props.progression.institutions.polity },
    { key: 'tax', group: props.progression.institutions.tax },
  ]
  for (const g of instGroups) {
    const found = g.group.nodes.find((n) => n.id === selectedId.value)
    if (found) return { kind: 'inst', instKind: g.key, groupTitle: g.group.title, node: found }
  }
  const firstBranch = props.progression.branches[0]
  return firstBranch?.nodes[0] ? { kind: 'tech', node: firstBranch.nodes[0] } : null
})

const decreeLookup = computed(() => {
  const map = new Map<string, Decree>()
  for (const d of props.game.availableDecrees ?? []) {
    map.set(d.title, d)
    map.set(d.text, d)
  }
  return map
})

function pickNode(id: string) {
  selectedId.value = id
  emit('select-node', id)
}

function stageSuggested(allNames: string[]) {
  const available = allNames.filter((name) => decreeLookup.value.get(name)?.available !== false)
  emit('stage-decrees', available.length ? available : allNames)
}

function statusLabelTech(node: TechNode): string {
  if (node.status === 'unlocked') return '已成'
  if (node.status === 'next') return `可攻关 · ${node.progress}%`
  return `${node.progress}%`
}

function statusLabelInst(node: InstitutionNode): string {
  if (node.status === 'active') return '现行'
  if (node.status === 'unlocked') return '曾历'
  return '未启'
}
</script>

<template>
  <section class="tree-view" data-testid="civsim-tech-tree">
    <div class="tree-canvas">
      <div class="tree-header">
        <div>
          <h2 class="tree-title">天工 · 典章演进图谱</h2>
          <p class="tree-sub">
            三脉技艺随朝政积淀阶梯解锁，田制、政体与赋役亦随改革渐次跃迁。
          </p>
        </div>
        <div class="tree-header-badges">
          <span class="tree-total">已成 {{ progression.unlockedCount }} / {{ progression.totalNodes }} 脉</span>
          <span class="legend-chip is-unlocked">已成</span>
          <span class="legend-chip is-next">可攻关</span>
          <span class="legend-chip is-locked">未启</span>
        </div>
      </div>

      <div class="branch-stack">
        <div
          v-for="branch in progression.branches"
          :key="branch.id"
          class="branch-lane"
          :data-branch="branch.id"
        >
          <div class="branch-head">
            <span class="branch-name">{{ branch.name }}</span>
            <span class="branch-lv">{{ branch.levelText }}</span>
            <span class="branch-count">{{ branch.unlockedCount }} / {{ branch.totalCount }}</span>
          </div>
          <div class="node-row">
            <button
              v-for="node in branch.nodes"
              :key="node.id"
              type="button"
              class="tech-node"
              :class="[`is-${node.status}`, { 'is-selected': selectedEntry?.node.id === node.id }]"
              :data-testid="`civsim-node-${node.id}`"
              @click="pickNode(node.id)"
            >
              <div class="node-top">
                <span class="node-era">{{ node.era }}</span>
                <span class="node-state">{{ node.status === 'unlocked' ? '已成' : `${node.progress}%` }}</span>
              </div>
              <div class="node-art-wrap">
                <ArtifactArt :art="node.art" :size="32" />
              </div>
              <div class="node-name">{{ node.name }}</div>
              <div class="node-sub">{{ node.subtitle }}</div>
              <div class="node-meter">
                <span class="node-meter-fill" :style="{ width: node.progress + '%' }" />
              </div>
            </button>
          </div>
        </div>
      </div>

      <div class="inst-panel">
        <h3 class="inst-heading">典章制度演进</h3>
        <div class="inst-grid">
          <div
            v-for="item in [
              { key: 'land', group: progression.institutions.land },
              { key: 'polity', group: progression.institutions.polity },
              { key: 'tax', group: progression.institutions.tax },
            ]"
            :key="item.key"
            class="inst-row"
          >
            <div class="inst-row-label">{{ item.group.title }}</div>
            <div class="inst-chips">
              <button
                v-for="node in item.group.nodes"
                :key="node.id"
                type="button"
                class="inst-chip"
                :class="[`is-${node.status}`, { 'is-selected': selectedEntry?.node.id === node.id }]"
                :data-testid="`civsim-node-${node.id}`"
                @click="pickNode(node.id)"
              >
                <span class="inst-chip-name">{{ node.name }}</span>
                <span class="inst-chip-tag">{{ statusLabelInst(node) }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <aside v-if="selectedEntry" class="tree-inspector" data-testid="civsim-node-inspector">
      <div class="insp-hero">
        <div class="insp-art">
          <ArtifactArt
            v-if="selectedEntry.kind === 'tech'"
            :art="selectedEntry.node.art"
            :size="78"
          />
          <ArtifactArt
            v-else
            :kind="selectedEntry.instKind"
            :size="78"
          />
        </div>
        <div class="insp-titles">
          <div class="insp-eyebrow">
            <span v-if="selectedEntry.kind === 'tech'">{{ selectedEntry.node.branchName }} · 第 {{ selectedEntry.node.stage }} 阶</span>
            <span v-else>{{ selectedEntry.groupTitle }}</span>
            <span
              class="insp-seal"
              :class="`is-${selectedEntry.node.status}`"
            >
              {{
                selectedEntry.kind === 'tech'
                  ? statusLabelTech(selectedEntry.node)
                  : statusLabelInst(selectedEntry.node)
              }}
            </span>
          </div>
          <h3 class="insp-name">{{ selectedEntry.node.name }}</h3>
          <p v-if="selectedEntry.kind === 'tech'" class="insp-sub">
            {{ selectedEntry.node.subtitle }}
          </p>
        </div>
      </div>

      <blockquote
        v-if="selectedEntry.kind === 'tech'"
        class="insp-quote"
      >
        {{ selectedEntry.node.chronicleNote }}
      </blockquote>

      <div class="insp-block">
        <div class="insp-block-title">效用与典章要义</div>
        <p class="insp-body">
          {{ selectedEntry.kind === 'tech' ? selectedEntry.node.effect : selectedEntry.node.summary }}
        </p>
      </div>

      <div v-if="selectedEntry.kind === 'tech'" class="insp-block">
        <div class="insp-block-title">门槛达成进度</div>
        <div class="req-list">
          <div
            v-for="req in selectedEntry.node.reqs"
            :key="req.key"
            class="req-row"
            :class="{ 'is-met': req.met }"
          >
            <div class="req-row-head">
              <span>{{ req.label }}</span>
              <span class="req-val">{{ req.currentText }} / {{ req.targetText }}</span>
            </div>
            <div class="req-bar">
              <span class="req-bar-fill" :style="{ width: Math.round(req.ratio * 100) + '%' }" />
            </div>
          </div>
        </div>
      </div>

      <div v-else class="insp-block">
        <div class="insp-block-title">演进触发途径</div>
        <p class="insp-body">{{ selectedEntry.node.triggerHint }}</p>
      </div>

      <div class="insp-block">
        <div class="insp-block-title">推荐推进政令</div>
        <div class="insp-decrees">
          <button
            v-for="dec in selectedEntry.node.suggestedDecrees"
            :key="dec"
            type="button"
            class="insp-decree-pill"
            :class="{ 'is-unmet': decreeLookup.get(dec)?.available === false }"
            :title="decreeLookup.get(dec)?.unmetReason || '点击填入拟诏输入框'"
            @click="$emit('stage-decrees', [dec])"
          >
            <span>{{ dec }}</span>
            <span class="pill-state">
              {{ decreeLookup.get(dec)?.available === false ? '未备' : '可行' }}
            </span>
          </button>
        </div>
      </div>

      <button
        type="button"
        class="insp-cta"
        data-testid="civsim-stage-branch"
        @click="stageSuggested(selectedEntry.node.suggestedDecrees)"
      >
        拟诏推进此脉
      </button>
    </aside>
  </section>
</template>

<style scoped>
.tree-view {
  flex: 1 1 0;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(290px, 0.85fr);
  gap: 14px;
  padding: 10px 0 0;
  overflow: hidden;
}
.tree-canvas,
.tree-inspector {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-bottom: max(68px, calc(var(--wanxiang-composer-inset, 74px) - 6px));
}
.tree-canvas {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding-right: 6px;
}
.tree-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 10px;
  border: 1px solid rgba(36, 30, 24, 0.14);
  border-radius: 6px;
  background: rgba(251, 247, 238, 0.88);
}
.tree-title {
  margin: 0;
  font-size: 16px;
  color: #231d17;
}
.tree-sub {
  margin: 3px 0 0;
  font-size: 12px;
  color: #6b5e50;
}
.tree-header-badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
  font-size: 11px;
}
.tree-total {
  padding: 3px 8px;
  border-radius: 999px;
  background: #231d17;
  color: #f8f2e6;
  font-weight: 600;
}
.legend-chip {
  padding: 3px 7px;
  border-radius: 4px;
  border: 1px solid rgba(36, 30, 24, 0.2);
}
.legend-chip.is-unlocked {
  background: rgba(158, 50, 35, 0.12);
  border-color: rgba(158, 50, 35, 0.45);
  color: #9e3223;
}
.legend-chip.is-next {
  border-style: dashed;
  border-color: #9e3223;
  color: #6f2d20;
}
.legend-chip.is-locked {
  color: #7c7163;
}
.branch-stack {
  display: grid;
  gap: 6px;
}
.branch-lane {
  padding: 6px 9px 7px;
  border: 1px solid rgba(36, 30, 24, 0.14);
  border-radius: 6px;
  background: rgba(252, 249, 242, 0.88);
}
.branch-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.branch-name {
  font-size: 13px;
  font-weight: 700;
  color: #231d17;
}
.branch-lv {
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(36, 30, 24, 0.08);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: #3f362c;
}
.branch-count {
  margin-left: auto;
  font-size: 11px;
  color: #6f6254;
}
.node-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  position: relative;
}
.tech-node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  padding: 4px 5px;
  border: 1px solid rgba(36, 30, 24, 0.18);
  border-radius: 6px;
  background: rgba(255, 253, 249, 0.9);
  color: #231d17;
  cursor: pointer;
  text-align: center;
  transition: transform 0.12s ease, border-color 0.12s ease, box-shadow 0.12s ease;
}
.tech-node:hover {
  transform: translateY(-1px);
  border-color: rgba(158, 50, 35, 0.55);
}
.tech-node.is-unlocked {
  background: linear-gradient(180deg, rgba(251, 244, 232, 0.98), rgba(244, 233, 214, 0.94));
  border-color: rgba(158, 50, 35, 0.45);
}
.tech-node.is-next {
  border-style: dashed;
  border-color: rgba(158, 50, 35, 0.6);
  background: rgba(255, 250, 242, 0.95);
}
.tech-node.is-locked {
  opacity: 0.72;
}
.tech-node.is-selected {
  outline: 2px solid #9e3223;
  outline-offset: 1px;
  opacity: 1;
}
.node-top {
  width: 100%;
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #716354;
}
.node-era {
  font-weight: 600;
}
.tech-node.is-unlocked .node-state {
  color: #9e3223;
  font-weight: 700;
}
.node-art-wrap {
  margin: 1px 0;
}
.node-name {
  font-size: 12px;
  font-weight: 700;
  line-height: 1.25;
}
.node-sub {
  font-size: 10.5px;
  color: #6f6254;
  line-height: 1.2;
}
.node-meter {
  width: 100%;
  height: 3px;
  margin-top: 2px;
  border-radius: 999px;
  background: rgba(36, 30, 24, 0.1);
  overflow: hidden;
}
.node-meter-fill {
  display: block;
  height: 100%;
  background: #9e3223;
}
.inst-panel {
  padding: 7px 10px;
  border: 1px solid rgba(36, 30, 24, 0.14);
  border-radius: 6px;
  background: rgba(252, 249, 242, 0.88);
}
.inst-heading {
  margin: 0 0 5px;
  font-size: 12.5px;
  color: #231d17;
}
.inst-grid {
  display: grid;
  gap: 5px;
}
.inst-row {
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}
.inst-row-label {
  font-size: 11.5px;
  font-weight: 600;
  color: #5b5044;
}
.inst-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.inst-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border: 1px solid rgba(36, 30, 24, 0.18);
  border-radius: 4px;
  background: rgba(255, 253, 248, 0.9);
  font-size: 11.5px;
  color: #3a3128;
  cursor: pointer;
}
.inst-chip.is-active {
  background: #9e3223;
  border-color: #9e3223;
  color: #fff9f2;
}
.inst-chip.is-unlocked {
  border-color: rgba(36, 30, 24, 0.45);
  background: rgba(242, 234, 220, 0.95);
}
.inst-chip.is-locked {
  opacity: 0.7;
}
.inst-chip.is-selected {
  outline: 2px solid #9e3223;
  outline-offset: 1px;
  opacity: 1;
}
.inst-chip-tag {
  font-size: 10px;
  opacity: 0.85;
}
.tree-inspector {
  display: flex;
  flex-direction: column;
  gap: 11px;
  padding: 12px 14px;
  border: 1px solid rgba(36, 30, 24, 0.16);
  border-radius: 6px;
  background: rgba(252, 248, 240, 0.94);
}
.insp-hero {
  display: flex;
  align-items: center;
  gap: 12px;
}
.insp-art {
  flex: none;
  padding: 4px;
  border-radius: 6px;
  background: rgba(242, 234, 219, 0.8);
}
.insp-titles {
  min-width: 0;
  flex: 1;
}
.insp-eyebrow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 11px;
  color: #6b5e50;
}
.insp-seal {
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 700;
  border: 1px solid rgba(36, 30, 24, 0.2);
}
.insp-seal.is-unlocked,
.insp-seal.is-active {
  background: rgba(158, 50, 35, 0.14);
  border-color: rgba(158, 50, 35, 0.45);
  color: #9e3223;
}
.insp-name {
  margin: 4px 0 0;
  font-size: 18px;
  color: #201a14;
}
.insp-sub {
  margin: 2px 0 0;
  font-size: 12px;
  color: #6c5f51;
}
.insp-quote {
  margin: 0;
  padding: 7px 10px;
  border-left: 3px solid #9e3223;
  background: rgba(158, 50, 35, 0.05);
  font-size: 12px;
  line-height: 1.5;
  color: #463a2f;
}
.insp-block {
  display: grid;
  gap: 6px;
}
.insp-block-title {
  font-size: 11.5px;
  font-weight: 700;
  color: #5b4f42;
}
.insp-body {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.55;
  color: #2c241c;
}
.req-list {
  display: grid;
  gap: 7px;
}
.req-row-head {
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  color: #473d33;
}
.req-val {
  font-variant-numeric: tabular-nums;
}
.req-row.is-met .req-val {
  color: #2c6a4f;
  font-weight: 700;
}
.req-bar {
  height: 5px;
  margin-top: 3px;
  border-radius: 999px;
  background: rgba(36, 30, 24, 0.1);
  overflow: hidden;
}
.req-bar-fill {
  display: block;
  height: 100%;
  background: #9e3223;
}
.req-row.is-met .req-bar-fill {
  background: #2c6a4f;
}
.insp-decrees {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.insp-decree-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
  border: 1px solid rgba(36, 30, 24, 0.22);
  border-radius: 4px;
  background: #fffdf8;
  font-size: 12px;
  color: #231d17;
  cursor: pointer;
}
.insp-decree-pill:hover {
  border-color: #9e3223;
}
.insp-decree-pill.is-unmet {
  opacity: 0.72;
}
.pill-state {
  font-size: 10px;
  color: #2c6a4f;
  font-weight: 600;
}
.insp-decree-pill.is-unmet .pill-state {
  color: #8b7b6b;
}
.insp-cta {
  width: 100%;
  padding: 9px 12px;
  border: none;
  border-radius: 5px;
  background: #9e3223;
  color: #fff9f2;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
  cursor: pointer;
}
.insp-cta:hover {
  background: #84281b;
}
@media (max-height: 750px) {
  .tree-view {
    padding: 8px 14px 0;
    gap: 10px;
  }
  .tree-header {
    padding: 7px 10px;
  }
  .branch-lane {
    padding: 7px 9px;
  }
  .tech-node {
    padding: 5px 4px;
  }
  .node-sub {
    display: none;
  }
}
</style>
