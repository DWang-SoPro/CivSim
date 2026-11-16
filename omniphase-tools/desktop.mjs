// Source-checkout launcher for the single-player desktop edition.
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { existsSync, mkdirSync, realpathSync } from 'node:fs'
import net from 'node:net'
import os from 'node:os'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { setTimeout as delay } from 'node:timers/promises'

const game = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const windows = process.platform === 'win32'

export function desktopFiles(hostDirectory) {
  const host = realpathSync(hostDirectory)
  const gui = path.join(host, 'gui')
  const hostRequire = createRequire(path.join(gui, 'package.json'))
  const python = path.join(game, '.venv', windows ? 'Scripts/python.exe' : 'bin/python')
  const server = path.join(host, 'bin', 'dev', windows ? 'omniagent-server.exe' : 'omniagent-server')
  const main = path.join(gui, 'out', 'main', 'main.js')
  for (const file of [main, server, python]) {
    if (!existsSync(file)) throw new Error('缺少本机运行文件，请先按开发说明构建：' + file)
  }
  return { gui, main, server, python, hostRequire, electron: hostRequire('electron') }
}

async function freePort() {
  const probe = net.createServer()
  probe.listen(0, '127.0.0.1')
  await once(probe, 'listening')
  const port = probe.address().port
  await new Promise((resolve, reject) => probe.close(err => err ? reject(err) : resolve()))
  return port
}

export async function prepareDesktop(files, dataDirectory) {
  mkdirSync(path.resolve(dataDirectory), { recursive: true, mode: 0o700 })
  const state = realpathSync(dataDirectory)
  const home = path.join(state, 'platform')
  mkdirSync(home, { recursive: true, mode: 0o700 })
  const port = await freePort()
  const url = 'http://127.0.0.1:' + port
  const systemEnv = Object.fromEntries(['PATH','LANG','TMPDIR','TEMP','TMP','SystemRoot','COMSPEC','PATHEXT'].flatMap(key =>
    process.env[key] ? [[key, process.env[key]]] : []))
  const apiHost = spawn(files.server, ['--addr', '127.0.0.1:' + port], {
    cwd: home, stdio: ['ignore','pipe','inherit'],
    env: { ...systemEnv, HOME: home, USERPROFILE: home, APPDATA: home, LOCALAPPDATA: home,
      XDG_CONFIG_HOME: home, OMNIAGENT_DATABASE_PATH: path.join(home, 'platform.db'), OMNIAGENT_CLOUD_GATEWAY: '1' }
  })
  let lastError = ''
  apiHost.stdout.on('data', data => {
    for (const line of data.toString().split('\n')) {
      try { const row = JSON.parse(line); if (row.level === 'ERROR') lastError = String(row.error || row.msg) } catch {}
    }
  })
  let launchError
  apiHost.on('error', err => { launchError = err })
  const closed = once(apiHost, 'exit').catch(() => {})
  const stop = async () => {
    if (!apiHost.pid || apiHost.exitCode !== null || apiHost.signalCode !== null) return
    apiHost.kill()
    const kill = setTimeout(() => apiHost.kill('SIGKILL'), 4000)
    try { await closed } finally { clearTimeout(kill) }
  }
  try {
    let healthy = false
    for (let i = 0; i < 100; i++) {
      if (launchError || apiHost.exitCode !== null) throw launchError || new Error('万相本机服务提前退出：' + (lastError || apiHost.exitCode))
      try { healthy = (await fetch(url + '/health', { signal: AbortSignal.timeout(500) })).ok } catch {}
      if (healthy) break
      await delay(150)
    }
    if (!healthy) throw new Error('万相本机服务启动超时')
    const auth = await fetch(url + '/api/auth/token', { redirect: 'error' })
    if (!auth.ok) throw new Error('无法连接万相本机服务')
    const { token } = await auth.json()
    async function api(route, body) {
      const res = await fetch(url + '/api/v1' + route, { redirect:'error', method:body ? 'POST' : 'GET',
        headers:{ 'Content-Type':'application/json','X-Local-Token':token }, body:body && JSON.stringify(body) })
      if (!res.ok) throw new Error(route + ' ' + res.status + ' ' + (await res.text()).slice(0, 400))
      return res.json()
    }
    const appPath = realpathSync(path.join(game, 'omniphase-app'))
    const { projects } = await api('/projects')
    const project = projects.find(candidate => candidate.path === appPath)
      || await api('/projects', { name: '文明灵', path: appPath })
    const preview = await api('/projects/' + project.id + '/app-package')
    if (preview.id !== 'civsim' || !/^[0-9a-f]{64}$/.test(preview.digest)) throw new Error('文明灵应用包的身份验证失败')
    const { apps } = await api('/apps')
    const installed = apps.find(app => app.id === preview.id)
    if (installed?.digest !== preview.digest) {
      await api('/apps/install', { project_id:project.id, digest:preview.digest, expected_current_digest:installed?.digest || '' })
    }
    const profile = path.join(state,'desktop')
    const env = { ...systemEnv, HOME:os.homedir(), USERPROFILE:os.homedir(),
      ...Object.fromEntries(['APPDATA','LOCALAPPDATA','DISPLAY','WAYLAND_DISPLAY','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR'].flatMap(k=>process.env[k]?[[k,process.env[k]]]:[])),
      OMNIAGENT_DEV_USER_DATA:profile, OMNIAGENT_SERVER_URL:url,
      ...(process.env.CIVSIM_MODEL_MODE === 'enabled' ? Object.fromEntries(
        ['CIVSIM_MODEL_MODE','CIVSIM_MODEL_URL','CIVSIM_MODEL_NAME','CIVSIM_MODEL_API_KEY']
          .filter(key => process.env[key]).map(key => [key, process.env[key]])) : {}),
      OMNIPHASE_CIVSIM_DIGEST:preview.digest, OMNIPHASE_CIVSIM_PYTHON:files.python,
      OMNIPHASE_CIVSIM_ROOT:game, OMNIPHASE_CIVSIM_DATA:path.join(state,'campaigns') }
    return { env, args:[files.main,'--user-data-dir='+profile], stop, projectId:project.id, api }
  } catch (error) { await stop(); throw error }
}

async function main() {
  const [host, data] = process.argv.slice(2)
  if (!host) throw new Error('用法：node omniphase-tools/desktop.mjs <万相源码目录> [本机存档目录]')
  const files = desktopFiles(host)
  const state = data || path.join(os.homedir(), '.civsim-omniphase')
  const setup = await prepareDesktop(files, state)
  let desktop
  const quit = () => { desktop?.kill() }
  try {
    desktop = spawn(files.electron, setup.args, { env: setup.env, cwd: files.gui, stdio: 'inherit' })
    process.once('SIGINT', quit)
    process.once('SIGTERM', quit)
    const [code] = await once(desktop, 'exit')
    process.exitCode = code || 0
  } finally {
    process.removeListener('SIGINT', quit)
    process.removeListener('SIGTERM', quit)
    await setup.stop()
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error(error.message); process.exitCode = 1 })
}
