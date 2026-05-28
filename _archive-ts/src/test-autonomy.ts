/**
 * test-autonomy.ts — Integration test for Squad OS daemon autonomy
 * 
 * 1. Spawns main.ts (daemon) in the background
 * 2. Waits 2s, then drops a task JSON into data/inbox/
 * 3. Waits 10s for the daemon to pick it up, dispatch, and archive
 * 4. Kills the background process
 * 5. Reports results
 */

import { spawn } from 'child_process';
import { writeFile, readdir } from 'fs/promises';
import { join } from 'path';
import { readFile } from 'fs/promises';

const INBOX = 'data/inbox';
const ARCHIVE = 'data/archive';
const LOG_PATH = 'data/logs/squad.log';
const TASK_FILE = 'task-1.json';

async function readLog(): Promise<string> {
  try {
    return await readFile(LOG_PATH, 'utf-8');
  } catch {
    return '';
  }
}

async function main() {
  console.log('\n🧪 Squad OS — Autonomy Integration Test\n');
  console.log('='.repeat(45));

  // Spawn daemon
  console.log('\n1️⃣  Spawning daemon (npm start)...');
  const daemon = spawn('npx', ['tsx', 'src/main.ts'], {
    cwd: process.cwd(),
    stdio: 'pipe',
  });

  daemon.stdout?.on('data', (d) => process.stdout.write(d));
  daemon.stderr?.on('data', (d) => process.stderr.write(d));

  // Wait 2s, then drop a task
  console.log('\n2️⃣  Waiting 2s, then writing task to inbox...');
  await new Promise((r) => setTimeout(r, 2000));

  const payload = JSON.stringify({ role: 'Researcher', task: 'Analyze latest OpenClaw documentation' }, null, 2);
  await writeFile(join(INBOX, TASK_FILE), payload, 'utf-8');
  console.log(`   ✅ Wrote ${TASK_FILE} to ${INBOX}/`);

  // Wait 10s for daemon to process
  console.log('\n3️⃣  Waiting 10s for daemon to pick up, dispatch, and archive...\n');
  await new Promise((r) => setTimeout(r, 10_000));

  // Check archive
  console.log('4️⃣  Checking archive...');
  let archiveFiles: string[] = [];
  try {
    archiveFiles = await readdir(ARCHIVE);
  } catch {
    console.log('   ⚠️  Archive dir not found');
  }

  if (archiveFiles.includes(TASK_FILE)) {
    console.log(`   ✅ ${TASK_FILE} was moved to archive/`);
  } else {
    console.log(`   ❌ ${TASK_FILE} NOT found in archive/`);
    console.log('   Archive contents:', archiveFiles);
  }

  // Check inbox is empty
  let inboxFiles: string[] = [];
  try {
    inboxFiles = await readdir(INBOX);
  } catch {
    inboxFiles = [];
  }
  if (inboxFiles.length === 0) {
    console.log('   ✅ Inbox is empty — all tasks processed.');
  } else {
    console.log(`   ⚠️  Inbox still has: ${inboxFiles}`);
  }

  // Kill daemon
  console.log('\n5️⃣  Killing daemon...');
  daemon.kill('SIGTERM');
  await new Promise((r) => setTimeout(r, 500));
  console.log('   ✅ Daemon stopped.\n');

  // Print updated log
  console.log('='.repeat(45));
  console.log('\n📋 Updated squad.log:\n');
  const log = await readLog();
  console.log(log || '(empty)');

  console.log('\n✅ Autonomy test complete.\n');
}

main().catch(async (err) => {
  console.error('\n💥 Test failed:', err);
  process.exit(1);
});
