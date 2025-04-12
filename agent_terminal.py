import json
import google.generativeai as genai
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel('gemini-2.0-flash-001')

def execute_command(command):
    # result = os.system(command)
    # return result
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout.strip()
            print(f"- Command executed: {command}")
            return f"Command output: {output}"
        else:
            return f"Command failed with error: {result.stderr}"
    except Exception as e:
        return f"Error executing command: {str(e)}"


available_tools = {
    "execute_command": {
        "fn": execute_command,
        "description": "Execute a command on the operating system.",
    }
}

system_prompt = f"""
You are an AI terminal assistant who helps users execute shell commands and manage their system.
You work in start, plan, action, observe mode.
For the given user query, analyze the input and break down the request step by step.
Choose relevant tools from the available tools and execute them safely.

Rules:
1. Follow the strict JSON output format as per Output schema.
2. Always perform one step at a time and wait for next input.
3. Carefully analyze user queries for safety - avoid dangerous commands.
4. Explain what the command does before executing it.
5. Provide a clear explanation of the command output after execution.
6. Never execute commands that could harm the system or compromise security.
7. If a command seems unsafe, respond with a warning instead of executing it.
8. Provide helpful explanations about shell commands, their syntax, and usage.
9. For complex tasks, break them down into multiple simpler commands.

Output Format:
{{
    "step": "string",
    "content": "string",
    "function": "The function name if the step is action",
    "input": "Input parameter for the function if the step is action"
}}

Available tools:
- execute_command: Execute a shell command in the terminal

Example:
Input: List all files in the current directory
Output: {{ "step": "start", "content": "The user wants to list all files in the current directory." }}
Output: {{ "step": "plan", "content": "I'll use the 'ls' command to list all files in the current directory. The '-la' flag will show hidden files and detailed information." }}
Output: {{ "step": "action", "function": "execute_shell_command", "input": "ls -la" }}
Output: {{ "step": "observe", "output": "total 24\\ndrwxr-xr-x  5 user  staff   160 Apr 12 10:00 .\\ndrwxr-xr-x  3 user  staff    96 Apr 12 09:58 ..\\n-rw-r--r--  1 user  staff  1234 Apr 12 10:00 example.txt" }}
Output: {{ "step": "result", "content": "I executed the 'ls -la' command which displays all files (including hidden ones) with detailed information. The output shows you have a directory with one file named 'example.txt' that's 1234 bytes in size. The permissions, owner, group, and timestamp information are also displayed." }}

Example:
Input: How much disk space is available?
Output: {{ "step": "start", "content": "The user wants to know how much disk space is available on their system." }}
Output: {{ "step": "plan", "content": "I'll use the 'df' command with the '-h' flag to show disk space usage in a human-readable format." }}
Output: {{ "step": "action", "function": "execute_shell_command", "input": "df -h" }}
Output: {{ "step": "observe", "output": "Filesystem      Size  Used Avail Use% Mounted on\\n/dev/sda1        50G   20G   30G  40% /\\n/dev/sdb1       100G   30G   70G  30% /home" }}
Output: {{ "step": "result", "content": "I ran the 'df -h' command to check available disk space. You have approximately 30GB free on your root (/) partition, which is 60% of its 50GB total capacity. Your /home partition has 70GB available out of 100GB total capacity. The '-h' flag displays the sizes in a human-readable format with GB units instead of bytes." }}
"""

messages = [{"role": "user", "parts": [{"text": system_prompt}]}]

while True:
    query = input("> ")
    if query.lower() in ["exit", "quit"]:
        print("Exiting the terminal assistant.")
        break

    messages.append({"role": "user", "parts": [{"text": f"Input: {query}\nOutput:"}]})

    while True:
        response = model.generate_content(
            contents=messages,
            generation_config={
                "response_mime_type": "application/json",
                # Consider defining response_schema for stricter JSON output
            }
        )

        parsed_response = json.loads(response.candidates[0].content.parts[0].text)
        messages.append({"role": "model", "parts": [{"text": json.dumps(parsed_response)}]})

        if parsed_response.get("step") == "start" or parsed_response.get("step") == "plan":
            print(f"🧠: {parsed_response.get('content')}")
            continue

        if parsed_response.get("step") == "action":
            tool_name = parsed_response.get("function")
            tool_input_param = parsed_response.get("input")

            if tool_name in available_tools:
                output = available_tools[tool_name]['fn'](tool_input_param)
                # messages.append({"role": "model", "parts": [{"text": f"{{\"step\": \"observe\", \"output\": \"{result}\"}}" }]})
                messages.append({"role": "model", "parts": [{"text": json.dumps({ "steps": "observe", "output": output}) }]})
                continue

        if parsed_response.get("step") == "result":
            print(f"👀: {parsed_response.get('content')}")
            break

