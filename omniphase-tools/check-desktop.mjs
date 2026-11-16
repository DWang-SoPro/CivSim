// Exercises the normal install/open/composer path against a real local game process.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { desktopFiles, prepareDesktop } from './desktop.mjs'

const files = desktopFiles(process.argv[2])
const { _electron: electron, expect } = files.hostRequire('@playwright/test')
const state = await fs.mkdtemp(path.join(os.tmpdir(), 'civsim-desktop-check-'))
const evidence = process.argv[3] && path.resolve(process.argv[3])
if (evidence) await fs.mkdir(evidence, { recursive: true })
let app, runtime, page
async function launch() {
  runtime = await prepareDesktop(files, state)
  for (const key of Object.keys(runtime.env).filter(key => key.startsWith('CIVSIM_MODEL_'))) delete runtime.env[key]
  app = await electron.launch({ args:runtime.args, env:runtime.env, cwd:files.gui })
  await expect.poll(() => app.windows().some(p => p.url().includes('out/renderer'))).toBe(true)
  page = app.windows().find(p => p.url().includes('out/renderer'))
  await page.evaluate(() => {
    localStorage.setItem('i18nextLng','zh-CN')
    localStorage.setItem('omniagent-theme',JSON.stringify({state:{theme:'sopro',effectiveTheme:'sopro',customVars:{},systemThemeEnabled:false,systemPreference:'dark'},version:1}))
  })
  await page.reload()
  await page.locator('.oa-home-apps').getByRole('button', {name:'文明灵', exact:true}).click()
}
async function close() {
  try { if (app) await app.close() } finally { app = undefined; if (runtime) await runtime.stop(); runtime = undefined }
}
async function guest(code) {
  const id = await page.locator('webview[data-workspace-app-instance]:visible').first().evaluate(el => {
    try { return el.getWebContentsId() } catch { return null }
  }, undefined, {timeout: 6000})
  if (!id) return undefined
  return app.evaluate(({webContents}, {id, code}) => {
    const game = webContents.fromId(id)
    if (game?.getURL().startsWith('wanxiang-app://')) return game.executeJavaScript(code)
  }, {id, code})
}
const sel = id => '[data-testid="' + id + '"]'
const read = id => guest('document.querySelector(' + JSON.stringify(sel(id)) + ')?.textContent?.trim()')
const click = id => guest('document.querySelector(' + JSON.stringify(sel(id)) + ')?.click()')
async function captureWindow(destination) {
  if (process.platform !== 'darwin') {
    await page.screenshot({path:destination, caret:'hide', scale:'css'})
    return
  }
  // Capture the display compositor, which includes the independently rendered game.
  const windowId = await app.evaluate(({BrowserWindow}) => {
    const window = BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('out/renderer'))
    window.show()
    window.focus()
    return window.getMediaSourceId().split(':')[1]
  })
  assert.match(windowId, /^[0-9]+$/)
  await page.waitForTimeout(250)
  execFileSync('/usr/sbin/screencapture', ['-x','-o','-l',windowId,destination])
}
async function shot(name) {
  if (evidence) await captureWindow(path.join(evidence,name+'.png'))
}
async function verifyFloatingGameInput() {
  const embedded = page.locator('webview[data-workspace-app-instance]:visible')
  const glass = page.locator('[data-testid="workspace-composer-host"] .oa-composer--glass:visible')
  const viewport = await page.evaluate(() => ({height: innerHeight, width: innerWidth}))
  const box = await glass.boundingBox()
  const view = await embedded.boundingBox()
  assert.ok(box && view, 'game and composer need visible bounds')
  assert.ok(Math.abs(view.y + view.height - viewport.height) <= 1, 'game content should extend to the window bottom')
  assert.ok(box.y > view.y && box.y + box.height < view.y + view.height, 'the editor floats inside the game extent')

  // The marker lives inside the independent game process. Changing its scroll
  // position must alter the host glass itself, including across the process boundary.
  await guest(`(() => {
    const strip=document.createElement('div'); strip.id='civsim-glass-scroll-check'
    Object.assign(strip.style,{position:'fixed',inset:'0',overflowY:'auto',zIndex:2147483647})
    for (const color of ['#df2128','#1a61e2']) {
      const band=document.createElement('button')
      Object.assign(band.style,{display:'block',width:'100%',height:'170vh',background:color,border:'0',borderRadius:'0'})
      band.onclick=()=>strip.dataset.clicked=color
      strip.append(band)
    }
    document.body.append(strip)
  })()`)
  try {
    const beside = {x: Math.floor(box.x - 12), y: Math.floor(box.y + box.height / 2)}
    const frame = async (name) => {
      await page.mouse.move(0, 0)
      await guest('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
      const file=path.join(state,name+'.png')
      await captureWindow(file)
      return (await fs.readFile(file)).toString('base64')
    }
    const red = await frame('glass-red')
    await page.mouse.move(beside.x, beside.y)
    await page.mouse.wheel(0, Math.ceil(view.height*1.5))
    await expect.poll(()=>guest('document.getElementById("civsim-glass-scroll-check").scrollTop')).toBeGreaterThan(view.height)
    await page.mouse.click(beside.x, beside.y)
    await expect.poll(()=>guest('document.getElementById("civsim-glass-scroll-check").dataset.clicked')).toBe('#1a61e2')
    const blue = await frame('glass-blue')
    assert.deepEqual(await glass.boundingBox(),box)
    const [warm,cool] = await app.evaluate(({nativeImage},{frames,box,viewport}) => frames.map(encoded => {
      const image=nativeImage.createFromBuffer(Buffer.from(encoded,'base64'))
      const bytes=image.toBitmap(), {width,height}=image.getSize()
      const sx=width/viewport.width, sy=height/viewport.height
      function tone(from,to) {
        let sum=0,pixels=0
        for (let y=Math.floor((box.y+box.height*.36)*sy); y<(box.y+box.height*.65)*sy; y++) {
          for (let x=Math.floor(from*sx); x<to*sx; x++) {
            const n=4*(y*width+x)
            sum+=bytes[n+2]-bytes[n]; pixels++
          }
        }
        return sum/pixels
      }
      return {inside:tone(box.x+box.width*.62,box.x+box.width*.70),outside:tone(box.x-30,box.x-10)}
    }),{frames:[red,blue],box,viewport})
    console.log('game backdrop pixels', {red:warm,blue:cool})
    assert.ok(warm.outside-cool.outside>140,'the reference bands must visibly move in the real application window')
    assert.ok(warm.inside-cool.inside>60,'guest scrolling must visibly change the glass over it')
    console.log('PASS · 游戏画面铺底，玻璃两侧可点击和滚动，框内颜色随游戏转动')
  } finally { await guest('document.getElementById("civsim-glass-scroll-check")?.remove()') }
}
try {
  await launch()
  await expect.poll(()=>guest('document.querySelector(' + JSON.stringify(sel('civsim-start')) + ')?.disabled')).toBe(false)
  await shot('01-choose')
  await click('civsim-template-zhou')
  await expect.poll(()=>guest('document.querySelector(' + JSON.stringify(sel('civsim-start')) + ')?.disabled')).toBe(false)
  await click('civsim-start')
  await expect.poll(()=>read('civsim-turn')).toBe('0')
  const input = page.getByTestId('workspace-composer-host').getByRole('textbox')
  await input.fill('希望四海升平')
  await input.press('Enter')
  await expect.poll(()=>read('civsim-clarification')).toBeTruthy()
  await expect(input).toHaveValue('')
  assert.equal(await read('civsim-turn'),'0')
  await input.fill('兴修水利')
  await input.press('Enter')
  await expect(input).toHaveValue('')
  await page.getByTestId('workspace-home').click()
  await page.getByTestId('rail-app-civsim').click()
  await expect.poll(()=>read('civsim-turn'), {timeout:20000}).toBe('1')
  const first=await read('civsim-narrative')
  assert.ok(first && first.length>5,'first turn needs a chronicle')
  await shot('02-first-turn')
  await verifyFloatingGameInput()
  await input.fill('问史官：最近粮食怎样变化？')
  await input.press('Enter')
  await expect.poll(()=>read('civsim-answer')).toBeTruthy()
  assert.equal(await read('civsim-turn'),'1')
  await close()
  await launch()
  await expect.poll(()=>read('civsim-turn'), {timeout:20000}).toBe('1')
  assert.equal(await read('civsim-narrative'), first)
  const reopened=page.getByTestId('workspace-composer-host').getByRole('textbox')
  await reopened.fill('修建粮仓')
  await reopened.press('Enter')
  await expect.poll(()=>read('civsim-turn')).toBe('2')
  await shot('03-second-turn')
  if (evidence) {
    // A real, condensed history puts the reading material behind the floating field.
    for (const [turn,order] of [[3,'兴修水利'],[4,'修建粮仓'],[5,'兴修水利']]) {
      await reopened.fill(order)
      await reopened.press('Enter')
      await expect.poll(()=>read('civsim-turn')).toBe(String(turn))
    }
    await click('civsim-history')
    await app.evaluate(({BrowserWindow}) => {
      BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('out/renderer')).setContentSize(1080,640)
    })
    await expect.poll(()=>guest('document.documentElement.scrollHeight')).toBeGreaterThan(720)
    const capsule = await page.locator('.oa-composer--glass:visible').boundingBox()
    const viewport = await page.locator('webview[data-workspace-app-instance]:visible').boundingBox()
    const y = capsule.y + capsule.height / 2 - viewport.y
    await reopened.blur()
    await guest(`(() => {
      const line = document.querySelectorAll('.archive-entry p')[3].getBoundingClientRect()
      window.scrollBy(0, line.top + line.height/2 - ${y})
    })()`)
    await shot('04-国史与悬浮输入框')
  }
  console.log('PASS · 安装、选西周、澄清不推进、底栏下令、切换、问史不推进、完整重启、读取原回合、续玩第二回合')
} finally { await close(); await fs.rm(state,{recursive:true,force:true}) }
