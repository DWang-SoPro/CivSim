<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    art?: string
    kind?: string
    size?: number | string
  }>(),
  {
    art: '',
    kind: 'tech',
    size: 56,
  }
)

const C = '#9e3223'
</script>

<template>
  <svg
    class="artifact-art"
    :width="props.size"
    :height="props.size"
    viewBox="0 0 80 80"
    fill="none"
    aria-hidden="true"
  >
    <!-- 外框双线刻痕：宋元木刻/汉砖拓片边框 -->
    <rect x="4" y="4" width="72" height="72" rx="4" stroke="currentColor" stroke-width="1.6" stroke-opacity="0.32" />
    <rect x="7" y="7" width="66" height="66" rx="2" stroke="currentColor" stroke-width="0.9" stroke-opacity="0.22" />

    <!-- 1. 耒耜初耕 -->
    <g v-if="art === 'stone_ard'">
      <path d="M16 58 Q30 53 44 58 Q56 62 66 57" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
      <path d="M16 65 Q30 60 44 65 Q56 69 66 64" stroke="currentColor" stroke-width="1.5" stroke-opacity="0.6" stroke-linecap="round" />
      <path d="M53 16 L36 53 L26 53 L31 44 L46 21" stroke="currentColor" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" />
      <path d="M27 32 L54 36" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
      <path d="M36 53 L21 56 L30 43 Z" :fill="C" fill-opacity="0.22" :stroke="C" stroke-width="1.8" stroke-linejoin="round" />
    </g>

    <!-- 2. 青铜耦犁 -->
    <g v-else-if="art === 'bronze_plow'">
      <path d="M14 59 Q32 54 48 59 Q58 62 67 58" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
      <path d="M22 22 C28 16, 39 16, 44 23 C49 16, 60 16, 65 22" :stroke="C" stroke-width="2.1" stroke-linecap="round" />
      <path d="M44 23 L40 46 L23 56" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
      <path d="M24 37 L53 41" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" />
      <path d="M42 46 L18 57 L46 55 Z" :fill="C" fill-opacity="0.28" :stroke="C" stroke-width="1.9" stroke-linejoin="round" />
      <circle cx="44" cy="23" r="2.6" :fill="C" />
    </g>

    <!-- 3. 沟洫灌渠 -->
    <g v-else-if="art === 'canal_weir'">
      <path d="M12 22 H40 V63" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" />
      <path d="M12 31 H31 V63" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" />
      <rect x="33" y="21" width="5" height="17" :fill="C" fill-opacity="0.3" :stroke="C" stroke-width="1.6" />
      <path d="M15 26.5 Q24 25 32 26.5" :stroke="C" stroke-width="1.5" stroke-linecap="round" />
      <path d="M35.5 40 Q33 49 35.5 59" :stroke="C" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="3 2.5" />
      <rect x="44" y="25" width="22" height="14" stroke="currentColor" stroke-width="1.7" />
      <line x1="44" y1="32" x2="66" y2="32" stroke="currentColor" stroke-width="1.2" />
      <line x1="55" y1="25" x2="55" y2="39" stroke="currentColor" stroke-width="1.2" />
      <rect x="44" y="45" width="22" height="15" stroke="currentColor" stroke-width="1.7" />
      <line x1="44" y1="52.5" x2="66" y2="52.5" stroke="currentColor" stroke-width="1.2" />
      <line x1="55" y1="45" x2="55" y2="60" stroke="currentColor" stroke-width="1.2" />
    </g>

    <!-- 4. 常平仓廪 -->
    <g v-else-if="art === 'ever_normal_granary'">
      <path d="M13 33 L40 16 L67 33 Z" :fill="C" fill-opacity="0.18" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" />
      <path d="M19 33 V57 H61 V33" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" />
      <line x1="25" y1="57" x2="25" y2="64" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" />
      <line x1="55" y1="57" x2="55" y2="64" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" />
      <rect x="33" y="40" width="14" height="17" stroke="currentColor" stroke-width="1.7" />
      <rect x="35.5" y="24" width="9" height="6" :fill="C" fill-opacity="0.7" />
      <path d="M15 64 H65" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
      <path d="M22 57 Q27 49 32 57" :fill="C" fill-opacity="0.25" :stroke="C" stroke-width="1.4" />
    </g>

    <!-- 5. 铁犁精耕 -->
    <g v-else-if="art === 'iron_coulter'">
      <path d="M14 60 Q28 52 44 59 Q58 64 67 56" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" />
      <path d="M52 20 C56 32, 57 42, 46 47 C36 52, 23 51, 17 57 L45 55 L60 44" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" />
      <path d="M28 32 L54 27" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
      <path d="M35 31 L27 52" :stroke="C" stroke-width="2" stroke-linecap="round" />
      <path d="M40 46 L18 57 L43 54 Z" :fill="C" fill-opacity="0.32" :stroke="C" stroke-width="1.9" stroke-linejoin="round" />
      <circle cx="24" cy="24" r="3" :stroke="C" stroke-width="1.8" />
    </g>

    <!-- 6. 版筑夯土 -->
    <g v-else-if="art === 'rammed_wall'">
      <rect x="16" y="47" width="48" height="14" stroke="currentColor" stroke-width="2" />
      <line x1="16" y1="54" x2="64" y2="54" stroke="currentColor" stroke-width="1.2" stroke-dasharray="6 3" />
      <rect x="20" y="34" width="40" height="13" stroke="currentColor" stroke-width="2" />
      <line x1="20" y1="40.5" x2="60" y2="40.5" stroke="currentColor" stroke-width="1.2" stroke-dasharray="5 3" />
      <path d="M22 34 V28 H29 V34 H36 V28 H44 V34 H51 V28 H58 V34" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round" />
      <line x1="33" y1="15" x2="33" y2="30" :stroke="C" stroke-width="2.1" stroke-linecap="round" />
      <rect x="29" y="25" width="8" height="5" :fill="C" fill-opacity="0.35" :stroke="C" stroke-width="1.5" />
      <line x1="48" y1="13" x2="48" y2="28" :stroke="C" stroke-width="2.1" stroke-linecap="round" />
      <rect x="44" y="23" width="8" height="5" :fill="C" fill-opacity="0.35" :stroke="C" stroke-width="1.5" />
    </g>

    <!-- 7. 青铜冶铸 -->
    <g v-else-if="art === 'bronze_foundry'">
      <path d="M22 44 C22 57, 58 57, 58 44 Z" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" />
      <path d="M20 44 H60" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" />
      <path d="M25 40 C25 36, 29 36, 29 40 V44 M51 44 V40 C51 36, 55 36, 55 40" stroke="currentColor" stroke-width="1.8" />
      <line x1="30" y1="53" x2="27" y2="64" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
      <line x1="40" y1="54" x2="40" y2="65" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
      <line x1="50" y1="53" x2="53" y2="64" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
      <path d="M47 16 L60 22 L53 31 L43 24 Z" :fill="C" fill-opacity="0.22" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
      <path d="M44 26 Q40 34 40 43" :stroke="C" stroke-width="2.2" stroke-linecap="round" />
    </g>

    <!-- 8. 泉府铸币 -->
    <g v-else-if="art === 'mint_coinage'">
      <circle cx="40" cy="40" r="19" stroke="currentColor" stroke-width="2.2" />
      <circle cx="40" cy="40" r="15.5" stroke="currentColor" stroke-width="1" stroke-opacity="0.5" />
      <rect x="33.5" y="33.5" width="13" height="13" :fill="C" fill-opacity="0.18" :stroke="C" stroke-width="2.1" />
      <path d="M16 20 L16 60 M64 20 L64 60" stroke="currentColor" stroke-width="1.5" stroke-opacity="0.45" stroke-dasharray="3 3" />
      <circle cx="40" cy="14" r="2.2" :fill="C" />
      <circle cx="40" cy="66" r="2.2" :fill="C" />
    </g>

    <!-- 9. 坚壁虎符 -->
    <g v-else-if="art === 'city_bastion'">
      <path d="M14 58 H66" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
      <path d="M18 58 V41 H27 V45 H33 V35 H47 V45 H53 V41 H62 V58" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
      <path d="M29 35 L40 24 L51 35" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" />
      <path d="M36 58 V48 C36 45, 44 45, 44 48 V58" stroke="currentColor" stroke-width="1.8" />
      <path d="M35 20 Q40 12 45 20 Q40 24 35 20 Z" :fill="C" fill-opacity="0.7" :stroke="C" stroke-width="1.4" />
      <line x1="40" y1="15" x2="40" y2="24" :stroke="C" stroke-width="1.3" stroke-dasharray="2 2" />
    </g>

    <!-- 10. 水排鼓风 -->
    <g v-else-if="art === 'water_bellows'">
      <circle cx="25" cy="44" r="13" stroke="currentColor" stroke-width="2" />
      <circle cx="25" cy="44" r="3" :fill="C" />
      <line x1="25" y1="29" x2="25" y2="59" stroke="currentColor" stroke-width="1.3" />
      <line x1="10" y1="44" x2="40" y2="44" stroke="currentColor" stroke-width="1.3" />
      <line x1="14" y1="33" x2="36" y2="55" stroke="currentColor" stroke-width="1.3" />
      <line x1="36" y1="33" x2="14" y2="55" stroke="currentColor" stroke-width="1.3" />
      <path d="M27 42 L47 36" :stroke="C" stroke-width="2.1" stroke-linecap="round" />
      <rect x="46" y="29" width="19" height="14" rx="2" stroke="currentColor" stroke-width="1.9" />
      <path d="M51 58 L55.5 46 L60 58 Z" :fill="C" fill-opacity="0.4" :stroke="C" stroke-width="1.7" />
      <path d="M13 62 Q25 58 37 62" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
    </g>

    <!-- 11. 结绳刻符 -->
    <g v-else-if="art === 'oracle_script'">
      <path d="M24 22 C33 15, 47 15, 56 22 L59 38 C59 53, 51 64, 40 66 C29 64, 21 53, 21 38 Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
      <line x1="40" y1="18" x2="40" y2="65" stroke="currentColor" stroke-width="1.3" stroke-opacity="0.6" />
      <path d="M29 31 H35 M32 27 V38 M29 44 L36 47" :stroke="C" stroke-width="1.7" stroke-linecap="round" />
      <rect x="45" y="28" width="7" height="9" :stroke="C" stroke-width="1.5" />
      <line x1="45" y1="32.5" x2="52" y2="32.5" :stroke="C" stroke-width="1.4" />
      <path d="M46 43 C51 43, 51 50, 46 52" :stroke="C" stroke-width="1.7" stroke-linecap="round" />
    </g>

    <!-- 12. 太学典诰 -->
    <g v-else-if="art === 'academy_scroll'">
      <rect x="17" y="22" width="38" height="36" rx="2" stroke="currentColor" stroke-width="1.9" />
      <line x1="25" y1="22" x2="25" y2="58" stroke="currentColor" stroke-width="1.1" stroke-opacity="0.55" />
      <line x1="33" y1="22" x2="33" y2="58" stroke="currentColor" stroke-width="1.1" stroke-opacity="0.55" />
      <line x1="41" y1="22" x2="41" y2="58" stroke="currentColor" stroke-width="1.1" stroke-opacity="0.55" />
      <line x1="49" y1="22" x2="49" y2="58" stroke="currentColor" stroke-width="1.1" stroke-opacity="0.55" />
      <path d="M17 31 H55 M17 49 H55" stroke="currentColor" stroke-width="1.3" stroke-dasharray="4 4" />
      <path d="M62 18 L57 52 L60 59 L63 52 L67 18 Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
      <rect x="21" y="45" width="9" height="9" :fill="C" fill-opacity="0.82" rx="1" />
    </g>

    <!-- 13. 明法颁律 -->
    <g v-else-if="art === 'bronze_statute'">
      <line x1="40" y1="16" x2="40" y2="62" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" />
      <line x1="28" y1="62" x2="52" y2="62" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" />
      <line x1="18" y1="27" x2="62" y2="27" :stroke="C" stroke-width="2.1" stroke-linecap="round" />
      <circle cx="40" cy="27" r="3" :fill="C" />
      <path d="M19 27 L14 43 H24 Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
      <path d="M13 43 C15 47, 23 47, 25 43 Z" :fill="C" fill-opacity="0.25" stroke="currentColor" stroke-width="1.6" />
      <path d="M61 27 L56 43 H66 Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
      <path d="M55 43 C57 47, 65 47, 67 43 Z" :fill="C" fill-opacity="0.25" stroke="currentColor" stroke-width="1.6" />
    </g>

    <!-- 14. 石渠修史 -->
    <g v-else-if="art === 'canon_library'">
      <rect x="18" y="46" width="44" height="12" rx="1.5" stroke="currentColor" stroke-width="1.9" />
      <rect x="20" y="33" width="40" height="12" rx="1.5" stroke="currentColor" stroke-width="1.9" />
      <rect x="23" y="20" width="34" height="12" rx="1.5" stroke="currentColor" stroke-width="1.9" />
      <line x1="28" y1="46" x2="28" y2="58" :stroke="C" stroke-width="1.8" />
      <line x1="30" y1="33" x2="30" y2="45" :stroke="C" stroke-width="1.8" />
      <line x1="33" y1="20" x2="33" y2="32" :stroke="C" stroke-width="1.8" />
      <rect x="44" y="23" width="8" height="6" :fill="C" fill-opacity="0.75" rx="0.8" />
      <line x1="34" y1="39" x2="54" y2="39" stroke="currentColor" stroke-width="1.3" />
      <line x1="32" y1="52" x2="56" y2="52" stroke="currentColor" stroke-width="1.3" />
    </g>

    <!-- 15. 格物致知 -->
    <g v-else-if="art === 'armillary_press'">
      <circle cx="40" cy="36" r="17" stroke="currentColor" stroke-width="2" />
      <ellipse cx="40" cy="36" rx="17" ry="6.5" stroke="currentColor" stroke-width="1.5" />
      <ellipse cx="40" cy="36" rx="7" ry="17" :stroke="C" stroke-width="1.5" />
      <line x1="25" y1="21" x2="55" y2="51" :stroke="C" stroke-width="1.8" stroke-linecap="round" />
      <circle cx="40" cy="36" r="2.6" :fill="C" />
      <path d="M26 63 L33 52 H47 L54 63 Z" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round" />
    </g>

    <!-- 制度印章（田制/政体/赋役） -->
    <g v-else-if="kind === 'land'">
      <rect x="20" y="20" width="40" height="40" rx="3" stroke="currentColor" stroke-width="2.1" />
      <line x1="40" y1="20" x2="40" y2="60" :stroke="C" stroke-width="2" />
      <line x1="20" y1="40" x2="60" y2="40" :stroke="C" stroke-width="2" />
      <rect x="24" y="24" width="12" height="12" fill="currentColor" fill-opacity="0.1" />
      <rect x="44" y="44" width="12" height="12" :fill="C" fill-opacity="0.2" />
    </g>
    <g v-else-if="kind === 'polity'">
      <rect x="22" y="26" width="36" height="34" rx="2" stroke="currentColor" stroke-width="2.1" />
      <path d="M32 26 V19 H48 V26" :stroke="C" stroke-width="2.1" stroke-linejoin="round" />
      <path d="M31 37 H49 M31 44 H49 M40 33 V52" :stroke="C" stroke-width="1.8" stroke-linecap="round" />
    </g>
    <g v-else>
      <circle cx="40" cy="40" r="18" stroke="currentColor" stroke-width="2" />
      <rect x="33" y="33" width="14" height="14" :fill="C" fill-opacity="0.22" :stroke="C" stroke-width="1.8" />
    </g>
  </svg>
</template>

<style scoped>
.artifact-art {
  display: block;
  flex: none;
  color: #231f1a;
}
</style>
