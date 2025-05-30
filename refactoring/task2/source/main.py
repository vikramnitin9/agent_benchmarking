import argparse
import shutil
import os
from pathlib import Path
import subprocess
import json
import networkx as nx
import datetime
from typing import List, Dict, Tuple

from models import get_model_from_name

def prRed(skk): print("\033[91m {}\033[00m" .format(skk))
def prGreen(skk): print("\033[92m {}\033[00m" .format(skk))
def prCyan(skk): print("\033[96m {}\033[00m" .format(skk))
def prYellow(skk): print("\033[93m {}\033[00m" .format(skk))
def prLightPurple(skk): print("\033[94m {}\033[00m" .format(skk))
def prLightGray(skk): print("\033[97m {}\033[00m" .format(skk))

class CompileException(Exception):
    pass

class RunException(Exception):
    pass

def run(command):

    try:
        result = subprocess.run(
            command,
            shell=True,
            timeout=120,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        if result.returncode != 0:
            exec_output = result.stderr.decode('utf-8', errors='ignore')
            if exec_output.strip() == '':
                exec_output = result.stdout.decode('utf-8', errors='ignore')
            raise RunException(exec_output)
    except subprocess.TimeoutExpired:
        raise RunException("Timeout")
    except subprocess.CalledProcessError as e:
        raise RunException(e.output.decode('utf-8', errors='ignore'))
    except Exception as e:
        raise RunException(str(e))

class SourceManager:

    def __init__(self, code_dir):
        self.code_dir = code_dir
        self.c_code_dir = Path(self.code_dir)/'c_src'
        self.cargo_bin_target = 'foo' # Placeholder
        self.bindgen_blocklist = Path(self.code_dir, 'bindgen_blocklist.txt')
        if not self.bindgen_blocklist.exists():
            self.bindgen_blocklist.touch()
    
    def get_bin_target(self):

        cwd = os.getcwd()
        os.chdir(self.c_code_dir)

        # Get the list of executable targets in the Makefile
        command = """make -pq | awk -F' ' '
        /^[a-zA-Z0-9_-]+:([^=]|$)/ {
            target=$1;
            gsub(/:/, "", target);
            if (target !~ /^\\./) targets[target]=1
        }
        /^\\.PHONY:/ { for (i=2; i<=NF; i++) { phony[$i]=1 } }
        END { for (t in targets) {
            if (!(t in phony) && (t != "Makefile")) { print t }
        }}'"""

        try:
            result = subprocess.run(
                command,
                shell=True,
                timeout=20,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            if result.returncode != 0:
                exec_output = result.stderr.decode('utf-8', errors='ignore')
                if exec_output.strip() == '':
                    exec_output = result.stdout.decode('utf-8', errors='ignore')
                raise RunException(exec_output)
        except subprocess.TimeoutExpired:
            raise RunException("Timeout")
        
        targets = result.stdout.decode('utf-8', errors='ignore').split('\n')
        targets = [target for target in targets if target != '']
        if len(targets) == 0:
            raise Exception("No executable targets found in Makefile.")
        elif len(targets) > 1:
            raise NotImplementedError(f"Multiple executable targets ({','.join(targets)}) are not supported.")
        else:
            target = targets[0]
            prGreen(f"Found executable target: {target}")
        os.chdir(cwd)
        return target
    
    def set_cargo_bin_target(self, target):
        # Set the target in the Cargo.toml file
        cargo_toml = Path(self.code_dir, 'Cargo.toml')
        with open(cargo_toml, 'r') as f:
            lines = f.readlines()
        inside_bin = False
        for i, line in enumerate(lines):
            if line.startswith('[[bin]]'):
                inside_bin = True
            elif inside_bin and line.startswith('name ='):
                # Found the name line, replace it
                lines[i] = f'name = "{target}"\n'
                break
        with open(cargo_toml, 'w') as f:
            f.writelines(lines)
        self.cargo_bin_target = target
    
    def get_static_analysis_results(self):
        functions_json_path = Path(self.code_dir)/'c_src'/'functions.json'
        return json.load(open(functions_json_path, 'r'))
    
    def get_executable(self):
        # Check if the executable exists
        executable = Path(self.code_dir, f'target/debug/{self.cargo_bin_target}')
        if not executable.exists():
            raise Exception("Executable not found. Please compile the code first.")
        return executable
    
    def compile(self, verbose=False):
        cwd = os.getcwd()
        cmd = 'cd {} && RUSTFLAGS="-Awarnings" cargo build'.format(self.code_dir)

        try:
            result = subprocess.run(
                        cmd,
                        shell=True,
                        timeout=60,
                        stderr=subprocess.STDOUT if verbose else subprocess.PIPE,
                        stdout=None if verbose else subprocess.PIPE,
                    )
            if result.returncode != 0:
                if not verbose:
                    compiler_output = result.stderr.decode('utf-8', errors='ignore')
                else:
                    compiler_output = result.stdout.decode('utf-8', errors='ignore')
                raise CompileException(compiler_output)

        except (subprocess.TimeoutExpired, TimeoutError):
            raise CompileException("Timeout")

        finally:
            os.chdir(cwd)
    
    def extract_body(self, func):
        fpath = Path(os.path.join(self.c_code_dir, func['filename']))
        start_line = func['startLine']
        start_col = func['startCol']
        end_line = func['endLine']
        end_col = func['endCol']

        with open(fpath, 'r') as f:
            lines = f.readlines()
        
        body = lines[start_line-1][start_col-1:]
        for i in range(start_line, end_line-1):
            body += lines[i]
        body += lines[end_line-1][:end_col]
        return body

    def insert_translation(self, func, translation):

        self.comment_out_in_c(func)
        self.insert_in_rust(translation)
        # Add the function to the bindgen blocklist
        shutil.copy(self.bindgen_blocklist, self.bindgen_blocklist.with_suffix('.old'))
        with open(self.bindgen_blocklist, 'a') as f:
            f.write(f"{func['name']}\n")
    
    def comment_out_in_c(self, func):

        fpath = Path(os.path.join(self.c_code_dir, func['filename']))
        start_line = func['startLine']
        start_col = func['startCol']
        end_line = func['endLine']
        end_col = func['endCol']

        with open(fpath, 'r') as f:
            lines = f.readlines()

        old_lines = lines.copy()
        lines = [line.rstrip() for line in lines]

        # We can't do a multiline comment because C doesn't support nested multiline comments
        lines[start_line-1] = lines[start_line-1][:start_col-1] + '// ' + lines[start_line-1][start_col-1:]
        for i in range(start_line, end_line-1):
            lines[i] = '// ' + lines[i]
        if lines[end_line-1][end_col:] != '':
            # Taking advantage of the fact that you can insert a linebreak anywhere in C, for the most part
            lines[end_line-1] = '// ' + lines[end_line-1][:end_col] + '\n' + lines[end_line-1][end_col:]
        else:
            lines[end_line-1] = '// ' + lines[end_line-1]
        
        with open(fpath, 'w') as f:
            f.write('\n'.join(lines))
        with open(fpath.with_suffix('.old'), 'w') as f:
            f.write(''.join(old_lines))

    def insert_in_rust(self, translation):

        function_trans = translation['func']
        wrapper = translation['wrapper']
        imports = translation['imports'] if 'imports' in translation else ''

        # Write the function translation to src/main.rs

        # Read the contents of the main.rs file
        main_rs = Path(self.code_dir, 'src/main.rs')
        contents = main_rs.read_text()
        old_contents = contents
        lines = contents.split('\n')

        inside_attribute = False
        for i, line in enumerate(lines):
            # Check if line starts with "#!" (inner attribute)
            # These could also extend over multiple lines, which is tricky
            # Like #![feature(try_blocks), 
            #       feature(never_type)]
            if inside_attribute:
                if ']' in line:
                    inside_attribute = False
                continue
            if line.startswith('#!'):
                if ']' not in line:
                    inside_attribute = True
                continue
            # There can be empty lines between inner attribute lines
            if line.strip() == '':
                continue
            break
        lines.insert(i, imports)
        new_contents = '\n'.join(lines)

        # Insert the function_trans and wrapper at the bottom
        new_contents += '\n' + function_trans + '\n' + wrapper

        main_rs.write_text(new_contents)
        # De-duplicate imports
        try:
            run(f'cd {self.code_dir} && rustfmt --config imports_granularity=Crate src/main.rs')
        except:
            prRed("Rustfmt failed. There may be a syntax error in the generated code.")

        with open(main_rs.with_suffix('.old'), 'w') as f:
            f.write(old_contents)
    
    def reset_func(self, func):
        prCyan("Resetting changes.")
        # Replace the ".rs" and ".c" files with the ".old" files if they exist
        original_c_file = Path(self.c_code_dir, func['filename'])
        original_rust_file = Path(self.code_dir, 'src/main.rs')
        for file in [original_c_file, original_rust_file, self.bindgen_blocklist]:
            if file.with_suffix('.old').exists():
                shutil.copy(file.with_suffix('.old'), file)
                file.with_suffix('.old').unlink()

    def cleanup(self):
        cwd = os.getcwd()
        os.chdir(self.code_dir)
        cmd = 'rm -rf target'
        try:
            run(cmd)
        except RunException as e:
            # Read e and look for strings that say:
            # rm: cannot remove '<filename>': Device or resource busy
            # Get a list of these filenames
            for line in str(e).split('\n'):
                if 'cannot remove' in line and "Device or resource busy" in line:
                    filename = line.split('\'')[1]
                    try:
                        run(f'fuser -k {filename}')
                    except:
                        pass
                    try:
                        run(f'rm -rf {filename}')
                    except:
                        pass
            try:
                run(cmd)
            except RunException as e:
                prRed(f"Failed to fully cleanup {self.code_dir}")
        os.chdir(cwd)


class TestManager:

    def __init__(self, test_scripts: List[Path], setup_script: Path, verbose: bool = False):
        self.test_scripts   = test_scripts
        self.setup_script   = setup_script
        self.status         = []
        self.verbose        = verbose

    def run_tests(self, executable: Path, stop_on_failure=False):
        prCyan("Running tests against the following executable: {}".format(executable))

        if self.setup_script is not None:
            # Run the setup script
            cmd = f'PATH="{executable.parent.absolute()}:$PATH" bash {self.setup_script}'
            try:
                run(cmd)
                if self.verbose:
                    prGreen(f"Setup script passed: {self.setup_script}")
            except RunException as e:
                if self.verbose:
                    prRed(f"Setup script failed: {self.setup_script}")
                raise e

        self.status = []
        # Run each test file
        for test_path in self.test_scripts:
            # Run the test file
            cmd = f'PATH="{executable.parent.absolute()}:$PATH" bash {test_path}'
            try:
                run(cmd)
                if self.verbose:
                    prGreen(f"Test passed: {test_path}")
                self.status.append({'test': test_path, 'status': 'passed'})
            except RunException as e:
                if self.verbose:
                    prRed(f"Test failed: {test_path}")
                self.status.append({'test': test_path, 'status': 'failed', 'error': str(e)})
                if stop_on_failure:
                    # Stop running tests if one fails
                    break
        return self.status
    
    def passed(self):
        # Check if all tests passed
        return all([s['status'] == 'passed' for s in self.status])
    
    def set_test_scripts(self, test_scripts):
        # Sometimes we want to use only a subset of the test scripts
        self.test_scripts = test_scripts

class Orchestrator:

    def function_iter(self, source_manager):
        static_analysis_results = source_manager.get_static_analysis_results()
        # Build call graph of functions
        self.call_graph = nx.DiGraph()
        for func in static_analysis_results:
            if 'calledFunctions' not in func:
                # These are functions which were in the AST but not in the LLVM IR
                continue
            self.call_graph.add_node('"{}"'.format(func['name']))
            for called_func in func['calledFunctions']:
                self.call_graph.add_edge('"{}"'.format(func['name']), '"{}"'.format(called_func))

        # We only want to translate functions that are reachable from main
        reachable_nodes = nx.descendants(self.call_graph, '"main_0"') | {'"main_0"'}
        subgraph = self.call_graph.subgraph(reachable_nodes)
        components = nx.weakly_connected_components(subgraph)
        assert len(list(components)) == 1

        try:
            func_ordering = list(reversed(list(nx.topological_sort(subgraph))))
        except nx.NetworkXUnfeasible:
            func_ordering = list(nx.dfs_postorder_nodes(subgraph, source='"main_0"'))
        
        func_ordering = [f.strip('"') for f in func_ordering]

        for func_name in func_ordering:
            funcs = [f for f in static_analysis_results if f['name'] == func_name]
            if len(funcs) == 0:
                continue
            func = funcs[0]
            yield func

class Translator:

    def __init__(self, model):
        self.model = get_model_from_name(model)
        self.conversation = []

    def construct_prompt_for_func(self, func):

        prompt = f'''Translate the following C function to idiomatic Rust:
```c
{func['body']}
```
As far as possible, use only safe Rust. Avoid raw pointers and unsafe function calls.
You can assume that all the structures and global variables already have definitions in Rust, and you do not need to redefine them.
Do not use any dummy code like "// Full implementation goes here", etc. All the code you write will be substituted directly into the codebase without a human reviewing it. So it should be functional and complete.
Feel free to change the function signature and modify the function body as needed.
If you need imports, you can add them in the <IMPORTS>...</IMPORTS> section. Do not provide them along with the function body.

Also provide a wrapper function that calls this function.
The wrapper function should have the *same* arguments and return type as the C function, except with C types replaced with their corresponding libc crate types.
For example, replace `int` with `libc::c_int`, `char*` with `*mut libc::c_char`, etc.
Also remember to use `#[no_mangle]` and `pub extern "C" fn ...` for the wrapper function.

The name of the Rust function should be `{func['name']}_rust` and the wrapper function should be `{func['name']}`.

Follow this format:

<IMPORTS>
Any imports you need for {func['name']}_rust and {func['name']}
</IMPORTS>

<FUNC>
fn {func['name']}_rust ...
</FUNC>

<WRAPPER>
#[no_mangle]
pub extern "C" fn {func['name']} ...
</WRAPPER>
'''
        return prompt
    
    def translate(self, func, source_manager, verbose=False):

        body = source_manager.extract_body(func)
        func['body'] = body

        translation_prompt = self.construct_prompt_for_func(func)

        self.conversation = [{'role': 'system', 'content': 'You are an intelligent code assistant'},
                            {'role': 'user', 'content': translation_prompt.strip()}]

        while True:
            try:
                prCyan("Calling LLM for translation")
                response = self.model.gen(self.conversation, top_k=1, temperature=0)[0]
                self.conversation.append({'role': 'assistant', 'content': response})
                prGreen("LLM response received")
                if verbose:
                    prLightGray(response)
                # Parse the response and extract the text between either
                # <FUNC>...</FUNC>, <IMPORT>...</IMPORT> or <WRAPPER>...</WRAPPER> tags
                if '<IMPORTS>\n' in response:
                    imports = response.split('<IMPORTS>\n')[1].split('</IMPORTS>')[0]
                else:
                    imports = ''
                
                if '<FUNC>\n' not in response:
                    prRed("Response does not contain <FUNC> tag. Trying again.")
                    continue
                if '<WRAPPER>\n' not in response:
                    prRed("Response does not contain <WRAPPER> tag. Trying again.")
                    continue
                function_trans = response.split('<FUNC>\n')[1].split('</FUNC>')[0]
                wrapper = response.split('<WRAPPER>\n')[1].split('</WRAPPER>')[0]

                # Remove any ```rust and ``` tags from imports, function_trans and wrapper
                imports = imports.replace('```rust', '').replace('```', '').strip()
                function_trans = function_trans.replace('```rust', '').replace('```', '').strip()
                wrapper = wrapper.replace('```rust', '').replace('```', '').strip()
                break
            except ModelException as e:
                prCyan("Model exception")
                prCyan(e)
                prCyan("Trying again")
                continue

        return {
            'func': function_trans,
            'wrapper': wrapper,
            'imports': imports,
        }
    
    def repair(self, result, source_manager, verbose=False):

        assert len(self.conversation) > 0, "Repair called before translation"

        if result['category'] == "Compile Error":
            prompt = ("The translation generated the following compile error:\n"
                    f"{result['message']}\n"
                    f"Please re-generate the translation of the function, wrapper function, and imports. "
                    f"Remember to follow the same format with <IMPORTS></IMPORTS>, <FUNC></FUNC>, and <WRAPPER></WRAPPER> tags.")
        elif result['category'] == "Test Failure":
            prompt = ("The translation failed tests. This was the command output:\n"
                    f"{result['message']}\n"
                    f"Please re-generate the translation of the function, wrapper function, and imports. "
                    f"Remember to follow the same format with <IMPORTS></IMPORTS>, <FUNC></FUNC>, and <WRAPPER></WRAPPER> tags.")
        else:
            raise NotImplementedError("Repair not implemented for this error type")
        
        self.conversation += [{'role': 'user', 'content': prompt.strip()}]

        while True:
            try:
                prCyan("Calling LLM for repair")
                response = self.model.gen(self.conversation, top_k=1, temperature=0)[0]
                self.conversation.append({'role': 'assistant', 'content': response})
                prGreen("LLM response received")
                if verbose:
                    prLightGray(response)
                # Parse the response and extract the text between either
                # <FUNC>...</FUNC>, <IMPORT>...</IMPORT> or <WRAPPER>...</WRAPPER> tags
                if '<IMPORTS>\n' in response:
                    imports = response.split('<IMPORTS>\n')[1].split('</IMPORTS>')[0]
                else:
                    imports = ''
                
                if '<FUNC>\n' not in response:
                    prRed("Response does not contain <FUNC> tag. Trying again.")
                    continue
                if '<WRAPPER>\n' not in response:
                    prRed("Response does not contain <WRAPPER> tag. Trying again.")
                    continue
                function_trans = response.split('<FUNC>\n')[1].split('</FUNC>')[0]
                wrapper = response.split('<WRAPPER>\n')[1].split('</WRAPPER>')[0]

                # Remove any ```rust and ``` tags from imports, function_trans and wrapper
                imports = imports.replace('```rust', '').replace('```', '').strip()
                function_trans = function_trans.replace('```rust', '').replace('```', '').strip()
                wrapper = wrapper.replace('```rust', '').replace('```', '').strip()
                break
            except ModelException as e:
                prCyan("Model exception")
                prCyan(e)
                prCyan("Trying again")
                continue

        return {
            'func': function_trans,
            'wrapper': wrapper,
            'imports': imports,
        }


class Validator:

    def __init__(self, compile_attempts=5):
        self.compile_attempts = 5

    def validate(self, func, translation, source_manager, test_manager):
        source_manager.insert_translation(func, translation)

        compile_success = False
        error_message = ''
        # Try 2 times to compile, in case there is a timeout or mysterious linker error
        for _ in range(2):
            try:
                source_manager.compile()
                compile_success = True
                break
            except CompileException as e:
                error_message = str(e)
                if "Timeout" in str(e):
                    prRed("Timeout. Trying again.")
                    continue
                elif "rust-lld: error:" in str(e):
                    prRed("Linker error. Cleaning up and trying again.")
                    source_manager.cleanup()
                    continue

        if not compile_success:
            return {"success": False,
                    "category": "Compile Error",
                    "message" : error_message}
        
        # If we get here, the code compiled successfully
        # Run the test suite
        executable = source_manager.get_executable()
        test_res = test_manager.run_tests(executable, stop_on_failure=True)
        if test_manager.passed():
            return {"success": True,
                "category": "",
                "message" : ""}
        else:
            failed_test = [res for res in test_res if res['status'] == 'failed'][0]
            return {"success": False,
                    "category": "Test Failure",
                    "message" : failed_test['error']}

class TranslationEngine:

    def __init__(self,
                dataset: dict,
                output_dir: str,
                model: str,
                num_attempts: int=5,
                verbose: bool=False):
        
        self.dataset = dataset
        self.verbose = verbose
        self.output_dir = Path(output_dir)
        self.setup() # Sets up self.source_manager
        self.num_attempts = num_attempts
        self.log_file = Path(self.output_dir, 'log.json')

        self.log = {'date': f"{datetime.datetime.now()}",
                    'attempts': num_attempts,
                    'model': model,
                    'results': []}

        with open(self.log_file, 'w') as f:
            f.write(json.dumps(self.log, indent=4))

    def setup(self):

        code_dir = Path("data")/Path(self.dataset["code_dir"])
        assert Path(code_dir).exists(), f"Code directory {code_dir} does not exist"

        prCyan("Translating code in directory: {}".format(code_dir.absolute()))

        # Creating new subdirectories
        # Create a folder called `rust_bench` in the parent directory of the code dir
        output_dir = Path(self.output_dir)
        if output_dir.exists():
            prRed(f"Directory {output_dir} already exists. Please remove it before running the script.")
            raise FileExistsError(f"Directory {output_dir} already exists. Please remove it before running the script.")
            
        shutil.copytree('rust_wrapper', output_dir)
        shutil.copytree(code_dir, output_dir/'c_src')

        code_dir = output_dir
        prCyan("Copied over the code to {}".format(code_dir.absolute()))
        self.source_manager = SourceManager(code_dir)
        target = self.source_manager.get_bin_target()
        self.source_manager.set_cargo_bin_target(target)

        try:
            self.source_manager.compile()
            prGreen("Compilation succeeded")
        except CompileException as e:
            prRed("Compilation failed")
            if self.verbose:
                prLightGray(e)
            raise CompileException(e)
        
        executable = self.source_manager.get_executable()
        prGreen("Generated executable: {}".format(executable))

        test_dir = Path("data")/Path(self.dataset["test_dir"])
        if test_dir != "":
            assert Path(test_dir).exists(), f"Code directory {test_dir} does not exist"
        test_paths = self.dataset["test_scripts"]
        test_paths = [Path(test_dir)/Path(t) for t in test_paths]
        for test_path in test_paths:
            assert Path(test_path).exists(), f"Test file {test_path} does not exist"
        if self.dataset["setup_script"] != "":
            setup_script = Path("data")/Path(self.dataset["setup_script"])
        else:
            setup_script = None
        
        self.test_manager = TestManager(test_paths, setup_script, verbose=self.verbose)
        test_statuses = self.test_manager.run_tests(executable)
        selected_tests = []
        for status in test_statuses:
            if status['status'] == "passed":
                prGreen("Test passed: {}".format(status['test']))
                selected_tests.append(status['test'])
            else:
                prRed(f"Test failed: {test_path}. This will be skipped")
        
        return 
    
    def run(self,
            orchestrator: Orchestrator,
            translator: Translator,
            validator: Validator):

        for func in orchestrator.function_iter(self.source_manager):
            prCyan("Translating function: {}".format(func['name']))
            translation = translator.translate(func, self.source_manager, self.verbose)
            result = validator.validate(func, translation, self.source_manager, self.test_manager)

            for i in range(self.num_attempts):
                prCyan(f"Attempt {i+1}/{self.num_attempts}")

                if result['success']:
                    prGreen("Translation succeeded")
                    break
                else:
                    prRed("Translation failed")
                    if self.verbose:
                        prLightGray(result['message'])
                    self.source_manager.reset_func(func)
                    if i == self.num_attempts - 1:
                        break
                    translation = translator.repair(result, self.source_manager, self.verbose)
                    result = validator.validate(func, translation, self.source_manager, self.test_manager)
            
            exit(0) # This is just for testing purposes, to stop after the first function
            
            self.log['results'].append({'function': func['name'],
                                   'results': "Success" if result['success'] else result['category']})
            with open(self.log_file, 'w') as f:
                f.write(json.dumps(self.log, indent=4))
        

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Translate code snippets to idiomatic Rust')
    parser.add_argument('--dataset',        type=str,   default='toy',          help='Dataset identifier from datasets.yaml')
    parser.add_argument('--model',          type=str,   default='gpt4o-mini',   help='Model to use for translation')
    parser.add_argument('--num_attempts',   type=int,   default=2,              help='Number of attempts to translate each function')
    parser.add_argument('--output_dir',     type=str,   default='output/translation', help='Directory to write the output')
    parser.add_argument('--verbose',        action='store_true',                help='Enable verbose output')
    args = parser.parse_args()

    datasets = json.loads(open('data/datasets.json').read())
    assert args.dataset in datasets, f"Dataset {args.dataset} not found in datasets.yaml"
    dataset = datasets[args.dataset]
    assert 'code_dir' in dataset, f"Code directory not specified for dataset {args.dataset}"

    orchestrator = Orchestrator()
    translator = Translator(args.model)
    validator = Validator(compile_attempts=5) # In case compilation times out, how many times to retry

    engine = TranslationEngine(dataset=dataset,
                               output_dir=args.output_dir,
                               model=args.model,
                               num_attempts=args.num_attempts,
                               verbose=args.verbose)

    engine.run(translator=translator,
               orchestrator=orchestrator,
               validator=validator)