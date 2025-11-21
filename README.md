# Scenarios for Agent Benchmarking

This folder contains 11 scenarios, divided into 3 categories:
- Creation: 5
- Refactoring: 2
- Debugging: 3
- Translation: 1

To run and evaluate a particular scenario, consult the `README.md` located in the subfolder of the scenario you would like to run.

# Setting up the editor

Run VSCode Agent in "Auto Approve" mode. Go to Settings (ctrl + ,) and search for "Auto Approve". Enable it.
Run Cursor in "Yolo" mode.

Sometimes, VSCode will ask you "Continue to iterate?". You can click the "Continue" button for this. But do not type any text response.
Similarly, Cursor also asks you whether to continue generation ("by default we stop after 25 LLM calls..."). You can click "continue" here, but do not enter any text response.

## Logging chats
Once you run a particular scenario, you can log the chat to preserve a record.
- In VSCode, make sure the log level for terminal and Github copilot chat are set to "Debug". Then click on "Chat: Export Chat", and save the json as `chat.json` in the scenario subfolder. For example, `creation/task1/vscode_gpt41/chat.json`.
- Cursor doesn't have a direct way to log chats. I used the extension SpecStory, which export chats in `.md` format. Save these as `chat.md` in the scenario subfolder. For example, `creation/task1/cursor_gpt41/chat.md`.

## Computing (approx) costs
After saving all the chat logs, you can run `python vscode_cost.py` and `python cursor_cost.py` to get a very approximate (and probably underestimated) number of tokens for each scenario/model/editor.

# Extra tasks
## Claude Code

```sh
# From MSBench-3P-Agents/msbench-claude-code
conda activate msbench
npm install && yes | npm run msbench --- --model claude-sonnet-4.5 --benchmark mfa.nlp.js-769
npm install && yes | npm run msbench --- --model claude-sonnet-4.5 --benchmark mfa.nlp.js-825
npm install && yes | npm run msbench --- --model claude-sonnet-4.5 --benchmark swebenchcsharp.dotnet__benchmarkdotnet-2106
npm install && yes | npm run msbench --- --model claude-sonnet-4.5 --benchmark gitgoodbench.alibaba_spring_cloud_alibaba_merge_0001
npm install && yes | npm run msbench --- --model claude-sonnet-4.5 --benchmark gitgoodbench.kotlin_dokka_merge_0005
```

## Codex CLI
```sh
# From MSBench-3P-Agents_shibani/msbench-codex-cli
conda activate msbench
yes | msbench-cli run --config msbench-config.yaml --model gpt-5-codex --benchmark mfa.nlp.js-769
yes | msbench-cli run --config msbench-config.yaml --model gpt-5-codex --benchmark mfa.nlp.js-825
yes | msbench-cli run --config msbench-config.yaml --model gpt-5-codex --benchmark swebenchcsharp.dotnet__benchmarkdotnet-2106
yes | msbench-cli run --config msbench-config.yaml --model gpt-5-codex --benchmark gitgoodbench.alibaba_spring_cloud_alibaba_merge_0001
yes | msbench-cli run --config msbench-config.yaml --model gpt-5-codex --benchmark gitgoodbench.kotlin_dokka_merge_0005
```

## Copilot CLI (with GPT-5-Codex)
```sh
conda activate msbench
yes | msbench-cli run --agent github-copilot-cli=shibanib-use-responses-aoai-20251031-015004 --model gpt-5-codex --benchmark mfa.nlp.js-769
yes | msbench-cli run --agent github-copilot-cli=shibanib-use-responses-aoai-20251031-015004 --model gpt-5-codex --benchmark mfa.nlp.js-825
yes | msbench-cli run --agent github-copilot-cli=shibanib-use-responses-aoai-20251031-015004 --model gpt-5-codex --benchmark swebenchcsharp.dotnet__benchmarkdotnet-2106
yes | msbench-cli run --agent github-copilot-cli=shibanib-use-responses-aoai-20251031-015004 --model gpt-5-codex --benchmark gitgoodbench.alibaba_spring_cloud_alibaba_merge_0001
yes | msbench-cli run --agent github-copilot-cli=shibanib-use-responses-aoai-20251031-015004 --model gpt-5-codex --benchmark gitgoodbench.kotlin_dokka_merge_0005
```