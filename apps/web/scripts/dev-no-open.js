/**
 * Development script without auto-opening the browser.
 */
const { spawn } = require('child_process');

const port = process.env.PORT || '3999';

const proc = spawn('next', ['dev', '--turbo'], {
  stdio: 'inherit',
  shell: true,
  env: { ...process.env, PORT: port },
});

proc.on('exit', (code) => {
  process.exit(code || 0);
});
