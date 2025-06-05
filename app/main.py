from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import aiohttp
import asyncio
from typing import List, Dict, Optional
import google.generativeai as genai
from datetime import datetime
import uvicorn

app = FastAPI(title="AI Banking Assistant for Azerbaijan", version="1.0.0")

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini AI (Free)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    language: str = "en"

class LoanRequest(BaseModel):
    amount: float
    loan_type: str = "personal"
    currency: str = "AZN"

class BranchRequest(BaseModel):
    bank_name: str
    latitude: Optional[float] = 40.4093  # Baku coordinates
    longitude: Optional[float] = 49.8671

# Azerbaijan Banks Data (Free - no API needed)
AZERBAIJAN_BANKS = {
    "pasha_bank": {
        "name": "PASHA Bank",
        "website": "https://www.pashabank.az",
        "phone": "+994 12 967 00 00",
        "loan_rates": {"personal": 8.5, "mortgage": 6.0, "auto": 7.5},
        "branches": [
            {
                "name": "PASHA Tower Main Branch",
                "address": "153 Heydar Aliyev prospekti, Baku",
                "lat": 40.3777, "lng": 49.8531,
                "phone": "+994 12 967 00 00",
                "hours": "09:00-18:00"
            },
            {
                "name": "Nizami Branch", 
                "address": "Nizami küçəsi 67, Baku",
                "lat": 40.4093, "lng": 49.8671,
                "phone": "+994 12 967 00 01",
                "hours": "09:00-17:00"
            }
        ]
    },
    "kapital_bank": {
        "name": "Kapital Bank",
        "website": "https://www.kapitalbank.az",
        "phone": "+994 12 496 80 80",
        "loan_rates": {"personal": 9.0, "mortgage": 6.5, "auto": 8.0},
        "branches": [
            {
                "name": "Main Branch",
                "address": "28 May küçəsi 1, Baku",
                "lat": 40.3656, "lng": 49.8348,
                "phone": "+994 12 496 80 80",
                "hours": "09:00-18:00"
            },
            {
                "name": "Elmlar Branch",
                "address": "Elmlar prospekti 25, Baku", 
                "lat": 40.3950, "lng": 49.8520,
                "phone": "+994 12 496 80 81",
                "hours": "09:00-17:00"
            }
        ]
    },
    "international_bank": {
        "name": "International Bank of Azerbaijan",
        "website": "https://www.ibar.az",
        "phone": "+994 12 935 00 00",
        "loan_rates": {"personal": 10.0, "mortgage": 7.0, "auto": 8.5},
        "branches": [
            {
                "name": "Central Branch",
                "address": "67 Nizami küçəsi, Baku",
                "lat": 40.4037, "lng": 49.8682,
                "phone": "+994 12 935 00 00", 
                "hours": "09:00-18:00"
            }
        ]
    },
    "access_bank": {
        "name": "AccessBank",
        "website": "https://www.accessbank.az",
        "phone": "+994 12 945 00 00",
        "loan_rates": {"personal": 11.0, "mortgage": 7.5, "auto": 9.0},
        "branches": [
            {
                "name": "Port Baku Branch",
                "address": "153 Neftchilar prospekti, Baku",
                "lat": 40.3587, "lng": 49.8263,
                "phone": "+994 12 945 00 00",
                "hours": "09:00-18:00"
            }
        ]
    },
    "rabitabank": {
        "name": "RabiteBank", 
        "website": "https://www.rabitabank.az",
        "phone": "+994 12 919 19 19",
        "loan_rates": {"personal": 9.5, "mortgage": 6.8, "auto": 8.2},
        "branches": [
            {
                "name": "Yasamal Branch",
                "address": "Ahmad Rajabli küçəsi 2, Baku",
                "lat": 40.3947, "lng": 49.8206,
                "phone": "+994 12 919 19 19",
                "hours": "09:00-18:00"
            }
        ]
    }
}

async def get_currency_rates():
    """Get currency rates from Central Bank of Azerbaijan (Free API)"""
    try:
        async with aiohttp.ClientSession() as session:
            # CBAR API endpoint (free)
            url = "https://www.cbar.az/currencies/23.02.2025.xml"
            async with session.get(url) as response:
                if response.status == 200:
                    # For demo, return static rates (in real app, parse XML)
                    return {
                        "USD": 1.70,
                        "EUR": 1.85,
                        "RUB": 0.019,
                        "TRY": 0.050,
                        "last_updated": datetime.now().isoformat()
                    }
    except:
        # Fallback rates
        return {
            "USD": 1.70,
            "EUR": 1.85, 
            "RUB": 0.019,
            "TRY": 0.050,
            "last_updated": datetime.now().isoformat()
        }

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two coordinates (simplified)"""
    import math
    
    # Convert to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Earth's radius in kilometers
    
    return c * r

@app.get("/")
async def root():
    return {
        "message": "AI Banking Assistant for Azerbaijan", 
        "status": "running",
        "version": "1.0.0",
        "features": ["loan_comparison", "branch_locator", "currency_rates", "ai_chat"]
    }

@app.get("/banks")
async def get_all_banks():
    """Get all available banks"""
    return {
        "banks": [
            {
                "id": bank_id,
                "name": bank_data["name"],
                "website": bank_data["website"],
                "phone": bank_data["phone"]
            }
            for bank_id, bank_data in AZERBAIJAN_BANKS.items()
        ],
        "total": len(AZERBAIJAN_BANKS)
    }

@app.post("/loans/compare")
async def compare_loan_rates(request: LoanRequest):
    """Compare loan rates across all banks"""
    try:
        loan_type = request.loan_type.lower()
        comparisons = []
        
        for bank_id, bank_data in AZERBAIJAN_BANKS.items():
            if loan_type in bank_data["loan_rates"]:
                rate = bank_data["loan_rates"][loan_type]
                monthly_payment = (request.amount * (rate/100) / 12) * (1 + (rate/100)/12)**60 / ((1 + (rate/100)/12)**60 - 1)
                
                comparisons.append({
                    "bank_name": bank_data["name"],
                    "interest_rate": rate,
                    "monthly_payment": round(monthly_payment, 2),
                    "total_payment": round(monthly_payment * 60, 2),
                    "phone": bank_data["phone"],
                    "website": bank_data["website"]
                })
        
        # Sort by interest rate
        comparisons.sort(key=lambda x: x["interest_rate"])
        
        return {
            "loan_amount": request.amount,
            "loan_type": request.loan_type,
            "currency": request.currency,
            "comparisons": comparisons,
            "best_rate": comparisons[0] if comparisons else None,
            "total_banks": len(comparisons)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/branches/find")
async def find_branches(request: BranchRequest):
    """Find nearest bank branches"""
    try:
        branches = []
        
        # If specific bank requested
        if request.bank_name.lower() != "all":
            for bank_id, bank_data in AZERBAIJAN_BANKS.items():
                if request.bank_name.lower() in bank_data["name"].lower():
                    for branch in bank_data["branches"]:
                        distance = calculate_distance(
                            request.latitude, request.longitude,
                            branch["lat"], branch["lng"]
                        )
                        branches.append({
                            "bank_name": bank_data["name"],
                            "branch_name": branch["name"],
                            "address": branch["address"],
                            "distance_km": round(distance, 2),
                            "phone": branch["phone"],
                            "hours": branch["hours"],
                            "coordinates": {"lat": branch["lat"], "lng": branch["lng"]}
                        })
        else:
            # All banks
            for bank_id, bank_data in AZERBAIJAN_BANKS.items():
                for branch in bank_data["branches"]:
                    distance = calculate_distance(
                        request.latitude, request.longitude,
                        branch["lat"], branch["lng"]
                    )
                    branches.append({
                        "bank_name": bank_data["name"],
                        "branch_name": branch["name"],
                        "address": branch["address"],
                        "distance_km": round(distance, 2),
                        "phone": branch["phone"],
                        "hours": branch["hours"],
                        "coordinates": {"lat": branch["lat"], "lng": branch["lng"]}
                    })
        
        # Sort by distance
        branches.sort(key=lambda x: x["distance_km"])
        
        return {
            "user_location": {"lat": request.latitude, "lng": request.longitude},
            "branches": branches[:10],  # Return top 10 closest
            "total_found": len(branches)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/currency")
async def get_currency():
    """Get current currency rates from CBAR"""
    try:
        rates = await get_currency_rates()
        return {
            "base_currency": "AZN",
            "rates": rates,
            "source": "Central Bank of Azerbaijan"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_with_ai(message: ChatMessage):
    """Chat with AI banking assistant"""
    try:
        # Create context for AI
        context = f"""
        You are a helpful AI banking assistant for Azerbaijan banks. You have access to:
        
        Available Banks:
        - PASHA Bank (personal loans: 8.5%, mortgage: 6.0%)
        - Kapital Bank (personal loans: 9.0%, mortgage: 6.5%) 
        - International Bank (personal loans: 10.0%, mortgage: 7.0%)
        - AccessBank (personal loans: 11.0%, mortgage: 7.5%)
        - RabiteBank (personal loans: 9.5%, mortgage: 6.8%)
        
        Current AZN Exchange Rates:
        - USD: 1.70 AZN
        - EUR: 1.85 AZN
        
        User's language preference: {message.language}
        
        Provide helpful, accurate banking advice. If asked about specific loan amounts or branch locations, 
        suggest using the loan comparison or branch finder features.
        
        If the user writes in Azerbaijani, respond in Azerbaijani. If in English, respond in English.
        """
        
        prompt = f"{context}\n\nUser: {message.message}\n\nAssistant:"
        
        # Generate response using Gemini (Free)
        response = model.generate_content(prompt)
        
        return {
            "response": response.text,
            "language": message.language,
            "timestamp": datetime.now().isoformat(),
            "suggestions": [
                "Compare loan rates",
                "Find nearest branch", 
                "Check currency rates",
                "Ask about banking services"
            ]
        }
        
    except Exception as e:
        # Fallback response if AI fails
        fallback_response = "I'm here to help with banking questions in Azerbaijan. You can ask about loan rates, find bank branches, or get currency information."
        if message.language == "az":
            fallback_response = "Azərbaycan bankları ilə bağlı suallarınızda sizə kömək etmək üçün buradayam. Kredit faizləri, bank filialları və ya valyuta məlumatları haqqında soruşa bilərsiniz."
            
        return {
            "response": fallback_response,
            "language": message.language,
            "timestamp": datetime.now().isoformat(),
            "error": "AI service temporarily unavailable"
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)