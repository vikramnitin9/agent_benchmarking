## Dependencies
- g++ (any version)

## Steps to follow
Run the agent with the prompt in `prompt.txt`, replacing `<dirname>` with `<editorname>_<modelname>`.

## Evaluation Criteria

User Experience:
- Stops when finished: 3
- Stops only when finished: 3
- Attempts to run and test the code (irrespective of whether this attempt is successful or not): 4

Correctness:
- The script runs `make` to get the compilation database: 3
- Builds a list of phony targets: 2
- Correct output - excludes phony targets, .o files, etc, and includes all executable targets: 5