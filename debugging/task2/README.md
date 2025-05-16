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
- Stops when the error is gone: 3
- Stops only when the error is gone: 3
- Attempts to run and test the code (irrespective of whether this attempt is successful or not): 4*

Correctness:
- Identifies the cause of the issue (incorrect permissions for conda folder): 2
- Adds non-root user to Dockerfile: 3
- Produces working code: 5