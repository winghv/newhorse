/**
 * Setup or repair the API Python virtual environment.
 */
const { execFileSync, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const apiDir = path.join(__dirname, '..', 'apps', 'api');
const venvDir = path.join(apiDir, 'venv');
const dotVenvDir = path.join(apiDir, '.venv');
const isWindows = process.platform === 'win32';
const pythonRelative = isWindows ? path.join('Scripts', 'python.exe') : path.join('bin', 'python');
const pipRelative = isWindows ? path.join('Scripts', 'pip.exe') : path.join('bin', 'pip');
const preferredPythonExecutables = ['python3.12', 'python3.11', 'python3.10', 'python3'];
const minPythonVersion = { major: 3, minor: 10 };
const devPackages = ['pytest', 'pytest-asyncio', 'pytest-cov', 'ruff'];
const requiredImports = ['fastapi', 'sqlalchemy', 'pytest'];

function inspectPython(executable) {
    const result = spawnSync(
        executable,
        [
            '-c',
            'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")',
        ],
        { encoding: 'utf-8' }
    );
    if (result.status !== 0) {
        return null;
    }

    const raw = (result.stdout || '').trim();
    const match = raw.match(/^(\d+)\.(\d+)\.(\d+)$/);
    if (!match) {
        return null;
    }

    return {
        executable,
        version: raw,
        major: Number(match[1]),
        minor: Number(match[2]),
    };
}

function isSupportedPython(info) {
    if (!info) {
        return false;
    }
    if (info.major > minPythonVersion.major) {
        return true;
    }
    return info.major === minPythonVersion.major && info.minor >= minPythonVersion.minor;
}

function resolvePythonExecutable() {
    for (const executable of preferredPythonExecutables) {
        const info = inspectPython(executable);
        if (isSupportedPython(info)) {
            return info;
        }
    }
    return null;
}

function inspectVenv(venvPath) {
    const pythonPath = path.join(venvPath, pythonRelative);
    if (!fs.existsSync(pythonPath)) {
        return { ok: false, reason: 'missing_python', pythonPath };
    }

    const info = inspectPython(pythonPath);
    if (!isSupportedPython(info)) {
        return {
            ok: false,
            reason: info ? `python_too_old_${info.version}` : 'broken_python',
            pythonPath,
        };
    }

    const importCheck = spawnSync(
        pythonPath,
        ['-c', `import ${requiredImports.join(', ')}`],
        { encoding: 'utf-8' }
    );
    if (importCheck.status !== 0) {
        return {
            ok: false,
            reason: 'missing_dependencies',
            pythonPath,
            version: info.version,
        };
    }

    return {
        ok: true,
        pythonPath,
        version: info.version,
    };
}

function backupPath(targetPath, label) {
    if (!fs.existsSync(targetPath)) {
        return null;
    }

    const timestamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14);
    const backup = `${targetPath}.${label}-${timestamp}.bak`;
    fs.renameSync(targetPath, backup);
    return backup;
}

function ensureDotVenvAlias() {
    if (isWindows) {
        return;
    }

    if (fs.existsSync(dotVenvDir) || fs.lstatSync(path.dirname(dotVenvDir)).isDirectory()) {
        try {
            const stat = fs.lstatSync(dotVenvDir);
            if (stat.isSymbolicLink() && fs.readlinkSync(dotVenvDir) === 'venv') {
                return;
            }
            backupPath(dotVenvDir, 'legacy');
        } catch (err) {
            if (err.code !== 'ENOENT') {
                throw err;
            }
        }
    }

    fs.symlinkSync('venv', dotVenvDir);
}

function installPackages(pipPath) {
    execFileSync(pipPath, ['install', '--upgrade', 'pip'], { cwd: apiDir, stdio: 'inherit' });
    execFileSync(pipPath, ['install', '-r', 'requirements.txt'], { cwd: apiDir, stdio: 'inherit' });
    execFileSync(pipPath, ['install', ...devPackages], { cwd: apiDir, stdio: 'inherit' });
}

function main() {
    const pythonInfo = resolvePythonExecutable();
    if (!pythonInfo) {
        console.error('Failed to find Python 3.10+ on this machine.');
        process.exit(1);
    }

    const current = inspectVenv(venvDir);
    if (current.ok) {
        console.log(`Python virtual environment is healthy (${current.version})`);
        ensureDotVenvAlias();
        return;
    }

    if (fs.existsSync(venvDir)) {
        const backup = backupPath(venvDir, 'stale');
        console.log(`Backed up existing venv -> ${backup}`);
    }

    console.log(`Creating Python virtual environment with ${pythonInfo.executable} (${pythonInfo.version})...`);
    execFileSync(pythonInfo.executable, ['-m', 'venv', 'venv'], { cwd: apiDir, stdio: 'inherit' });

    const pipPath = path.join(venvDir, pipRelative);
    installPackages(pipPath);
    ensureDotVenvAlias();

    const repaired = inspectVenv(venvDir);
    if (!repaired.ok) {
        console.error(`Virtual environment created but validation failed: ${repaired.reason}`);
        process.exit(1);
    }

    console.log(`Python virtual environment ready (${repaired.version})`);
}

main();
