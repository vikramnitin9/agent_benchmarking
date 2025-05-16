# Read a json file passed as command line argument

import json
import sys

import tiktoken

top_dirs = ["creation/task1", "creation/task2", "creation/task3", "creation/task4", "creation/task5", \
            "refactoring/task1", "refactoring/task2", \
            "debugging/task1", "debugging/task2", "debugging/task3"]

cursor_dirs = ["cursor_gpt41", "cursor_claude37"]

if __name__ == "__main__":

    results = []
    for cursor_dir in cursor_dirs:
        for top_dir in top_dirs:
            # Read the markdown file
            with open(f"{top_dir}/{cursor_dir}/chat.md", "r") as f:
                lines = f.readlines()
            inputs = []
            outputs = []
            section = None
            for line in lines:
                if line.strip() == "---":
                    continue
                if "_**User**_" in line:
                    section = "input"
                elif "_**Assistant**_" in line:
                    section = "output"
                elif section == "input":
                    inputs.append(line.strip())
                elif section == "output":
                    outputs.append(line.strip())

            all_inputs = "\n".join(inputs)
            all_outputs = "\n".join(outputs)
            # Count the number of tokens in the inputs and outputs
            enc = tiktoken.encoding_for_model("gpt-4o")
            input_tokens = len(enc.encode(all_inputs))
            output_tokens = len(enc.encode(all_outputs))
            # Append the results to the list
            results.append({
                "task": top_dir,
                "model": cursor_dir,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            })
        
    # Write the results to a CSV
    with open("cursor_cost.csv", "w") as f:
        f.write("task,model,input_tokens,output_tokens\n")
        for result in results:
            f.write(f"{result['task']},{result['model']},{result['input_tokens']},{result['output_tokens']}\n")
        print("Written to cursor_cost.csv")