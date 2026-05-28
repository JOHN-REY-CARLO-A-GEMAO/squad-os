import shutil, re

src = r'D:\Downloads\squad-os\squad_os\orchestrator\manager.py'
bak = src + '.bak'

with open(src, 'r', encoding='utf-8') as f:
    code = f.read()

# Backup
shutil.copy2(src, bak)
print(f'Backup created: {bak}')

# Fix 2: Add Semaphore after _memory_written = False
code = code.replace(
    '_memory_written = False',
    '_memory_written = False\n        sem = asyncio.Semaphore(getattr(self.plan_mission_obj, \'suggested_parallelism\', 2))'
)

# Fix 2: Replace gather with capped_execute
old_gather = '''            results = await asyncio.gather(
                *[self.execute_task(idx, task_contexts[idx], mission_id, task_states, task_results, task_ids, tasks) for idx in ready_tasks],
                return_exceptions=True
            )'''
new_gather = '''            async def capped_execute(idx):
                async with sem:
                    return await self.execute_task(idx, task_contexts[idx], mission_id, task_states, task_results, task_ids, tasks)
            results = await asyncio.gather(*[capped_execute(idx) for idx in ready_tasks], return_exceptions=True)'''
code = code.replace(old_gather, new_gather)
print('Fix 2 applied: Semaphore + capped_execute')

# Fix 3: Circuit breaker in swarm agent_task
old_swarm = '''        async def agent_task(role: str):
            agent = self.active_agents.get(role)
            if not agent: return f"[{role}]: Agent not found."
            print(f"  🐝 [Swarm]: {role} is thinking...")
            result = await agent.execute_task(task_data.description, context)
            return f"[{role}]: {result.get('output', 'No output')}"

        outputs = await asyncio.gather(*[agent_task(r) for r in roles])'''
new_swarm = '''        async def agent_task(role: str):
            agent = self.active_agents.get(role)
            if not agent: return f"[{role}]: Agent not found."
            print(f"  🐝 [Swarm]: {role} is thinking...")
            try:
                result = await agent.execute_task(task_data.description, context)
                return f"[{role}]: {result.get('output', 'No output')}"
            except Exception as e:
                print(f"  ⚠️ [Swarm]: {role} failed: {e}")
                return f"[{role}]: FAILED - {str(e)}"

        outputs = await asyncio.gather(*[agent_task(r) for r in roles])'''
code = code.replace(old_swarm, new_swarm)
print('Fix 3 applied: circuit breaker in swarm')

# Fix 1: try/finally on load counter
old_load = '''        start_time = datetime.now()
        result = await agent.execute_task(task_data.description, context)
        elapsed = (datetime.now() - start_time).total_seconds()

        output_text = result.get("output", "Task completed without text summary.")'''
new_load = '''        start_time = datetime.now()
        try:
            result = await agent.execute_task(task_data.description, context)
        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            self.agent_load[task_data.assigned_agent_role] = max(0, self.agent_load.get(task_data.assigned_agent_role, 0) - 1)

        output_text = result.get("output", "Task completed without text summary.")'''
code = code.replace(old_load, new_load)
print('Fix 1 applied: try/finally on load counter')

with open(src, 'w', encoding='utf-8') as f:
    f.write(code)

print(f'Written: {src} ({len(code)} bytes)')
