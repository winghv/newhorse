/**
 * Development script with auto-open browser
 */
const { spawn, exec } = require('child_process');
const port = process.env.PORT || '3999';

const proc = spawn('next', ['dev', '--turbo'], {
  stdio: 'inherit',
  shell: true,
  env: { ...process.env, PORT: port },
});

// Open browser after a short delay
setTimeout(() => {
  const url = `http://localhost:${port}`;
  const platform = process.platform;

  if (platform === 'darwin') {
    exec(`open ${url}`);
  } else if (platform === 'win32') {
    exec(`start ${url}`);
  } else {
    exec(`xdg-open ${url}`);
  }
}, 3000);

proc.on('exit', (code) => {
  process.exit(code || 0);
});
