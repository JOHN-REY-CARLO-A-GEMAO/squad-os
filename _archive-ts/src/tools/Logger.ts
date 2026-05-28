/**
 * Logger.ts — Squad OS Log Utility
 * Appends timestamped, level-tagged entries to data/logs/squad.log
 */

import { appendFile, mkdir } from 'fs/promises';
import { dirname } from 'path';

const LOG_PATH = 'data/logs/squad.log';

export type LogLevel = 'INFO' | 'WARN' | 'ERROR';

function timestamp(): string {
  return new Date().toISOString();
}

async function ensureLogDir(): Promise<void> {
  try {
    await mkdir(dirname(LOG_PATH), { recursive: true });
  } catch {
    // dir already exists
  }
}

export async function log(level: LogLevel, message: string): Promise<void> {
  await ensureLogDir();
  const entry = `[${timestamp()}] [${level}] ${message}\n`;
  await appendFile(LOG_PATH, entry, 'utf-8');
}

export const logger = {
  info: (msg: string) => log('INFO', msg),
  warn: (msg: string) => log('WARN', msg),
  error: (msg: string) => log('ERROR', msg),
};
