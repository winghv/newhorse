/**
 * Run a Python command inside the API virtual environment.
 */
const { spawn } = require('child_process');
const path = require('path');

const apiDir = path.join(__dirname, '..', 'apps', 'api');
const isWindows = process.platform === 'win32';
const pythonPath = isWindows
    ? path.join(apiDir, 'venv', 'Scripts', 'python.exe')
    : path.join(apiDir, 'venv', 'bin', 'python');
const args = process.argv.slice(2);

if (args.length === 0) {
    console.error('Usage: node scripts/run-api-python.js <python args...>');
    process.exit(1);
}

const proc = spawn(pythonPath, args, {
    cwd: apiDir,
    stdio: 'inherit',
    env: { ...process.env },
});

proc.on('error', (err) => {
    console.error('Failed to start API Python command:', err);
    process.exit(1);
});

proc.on('exit', (code) => {
    process.exit(code || 0);
});
