<script setup lang="ts">
import { computed } from 'vue'
import atlas from './art/atlas.svg'
const props = defineProps<{ selected: string }>()
const points = [
  { id: 'zhou', label: '西周', lon: 108.8, lat: 34.3, dx: 13, dy: -7 },
  { id: 'greece', label: '希腊', lon: 23.7, lat: 38, dx: -12, dy: -10 },
  { id: 'egypt', label: '埃及', lon: 31.2, lat: 29.9, dx: -13, dy: 17 },
  { id: 'babylon', label: '巴比伦', lon: 44.4, lat: 32.5, dx: 1, dy: -20 },
  { id: 'sumer', label: '苏美尔', lon: 45.6, lat: 31.3, dx: 10, dy: 24 },
  { id: 'harappa', label: '哈拉帕', lon: 72.9, lat: 30.6, dx: -1, dy: -16 },
]
const emit = defineEmits<{ select:[id:string] }>()
const sites = computed(()=>[...points].sort((a,b)=>Number(a.id===props.selected)-Number(b.id===props.selected)))
</script>
<template>
  <svg class="atlas" viewBox="0 0 720 322.4" aria-label="六个古代文明的发源地">
    <image :href="atlas" width="720" height="322.4"/>
    <g class="map-seas" aria-hidden="true"><text x="126" y="144">地 中 海</text><text x="373" y="285">印 度 洋</text></g>
    <g v-for="site in sites" :key="site.id" :class="['map-site', { selected: site.id === selected }]" :transform="`translate(${(site.lon+12)*5} ${(62-site.lat)*5.2})`" @click="emit('select',site.id)" aria-hidden="true">
      <circle class="halo" r="13"/><circle class="pin" r="3.5"/>
      <text :x="site.dx" :y="site.dy" :text-anchor="site.dx < -5 ? 'end' : site.dx > 6 ? 'start' : 'middle'">{{ site.label }}</text>
    </g>
    <g class="map-compass" transform="translate(672 45)" aria-hidden="true">
      <circle r="15"/><circle r="12"/><path d="M0 -21L4 0L0 21L-4 0Z"/><path d="M-17 0H17"/><text x="0" y="-26" text-anchor="middle">北</text>
    </g>
  </svg>
</template>
