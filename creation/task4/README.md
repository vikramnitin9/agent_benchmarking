## Dependencies
- Rust (any version)

## Steps to follow
Run the agent with the prompt in `prompt.txt`, replacing `<dirname>` with `<editorname>_<modelname>`.

## Evaluation Criteria

User Experience:
- Stops when finished: 3
- Stops only when finished: 3
- Attempts to run and test the code (irrespective of whether this attempt is successful or not): 4

Correctness:
- Creates both the counter and the test program: 2
- Counter compiles: 2
- Counter runs and produces a correct count: 3
- Counter implemented using Rust IR specifically: 3