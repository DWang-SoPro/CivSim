# 高级 CSS 效果实现指南

> 针对复古硬件风格的文明演化模拟器 (CivSim)

---

## 1. 文字辉光效果 (Text Glow Effect)

### ⚠️ 性能警告

**关键发现**: `text-shadow` 在频繁更新的内容上会导致严重的性能问题 (从 60fps 降至 1-2fps)。

**原因**: 每次 DOM 更新时，浏览器需要重新渲染 text-shadow，耗时可达 1 秒。

### ✅ 最佳实践

```css
/* ❌ 避免：频繁更新的内容上使用 text-shadow */
.score {
  text-shadow: 0px 0px 1em red; /* 性能杀手 */
}

/* ✅ 推荐：静态内容或低频率更新 */
.title-glow {
  color: #fff;
  text-shadow: 
    0 0 10px rgba(255, 100, 100, 0.8),
    0 0 20px rgba(255, 100, 100, 0.6),
    0 0 30px rgba(255, 100, 100, 0.4),
    0 0 40px rgba(255, 100, 100, 0.2);
}

/* ✅ 替代方案：使用 filter 或伪元素 */
.glow-alternative {
  position: relative;
  color: #fff;
}

.glow-alternative::before {
  content: attr(data-text);
  position: absolute;
  left: 0;
  top: 0;
  color: rgba(255, 100, 100, 0.5);
  filter: blur(8px);
  z-index: -1;
}
```

### 动画辉光 (Pulsating Glow)

```css
@keyframes glow-pulse {
  0%, 100% {
    text-shadow: 
      0 0 4px rgba(255, 100, 100, 0.5),
      0 0 8px rgba(255, 100, 100, 0.3);
  }
  50% {
    text-shadow: 
      0 0 8px rgba(255, 100, 100, 0.8),
      0 0 16px rgba(255, 100, 100, 0.6),
      0 0 24px rgba(255, 100, 100, 0.4);
  }
}

.retro-title {
  color: #ff6b6b;
  animation: glow-pulse 2s ease-in-out infinite;
}
```

### Tailwind 集成

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      textShadow: {
        'glow': '0 0 10px rgba(255, 100, 100, 0.8)',
        'glow-lg': `
          0 0 10px rgba(255, 100, 100, 0.8),
          0 0 20px rgba(255, 100, 100, 0.6),
          0 0 30px rgba(255, 100, 100, 0.4)
        `,
      },
      animation: {
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': {
            textShadow: '0 0 4px rgba(255, 100, 100, 0.5), 0 0 8px rgba(255, 100, 100, 0.3)',
          },
          '50%': {
            textShadow: '0 0 8px rgba(255, 100, 100, 0.8), 0 0 16px rgba(255, 100, 100, 0.6), 0 0 24px rgba(255, 100, 100, 0.4)',
          },
        },
      },
    },
  },
  plugins: [
    function({ matchUtilities, theme }) {
      matchUtilities(
        {
          'text-shadow': (value) => ({
            textShadow: value,
          }),
        },
        { values: theme('textShadow') }
      )
    },
  ],
}
```

```html
<!-- 使用示例 -->
<h1 class="text-shadow-glow-lg animate-glow-pulse text-red-400">
  文明灵 CivSim
</h1>
```

---

## 2. 玻璃材质效果 (Glassmorphism)

### 核心实现

```css
.glass-panel {
  /* 半透明背景 */
  background: rgba(255, 255, 255, 0.1);
  
  /* 背景模糊 - 核心效果 */
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px); /* Safari 支持 */
  
  /* 边框 - 增加厚度感 */
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-top: 1px solid rgba(255, 255, 255, 0.3); /* 顶部更亮 */
  border-left: 1px solid rgba(255, 255, 255, 0.3); /* 左侧更亮 */
  
  /* 阴影 - 增加深度 */
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 0 0 1px rgba(255, 255, 255, 0.05);
  
  /* 圆角 */
  border-radius: 16px;
}
```

### 增强厚度感 (高级技巧)

```css
.glass-thick {
  /* 多层叠加创造厚度 */
  background: 
    linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.15) 0%,
      rgba(255, 255, 255, 0.05) 100%
    );
  
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  
  /* 多层边框模拟厚度 */
  border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow: 
    /* 外部阴影 */
    0 8px 32px 0 rgba(0, 0, 0, 0.37),
    /* 内部高光 */
    inset 0 0 0 1px rgba(255, 255, 255, 0.1),
    inset 0 1px 0 0 rgba(255, 255, 255, 0.2),
    /* 底部厚度阴影 */
    0 1px 2px rgba(0, 0, 0, 0.2);
  
  /* 内部渐变增加立体感 */
  position: relative;
}

.glass-thick::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.4),
    rgba(255, 255, 255, 0.05) 50%,
    rgba(255, 255, 255, 0) 100%
  );
  -webkit-mask: 
    linear-gradient(#fff 0 0) content-box, 
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}
```

### 性能优化

```css
/* ✅ 使用 will-change 提示 GPU 加速 */
.glass-panel {
  will-change: backdrop-filter;
  transform: translateZ(0); /* 强制 GPU 层 */
}

/* ✅ 限制同时使用的 backdrop-filter 数量 (建议 ≤ 3) */

/* ✅ 避免在动画元素上使用 backdrop-filter */
```

### Tailwind 集成

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      backgroundColor: {
        'glass': 'rgba(255, 255, 255, 0.1)',
        'glass-dark': 'rgba(0, 0, 0, 0.2)',
      },
      backdropBlur: {
        'xs': '2px',
        'glass': '12px',
        'glass-lg': '20px',
      },
      borderColor: {
        'glass': 'rgba(255, 255, 255, 0.2)',
        'glass-light': 'rgba(255, 255, 255, 0.3)',
      },
      boxShadow: {
        'glass': `
          0 8px 32px 0 rgba(0, 0, 0, 0.3),
          inset 0 0 0 1px rgba(255, 255, 255, 0.05)
        `,
        'glass-thick': `
          0 8px 32px 0 rgba(0, 0, 0, 0.37),
          inset 0 0 0 1px rgba(255, 255, 255, 0.1),
          inset 0 1px 0 0 rgba(255, 255, 255, 0.2)
        `,
      },
    },
  },
  plugins: [],
}
```

```html
<!-- 使用示例 -->
<div class="bg-glass backdrop-blur-glass border border-glass 
            shadow-glass rounded-2xl p-6">
  <h2 class="text-white text-xl">控制面板</h2>
</div>
```

---

## 3. 机械仪表盘动画 (Mechanical Gauge)

### 纯 CSS 方案 (推荐 - 性能最优)

```html
<!-- 极简 HTML -->
<div class="gauge" style="--value: 0.75;">
  <span class="gauge-value">75%</span>
</div>
```

```css
.gauge {
  /* 尺寸 */
  --size: 200px;
  --cutout: 60%;
  --color: #ff6b6b;
  --background: rgba(255, 255, 255, 0.1);
  
  width: var(--size);
  height: var(--size);
  border-radius: 50%;
  
  /* 表盘背景 */
  background: 
    /* 中心挖空 */
    radial-gradient(
      var(--background) 0% var(--cutout),
      transparent var(--cutout) 100%
    ),
    /* 刻度环 */
    conic-gradient(
      var(--color) calc(var(--value) * 100%),
      rgba(255, 255, 255, 0.1) 0deg
    );
  
  /* 居中文字 */
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  
  /* 性能优化 */
  transform: translateZ(0);
}

.gauge-value {
  font-size: 2rem;
  font-weight: bold;
  color: #fff;
  font-family: 'Courier New', monospace; /* 复古风格 */
}
```

### 270° 仪表盘 (更专业)

```css
.gauge-270 {
  --size: 200px;
  --value: 0.75; /* 0-1 */
  --color: #ff6b6b;
  --bg: rgba(255, 255, 255, 0.1);
  
  width: var(--size);
  height: var(--size);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gauge-270::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: 
    radial-gradient(transparent 60%, var(--bg) 61%),
    conic-gradient(
      from 135deg,
      var(--color) calc(var(--value) * 270deg),
      transparent 0deg
    );
  transform: rotate(-135deg);
}

/* 中心覆盖 */
.gauge-270::after {
  content: '';
  position: absolute;
  width: 60%;
  height: 60%;
  background: var(--bg);
  border-radius: 50%;
}
```

### 带指针的机械仪表

```css
.gauge-needle {
  --size: 200px;
  --angle: 0deg; /* 动态设置 */
  
  width: var(--size);
  height: var(--size);
  position: relative;
  
  /* 表盘 */
  background: conic-gradient(
    from 135deg,
    #ff4444 0deg 90deg,
    #ffaa00 90deg 180deg,
    #44ff44 180deg 270deg,
    transparent 270deg
  );
  border-radius: 50%;
}

/* 指针 */
.gauge-needle::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 45%;
  height: 4px;
  background: linear-gradient(90deg, #fff, #ff4444);
  transform-origin: left center;
  transform: translateY(-50%) rotate(var(--angle));
  border-radius: 2px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 中心圆点 */
.gauge-needle::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 16px;
  height: 16px;
  background: #333;
  border: 3px solid #fff;
  border-radius: 50%;
  transform: translate(-50%, -50%);
}

/* 指针动画 */
@keyframes needle-sweep {
  from { transform: translateY(-50%) rotate(-135deg); }
  to { transform: translateY(-50%) rotate(135deg); }
}

.gauge-needle.animate::before {
  animation: needle-sweep 2s ease-out forwards;
}
```

### Tailwind 集成

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      backgroundImage: {
        'gauge': `conic-gradient(from 135deg, #ff4444 0deg 90deg, #ffaa00 90deg 180deg, #44ff44 180deg 270deg, transparent 270deg)`,
      },
      transitionTimingFunction: {
        'mechanical': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [
    function({ addUtilities }) {
      addUtilities({
        '.gauge-270': {
          '--tw-gauge-value': '0.5',
          'background-image': `
            radial-gradient(transparent 60%, rgba(255,255,255,0.1) 61%),
            conic-gradient(from 135deg, rgb(255 107 107) calc(var(--tw-gauge-value) * 270deg), transparent 0deg)
          `,
        },
      })
    },
  ],
}
```

```html
<!-- 使用示例 -->
<div class="gauge-270 w-48 h-48 relative" 
     style="--tw-gauge-value: 0.75;">
  <span class="relative z-10 text-2xl font-mono text-white">
    75%
  </span>
</div>
```

---

## 4. 打字机效果 (Typewriter Effect)

### 纯 CSS 方案 (性能最佳)

```html
<div class="typewriter">
  <p class="typewriter-text">文明演化模拟器</p>
</div>
```

```css
.typewriter-text {
  /* 关键属性 */
  overflow: hidden;
  border-right: 3px solid #ff6b6b; /* 光标 */
  white-space: nowrap;
  margin: 0;
  
  /* 动画 */
  animation: 
    typing 3.5s steps(7) infinite,
    blink-caret 0.75s step-end infinite;
  
  /* 字体 */
  font-family: 'Courier New', monospace;
  font-size: 1.5rem;
  color: #fff;
}

/* 打字动画 */
@keyframes typing {
  from { width: 0 }
  to { width: 100% }
}

/* 光标闪烁 */
@keyframes blink-caret {
  from, to { border-color: transparent }
  50% { border-color: #ff6b6b }
}
```

### 多行打字机效果

```css
.typewriter-multi {
  font-family: 'Courier New', monospace;
}

.typewriter-line {
  display: block;
  overflow: hidden;
  border-right: 2px solid #ff6b6b;
  white-space: nowrap;
  animation: 
    typing-line 2s steps(20, end) forwards,
    blink-caret 0.75s step-end infinite;
}

.typewriter-line:nth-child(1) {
  animation-delay: 0s;
}

.typewriter-line:nth-child(2) {
  animation-delay: 2s;
}

.typewriter-line:nth-child(3) {
  animation-delay: 4s;
}

@keyframes typing-line {
  from { width: 0 }
  to { width: 100% }
}
```

### JavaScript 增强版 (动态内容)

```javascript
class Typewriter {
  constructor(element, options = {}) {
    this.element = element;
    this.text = element.textContent;
    this.speed = options.speed || 100;
    this.delay = options.delay || 2000;
    this.loop = options.loop || false;
    this.cursor = options.cursor !== false;
    
    element.textContent = '';
    element.style.borderRight = this.cursor ? '2px solid #ff6b6b' : 'none';
    
    this.index = 0;
    this.type();
  }
  
  type() {
    if (this.index < this.text.length) {
      this.element.textContent += this.text.charAt(this.index);
      this.index++;
      setTimeout(() => this.type(), this.speed);
    } else if (this.loop) {
      setTimeout(() => {
        this.index = 0;
        this.element.textContent = '';
        this.type();
      }, this.delay);
    }
  }
}

// 使用示例
const el = document.querySelector('.typewriter-text');
new Typewriter(el, { speed: 80, loop: true });
```

### Tailwind 集成

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      animation: {
        'typing': 'typing 3.5s steps(7) infinite',
        'blink': 'blink-caret 0.75s step-end infinite',
      },
      keyframes: {
        typing: {
          from: { width: '0' },
          to: { width: '100%' },
        },
        'blink-caret': {
          'from, to': { borderColor: 'transparent' },
          '50%': { borderColor: '#ff6b6b' },
        },
      },
    },
  },
  plugins: [],
}
```

```html
<!-- 使用示例 -->
<p class="font-mono text-lg text-white overflow-hidden 
          border-r-2 border-red-400 whitespace-nowrap
          animate-typing animate-blink">
  文明演化模拟器
</p>
```

### 性能优化建议

```css
/* ✅ 使用 steps() 实现逐字效果 (比逐帧流畅) */
.typewriter {
  animation: typing 3s steps(10, end);
}

/* ✅ 使用 will-change 提示优化 */
.typewriter-text {
  will-change: width;
}

/* ❌ 避免：在大量文本上使用 (建议 ≤ 50 字符) */
```

---

## 5. 数值跳变动画 (Counter Animation)

### 轻量级 Vanilla JS 实现 (推荐)

```javascript
class CounterAnimator {
  constructor(element, options = {}) {
    this.element = element;
    this.start = options.start || 0;
    this.end = options.end || 100;
    this.duration = options.duration || 2000;
    this.easing = options.easing || 'easeOut';
    this.decimals = options.decimals || 0;
    this.prefix = options.prefix || '';
    this.suffix = options.suffix || '';
    
    this.startTime = null;
    this.animate();
  }
  
  easeOut(t) {
    return 1 - Math.pow(1 - t, 3);
  }
  
  linear(t) {
    return t;
  }
  
  animate(currentTime = null) {
    if (!this.startTime) this.startTime = performance.now();
    
    const elapsed = performance.now() - this.startTime;
    const progress = Math.min(elapsed / this.duration, 1);
    
    const ease = this.easing === 'easeOut' ? 
      this.easeOut(progress) : 
      this.linear(progress);
    
    const current = this.start + (this.end - this.start) * ease;
    
    this.element.textContent = 
      this.prefix + 
      current.toFixed(this.decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + 
      this.suffix;
    
    if (progress < 1) {
      requestAnimationFrame((t) => this.animate(t));
    }
  }
}

// 使用示例
const counter = document.querySelector('.counter');
new CounterAnimator(counter, {
  start: 0,
  end: 1000000,
  duration: 3000,
  decimals: 0,
  prefix: '',
  suffix: '人'
});
```

### 平滑数字滚动效果 (高级)

```javascript
class SmoothCounter {
  constructor(element) {
    this.element = element;
    this.currentValue = 0;
    this.targetValue = 0;
    this.animationFrame = null;
  }
  
  setTarget(value, duration = 2000) {
    this.startValue = this.currentValue;
    this.targetValue = value;
    this.startTime = performance.now();
    this.duration = duration;
    
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
    }
    
    this.animate();
  }
  
  animate() {
    const elapsed = performance.now() - this.startTime;
    const progress = Math.min(elapsed / this.duration, 1);
    
    // 使用 ease-out-quart 缓动
    const eased = 1 - Math.pow(1 - progress, 4);
    
    this.currentValue = this.startValue + (this.targetValue - this.startValue) * eased;
    this.updateDisplay();
    
    if (progress < 1) {
      this.animationFrame = requestAnimationFrame(() => this.animate());
    }
  }
  
  updateDisplay() {
    // 整数部分
    const intPart = Math.floor(this.currentValue);
    this.element.textContent = intPart.toLocaleString();
  }
}

// 使用示例
const counter = new SmoothCounter(document.querySelector('.counter'));
counter.setTarget(1234567, 3000);
```

### 与仪表盘集成

```javascript
// 同步更新仪表盘和数值
function updateGauge(value) {
  // 更新 CSS 变量
  gaugeElement.style.setProperty('--value', value / 100);
  
  // 更新数值显示
  counterAnimator.setTarget(value * 10000, 1000);
  
  // 更新指针角度 (270° 范围)
  const angle = -135 + (value * 270);
  needleElement.style.setProperty('--angle', `${angle}deg`);
}

// 示例：从 API 获取数据后更新
fetch('/api/civ-stats')
  .then(res => res.json())
  .then(data => {
    updateGauge(data.stability / 100);
  });
```

### Tailwind 集成

```html
<!-- 结合使用 -->
<div class="relative w-48 h-48">
  <!-- 仪表盘背景 -->
  <div class="absolute inset-0 rounded-full" 
       style="background: conic-gradient(#ff6b6b calc(var(--value) * 270deg), rgba(255,255,255,0.1) 0deg);
              transform: rotate(-135deg);">
  </div>
  
  <!-- 中心数值 -->
  <div class="absolute inset-0 flex items-center justify-center">
    <span class="text-3xl font-mono text-white counter"></span>
  </div>
</div>

<script>
  // 初始化动画
  const counterEl = document.querySelector('.counter');
  new CounterAnimator(counterEl, {
    end: 850000,
    duration: 3000,
    suffix: '人'
  });
</script>
```

---

## 性能优化总结

| 效果 | 性能风险 | 优化建议 |
|------|---------|---------|
| **文字辉光** | ⚠️ 高 | 避免频繁更新内容，使用伪元素替代 |
| **玻璃材质** | ⚠️ 中 | 限制同时使用数量 ≤ 3，添加 will-change |
| **机械仪表** | ✅ 低 | 纯 CSS conic-gradient，性能最佳 |
| **打字机** | ✅ 低 | 使用 steps() 而非逐帧，限制文本长度 |
| **数值跳变** | ✅ 低 | 使用 requestAnimationFrame，避免 DOM 频繁操作 |

### 通用优化技巧

```css
/* 1. 使用 will-change 提示浏览器优化 */
.animated-element {
  will-change: transform, opacity;
}

/* 2. 强制 GPU 加速 */
.gpu-accelerated {
  transform: translateZ(0);
  backface-visibility: hidden;
}

/* 3. 避免在动画中使用 backdrop-filter */
/* ❌ 不推荐 */
.animated-glass {
  animation: slide 1s;
  backdrop-filter: blur(10px);
}

/* 4. 使用 CSS 变量实现动态效果 (避免 JS 操作 DOM) */
.dynamic-gauge {
  background: conic-gradient(red calc(var(--value) * 100%), transparent 0);
}
```

```javascript
// 5. 批量 DOM 更新
function updateMultipleGauges(values) {
  requestAnimationFrame(() => {
    values.forEach((value, index) => {
      gauges[index].style.setProperty('--value', value);
    });
  });
}

// 6. 使用 IntersectionObserver 延迟动画
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('animate');
      observer.unobserve(entry.target);
    }
  });
});

document.querySelectorAll('.gauge').forEach(gauge => {
  observer.observe(gauge);
});
```

---

## 完整示例：复古硬件风格控制面板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>文明灵 CivSim - 控制面板</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          animation: {
            'typing': 'typing 3s steps(7) infinite',
            'blink': 'blink 0.75s step-end infinite',
            'glow': 'glow-pulse 2s ease-in-out infinite',
          },
          keyframes: {
            typing: { from: { width: '0' }, to: { width: '100%' } },
            blink: { 'from, to': { borderColor: 'transparent' }, '50%': { borderColor: '#ff6b6b' } },
            'glow-pulse': {
              '0%, 100%': { textShadow: '0 0 4px rgba(255,107,107,0.5)' },
              '50%': { textShadow: '0 0 8px rgba(255,107,107,0.8), 0 0 16px rgba(255,107,107,0.6)' },
            },
          },
        },
      },
    }
  </script>
  <style>
    .glass-panel {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    .gauge {
      --value: 0.75;
      background: 
        radial-gradient(rgba(0,0,0,0.4) 60%, transparent 61%),
        conic-gradient(#ff6b6b calc(var(--value) * 270deg), rgba(255,255,255,0.1) 0deg);
    }
  </style>
</head>
<body class="bg-gray-900 min-h-screen p-8">
  <div class="max-w-6xl mx-auto">
    <!-- 标题 -->
    <h1 class="text-4xl font-mono text-red-400 mb-8 animate-glow text-center">
      文明灵 CivSim
    </h1>
    
    <!-- 控制面板 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- 稳定性仪表 -->
      <div class="glass-panel rounded-2xl p-6">
        <h2 class="text-white font-mono mb-4 animate-typing">稳定性</h2>
        <div class="gauge w-48 h-48 rounded-full mx-auto mb-4" style="--value: 0.82;"></div>
        <div class="text-center text-2xl font-mono text-white counter" data-target="82"></div>
      </div>
      
      <!-- 人口统计 -->
      <div class="glass-panel rounded-2xl p-6">
        <h2 class="text-white font-mono mb-4">总人口</h2>
        <div class="text-center text-4xl font-mono text-green-400 counter" data-target="1250000"></div>
      </div>
      
      <!-- 科技水平 -->
      <div class="glass-panel rounded-2xl p-6">
        <h2 class="text-white font-mono mb-4">科技等级</h2>
        <div class="text-center text-2xl font-mono text-blue-400">青铜时代</div>
      </div>
    </div>
  </div>
  
  <script>
    class CounterAnimator {
      constructor(element, options = {}) {
        this.element = element;
        this.target = parseInt(element.dataset.target) || 0;
        this.duration = options.duration || 2000;
        this.startTime = null;
        this.animate();
      }
      
      animate(currentTime = null) {
        if (!this.startTime) this.startTime = performance.now();
        const progress = Math.min((performance.now() - this.startTime) / this.duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(this.target * eased);
        this.element.textContent = current.toLocaleString();
        if (progress < 1) requestAnimationFrame((t) => this.animate(t));
      }
    }
    
    document.querySelectorAll('.counter').forEach(el => new CounterAnimator(el));
  </script>
</body>
</html>
```

---

## 参考资料

- [CSS text-shadow 性能分析 - Jake Gordon](https://jakesgordon.com/writing/noglow/)
- [Glassmorphism 高级技巧 - Josh Comeau](https://www.joshwcomeau.com/css/backdrop-filter/)
- [纯 CSS 仪表盘实现](https://pepijndevos.nl/2023/12/24/lightweight-pure-css-gauge.html)
- [CountUp.js - 数值动画库](https://github.com/inorganik/countUp.js)
- [30 Seconds of Code - Typewriter Effect](https://www.30secondsofcode.org/css/s/typewriter-effect)

---

*最后更新：2026 年 2 月 28 日*
