<script lang="ts">
  import { currentLang } from '$lib/stores/i18n.js';
  import { civState, stateChanges, type CivState, type StateChange } from '$lib/stores/civState.js';
  
  $: lang = $currentLang;
  $: state = $civState;
  $: changes = $stateChanges;
  
  const t = (key: string) => {
    const translations: Record<string, Record<string, string>> = {
      zh: {
        'sidebar.metrics': '文明指标',
        'sidebar.population': '人口',
        'sidebar.territory': '领土',
        'sidebar.technology': '科技',
        'sidebar.stability': '稳定性',
        'sidebar.authority': '统治力',
        'sidebar.culture': '文化',
        'sidebar.wealth': '财富',
        'sidebar.military': '军事',
        'sidebar.political': '政治制度',
        'sidebar.economic': '经济制度',
        'sidebar.diplomacy': '外交概览',
        'sidebar.neighbors': '邻近势力',
        'sidebar.trade': '贸易关系',
        'sidebar.border': '边境威胁',
        'sidebar.turn': '回合数',
        'sidebar.mode': '游戏模式',
        'sidebar.sandbox': '沙盒',
        'diplomacy.peaceful': '和平',
        'diplomacy.low': '低',
        'diplomacy.medium': '中',
        'diplomacy.high': '高',
      },
      en: {
        'sidebar.metrics': 'Civilization Metrics',
        'sidebar.population': 'Population',
        'sidebar.territory': 'Territory',
        'sidebar.technology': 'Technology',
        'sidebar.stability': 'Stability',
        'sidebar.authority': 'Authority',
        'sidebar.culture': 'Culture',
        'sidebar.wealth': 'Wealth',
        'sidebar.military': 'Military',
        'sidebar.political': 'Political System',
        'sidebar.economic': 'Economic System',
        'sidebar.diplomacy': 'Diplomacy Overview',
        'sidebar.neighbors': 'Neighboring Powers',
        'sidebar.trade': 'Trade Relations',
        'sidebar.border': 'Border Threats',
        'sidebar.turn': 'Turn',
        'sidebar.mode': 'Game Mode',
        'sidebar.sandbox': 'Sandbox',
        'diplomacy.peaceful': 'Peaceful',
        'diplomacy.low': 'Low',
        'diplomacy.medium': 'Medium',
        'diplomacy.high': 'High',
      }
    };
    return translations[lang][key] || key;
  };
  // 计算动态最大值（留20%余量）
  function calculateMax(value: number): number {
    if (value <= 0) return 100;
    // 向上取整到合适的数量级，并留20%余量
    const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
    const normalized = value / magnitude;
    let base: number;
    if (normalized <= 1) base = 1;
    else if (normalized <= 2) base = 2;
    else if (normalized <= 5) base = 5;
    else base = 10;
    return base * magnitude * 1.2;
  }

  // 格式化变化量显示
  function formatChange(value: number, isPercent: boolean = false): string {
    if (value === 0) return '';
    const sign = value > 0 ? '+' : '';
    if (isPercent) {
      return `${sign}${(value * 100).toFixed(1)}%`;
    }
    return `${sign}${Math.round(value).toLocaleString()}`;
  }

  // 获取变化量颜色
  function getChangeColor(value: number, inverse: boolean = false): string {
    if (value === 0) return 'rgba(180, 200, 180, 0.6)';
    const isGood = inverse ? value < 0 : value > 0;
    return isGood ? '#00ff99' : '#ff4444';
  }

  // Calculate dynamic stats based on current state
  $: stats = [
    { 
      label: 'sidebar.population', 
      value: state.population, 
      max: calculateMax(state.population), 
      color: '#00ff99',
      change: changes?.population || 0,
      isPercent: false
    },
    { 
      label: 'sidebar.territory', 
      value: state.territory_size, 
      max: calculateMax(state.territory_size), 
      color: '#ffb000',
      change: changes?.territory_size || 0,
      isPercent: false
    },
    { 
      label: 'sidebar.technology', 
      value: state.tech_level, 
      max: calculateMax(state.tech_level), 
      color: '#5aa8cc',
      change: changes?.tech_level || 0,
      isPercent: false
    },
    { 
      label: 'sidebar.stability', 
      value: state.stability, 
      max: 100, 
      color: state.stability >= 50 ? '#00ff99' : '#ff4444',
      change: changes?.stability || 0,
      isPercent: false,
      inverse: true // 稳定性降低是坏事
    },
    { 
      label: 'sidebar.authority', 
      value: state.authority, 
      max: 100, 
      color: '#ffb000',
      change: changes?.authority || 0,
      isPercent: false
    },
  ];
</script>

<aside class="sidebar">
  <div class="panel-content">
    <h2 class="panel-title">{t('sidebar.metrics')}</h2>
    <div class="stats-list">
      {#each stats as stat}
        <div class="stat-row">
          <div class="stat-header">
            <span class="stat-label">{t(stat.label)}</span>
            <div class="stat-values">
              <span class="stat-number">{Math.round(stat.value).toLocaleString()}</span>
              {#if stat.change !== 0}
                <span class="stat-change" style="color: {getChangeColor(stat.change, stat.inverse)}">
                  {formatChange(stat.change, stat.isPercent)}
                </span>
              {/if}
            </div>
          </div>
          <div class="progress-bar">
            <div 
              class="progress-fill" 
              style="width: {Math.min((stat.value / stat.max) * 100, 100)}%; background: {stat.color}"
            ></div>
          </div>
        </div>
      {/each}
    </div>
    
    <div class="section-divider"></div>
    
    <h3 class="section-title">{t('sidebar.political')}</h3>
    
    <div class="systems-list">
      <div class="system-item">
        <span class="system-label">{t('sidebar.political')}</span>
        <span class="system-value">{state.political_system || '-'}</span>
      </div>
      <div class="system-item">
        <span class="system-label">{t('sidebar.economic')}</span>
        <span class="system-value">{state.economic_system || '-'}</span>
      </div>
    </div>
    
    <div class="section-divider"></div>
    
    <h3 class="section-title">{t('sidebar.diplomacy')}</h3>
    
    <div class="diplomacy-list">
      <div class="diplomacy-item">
        <span class="diplomacy-label">{t('sidebar.neighbors')}</span>
        <span class="diplomacy-value">-</span>
      </div>
      <div class="diplomacy-item">
        <span class="diplomacy-label">{t('sidebar.trade')}</span>
        <span class="diplomacy-value text-green">{t('diplomacy.peaceful')}</span>
      </div>
      <div class="diplomacy-item">
        <span class="diplomacy-label">{t('sidebar.border')}</span>
        <span class="diplomacy-value text-amber">{t('diplomacy.low')}</span>
      </div>
    </div>
  </div>
</aside>

<style>
  .sidebar {
    width: 280px;
    background: #0f0f0f;
    border-right: 1px solid rgba(0, 255, 153, 0.15);
    overflow-y: auto;
    flex-shrink: 0;
  }
  
  .panel-content {
    padding: 24px;
  }
  
  .panel-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: rgba(180, 200, 180, 0.6);
    padding-bottom: 12px;
    margin-bottom: 20px;
    border-bottom: 1px solid rgba(0, 255, 153, 0.15);
  }
  
  .stats-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .stat-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  
  .stat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .stat-label {
    font-size: 12px;
    letter-spacing: 0.05em;
    color: rgba(180, 200, 180, 0.6);
  }
  
  .stat-values {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .stat-number {
    font-size: 13px;
    font-weight: 700;
    color: #ffb000;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.03em;
  }
  
  .stat-change {
    font-size: 11px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.03em;
  }
  
  .progress-bar {
    height: 4px;
    background: rgba(0, 255, 153, 0.1);
    border-radius: 2px;
    overflow: hidden;
  }
  
  .progress-fill {
    height: 100%;
    transition: width 0.3s ease;
  }
  
  .section-divider {
    height: 1px;
    background: rgba(0, 255, 153, 0.15);
    margin: 24px 0;
  }
  
  .section-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: rgba(180, 200, 180, 0.6);
    margin-bottom: 16px;
  }
  
  .diplomacy-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  .diplomacy-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .diplomacy-label {
    font-size: 12px;
    color: rgba(180, 200, 180, 0.6);
  }
  
  .diplomacy-value {
    font-size: 12px;
    font-weight: 600;
    color: rgba(180, 200, 180, 0.9);
  }
  
  .systems-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  .system-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: rgba(0, 255, 255, 153, 0.05);
    border: 1px solid rgba(0, 255, 153, 0.1);
    border-radius: 4px;
  }
  
  .system-label {
    font-size: 12px;
    color: rgba(180, 200, 180, 0.6);
  }
  
  .system-value {
    font-size: 12px;
    font-weight: 600;
    color: #00ff99;
    font-family: 'JetBrains Mono', monospace;
  }
  
  .text-green { color: #00ff99; }
  .text-amber { color: #ffb000; }
</style>
