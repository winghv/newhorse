/**
 * Run Web server script
 */
const { spawn } = require('child_process');
const path = require('path');

const webDir = path.join(__dirname, '..', 'apps', 'web');

const proc = spawn('npm', ['run', 'dev:no-open'], {
    cwd: webDir,
    stdio: 'inherit',
    shell: true,
    env: { ...process.env }
});

proc.on('error', (err) => {
    console.error('Failed to start web server:', err);
    process.exit(1);
});

proc.on('exit', (code) => {
    process.exit(code || 0);
});
