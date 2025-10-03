#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');

const mode = (process.argv[2] || 'cpu').toLowerCase();
const compose = mode === 'gpu' ? 'docker-compose.yml' : 'docker-compose.cpu.yml';

const env = { ...process.env, SMOKE_COMPOSE: compose };
const repoRoot = path.resolve(__dirname, '..');

const py = process.env.PYTHON || 'python';
const script = path.join(repoRoot, 'smoke', 'run_smoke_docker.py');

const child = spawn(py, [script], { stdio: 'inherit', cwd: repoRoot, env });
child.on('exit', (code) => process.exit(code || 0));

