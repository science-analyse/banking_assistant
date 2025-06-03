"""
Test the AI Banking Assistant
"""
import requests
import json

def test_ai_backend():
    """Test the AI backend API"""
    
    # Test health endpoint
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ AI Backend is healthy")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to AI backend: {e}")
        return False

def test_ai_chat():
    """Test AI chat functionality"""
    
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={
                "message": "What are the loan requirements?",
                "language": "en"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ AI Chat is working")
            print(f"   Response: {result['response'][:100]}...")
            print(f"   Model: {result['model_used']}")
            print(f"   Confidence: {result['confidence']}")
            return True
        else:
            print(f"❌ Chat test failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Chat test error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing AI Banking Assistant...")
    print("")
    
    backend_ok = test_ai_backend()
    if backend_ok:
        chat_ok = test_ai_chat()
        
        if chat_ok:
            print("")
            print("🎉 All tests passed! Your AI Banking Assistant is working!")
        else:
            print("")
            print("⚠️ AI chat needs troubleshooting")
    else:
        print("")
        print("❌ Backend not responding. Make sure to start it first:")
        print("   python run_ai_backend.py")
