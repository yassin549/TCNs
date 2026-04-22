import { spawn } from 'node:child_process'

const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm'

const dataWatcher = spawn('node', ['./scripts/generate-dashboard-data.mjs', '--watch'], {
  stdio: 'inherit',
  cwd: process.cwd(),
})

const vite = spawn(npmCmd, ['run', 'dev:vite'], {
  stdio: 'inherit',
  cwd: process.cwd(),
})

function shutdown(code = 0) {
  dataWatcher.kill('SIGINT')
  vite.kill('SIGINT')
  process.exit(code)
}

dataWatcher.on('exit', (code) => {
  if (code && code !== 0) {
    shutdown(code)
  }
})

vite.on('exit', (code) => {
  shutdown(code ?? 0)
})

process.on('SIGINT', () => shutdown(0))
process.on('SIGTERM', () => shutdown(0))
