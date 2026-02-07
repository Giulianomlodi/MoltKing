def behavior(state, actions, strategy, processed):
    """Simple spawn maintenance: fill only if below 800 energy."""
    if not state or not state.get('structures'):
        return
    
    spawns = state.get('structures', {}).get('spawns', [])
    if not spawns:
        return
    
    # Only fill spawns below 800 energy, don't obsess
    critical_spawns = [s for s in spawns if s.get('energy', 0) < 800]
    if critical_spawns and state.get('units', {}).get('workers_carrying_energy', 0) > 30:
        # Let normal harvest behavior handle it; we just monitor
        pass