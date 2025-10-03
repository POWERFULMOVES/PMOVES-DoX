#!/usr/bin/env node
const { spawnSync } = require('child_process');
const path = require('path');

const mode = (process.argv[2] || 'cpu').toLowerCase();
const compose = mode === 'gpu' ? 'docker-compose.yml' : 'docker-compose.cpu.yml';
const repoRoot = path.resolve(__dirname, '..');

function run(cmd, args, opts={}) {
  return spawnSync(cmd, args, { stdio: 'inherit', cwd: opts.cwd || repoRoot, env: opts.env || process.env });
}

async function waitUrl(url, tries=60, delayMs=2000) {
  for (let i=0;i<tries;i++) {
    const res = spawnSync('node', ['-e', `fetch("${url}").then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))`], { stdio: 'inherit' });
    if (res.status === 0) return true;
    await new Promise(r=>setTimeout(r, delayMs));
  }
  return false;
}

(async () => {
  try {
    run('docker', ['compose', '-f', compose, '--compatibility', 'build', 'backend', 'frontend']);
    run('docker', ['compose', '-f', compose, '--compatibility', 'up', '-d', 'backend', 'frontend']);
    const okApi = await waitUrl('http://localhost:8000/health', 45, 2000);
    const okWeb = await waitUrl('http://localhost:3000/', 45, 2000);
    if (!okApi || !okWeb) process.exit(1);
    // install browsers and run tests
    run('npx', ['playwright', 'install', '--with-deps'], { cwd: path.join(repoRoot, 'ui-smoke') });
    const code = run('npx', ['playwright', 'test', '--reporter=line'], { cwd: path.join(repoRoot, 'ui-smoke'), env: { ...process.env, BASE_URL: 'http://localhost:3000' } }).status;
    process.exit(code);
  } finally {
    run('docker', ['compose', '-f', compose, '--compatibility', 'down', '-v']);
  }
})();

