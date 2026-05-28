/**
 * main.ts — Squad OS Entry Point
 * 
 * Wires together Logger, Dispatcher, ResearcherAgent, and Daemon.
 * Runs in listening mode — watching data/inbox/ for tasks indefinitely.
 */

import { logger } from './tools/Logger.js';
import { Dispatcher } from './core/Dispatcher.js';
import { Daemon } from './core/Daemon.js';
import { ResearcherAgent } from './agents/ResearcherAgent.js';

async function main() {
  console.log('\n🧠 Squad OS — Initializing...\n');

  // Core components
  const dispatcher = new Dispatcher();
  const daemon = new Daemon(dispatcher);

  // Register agents
  const researcher = new ResearcherAgent('researcher-001', 'Researcher');
  dispatcher.registerAgent(researcher);

  // Start daemon in listening mode
  daemon.start();
  await logger.info('Squad OS started in Listening Mode — watching data/inbox/');
}

main().catch(async (err) => {
  await logger.error(`Fatal: ${err.message}`);
  console.error('Fatal error:', err);
  process.exit(1);
});
