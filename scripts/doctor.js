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

function findSupportedPython() {
    const candidates = ['python3.12', 'python3.11', 'python3.10', 'python3'];
    for (const executable of candidates) {
        const output = runCmd(`${executable} --version`);
        const version = parseVersion(output);
        if (version && (version.major > 3 || (version.major === 3 && version.minor >= 10))) {
            return { executable, output };
        }
    }
    return null;
}

function ffmpegFilterAvailable(filtersOutput, filterName) {
    if (!filtersOutput) {
        return false;
    }
    const pattern = new RegExp(`^\\s*[.A-Z]+\\s+${filterName}(?:\\s|$)`, 'm');
    return pattern.test(filtersOutput);
}

function checkPort(port) {
    return new Promise((resolve) => {
        const server = net.createServer();
        server.once('error', (error) => {
            if (error && error.code === 'EADDRINUSE') {
                resolve({ status: 'in_use' });
                return;
            }
            if (error && error.code === 'EPERM') {
                resolve({ status: 'restricted', code: error.code });
                return;
            }
            resolve({ status: 'error', code: error && error.code ? error.code : 'UNKNOWN' });
        });
        server.once('listening', () => {
            server.close(() => resolve({ status: 'free' }));
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
    const pythonInfo = findSupportedPython();
    if (pythonInfo) {
        pass('Python', `${pythonInfo.output.replace('Python ', '')} via ${pythonInfo.executable}`);
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

    const ffmpegVersion = runCmd('ffmpeg -hide_banner -version');
    const ffmpegFilters = runCmd('ffmpeg -hide_banner -filters');
    if (ffmpegVersion) {
        pass('ffmpeg', ffmpegVersion.split('\n')[0].replace('ffmpeg version ', ''));
        if (ffmpegFilterAvailable(ffmpegFilters, 'drawtext')) {
            pass('ffmpeg drawtext filter');
        } else {
            warn('ffmpeg drawtext filter missing', 'Typewriter overlays and text burns will fall back');
        }
        if (ffmpegFilterAvailable(ffmpegFilters, 'subtitles')) {
            pass('ffmpeg subtitles filter');
        } else {
            warn('ffmpeg subtitles filter missing', 'Final renders will skip burned-in subtitles on this machine');
        }
    } else {
        warn('ffmpeg not found', 'Media render workflows need ffmpeg installed');
    }

    // --- Ports ---
    console.log();
    console.log(bold('  Ports'));
    const port8999Status = await checkPort(8999);
    if (port8999Status.status === 'free') {
        pass('Port 8999 is free', 'API server');
    } else if (port8999Status.status === 'restricted') {
        warn('Port 8999 check skipped', 'Current environment disallows bind probes; verify manually if needed');
    } else if (port8999Status.status === 'in_use') {
        fail('Port 8999 is in use', 'Stop the process using port 8999 or change API_PORT in .env');
    } else {
        warn('Port 8999 check inconclusive', port8999Status.code || 'unknown error');
    }

    const port3999Status = await checkPort(3999);
    if (port3999Status.status === 'free') {
        pass('Port 3999 is free', 'Web server');
    } else if (port3999Status.status === 'restricted') {
        warn('Port 3999 check skipped', 'Current environment disallows bind probes; verify manually if needed');
    } else if (port3999Status.status === 'in_use') {
        fail('Port 3999 is in use', 'Stop the process using port 3999');
    } else {
        warn('Port 3999 check inconclusive', port3999Status.code || 'unknown error');
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
    const venvPython = path.join(venvPath, 'bin', 'python');
    if (fs.existsSync(venvPath) && fs.existsSync(venvPython)) {
        const venvPythonOut = runCmd(`"${venvPython}" --version`);
        const venvPythonVer = parseVersion(venvPythonOut);
        if (venvPythonVer && (venvPythonVer.major > 3 || (venvPythonVer.major === 3 && venvPythonVer.minor >= 10))) {
            pass('Python venv is healthy', venvPythonOut.replace('Python ', ''));
        } else if (venvPythonOut) {
            fail(`Python venv is too old: ${venvPythonOut}`, 'Run: npm run ensure:venv');
        } else {
            fail('Python venv exists but interpreter is broken', 'Run: npm run ensure:venv');
        }
    } else {
        fail('Python venv missing', 'Run: npm run ensure:venv');
    }

    const dotVenvPath = path.join(rootDir, 'apps', 'api', '.venv');
    try {
        const stat = fs.lstatSync(dotVenvPath);
        if (stat.isSymbolicLink()) {
            const target = fs.readlinkSync(dotVenvPath);
            if (target === 'venv') {
                pass('.venv alias', 'apps/api/.venv -> venv');
            } else {
                warn('.venv points somewhere else', target);
            }
        } else {
            warn('.venv exists but is not an alias', 'apps/api/.venv');
        }
    } catch {
        warn('.venv alias missing', 'Optional but recommended for editor/tool compatibility');
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
