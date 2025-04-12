import os
import sys
import json
import subprocess
import glob
import re
from typing import List, Dict, Any, Optional
import requests
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
import argparse

# Initialize rich console for better terminal output
console = Console()

class AICodeAgent:
    def __init__(self, api_key: str, project_dir: str = None):
        """
        Initialize the AI Coding Agent
        
        Args:
            api_key: API key for the AI service
            project_dir: The directory of the project (defaults to current directory)
        """
        self.api_key = api_key
        self.project_dir = project_dir or os.getcwd()
        self.conversation_history = []
        self.file_cache = {}  # Cache of file contents to avoid re-reading
        self.api_endpoint = "https://api.anthropic.com/v1/messages"
        self.api_headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        self.model = "claude-3-opus-20240229"  # Can be configured
        
        # Create project directory if it doesn't exist
        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)
        
        console.print(Panel.fit("[bold green]AI Coding Agent initialized[/bold green]"))
        console.print(f"Working directory: [bold]{self.project_dir}[/bold]")
    
    def scan_project(self) -> Dict[str, Any]:
        """
        Scan the project directory to build context about the project structure
        
        Returns:
            Dict containing project structure information
        """
        project_structure = {
            "files": [],
            "directories": [],
            "language_stats": {},
            "package_files": []
        }
        
        # Walk through the directory
        for root, dirs, files in os.walk(self.project_dir):
            # Skip hidden directories and common directories to ignore
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__', 'dist', 'build']]
            
            relative_root = os.path.relpath(root, self.project_dir)
            if relative_root != '.':
                project_structure["directories"].append(relative_root)
            
            for file in files:
                # Skip hidden files
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(relative_root, file)
                if relative_root == '.':
                    file_path = file
                
                project_structure["files"].append(file_path)
                
                # Identify file extensions for language stats
                _, ext = os.path.splitext(file)
                if ext:
                    ext = ext[1:]  # Remove the dot
                    if ext in project_structure["language_stats"]:
                        project_structure["language_stats"][ext] += 1
                    else:
                        project_structure["language_stats"][ext] = 1
                
                # Identify package files
                if file in ['package.json', 'requirements.txt', 'Pipfile', 'Cargo.toml', 'go.mod']:
                    project_structure["package_files"].append(file_path)
        
        return project_structure
    
    def read_file(self, file_path: str) -> str:
        """
        Read the contents of a file
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            Contents of the file as a string
        """
        abs_path = os.path.join(self.project_dir, file_path)
        
        # Check cache first
        if file_path in self.file_cache:
            return self.file_cache[file_path]
        
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Cache the content
                self.file_cache[file_path] = content
                return content
        except Exception as e:
            console.print(f"[bold red]Error reading file {file_path}:[/bold red] {str(e)}")
            return ""
    
    def write_file(self, file_path: str, content: str) -> bool:
        """
        Write content to a file
        
        Args:
            file_path: Path where to write the file
            content: Content to write to the file
            
        Returns:
            True if successful, False otherwise
        """
        abs_path = os.path.join(self.project_dir, file_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        try:
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update cache
            self.file_cache[file_path] = content
            console.print(f"[green]Successfully wrote to {file_path}[/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Error writing to file {file_path}:[/bold red] {str(e)}")
            return False
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Execute a shell command in the project directory
        
        Args:
            command: Command to execute
            
        Returns:
            Dict with stdout, stderr, and return code
        """
        console.print(f"[yellow]Executing command:[/yellow] {command}")
        
        try:
            # Run the command in the project directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            console.print(f"[bold red]Error executing command:[/bold red] {str(e)}")
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": 1
            }
    
    def get_project_context(self) -> str:
        """
        Generate a context message about the current project state
        
        Returns:
            String containing project context
        """
        project_structure = self.scan_project()
        
        # Get contents of critical files
        file_contents = {}
        for file_path in project_structure["files"]:
            # Look for key project files that define structure
            if file_path in project_structure["package_files"] or file_path.endswith('.json') or file_path.endswith('.md'):
                file_contents[file_path] = self.read_file(file_path)
        
        # Include a limited number of code files for context
        for ext in ['py', 'js', 'ts', 'jsx', 'tsx', 'html', 'css']:
            matching_files = [f for f in project_structure["files"] if f.endswith(f'.{ext}')]
            for file_path in matching_files[:3]:  # Limit to 3 files per extension
                file_contents[file_path] = self.read_file(file_path)
        
        context = f"""
Project Structure:
- Files: {', '.join(project_structure["files"][:50])}
- Directories: {', '.join(project_structure["directories"][:20])}
- Language stats: {json.dumps(project_structure["language_stats"])}

Key file contents:
"""
        for file_path, content in file_contents.items():
            # Truncate very large files
            if len(content) > 2000:
                content = content[:2000] + "... (truncated)"
            context += f"\n--- {file_path} ---\n{content}\n"
        
        return context
    
    def parse_ai_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the AI response to extract code blocks and commands
        
        Args:
            response: Response from the AI
            
        Returns:
            Dict with files to write and commands to execute
        """
        actions = {
            "files": {},
            "commands": []
        }
        
        # Extract file blocks (```filename.ext ... ```)
        file_blocks = re.finditer(r'```(?:(.+?)\n)?([\s\S]+?)```', response)
        for match in file_blocks:
            filename = match.group(1)
            content = match.group(2)
            
            # Skip if it's just a language marker without a filename
            if not filename or filename in ['python', 'javascript', 'typescript', 'html', 'css', 'json', 'bash', 'sh']:
                continue
                
            # Clean up the filename
            filename = filename.strip()
            actions["files"][filename] = content
        
        # Extract terminal commands ($ command or > command)
        command_lines = re.finditer(r'(?:^\$|\n\$|\n>) (.*?)(?:\n|$)', response)
        for match in command_lines:
            command = match.group(1).strip()
            if command:
                actions["commands"].append(command)
        
        return actions
    
    def ask_ai(self, prompt: str, with_context: bool = True) -> str:
        """
        Send a prompt to the AI and get a response
        
        Args:
            prompt: User prompt to send to the AI
            with_context: Whether to include project context
            
        Returns:
            Response from the AI
        """
        messages = self.conversation_history.copy()
        
        # Add project context if requested
        if with_context:
            context = self.get_project_context()
            messages.append({
                "role": "user", 
                "content": f"Project context (for reference):\n{context}\n\nPlease keep this context in mind for the next request."
            })
            messages.append({
                "role": "assistant",
                "content": "I've reviewed the project context and will keep it in mind when answering your next question."
            })
        
        # Add the current prompt
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Call the AI API
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 4000
            }
            
            console.print("[yellow]Thinking...[/yellow]")
            response = requests.post(
                self.api_endpoint,
                headers=self.api_headers,
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            ai_response = result["content"][0]["text"]
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            return ai_response
        
        except Exception as e:
            console.print(f"[bold red]Error calling AI API:[/bold red] {str(e)}")
            return f"Error: {str(e)}"
    
    def implement_changes(self, actions: Dict[str, Any]) -> None:
        """
        Implement the changes suggested by the AI
        
        Args:
            actions: Dict with files to write and commands to execute
        """
        # Create/modify files
        for file_path, content in actions["files"].items():
            console.print(f"[blue]Writing file:[/blue] {file_path}")
            self.write_file(file_path, content)
        
        # Execute commands
        for command in actions["commands"]:
            result = self.execute_command(command)
            
            # Display command output
            if result["returncode"] == 0:
                console.print(f"[green]Command executed successfully:[/green] {command}")
                if result["stdout"]:
                    console.print(Syntax(result["stdout"], "bash", theme="monokai", line_numbers=False))
            else:
                console.print(f"[bold red]Command failed:[/bold red] {command}")
                if result["stderr"]:
                    console.print(Syntax(result["stderr"], "bash", theme="monokai", line_numbers=False))
    
    def run_interactive_session(self) -> None:
        """
        Run an interactive coding session with the user
        """
        console.print(Panel.fit("[bold green]🤖 AI Coding Agent Interactive Session[/bold green]"))
        console.print("Type your requests, and I'll help develop your project.")
        console.print("Type [bold]'exit'[/bold] or [bold]'quit'[/bold] to end the session.\n")
        
        while True:
            # Get user input
            user_input = console.input("[bold blue]> [/bold blue]")
            
            if user_input.lower() in ['exit', 'quit']:
                console.print("[yellow]Exiting session. Goodbye![/yellow]")
                break
            
            # Get AI response
            ai_response = self.ask_ai(user_input)
            
            # Display the response
            console.print(Panel(Markdown(ai_response), title="AI Response"))
            
            # Parse and implement changes
            actions = self.parse_ai_response(ai_response)
            
            # Confirm before implementing changes
            if actions["files"] or actions["commands"]:
                console.print("[yellow]The following changes will be made:[/yellow]")
                
                if actions["files"]:
                    console.print("[blue]Files to write:[/blue]")
                    for file_path in actions["files"].keys():
                        console.print(f"  - {file_path}")
                
                if actions["commands"]:
                    console.print("[blue]Commands to execute:[/blue]")
                    for command in actions["commands"]:
                        console.print(f"  - {command}")
                
                confirm = console.input("\n[bold yellow]Implement these changes? (y/n):[/bold yellow] ")
                if confirm.lower() == 'y':
                    self.implement_changes(actions)
                else:
                    console.print("[yellow]Changes were not implemented.[/yellow]")

def main():
    parser = argparse.ArgumentParser(description="AI Coding Agent - A terminal-based AI assistant for coding tasks")
    parser.add_argument("--api-key", type=str, help="API key for the AI service")
    parser.add_argument("--project-dir", type=str, help="Project directory (defaults to current directory)")
    
    args = parser.parse_args()
    
    # Get API key from args or environment variable
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] API key is required. Provide it with --api-key or set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)
    
    # Create and run the agent
    agent = AICodeAgent(api_key=api_key, project_dir=args.project_dir)
    agent.run_interactive_session()

if __name__ == "__main__":
    main()