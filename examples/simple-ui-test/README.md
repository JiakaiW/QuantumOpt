# Simple UI Test Example

This example demonstrates a complete integration test of the QuantumOpt web interface, including:
- Task creation and management
- Real-time optimization visualization
- WebSocket communication
- Task queue control

## Setup

1. Install dependencies:
```bash
# Install backend dependencies
pip install -e .

# Install frontend dependencies
cd src/quantum_opt/web/frontend
npm install
```

2. Start the backend server:
```bash
python -m quantum_opt.web.backend.main
```

3. Start the frontend development server:
```bash
cd src/quantum_opt/web/frontend
npm run dev
```

## Test Components

### 1. Task Creation
- Simple quadratic optimization task
- Parameter configuration
- Optimizer settings

### 2. Real-time Monitoring
- WebSocket connection status
- Task queue visualization
- Optimization progress plot

### 3. Task Control
- Start/pause/resume/stop operations
- Error handling
- State management

## Test Flow

1. **Setup Phase**
   - Start backend server
   - Initialize WebSocket connection
   - Verify connection status

2. **Task Creation Phase**
   - Submit optimization task
   - Verify task creation
   - Check initial task state

3. **Monitoring Phase**
   - Start task execution
   - Monitor optimization progress
   - Verify real-time updates

4. **Control Phase**
   - Test pause/resume functionality
   - Test stop operation
   - Verify state transitions

5. **Results Phase**
   - Check optimization results
   - Verify convergence
   - Export results

## Running Tests

```bash
# Run frontend tests
cd src/quantum_opt/web/frontend
npm test

# Run integration tests
python -m pytest examples/simple-ui-test/src/test_integration.py
```

## Expected Results

1. Task Creation:
   - Task ID received
   - Initial state: "pending"

2. Optimization:
   - Progress updates received
   - Convergence to minimum
   - Real-time plot updates

3. Controls:
   - State transitions work
   - WebSocket maintains connection
   - UI updates correctly 