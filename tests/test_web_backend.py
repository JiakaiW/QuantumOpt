"""Tests for the web backend API."""
import pytest
from fastapi.testclient import TestClient
import json
from pathlib import Path

from quantum_opt.web.backend.main import app, OptimizationConfig

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def test_config():
    """Create a test optimization configuration."""
    return {
        "parameter_config": {
            "x1": {"type": "scalar", "init": 0.0, "lower": -2.0, "upper": 2.0},
            "x2": {"type": "scalar", "init": 0.0, "lower": -2.0, "upper": 2.0}
        },
        "optimizer_config": {
            "optimizer": "CMA",
            "budget": 10,  # Small budget for testing
            "num_workers": 2
        },
        "execution_config": {
            "checkpoint_dir": "./test_checkpoints",
            "log_file": "./test_logs/test.log",
            "log_level": "INFO",
            "precompile": False  # Disable precompilation for faster tests
        }
    }

def test_start_optimization(client, test_config):
    """Test starting an optimization."""
    response = client.post("/api/optimization", json=test_config)
    assert response.status_code == 200
    data = response.json()
    assert "optimization_id" in data

def test_optimization_control(client, test_config):
    """Test optimization control endpoints."""
    # Start optimization
    response = client.post("/api/optimization", json=test_config)
    assert response.status_code == 200
    
    # Test pause
    response = client.post("/api/optimization/pause")
    assert response.status_code == 200
    assert response.json()["status"] == "paused"
    
    # Test resume
    response = client.post("/api/optimization/resume")
    assert response.status_code == 200
    assert response.json()["status"] == "resumed"
    
    # Test stop
    response = client.post("/api/optimization/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "stopped"

def test_websocket_connection(client, test_config):
    """Test WebSocket connection and updates."""
    with client.websocket_connect("/ws") as websocket:
        # Send a test message
        websocket.send_text("ping")
        
        # Start optimization
        client.post("/api/optimization", json=test_config)
        
        # Wait for and verify updates
        try:
            data = websocket.receive_json()
            assert "type" in data
            assert "data" in data
            if data["type"] == "ITERATION_COMPLETE":
                assert "state" in data["data"]
        except Exception as e:
            pytest.fail(f"Did not receive WebSocket update: {str(e)}")

def test_invalid_config(client):
    """Test handling of invalid configuration."""
    # Test invalid parameter bounds
    invalid_bounds_config = {
        "parameter_config": {
            "x1": {
                "type": "scalar",
                "init": 0.0,
                "lower": 2.0,
                "upper": -2.0  # Invalid: upper bound less than lower bound
            }
        },
        "optimizer_config": {
            "optimizer": "CMA",
            "budget": 10,
            "num_workers": 2
        },
        "execution_config": {
            "checkpoint_dir": "./test_checkpoints",
            "log_file": "./test_logs/test.log",
            "log_level": "INFO",
            "precompile": False
        }
    }
    response = client.post("/api/optimization", json=invalid_bounds_config)
    assert response.status_code == 422  # Validation error
    assert "upper bound must be greater than lower bound" in response.text

    # Test invalid budget
    invalid_budget_config = {
        "parameter_config": {
            "x1": {
                "type": "scalar",
                "init": 0.0,
                "lower": -2.0,
                "upper": 2.0
            }
        },
        "optimizer_config": {
            "optimizer": "CMA",
            "budget": -1,  # Invalid: negative budget
            "num_workers": 2
        },
        "execution_config": {
            "checkpoint_dir": "./test_checkpoints",
            "log_file": "./test_logs/test.log",
            "log_level": "INFO",
            "precompile": False
        }
    }
    response = client.post("/api/optimization", json=invalid_budget_config)
    assert response.status_code == 422  # Validation error
    assert "budget must be positive" in response.text

def test_cleanup(client, test_config):
    """Test cleanup after optimization completion."""
    # Start optimization
    response = client.post("/api/optimization", json=test_config)
    opt_id = response.json()["optimization_id"]
    
    # Let it run and complete
    import time
    time.sleep(2)  # Give it time to complete
    
    # Verify cleanup
    from quantum_opt.web.backend.main import active_optimizations
    assert opt_id not in active_optimizations

@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test directories after tests."""
    yield
    import shutil
    shutil.rmtree("./test_checkpoints", ignore_errors=True)
    shutil.rmtree("./test_logs", ignore_errors=True) 