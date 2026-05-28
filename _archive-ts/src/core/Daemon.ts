/**
 * Daemon.ts — Squad OS Background Event Loop
 * 
 * Watches data/inbox/ for .json task files, dispatches them via the
 * Dispatcher, and moves processed files to data/archive/.
 */

import { readdir, readFile, rename } from 'fs/promises';
import { join, basename } from 'path';
import { Dispatcher } from './Dispatcher.js';
import { logger } from '../tools/Logger.js';

export interface InboxTask {
  role: string;
  task: string;
}

export class Daemon {
  private readonly inboxDir: string;
  private readonly archiveDir: string;
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private tickCount = 0;

  constructor(
    private readonly dispatcher: Dispatcher,
    inboxDir: string = 'data/inbox',
    archiveDir: string = 'data/archive'
  ) {
    this.inboxDir = inboxDir;
    this.archiveDir = archiveDir;
  }

  /** Start the event loop — runs every 5 seconds indefinitely. */
  start(): void {
    if (this.intervalId !== null) {
      logger.warn('Daemon: Already running — start() called twice.');
      return;
    }

    logger.info(`Daemon: Starting event loop (tick every 5s) — watching ${this.inboxDir}/`);
    console.log(`\n👁️  Daemon: Listening on ${this.inboxDir}/ every 5s\n`);

    this.intervalId = setInterval(() => this.tick(), 5_000);
  }

  /** Stop the event loop. */
  stop(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      logger.info('Daemon: Event loop stopped.');
      console.log('\n🛑 Daemon: Stopped.\n');
    }
  }

  /** Single tick: scan inbox, process any .json files found. */
  async tick(): Promise<void> {
    this.tickCount++;
    const ts = new Date().toISOString();
    logger.info(`Daemon: Tick #${this.tickCount} at ${ts}`);

    let files: string[] = [];
    try {
      files = await readdir(this.inboxDir);
    } catch (err) {
      logger.error(`Daemon: Could not read inbox dir — ${err}`);
      return;
    }

    const jsonFiles = files.filter((f) => f.endsWith('.json'));

    if (jsonFiles.length === 0) {
      console.log(`  [Tick #${this.tickCount}] No tasks in inbox.`);
      return;
    }

    console.log(`\n  [Tick #${this.tickCount}] Found ${jsonFiles.length} task file(s): ${jsonFiles.join(', ')}`);

    for (const file of jsonFiles) {
      await this.processFile(file);
    }
  }

  private async processFile(filename: string): Promise<void> {
    const inboxPath = join(this.inboxDir, filename);
    const archivePath = join(this.archiveDir, filename);

    let task: InboxTask;
    try {
      const raw = await readFile(inboxPath, 'utf-8');
      task = JSON.parse(raw) as InboxTask;
      if (!task.role || !task.task) {
        throw new Error('Invalid task shape — expected { role, task }');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      logger.error(`Daemon: Failed to read/parse ${filename} — ${msg}`);
      console.error(`  ❌ ${filename}: ${msg}`);
      return;
    }

    console.log(`  📋 Processing: [${task.role}] "${task.task}"`);

    try {
      const result = await this.dispatcher.dispatchTask(task.role, task.task);
      logger.info(`Daemon: Task "${task.task}" → "${result}"`);
      console.log(`  ✅ Done: ${result}`);

      // Move to archive
      await rename(inboxPath, archivePath);
      logger.info(`Daemon: Archived ${filename} → ${archivePath}`);
      console.log(`  📦 Archived: ${filename} → data/archive/`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      logger.error(`Daemon: Task dispatch failed for ${filename} — ${msg}`);
      console.error(`  ❌ Dispatch failed: ${msg}`);
    }
  }
}
