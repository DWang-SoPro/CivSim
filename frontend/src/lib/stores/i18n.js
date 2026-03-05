import { writable } from 'svelte/store';

// 语言字典
const translations = {
  zh: {
    // 状态栏
    'status.year': '年份',
    'status.civilization': '文明',
    'status.stability': '稳定性',
    'status.authority': '统治力',
    
    // 侧边栏
    'sidebar.metrics': '文明指标',
    'sidebar.population': '人口',
    'sidebar.territory': '领土',
    'sidebar.technology': '科技',
    'sidebar.culture': '文化',
    'sidebar.wealth': '财富',
    'sidebar.military': '军事',
    'sidebar.diplomacy': '外交概览',
    'sidebar.neighbors': '邻近势力',
    'sidebar.trade': '贸易关系',
    'sidebar.border': '边境威胁',
    'sidebar.turn': '回合数',
    'sidebar.mode': '游戏模式',
    'sidebar.sandbox': '沙盒',
    
    // 外交状态
    'diplomacy.peaceful': '和平',
    'diplomacy.low': '低',
    'diplomacy.medium': '中',
    'diplomacy.high': '高',
    
    // 主显示区
    'main.awaiting': '等待指令中...',
    'main.hint': '请在下方输入您的文明敕令',
    'main.log': '历史日志',
    
    // 底部输入
    'footer.placeholder': '请输入您的文明敕令...',
    'footer.submit': '执行',
    'footer.processing': '处理中...',
    'footer.enter_hint': '按 Enter 提交',
    'footer.natural_hint': '支持自然语言',
    'footer.error': '错误：',
    
    // 按钮
    'btn.submit': '执行',
    'btn.cancel': '取消',
    'btn.language': '语言',
    
    // 语言名称
    'lang.zh': '中文',
    'lang.en': 'English',
    
    // 文明选择屏幕
    'select.title': '文明灵',
    'select.subtitle': 'CIVILIZATION SIMULATOR',
    'select.new_game': '开始新游戏',
    'select.load_game': '加载存档',
    'select.new_game_en': 'NEW GAME',
    'select.load_game_en': 'LOAD GAME',
    
    // 时代选择
    'era.title': '选择时代',
    'era.select': 'SELECT ERA',
    'era.random': '随机选择',
    'era.back': '返回',
    'era.3000_bce': '公元前 3000 年',
    'era.2000_bce': '公元前 2000 年',
    'era.1000_bce': '公元前 1000 年',
    'era.500_bce': '公元前 500 年',
    
    // 地点选择
    'location.title': '选择地点',
    'location.select': 'SELECT LOCATION',
    'location.valid_only': '该时代可选地点',
    'location.all': '所有地点',
    'location.mesopotamia': '美索不达米亚',
    'location.indus_valley': '印度河流域',
    'location.nile_delta': '尼罗河三角洲',
    'location.yellow_river': '黄河流域',
    'location.mediterranean': '地中海东岸',
    
    // 确认屏幕
    'confirm.title': '确认文明',
    'confirm.preview': 'PREVIEW CIVILIZATION',
    'confirm.start': '开始游戏',
    'confirm.regenerate': '重新生成',
    'confirm.back': '返回修改',
    'confirm.name': '文明名称',
    'confirm.year': '起始年份',
    'confirm.population': '初始人口',
    'confirm.stability': '稳定性',
    'confirm.authority': '统治力',
    
    // 存档列表
    'save.title': '选择存档',
    'save.select': 'SELECT SAVE',
    'save.no_saves': '暂无存档',
    'save.load': '加载',
    'save.delete': '删除',
    'save.confirm_delete': '确认删除此存档？',
    'save.created': '创建于',
    
    // 错误信息
    'error.no_era': '请先选择时代',
    'error.no_location': '请先选择地点',
    'error.no_template': '该组合暂无预设模板',
    'error.generation_failed': '生成失败',
    'error.network': '网络错误',
    'error.unknown': '未知错误',
  },
  
  en: {
    // Status Bar
    'status.year': 'YEAR',
    'status.civilization': 'CIVILIZATION',
    'status.stability': 'STABILITY',
    'status.authority': 'AUTHORITY',
    
    // Sidebar
    'sidebar.metrics': 'Civilization Metrics',
    'sidebar.population': 'Population',
    'sidebar.territory': 'Territory',
    'sidebar.technology': 'Technology',
    'sidebar.culture': 'Culture',
    'sidebar.wealth': 'Wealth',
    'sidebar.military': 'Military',
    'sidebar.diplomacy': 'Diplomacy Overview',
    'sidebar.neighbors': 'Neighboring Powers',
    'sidebar.trade': 'Trade Relations',
    'sidebar.border': 'Border Threats',
    'sidebar.turn': 'Turn',
    'sidebar.mode': 'Game Mode',
    'sidebar.sandbox': 'Sandbox',
    
    // Diplomacy Status
    'diplomacy.peaceful': 'Peaceful',
    'diplomacy.low': 'Low',
    'diplomacy.medium': 'Medium',
    'diplomacy.high': 'High',
    
    // Main Display
    'main.awaiting': 'Awaiting input...',
    'main.hint': 'Enter your civilization decree below',
    'main.log': 'History Log',
    
    // Footer Input
    'footer.placeholder': 'Enter your civilization decree...',
    'footer.submit': 'EXECUTE',
    'footer.processing': 'PROCESSING...',
    'footer.enter_hint': 'PRESS ENTER TO SUBMIT',
    'footer.natural_hint': 'NATURAL LANGUAGE SUPPORTED',
    'footer.error': 'Error: ',
    
    // Buttons
    'btn.submit': 'EXECUTE',
    'btn.cancel': 'CANCEL',
    'btn.language': 'LANG',
    
    // Language Names
    'lang.zh': '中文',
    'lang.en': 'English',
    
    // Civilization Selection Screen
    'select.title': 'CivSim',
    'select.subtitle': 'CIVILIZATION SIMULATOR',
    'select.new_game': 'NEW GAME',
    'select.load_game': 'LOAD GAME',
    'select.new_game_en': 'NEW GAME',
    'select.load_game_en': 'LOAD GAME',
    
    // Era Selection
    'era.title': 'SELECT ERA',
    'era.select': 'SELECT ERA',
    'era.random': 'RANDOM',
    'era.back': 'BACK',
    'era.3000_bce': '3000 BCE',
    'era.2000_bce': '2000 BCE',
    'era.1000_bce': '1000 BCE',
    'era.500_bce': '500 BCE',
    
    // Location Selection
    'location.title': 'SELECT LOCATION',
    'location.select': 'SELECT LOCATION',
    'location.valid_only': 'Available for this era',
    'location.all': 'All Locations',
    'location.mesopotamia': 'Mesopotamia',
    'location.indus_valley': 'Indus Valley',
    'location.nile_delta': 'Nile Delta',
    'location.yellow_river': 'Yellow River',
    'location.mediterranean': 'Eastern Mediterranean',
    
    // Confirm Screen
    'confirm.title': 'CONFIRM CIVILIZATION',
    'confirm.preview': 'PREVIEW CIVILIZATION',
    'confirm.start': 'START GAME',
    'confirm.regenerate': 'REGENERATE',
    'confirm.back': 'BACK',
    'confirm.name': 'Civilization Name',
    'confirm.year': 'Starting Year',
    'confirm.population': 'Initial Population',
    'confirm.stability': 'Stability',
    'confirm.authority': 'Authority',
    
    // Save List
    'save.title': 'SELECT SAVE',
    'save.select': 'SELECT SAVE',
    'save.no_saves': 'NO SAVES',
    'save.load': 'LOAD',
    'save.delete': 'DELETE',
    'save.confirm_delete': 'Confirm delete this save?',
    'save.created': 'Created',
    
    // Error Messages
    'error.no_era': 'Please select an era first',
    'error.no_location': 'Please select a location first',
    'error.no_template': 'No preset template for this combination',
    'error.generation_failed': 'Generation failed',
    'error.network': 'Network error',
    'error.unknown': 'Unknown error',
  }
};

// 当前语言
export const currentLang = writable('zh');

// 翻译函数
export function t(key, lang = 'zh') {
  const langDict = translations[lang] || translations.zh;
  return langDict[key] || key;
}

// 切换语言
export function toggleLanguage() {
  currentLang.update(lang => lang === 'zh' ? 'en' : 'zh');
}

// 获取当前语言的翻译字典
export function getTranslations(lang) {
  return translations[lang] || translations.zh;
}
