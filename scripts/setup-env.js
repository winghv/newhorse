/**
 * Setup environment script
 */
const fs = require('fs');
const path = require('path');

const rootDir = path.join(__dirname, '..');
const envFile = path.join(rootDir, '.env');
const envExample = path.join(rootDir, '.env.example');

if (!fs.existsSync(envFile)) {
    if (fs.existsSync(envExample)) {
        fs.copyFileSync(envExample, envFile);
        console.log('Created .env from .env.example');
    } else {
        console.log('No .env.example found, skipping');
    }
} else {
    console.log('.env already exists');
}
