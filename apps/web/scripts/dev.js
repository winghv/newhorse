/**
 * Development script with auto-open browser
 */
const { spawn, exec } = require('child_process');

const proc = spawn('next', ['dev', '--turbo'], {
  stdio: 'inherit',
  shell: true,
});

// Open browser after a short delay
setTimeout(() => {
  const url = 'http://localhost:3000';
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
