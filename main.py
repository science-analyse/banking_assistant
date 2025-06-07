from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Banking AI Assistant - Chat Only",
    description="AI-powered banking assistant with chat interface",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Import Gemini AI if available
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('gemini-pro')
        AI_AVAILABLE = True
        logger.info("Gemini AI initialized successfully")
    else:
        AI_AVAILABLE = False
        logger.warning("GEMINI_API_KEY not found. AI features will be limited.")
except ImportError:
    AI_AVAILABLE = False
    logger.warning("Gemini AI library not available. AI features will be limited.")

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

# AI Helper Functions
async def generate_ai_response(message: str) -> str:
    """Generate AI response using Gemini or fallback"""
    if not AI_AVAILABLE:
        return get_fallback_response(message)
    
    try:
        prompt = f"""You are a helpful banking AI assistant for Azerbaijan. You can help with:
        - General banking questions and advice
        - Banking services information
        - Financial literacy and tips
        - Currency and economic information about Azerbaijan
        
        Keep responses concise, helpful, and professional. Always prioritize user safety and accurate information.
        
        User message: {message}"""
        
        response = ai_model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        return get_fallback_response(message)

def get_fallback_response(message: str) -> str:
    """Fallback responses when AI is unavailable"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
        return "Hello! I'm your banking AI assistant. How can I help you today?"
    
    elif any(word in message_lower for word in ["help", "what", "how"]):
        return """I can help you with:
        
🏦 **Banking Services** - Information about accounts, loans, and services
💰 **Financial Advice** - Tips for saving, budgeting, and financial planning
🇦🇿 **Azerbaijan Banking** - Local banking information and regulations
💱 **Currency Information** - Exchange rates and currency-related questions
📱 **Digital Banking** - Online and mobile banking guidance

What specific banking topic would you like to know about?"""
    
    elif any(word in message_lower for word in ["thanks", "thank"]):
        return "You're welcome! Feel free to ask if you need any more banking assistance."
    
    else:
        return """I'm here to help with banking-related questions! I can assist with:

• Banking services and account information
• Financial planning and budgeting tips
• Currency and exchange information
• Digital banking guidance
• General financial advice

What would you like to know about?"""

# API Routes
@app.post("/api/chat")
async def chat_endpoint(message: ChatMessage):
    """Main chat endpoint with real AI integration"""
    try:
        response_text = await generate_ai_response(message.message)
        
        return {
            "response": response_text,
            "timestamp": datetime.now().isoformat(),
            "session_id": message.session_id or "default",
            "ai_powered": AI_AVAILABLE
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat service temporarily unavailable")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        ai_status = "operational" if AI_AVAILABLE else "unavailable"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "services": {
                "ai_chat": ai_status
            },
            "environment": "production" if not os.getenv("DEBUG") else "development"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# Page Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main chat page - now the only page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Banking AI Assistant"
    })

@app.get("/chat", response_class=HTMLResponse)
async def chat_redirect(request: Request):
    """Redirect /chat to home since we only have chat now"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Banking AI Assistant"
    })

# Handle old routes with redirects
@app.get("/locations")
async def locations_redirect():
    """Redirect old locations page to chat"""
    return JSONResponse(
        status_code=302,
        content={"message": "This feature is now available through chat"},
        headers={"Location": "/"}
    )

@app.get("/currency")
async def currency_redirect():
    """Redirect old currency page to chat"""
    return JSONResponse(
        status_code=302,
        content={"message": "This feature is now available through chat"},
        headers={"Location": "/"}
    )

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 page - redirect to home"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Banking AI Assistant",
        "error_message": "Page not found - you've been redirected to the main chat interface"
    })

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 page"""
    logger.error(f"Server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "Please try again later"}
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize app on startup"""
    logger.info("Banking AI Assistant (Chat Only) starting up...")
    
    if AI_AVAILABLE:
        logger.info("AI features enabled with Gemini")
    else:
        logger.info("AI features limited - using rule-based responses")
    
    logger.info("Banking AI Assistant ready!")

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Banking AI Assistant shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )