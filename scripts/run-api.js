/**
 * Run API server script
 */
const { spawn } = require('child_process');
const path = require('path');

require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const apiDir = path.join(__dirname, '..', 'apps', 'api');

// Check if virtual environment exists
const venvPython = path.join(apiDir, 'venv', 'bin', 'python');

const proc = spawn(venvPython, [
    '-m', 'uvicorn',
    'app.main:app',
    '--host', '0.0.0.0',
    '--port', process.env.API_PORT || '8080',
    '--reload'
], {
    cwd: apiDir,
    stdio: 'inherit',
    env: { ...process.env }
});

proc.on('error', (err) => {
    console.error('Failed to start API server:', err);
    process.exit(1);
});

proc.on('exit', (code) => {
    process.exit(code || 0);
});
