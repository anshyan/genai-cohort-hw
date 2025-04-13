import subprocess
import json
import os

def execute_command(command):
    result = os.system(command)
    return result

def execute_shell_command(command):
    """
    Execute a shell command and return the output.
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"🔨 Successfully executed command: {command}")
            return result.stdout.strip()
        else:
            return f"Command failed with error: {result.stderr}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def create_project_structure(data):
    """
    Create a basic project structure for a Python project.
    """
    structure = json.loads(data)
    base_path = structure.get("base", "project")

    for path in structure.get("folders", []):
        os.makedirs(os.path.join(base_path, path), exist_ok=True)
        print(f"📁 Created folder: {path}")

    for file in structure.get("files", []):
        file_path = os.path.join(base_path, file)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write("")
        print(f"📄 Created file: {file}")

    print(f"🎉 Project structure successfully created at: {base_path}")
    return f"Project structure created at {base_path}"

def write_code_to_file(data):
    """
    Write the generated code to a file.
    """
    parsed = json.loads(data)
    path = parsed["path"]
    code = parsed["code"]

    with open(path, "w") as f:
        f.write(code)
    
    print(f"💾 Successfully wrote code to: {path}")
    return f"Code written to {path}"

def read_file(data):
    """
    Reads the contents of a file and returns it as a string.
    Expected input (JSON string): { "path": "path/to/file" }
    """
    import json
    try:
        parsed = json.loads(data)
        file_path = parsed["path"]

        with open(file_path, "r") as f:
            content = f.read()
        
        print(f"📖 Successfully read file: {file_path}")
        return content
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found."
    except Exception as e:
        return f"Error reading file: {str(e)}"