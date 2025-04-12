import json
import google.generativeai as genai
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

# Configure the API key globally
genai.configure(api_key=API_KEY)

# Initialize the Gemini Pro model
model = genai.GenerativeModel('gemini-2.0-flash-001')

def get_weather(location):
    url = f"https://wttr.in/{location}?format=%C+%t"
    response = requests.get(url)
    if response.status_code == 200:
        weather_data = response.text.strip()
        print(f"- Tool called for {location}: {weather_data}")
        return f"The current weather in {location} is {weather_data}"
    else:
        return f"Failed to get weather data: {response.status_code}"
   

available_tools = {
    "get_weather": {
        "fn": get_weather,
        "description": "Get the current weather for a given location",
    }
}

# Create a prompt with the system instructions and user query
system_prompt = f"""
You are an AI assistant who is expert in breaking down complex problems and then resolve the user query.
You work on start, plan, action, observe mode.
For the give user query, analyse the input and break down the problem step by step.
Based on the planning relevant tool from the available tools and based on the toll selection perform the action to invoke the tool.
And based on the tool output, observe the output and then return the final result.

Rules:
1. Follow the strict JSON output as per Output schema.
2. Always perform one step at a time and wait for next input
3. Carefully analyse the user query

Output Format:
{{ 
    step: "string", 
    content: "string", 
    function: "The function name if the step is action", 
    input: "Input parameter for the function if the step is action", 
}}

Available tools:
- get_weather: Get the current weather for a given location

Example:
Input: What is the weather in New York today?
Output: {{ step: "start", content: "The user is asking for the weather in New York today." }}
Output: {{ step: "plan", content: "Frm the available tools, get the current weather." }}
Output: {{ step: "action", function: "get_weather", input: "New York" }}
Output: {{ step: "observe", output: "25°C." }}
Output: {{ step: "result", content: "The weather in New York today is 25°C." }}
"""

messages = [{"role": "user", "parts": [{"text": system_prompt}]}]

while True:
    query = input("> ")

    messages.append({"role": "user", "parts": [{"text": f"Input: {query}\nOutput:"}]})

    # messages.append({"role": "model", "parts": [{
    #   "text": "{\n    \"step\": \"start\",\n    \"content\": \"The user is asking for the weather in Bengaluru.\"\n}"
    # }]})
    # messages.append({"role": "model", "parts": [{
    #   "text": "{\n    \"step\": \"plan\",\n    \"content\": \"From the available tools, get the current weather for Bengaluru.\",\n    \"function\": null,\n    \"input\": null\n}"
    # }]})
    # messages.append({"role": "model", "parts": [{
    #   "text":  "{\n    \"step\": \"action\",\n    \"content\": \"Calling the get_weather tool to get the weather for Bengaluru.\",\n    \"function\": \"get_weather\",\n    \"input\": \"Bengaluru\"\n}"
    # }]})
    # messages.append({"role": "model", "parts": [{
    #   "text":  "{\n    \"step\": \"observe\",\n    \"content\": \"Observed the output from the get_weather tool.\",\n    \"function\": null,\n    \"input\": null,\n    \"output\": \"28°C, Clear Sky\"\n}"
    # }]})
    # messages.append({"role": "model", "parts": [{
    #   "text": "{\n    \"step\": \"result\",\n    \"content\": \"The weather in Bengaluru is 28°C with clear sky.\"\n}"
    # }]})

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

