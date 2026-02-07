def behavior(state, actions, strategy, processed):
    """Route workers to critical spawns in priority order."""
    if not hasattr(state, 'units') or not hasattr(state, 'structures'):
        return
    
    # Only process if we have workers available
    workers = [u for u in state.units if u.get('type') == 'worker' and u.get('id') not in processed]
    if not workers:
        return
    
    # Get spawn locations
    spawns = {s.get('id'): s for s in state.structures if s.get('type') == 'spawn'}
    if not spawns:
        return
    
    # Priority order for critical spawns
    priority_order = [6, 2, 3, 1, 4, 5]
    
    # Filter to active spawns only
    active_critical = [sid for sid in priority_order if sid in spawns]
    
    # Route workers with >= 40% energy to nearest critical spawn
    for worker in workers:
        energy = worker.get('energy', 0)
        capacity = worker.get('energy_capacity', 100)
        
        if energy >= capacity * 0.4:  # Has sufficient energy
            # Find nearest critical spawn
            worker_pos = (worker.get('x', 0), worker.get('y', 0))
            nearest_spawn = None
            nearest_dist = float('inf')
            
            for spawn_id in active_critical:
                spawn = spawns[spawn_id]
                spawn_pos = (spawn.get('x', 0), spawn.get('y', 0))
                dist = ((spawn_pos[0] - worker_pos[0])**2 + (spawn_pos[1] - worker_pos[1])**2)**0.5
                
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_spawn = spawn_id
            
            if nearest_spawn:
                spawn = spawns[nearest_spawn]
                target_pos = (spawn.get('x', 0), spawn.get('y', 0))
                
                # Move towards spawn
                dx = target_pos[0] - worker_pos[0]
                dy = target_pos[1] - worker_pos[1]
                
                if abs(dx) > abs(dy):
                    direction = 'east' if dx > 0 else 'west'
                else:
                    direction = 'south' if dy > 0 else 'north'
                
                actions.append({'type': 'move', 'unitId': worker.get('id'), 'direction': direction})
                processed.add(worker.get('id'))
