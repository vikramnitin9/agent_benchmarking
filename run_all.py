from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import shlex

tasks = ['creation/task1', 'creation/task2', 'creation/task3', 'creation/task4', 'creation/task5',
         'debugging/task1', 'debugging/task2', 'debugging/task3',
         'refactoring/task1', 'refactoring/task2',
         'translation/task1']

agents = ['claude']

commands = {
    'copilot': 'COPILOT_EVENTS_LOG_DIRECTORY=$(pwd) copilot --allow-all-tools --allow-all-paths --prompt {prompt} 2>&1 | tee log.txt',
    'claude': 'ANTHROPIC_DEFAULT_SONNET_MODEL="claude-sonnet-4.5" ANTHROPIC_DEFAULT_HAIKU_MODEL="claude-haiku-4.5" claude -p --dangerously-skip-permissions {prompt} 2>&1 | tee log.txt',
    'codex': 'codex exec {prompt} 2>&1 | tee log.txt'
}

for task in tasks:
    for agent in agents:
        print(f"Running {task} with {agent}...")
        task_subfolder = Path.cwd() / task
        prompt_path = task_subfolder / "prompt.txt"
        prompt = prompt_path.read_text()

        # Check if there is a directory in workdir starting with "run_{agent}_"
        existing_runs = list(task_subfolder.glob(f"run_{agent}_*"))
        if existing_runs:
            print(f"Skipping {task} with {agent} as it has already been run.")
            continue

        working_dir = task_subfolder / f"run_{agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        source_dir = task_subfolder / "source"
        if not source_dir.exists():
            working_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Copy source folder to working directory
            shutil.copytree(source_dir, working_dir)

        prompt = shlex.quote(prompt)
        command = commands[agent].format(prompt=prompt)
        print(f"Executing command: {command} in {working_dir}")
        result = subprocess.run(command, shell=True, cwd=working_dir)
        # If the result is not successful, clean up the working directory
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}. Cleaning up {working_dir}.")
            # First copy the log out of the working directory
            log_path = working_dir / "log.txt"
            if log_path.exists():
                # The name of the new log file should be the working directory name with .txt extension
                new_log_path = task_subfolder / f"error_log_{working_dir.name}.txt"
                shutil.copy(log_path, new_log_path)
            shutil.rmtree(working_dir)