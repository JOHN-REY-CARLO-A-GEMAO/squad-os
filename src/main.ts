/**
 * main.ts — Squad OS Entry Point
 * 
 * Wires together Logger, Dispatcher, and a test ResearcherAgent.
 * Runs a live task dispatch to prove the swarm is connected.
 */

import { logger } from './tools/Logger.js';
import { Dispatcher } from './core/Dispatcher.js';
import { ResearcherAgent } from './agents/ResearcherAgent.js';

async function main() {
  console.log('\n🧠 Squad OS — Initializing...\n');

  // 1. Instantiate core components
  const dispatcher = new Dispatcher();
  await logger.info('Squad OS main.ts started');

  // 2. Spawn and register a ResearcherAgent
  const researcher = new ResearcherAgent('researcher-001', 'Researcher');
  dispatcher.registerAgent(researcher);

  // 3. Dispatch a test task
  console.log('📋 Dispatching test task...\n');

  try {
    const result = await dispatcher.dispatchTask(
      'Researcher',
      'Analyze latest OpenClaw documentation'
    );
    console.log(`\n🎯 Final result: ${result}`);
  } catch (err) {
    console.error('\n💥 Dispatch failed:', err);
  }

  // 4. Final status
  console.log('\n📊 Agent statuses:', dispatcher.listAgents());
  await logger.info(`Squad OS main.ts finished. Agents: ${JSON.stringify(dispatcher.listAgents())}`);
  console.log('\n✅ Squad OS pulse complete.\n');
}

main().catch(async (err) => {
  await logger.error(`Fatal: ${err.message}`);
  console.error('Fatal error:', err);
  process.exit(1);
});
