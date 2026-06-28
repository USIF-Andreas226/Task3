import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Set environmental variables for tests
os.environ["GROQ_MODEL"] = "openai/gpt-oss-120b"

from api import app

client = TestClient(app)

def test_health_endpoint():
    """Test the health check endpoint returns 200 and indicates healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data

def test_chat_endpoint():
    """Test sending a message to the chat endpoint."""
    payload = {
        "message": "Hello, I am interested in AI courses.",
        "user_id": "test_user_api",
        "conversation_id": "test_conv_api_123"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["user_id"] == "test_user_api"
    assert data["conversation_id"] == "test_conv_api_123"
    assert len(data["response"]) > 0

def test_get_tickets():
    """Test retrieving CRM lead tickets."""
    response = client.get("/api/tickets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_logs():
    """Test retrieving cost and usage logs."""
    response = client.get("/api/logs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
