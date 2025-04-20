from fastapi import FastAPI
from ollama import Client
from fastapi import Body

app = FastAPI()

client = Client(
    host="http://localhost:11434",
)

client.pull("gemma3:1b", force=True)

@app.post("/api/ollama/{model_name}/chat")
async def chat(model_name: str, message: str = Body(..., description="Chat message")):
    """
    Chat with the specified Ollama model.
    """
    # Assuming you have a function to handle the chat logic
    response = await client.chat(
        model=model_name or "gemma3:1b",
        messages=[{"role": "user", "content": message}],
    )
    print(f'🤖 : {response}')
    return response['message']['content']

