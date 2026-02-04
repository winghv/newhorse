/**
 * Setup Python virtual environment script
 */
const { execSync, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const apiDir = path.join(__dirname, '..', 'apps', 'api');
const venvDir = path.join(apiDir, 'venv');

if (!fs.existsSync(venvDir)) {
    console.log('Creating Python virtual environment...');

    try {
        execSync('python3 -m venv venv', { cwd: apiDir, stdio: 'inherit' });
        console.log('Virtual environment created');

        // Install dependencies
        const pip = path.join(venvDir, 'bin', 'pip');
        execSync(`${pip} install -r requirements.txt`, { cwd: apiDir, stdio: 'inherit' });
        console.log('Dependencies installed');
    } catch (err) {
        console.error('Failed to create virtual environment:', err);
        process.exit(1);
    }
} else {
    console.log('Virtual environment already exists');
}
