## Dependencies
- Docker (any version)
- Python (any version)

## Steps to follow
Run the agent with the prompt in `prompt.txt`, replacing `<dirname>` with `<editorname>_<modelname>`.

## Evaluation Criteria

User Experience:
- Stops when finished: 3
- Stops only when finished: 3
- Attempts to run and test the code (irrespective of whether this attempt is successful or not): 4

Correctness:
- Runs the Python code inside the container: 5
- Writes the correct output ("Hello World") to log.txt: 5