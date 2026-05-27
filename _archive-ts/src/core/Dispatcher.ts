/**
 * Dispatcher.ts — Central task orchestration hub for Squad OS
 * 
 * Maintains a registry of agents and dispatches tasks to the
 * first available agent matching the requested role.
 */

import { BaseAgent } from '../agents/BaseAgent.js';
import { logger } from '../tools/Logger.js';

export class Dispatcher {
  private registry: Map<string, BaseAgent> = new Map();

  /**
   * Register an agent with the dispatcher.
   */
  registerAgent(agent: BaseAgent): void {
    if (this.registry.has(agent.id)) {
      logger.warn(`Dispatcher: Agent ${agent.id} already registered — skipping.`);
      return;
    }
    this.registry.set(agent.id, agent);
    logger.info(`Dispatcher: Registered agent [${agent.role}] ${agent.id}`);
  }

  /**
   * List all registered agents and their current status.
   */
  listAgents(): Array<{ id: string; role: string; status: string }> {
    return Array.from(this.registry.values()).map((a) => ({
      id: a.id,
      role: a.role,
      status: a.status,
    }));
  }

  /**
   * Dispatch a task to the first available agent with the matching role.
   * Sets agent to 'working', awaits completion, logs result, returns to 'idle'.
   * 
   * Throws if no agent with the given role is found.
   */
  async dispatchTask(role: string, task: string): Promise<string> {
    const agent = Array.from(this.registry.values()).find(
      (a) => a.role === role && a.status === 'idle'
    );

    if (!agent) {
      const available = Array.from(this.registry.values())
        .filter((a) => a.role === role)
        .map((a) => a.status);
      const msg = `Dispatcher: No idle agent found for role "${role}". Statuses: [${available.join(', ')}]`;
      logger.error(msg);
      throw new Error(msg);
    }

    agent.status = 'working';
    logger.info(`Dispatcher: [${agent.role}] ${agent.id} — started: "${task}"`);
    console.log(`\n📦 [Dispatcher] Task assigned to [${agent.role}] ${agent.id}`);

    try {
      const result = await agent.processTask(task);
      logger.info(`Dispatcher: [${agent.role}] ${agent.id} — completed: "${result}"`);
      console.log(`✅ [Dispatcher] ${result}`);
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      logger.error(`Dispatcher: [${agent.role}] ${agent.id} — failed: "${msg}"`);
      console.error(`❌ [Dispatcher] ${agent.role} ${agent.id} failed: ${msg}`);
      throw err;
    } finally {
      agent.status = 'idle';
    }
  }
}
