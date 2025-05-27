## Dependencies
```sh
sudo apt install gcc-9 g++-9
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
sudo ./llvm.sh 14
sudo apt install llvm-14 llvm-14-dev llvm-14-tools clang-14 libclang-14-dev
sudo apt install bear
```

## Steps to follow
First copy the original code to the working directory
```sh
cp -r source <editorname>_<modelname>
```
Then run the agent with the prompt in `prompt.txt`, replacing `<dirname>` with `<editorname>_<modelname>`.

## Evaluation Criteria

User Experience:
- Stops when the error is gone: 2
- Stops only when the error is gone: 2
- Tries to reproduce the error first before debugging: 2
- Attempts to verify that the error is gone, after debugging (irrespective of whether this attempt is successful or not): 4

Correctness:
- Localizes the error*: 3
- Removes the segfault: 4
- General solution**: 3

*- The error is in `instrumentation.cpp`, at line 160.
```cpp
Value *RealFmt = Builder.CreateGlobalStringPtr("\"" + ArgName + "\"" + " : \"%.100s\", ");
```
The `%.100s` format specifier is the problem - the pointer could be null or freed, and there's no way to tell. Only solution is to replace `%.100s` with `%p`. Always print just the address, never the contents.

**- An example of a non-general solution is if the model finds the specific function with a null argument, and adds a check to exclude that function based on its name. This would work for this case, but if the function name were changed, it would break. We want a solution that works for all programs.