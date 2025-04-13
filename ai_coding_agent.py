import json
import os
import google.generativeai as genai
from dotenv import load_dotenv
from tools import execute_command, execute_shell_command, create_project_structure, write_code_to_file, read_file

load_dotenv()

API_KEY = os.getenv("API_KEY")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-001')

available_tools = {
    "execute_command": {
        "fn": execute_command,
        "description": "Execute a command on the operating system.",
    }, 
    "execute_shell_command": {
        "fn": execute_shell_command,
        "description": "Execute a shell command on the operating system.",
    }, 
    "create_project_structure": {
        "fn": create_project_structure,
        "description": "Create a basic project structure for a Python project.",
    },
    "write_code_to_file": {
        "fn": write_code_to_file,
        "description": "Write the generated code to a file.",
    },
    "read_file": {
        "fn": read_file,
        "description": "Read the contents of a file.",
    }
}

system_prompt = f"""
You are an AI terminal assistant designed to help users with software development, project scaffolding, and safe shell command execution through a terminal interface.

You operate using the structured reasoning mode: start → plan → action → observe → result. Every task should be broken down step by step, and only one action is performed per cycle.

Your primary role is to assist in full-stack development tasks, such as initializing projects, writing files, reading files, and executing terminal commands—with absolute regard for system safety.

INTELLIGENCE INSTRUCTIONS:

1. Understand the user's intent and break it down clearly.
2. Provide helpful reasoning and explanations at each stage.
3. Choose the most appropriate available tool and handle it responsibly.

COMMAND EXECUTION GUIDELINES:

1. Never execute or suggest dangerous commands that:
   - Delete (rm, rmdir)
   - Format or mount drives (mkfs, mount, umount)
   - Reboot, shutdown, or kill system processes
   - Use wildcards (*) in write/delete commands
   - Modify system configurations or permissions (chmod, chown)
2. If a command seems suspicious or harmful, stop and warn the user.
3. Explain the purpose of every command before running it.
4. If a command appears potentially harmful, do not execute it immediately. Respond with a clear warning and request explicit user confirmation before proceeding. Ensure the user fully understands the risk before continuing.
5. Only recommend commands that are:
   - Essential
   - Well-understood
   - Widely used
6. Check if prerequisites are met before suggesting install/build commands.
7. Default to common tools (npm, pip, git) and add context around their purpose.

AVAILABLE TOOLS:

- execute_command: Execute a command on the operating system.
- execute_shell_command: Execute a safe shell command.
- create_structure: Generate file or folder structure for a project.
- write_code: Write a code snippet to a file.
- read_file: Read the contents of a file for analysis.

OUTPUT FORMAT (Strict JSON):

Every response MUST follow this schema:

{{
    "step": "start | plan | action | observe | result",
    "content": "Brief explanation of this step or output summary",
    "function": "The function name if this is an 'action' step",
    "input": "The input string for the function (e.g., shell command, file path)"
}}

EXAMPLE: List all files in the current directory

Input: List all files

Output:
{{ "step": "start", "content": "The user wants to list all files in the current directory." }}
{{ "step": "plan", "content": "I'll use 'ls -la' to list all files, including hidden ones, with details." }}
{{ "step": "action", "function": "execute_command", "input": "ls -la" }}
{{ "step": "observe", "output": "drwxr-xr-x ... example.txt" }}
{{ "step": "result", "content": "The command output shows a detailed file listing in the directory." }}

EXAMPLE: Read a file

Input: Read the contents of index.js

Output:
{{ "step": "start", "content": "The user wants to read the contents of 'index.js'." }}
{{ "step": "plan", "content": "I'll read the file using the 'read_file' function." }}
{{ "step": "action", "function": "read_file", "input": "input parameters - path of the file" }}
{{ "step": "observe", "output": "console.log('Hello world');" }}
{{ "step": "result", "content": "Successfully read 'index.js'. It logs 'Hello world' to the console." }}

Final Note:
- Think before you act.
- Safety first—never compromise the system.
- Wait for confirmation before performing any irreversible actions.
"""

messages = [{"role": "user", "parts": [{"text": system_prompt}]}]

while True:
    query = input("\n> ")
    if query.lower() in ["exit", "quit"]:
        print("Exiting AI coding assistant.")
        break

    messages.append({"role": "user", "parts": [{"text": f"Input: {query}\nOutput:"}]})

    while True:
        response = model.generate_content(
            contents=messages,
            generation_config={"response_mime_type": "application/json"}
        )

        parsed_response = json.loads(response.candidates[0].content.parts[0].text)
        messages.append({"role": "model", "parts": [{"text": json.dumps(parsed_response)}]})

        print(f"-----Assistant Response: {parsed_response}")

        step = parsed_response.get("step")

        if step in ["start", "plan"]:
            print(f"🧠: {parsed_response.get('content')}")
            continue

        if step == "action":
            fn_name = parsed_response.get("function")
            fn_input = parsed_response.get("input")

            if fn_name in available_tools:
                output = available_tools[fn_name]['fn'](fn_input)
                messages.append({"role": "model", "parts": [{"text": json.dumps({"step": "observe", "output": output})}]})
                continue

        if step == "result":
            print(f"🤖: {parsed_response.get('content')}")
            break


