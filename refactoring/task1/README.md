## Dependencies
```sh
sudo apt install g++-9
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
sudo ./llvm.sh 14
sudo apt install llvm-14 llvm-14-dev llvm-14-tools clang-14 libclang-14-dev
```

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
- Attempts to run and test the code (irrespective of whether this attempt is successful or not): 4

Correctness:
- Creates at least file per class (there are 4 classes): 4
- Updates CMakeLists.txt to reflect the new source files: 2
- Refactored code compiles: 5