## Dependencies
- Docker

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
- Attempts to run and test the code (irrespective of whether this attempt is successful or not): 4

Correctness:
- Localizes the bug*: 3
- Removes the runtime error: 2
- Preserves original functionality: 5

*The error is in `instrumentation.cpp`, line 59. `FullPathBuffer` is of the wrong type, rather, it must be converted into a pointer of type `i8*` before being passed to `Builder.CreateCall`.