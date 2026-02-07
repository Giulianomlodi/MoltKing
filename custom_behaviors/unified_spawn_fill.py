
def behavior(state, actions, strategy, processed):
    """
    Unified spawn fill: Prioritize lowest-energy spawn.
    Every worker with energy >= threshold contributes to refilling spawns.
    """
    if not hasattr(state, 'spawns') or not state.spawns:
        return
    
    # Find lowest-energy spawn
    spawn_list = [(s['id'], s.get('energy', 0)) for s in state.spawns]
    if not spawn_list:
        return
    
    lowest_spawn_id, lowest_energy = min(spawn_list, key=lambda x: x[1])
    
    # If lowest spawn is above 850 energy, all spawns are healthy
    if lowest_energy >= 850:
        return
    
    # Get all workers with energy >= threshold
    threshold = strategy.get('worker_harvest_threshold', 0.7) * 100  # normalize to 0-100
    available_workers = [
        u for u in state.units
        if u.get('type') == 'worker'
        and u.get('energy', 0) >= threshold
        and u['id'] not in processed
    ]
    
    # Route them to lowest spawn
    for worker in available_workers[:80]:  # Limit to 80 per tick to prevent flooding
        actions.append({
            'type': 'transfer',
            'unitId': worker['id'],
            'targetId': lowest_spawn_id
        })
        processed.add(worker['id'])
