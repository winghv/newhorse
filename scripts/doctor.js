/**
 * Developer environment diagnostic script
 * Checks all prerequisites for running the Newhorse platform
 */
const { execSync } = require('child_process');
const fs = require('fs');
const net = require('net');
const path = require('path');

const rootDir = path.join(__dirname, '..');

// ANSI color helpers
const green = (s) => `\x1b[32m${s}\x1b[0m`;
const red = (s) => `\x1b[31m${s}\x1b[0m`;
const yellow = (s) => `\x1b[33m${s}\x1b[0m`;
const bold = (s) => `\x1b[1m${s}\x1b[0m`;
const dim = (s) => `\x1b[2m${s}\x1b[0m`;

const PASS = green('\u2713');
const FAIL = red('\u2717');
const WARN = yellow('!');

let passes = 0;
let failures = 0;
let warnings = 0;

function pass(label, detail) {
    passes++;
    console.log(`  ${PASS} ${label}${detail ? dim(` (${detail})`) : ''}`);
}

function fail(label, fix) {
    failures++;
    console.log(`  ${FAIL} ${label}`);
    if (fix) console.log(`    ${dim(`Fix: ${fix}`)}`);
}

function warn(label, detail) {
    warnings++;
    console.log(`  ${WARN} ${yellow(label)}${detail ? dim(` (${detail})`) : ''}`);
}

function runCmd(cmd) {
    try {
        return execSync(cmd, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
    } catch {
        return null;
    }
}

function parseVersion(str) {
    const match = str && str.match(/(\d+)\.(\d+)(?:\.(\d+))?/);
    if (!match) return null;
    return { major: parseInt(match[1]), minor: parseInt(match[2]), patch: parseInt(match[3] || 0) };
}

function checkPort(port) {
    return new Promise((resolve) => {
        const server = net.createServer();
        server.once('error', () => resolve(false));
        server.once('listening', () => {
            server.close(() => resolve(true));
        });
        server.listen(port, '0.0.0.0');
    });
}

async function main() {
    console.log();
    console.log(bold('  Newhorse Doctor'));
    console.log(dim('  Checking development environment...\n'));

    // --- Node.js ---
    console.log(bold('  Runtime'));
    const nodeVer = parseVersion(process.version);
    if (nodeVer && nodeVer.major >= 18) {
        pass('Node.js', process.version);
    } else {
        fail('Node.js >= 18 required', 'Install Node.js 18+ from https://nodejs.org');
    }

    // --- Python ---
    const pythonOut = runCmd('python3 --version');
    const pythonVer = parseVersion(pythonOut);
    if (pythonVer && (pythonVer.major > 3 || (pythonVer.major === 3 && pythonVer.minor >= 10))) {
        pass('Python', pythonOut.replace('Python ', ''));
    } else if (pythonOut) {
        fail(`Python >= 3.10 required, found ${pythonOut}`, 'Install Python 3.10+ from https://python.org');
    } else {
        fail('Python 3 not found', 'Install Python 3.10+ from https://python.org');
    }

    // --- npm ---
    const npmOut = runCmd('npm --version');
    if (npmOut) {
        pass('npm', npmOut);
    } else {
        fail('npm not found', 'npm should be bundled with Node.js — reinstall Node.js');
    }

    // --- Claude CLI ---
    const claudeOut = runCmd('claude --version');
    if (claudeOut) {
        pass('Claude CLI', claudeOut);
    } else {
        warn('Claude CLI not found', 'Optional — install from https://docs.anthropic.com');
    }

    // --- Ports ---
    console.log();
    console.log(bold('  Ports'));
    const port8080Free = await checkPort(8080);
    if (port8080Free) {
        pass('Port 8080 is free', 'API server');
    } else {
        fail('Port 8080 is in use', 'Stop the process using port 8080 or change API_PORT in .env');
    }

    const port3000Free = await checkPort(3000);
    if (port3000Free) {
        pass('Port 3000 is free', 'Web server');
    } else {
        fail('Port 3000 is in use', 'Stop the process using port 3000');
    }

    // --- Files ---
    console.log();
    console.log(bold('  Project'));
    const envPath = path.join(rootDir, '.env');
    if (fs.existsSync(envPath)) {
        pass('.env file exists');
    } else {
        fail('.env file missing', 'Run: npm run ensure:env');
    }

    const venvPath = path.join(rootDir, 'apps', 'api', 'venv');
    if (fs.existsSync(venvPath)) {
        pass('Python venv exists', 'apps/api/venv');
    } else {
        fail('Python venv missing', 'Run: npm run ensure:venv');
    }

    // --- Summary ---
    console.log();
    const parts = [green(`${passes} passed`)];
    if (failures > 0) parts.push(red(`${failures} failed`));
    if (warnings > 0) parts.push(yellow(`${warnings} warnings`));
    console.log(`  ${bold('Result:')} ${parts.join(', ')}`);

    if (failures > 0) {
        console.log(`\n  ${red('Fix the issues above before running')} ${bold('npm run dev')}`);
    } else {
        console.log(`\n  ${green('Ready to go!')} Run ${bold('npm run dev')} to start.`);
    }
    console.log();

    process.exit(failures > 0 ? 1 : 0);
}

main();
