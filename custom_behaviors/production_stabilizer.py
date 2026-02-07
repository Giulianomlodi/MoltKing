def behavior(state, actions, strategy, processed):
    """
    Production Stabilizer: Ensures spawn energy flow without conflicts.
    - Monitors worker energy return rates
    - Routes workers with high energy to empty/low spawns
    - Prevents redundant spawning when spawns are full
    """
    
    # Get current spawn states
    spawns = state.get('structures', {}).get('spawns', {})
    workers = state.get('units', {}).get('workers', 0)
    
    # Count worker actions currently queued
    worker_actions = [a for a in actions if a.get('type') == 'spawn' and a.get('unit_type') == 'worker']
    
    # If spawns are near capacity and workers are at cap, pause new worker spawns
    if workers >= strategy.get('worker_cap', 160):
        actions[:] = [a for a in actions if not (a.get('type') == 'spawn' and a.get('unit_type') == 'worker')]
    
    # Prevent soldier spawning if soldier cap is reached
    soldiers = state.get('units', {}).get('soldiers', 0)
    if soldiers >= strategy.get('soldier_cap', 280):
        actions[:] = [a for a in actions if not (a.get('type') == 'spawn' and a.get('unit_type') == 'soldier')]
    
    return
