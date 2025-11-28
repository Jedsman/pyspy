"""
Simple FastAPI service with LLM integration
This example shows how to build a basic API that talks to language models
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import anthropic
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Simple LLM API", version="1.0")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# Request/Response models
class ChatRequest(BaseModel):
    """Define what data the user sends"""
    message: str
    max_tokens: int = 1024


class ChatResponse(BaseModel):
    """Define what data we send back"""
    response: str
    model: str


# Simple health check endpoint
@app.get("/")
async def root():
    """Check if the API is running"""
    return {"status": "online", "message": "LLM API is running"}


# Main chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to Claude and get a response

    Example:
    POST /chat
    {
        "message": "What is FastAPI?",
        "max_tokens": 1024
    }
    """
    try:
        # Call the Anthropic API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=request.max_tokens,
            messages=[
                {"role": "user", "content": request.message}
            ]
        )

        # Extract the text response
        response_text = message.content[0].text

        return ChatResponse(
            response=response_text,
            model=message.model
        )

    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid API key")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# Simple streaming example
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream responses from Claude for real-time output
    This is more advanced - shows how to handle streaming
    """
    try:
        from fastapi.responses import StreamingResponse

        def generate():
            with client.messages.stream(
                model="claude-3-5-sonnet-20241022",
                max_tokens=request.max_tokens,
                messages=[{"role": "user", "content": request.message}]
            ) as stream:
                for text in stream.text_stream:
                    yield text

        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
