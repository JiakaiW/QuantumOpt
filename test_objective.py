import numpy as np
import qutip as qt

def objective_fn(amplitude=1.0, frequency=1.0, duration=1.0, phase=0.0):
    # System parameters
    N = 2  # Two-level system
    omega = 1.0  # Qubit frequency
    
    # Create operators
    sz = qt.sigmaz()
    sx = qt.sigmax()
    H0 = omega/2 * sz  # Static Hamiltonian
    
    # Time parameters
    nt = 100  # Number of time points
    times = np.linspace(0, duration, nt)
    
    # Create pulse envelope
    pulse = amplitude * np.sin(2*np.pi*frequency*times + phase)
    
    # Define time-dependent Hamiltonian terms
    def pulse_coeff(t, args):
        # Ensure time index is within bounds
        idx = min(int(t/duration * (nt-1)), nt-1)
        return pulse[idx]
    
    H = [H0, [sx, pulse_coeff]]
    
    # Initial and target states
    psi0 = qt.basis([N], 0)  # Start in ground state
    target = (qt.basis([N], 0) + qt.basis([N], 1)).unit()  # Target is |+⟩ state
    
    # Solve Schrödinger equation
    result = qt.sesolve(H, psi0, times)
    
    # Calculate fidelity with target state at final time
    final_state = result.states[-1]
    fidelity = abs(target.overlap(final_state))**2
    
    # Return negative fidelity (since we're minimizing)
    return -fidelity

if __name__ == "__main__":
    # Test with some example parameters
    print('Testing objective function with example parameters:')
    print('amplitude=1.0, frequency=1.0, duration=1.0, phase=0.0')
    result = objective_fn()
    print(f'Negative fidelity: {result}')
    print(f'Fidelity: {-result}')
    
    # Test with some other parameters
    print('\nTesting with different parameters:')
    print('amplitude=1.5, frequency=0.8, duration=2.0, phase=np.pi/2')
    result = objective_fn(amplitude=1.5, frequency=0.8, duration=2.0, phase=np.pi/2)
    print(f'Negative fidelity: {result}')
    print(f'Fidelity: {-result}') 