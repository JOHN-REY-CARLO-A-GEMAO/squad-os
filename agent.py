import ollama
import re
import subprocess
import os

class CodeAgent:
    def __init__(self):
        # Using 7b for deeper analysis. Ensure you have 'ollama pull qwen2.5-coder:7b'
        self.model = "qwen2.5-coder:7b" 

    def _ask(self, system, user):
        response = ollama.chat(model=self.model, messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user}
        ])
        return response['message']['content']

    def read_project(self):
        context = ""
        files_read = []
        for file in os.listdir('.'):
            # Only read .py files, ignore this script and system/hidden files
            if file.endswith('.py') and file != 'agent.py' and not file.startswith('.'):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        context += f"\n--- FILE: {file} ---\n{f.read()}\n"
                        files_read.append(file)
                except Exception as e:
                    context += f"\n--- Could not read {file}: {e} ---\n"
        
        print(f"📄 Analyzing files: {', '.join(files_read) if files_read else 'None found.'}")
        return context

    def run_command(self, user_instruction):
        project_context = self.read_project()
        
        if not project_context:
            print("⚠️ No Python files found in this directory.")
            return

        print(f"🧠 AI is thinking... (Analyzing project context)")
        
        system_prompt = (
            "You are a Senior Staff Engineer. Your job is to critique and debug code. "
            "You are extremely thorough. You MUST find something to improve (security, logic, or readability). "
            "If you cannot find a bug, suggest a best-practice refactoring."
        )
        
        prompt = f"""
        Here is the project codebase:
        {project_context}
        
        Task: {user_instruction}
        
        Rules:
        1. Explain the bug or improvement clearly.
        2. Output the complete corrected code in a ```python block.
        3. If there is no bug, suggest a significant refactoring.
        """
        
        response = self._ask(system_prompt, prompt)
        
        # Extract and Save
        match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            print("\n✅ Suggestion found! Extracting code...")
            fixed_code = match.group(1)
            with open("suggested_fix.py", "w", encoding='utf-8') as f:
                f.write(fixed_code)
            print("💾 Saved suggestion to 'suggested_fix.py'. Review it before replacing your original file.")
            print("-" * 30)
            print(f"AI Feedback:\n{response.split('```')[0]}")
        else:
            print("\n❌ No code block found. AI output:")
            print(response)

if __name__ == "__main__":
    agent = CodeAgent()
    print("--- CodeAgent Ready ---")
    cmd = input("What would you like me to do? (e.g., 'Identify 1 bug in this project and fix it'): ")
    if cmd.strip():
        agent.run_command(cmd)
    else:
        print("No input provided.")