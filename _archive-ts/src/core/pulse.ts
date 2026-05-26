/**
 * Squad OS Pulse — Heartbeat Script
 * 
 * A simple diagnostic that confirms the system is alive
 * and reports basic resource usage.
 * 
 * Run: npx tsx src/core/pulse.ts
 */

import { hostname, cpus, freemem, totalmem } from 'os';
import { readFile } from 'fs/promises';

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 ** 3);
  return `${gb.toFixed(2)} GB`;
}

function uptime(): string {
  const seconds = process.uptime();
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}

async function getCpuLoad(): Promise<string> {
  try {
    const stat = await readFile('/proc/stat', 'utf-8');
    const firstLine = stat.split('\n')[0];
    // /proc/stat format: cpu user nice system idle iowait irq softirq...
    const parts = firstLine.split(/\s+/).slice(1).map(Number);
    const total = parts.reduce((a, b) => a + b, 0);
    const idle = parts[3] || 0;
    const usage = total > 0 ? (((total - idle) / total) * 100).toFixed(1) : '0.0';
    return `${usage}%`;
  } catch {
    return 'unavailable';
  }
}

async function pulse(): Promise<void> {
  const timestamp = new Date().toISOString();
  const memFree = formatBytes(freemem());
  const memTotal = formatBytes(totalmem());
  const memUsedPct = (((totalmem() - freemem()) / totalmem()) * 100).toFixed(1);
  const cpuCount = cpus().length;
  const cpuLoad = await getCpuLoad();
  const uptimeStr = uptime();
  const host = hostname();

  console.log('╔════════════════════════════════════════╗');
  console.log('║     Squad OS Pulse: Online             ║');
  console.log('╠════════════════════════════════════════╣');
  console.log(`║  🕐 Timestamp : ${timestamp}     ║`);
  console.log(`║  🖥️  Hostname : ${host}              ║`);
  console.log(`║  🔢 CPU Cores: ${cpuCount}                        ║`);
  console.log(`║  📊 CPU Load : ${cpuLoad}                   ║`);
  console.log(`║  💾 Memory    : ${memUsedPct}% used (${memFree} free / ${memTotal})  ║`);
  console.log(`║  ⏱️  Uptime   : ${uptimeStr}              ║`);
  console.log('╚════════════════════════════════════════╝');
  console.log('\n✅ Squad OS is healthy and running.\n');
}

pulse().catch(console.error);
