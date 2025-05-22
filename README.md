# Scenarios for Agent Benchmarking

This folder contains 10 scenarios, divided into 3 categories:
- Creation: 5
- Refactoring: 2
- Debugging: 3

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
