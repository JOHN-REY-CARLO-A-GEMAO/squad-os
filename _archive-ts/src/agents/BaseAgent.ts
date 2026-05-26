/**
 * BaseAgent.ts — Abstract base class for Squad OS worker agents
 */

export type AgentStatus = 'idle' | 'working' | 'offline';

export abstract class BaseAgent {
  public readonly id: string;
  public readonly role: string;
  public status: AgentStatus = 'idle';

  constructor(id: string, role: string) {
    this.id = id;
    this.role = role;
  }

  /**
   * Process a task — subclasses define actual logic.
   * Returns a result string on completion.
   */
  abstract processTask(task: string): Promise<string>;

  /**
   * Simulates work with a delay. Override processTask in subclasses.
   */
  protected async simulateWork(task: string, ms: number = 2000): Promise<string> {
    await new Promise<void>((resolve) => setTimeout(resolve, ms));
    return `[${this.role}:${this.id}] Completed: "${task}"`;
  }
}
