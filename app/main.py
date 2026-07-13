from fastapi import FastAPI

# Initialize the FastAPI application
app = FastAPI(
    title="Real-Time Meeting Copilot",
    description="Backend for processing real-time meeting transcripts.",
    version="0.1.0"
)

# A simple health check endpoint to verify our server is running
@app.get("/health", tags=["Health"])
async def health_check():
    """
    This endpoint returns a simple JSON response.
    Because we use the 'async' keyword, FastAPI will run this non-blockingly!
    """
    return {"status": "healthy", "message": "Server is up and running!"}
