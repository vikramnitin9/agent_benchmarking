## Dependencies
- Docker (any version)

## Steps to follow
First copy the original code to the working directory
```sh
cp -r source <editorname>_<modelname>
```
Then run the agent with the prompt in `prompt.txt`, replacing `<dirname>` with `<editorname>_<modelname>`.

## Evaluation Criteria

User Experience:
- Stops when finished: 3
- Stops only when finished: 3
- Attempts to run and test the code (irrespective of whether this attempt is successful or not): 4*

*Note that it must run the code until "Translation Succeeded" is visible on the terminal. If it stops monitoring the output before that, deduct 1 point.

Correctness:
- Creates at least file per class (there are 6 classes): 4
- Syntactically correct: 2
- Functionally correct: 5