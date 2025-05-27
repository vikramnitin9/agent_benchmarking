## Dependencies
```sh
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
sudo ./llvm.sh 14
sudo apt install llvm-14 llvm-14-dev llvm-14-tools clang-14 libclang-14-dev
```

## Steps to follow
Run the agent with the prompt in `prompt.txt`, replacing `<dirname>` with `<editorname>_<modelname>`.

## Evaluation Criteria

User Experience:
- Stops when finished: 3
- Stops only when finished: 3
- Attempts to run and test the code (irrespective of whether this attempt is successful or not): 4

Correctness:
- Adds print statements in each function: 6
- Prints values of arguments: 2
- Prints return value: 2