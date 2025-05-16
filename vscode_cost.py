# Read a json file passed as command line argument

import json
import sys

import tiktoken

top_dirs = ["creation/task1", "creation/task2", "creation/task3", "creation/task4", "creation/task5", \
            "refactoring/task1", "refactoring/task2", \
            "debugging/task1", "debugging/task2", "debugging/task3"]

vscode_dirs = ["vscode_gpt41", "vscode_claude37"]

if __name__ == "__main__":

    results = []
    for vscode_dir in vscode_dirs:
        for top_dir in top_dirs:
            # Read the json file
            with open(f"{top_dir}/{vscode_dir}/chat.json", "r") as f:
                data = json.load(f)
            inputs = []
            outputs = []
            for request in data['requests']:
                inputs.append(request['message']['text'])
                for response in request['response']:
                    if 'value' in response:
                        outputs.append(response['value'])
                    else:
                        match response['kind']:
                            case 'toolInvocationSerialized':
                                if "toolSpecificData" in response:
                                    outputs.append(str(response['toolSpecificData']))
                            case 'textEditGroup':
                                for edit in response['edits']:
                                    for sub_edit in edit:
                                        outputs.append(sub_edit['text'])
                            case 'confirmation':
                                outputs.append(response['message'])
                            case 'codeblockUri':
                                pass # No idea what this is
                            case 'inlineReference':
                                pass # No idea what this is
                            case 'progressTask':
                                pass
                            case _:
                                print(f"Warning: Unknown response kind {response['kind']} in {top_dir}/{vscode_dir}/chat.json")

            all_inputs = "".join(inputs)
            all_outputs = "".join(outputs)
            # Count the number of tokens in the inputs and outputs
            enc = tiktoken.encoding_for_model("gpt-4o")
            input_tokens = len(enc.encode(all_inputs))
            output_tokens = len(enc.encode(all_outputs))
            # Append the results to the list
            results.append({
                "task": top_dir,
                "model": vscode_dir,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            })
        
    # Write the results to a CSV
    with open("vscode_cost.csv", "w") as f:
        f.write("task,model,input_tokens,output_tokens\n")
        for result in results:
            f.write(f"{result['task']},{result['model']},{result['input_tokens']},{result['output_tokens']}\n")
        print("Written to vscode_cost.csv")