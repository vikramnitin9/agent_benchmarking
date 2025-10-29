from pathlib import Path
from datetime import datetime
import shutil
import subprocess

tasks = ['creation/task1', 'creation/task2', 'creation/task3', 'creation/task4', 'creation/task5',
         'debugging/task1', 'debugging/task2', 'debugging/task3',
         'refactoring/task1', 'refactoring/task2']

agents = ['copilot', 'claude', 'codex']

commands = {
    'copilot': 'copilot --allow-all-tools --allow-all-paths --prompt "{prompt}" 2>&1 | tee log.txt',
    'claude': 'claude --dangerously-skip-permissions "{prompt}" 2>&1 | tee log.txt',
    'codex': 'codex exec "{prompt}" 2>&1 | tee log.txt'
}

for task in tasks:
    for agent in agents:
        print(f"Running {task} with {agent}...")
        subfolder = Path.cwd() / task
        prompt_path = subfolder / "prompt.txt"
        prompt = prompt_path.read_text()

        working_dir = subfolder / f"run_{agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        source_dir = subfolder / "source"
        if not source_dir.exists():
            working_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Copy source folder to working directory
            shutil.copytree(source_dir, working_dir)

        # Any quotes in the prompt need to be escaped
        prompt = prompt.replace('"', '\\"')
        prompt = prompt.replace('`', '\\`')
        command = commands[agent].format(prompt=prompt)
        print(f"Executing command: {command} in {working_dir}")
        result = subprocess.run(command, shell=True, cwd=working_dir)