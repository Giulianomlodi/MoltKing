
def behavior(state, actions, strategy, processed):
    """
    Route workers to fill spawns in priority order.
    Workers with sufficient energy naturally transfer to nearest critical spawn.
    """
    import math
    
    # Priority order for spawn filling
    spawn_priority = [6, 2, 3, 1, 4, 5]
    target_capacity = 1000
    
    # Get all spawns with their current energy
    if not hasattr(state, 'structures'):
        return
    
    spawns = state.structures.get('spawns', {})
    if not spawns:
        return
    
    # Get workers carrying energy
    workers = [u for u in state.units if u.get('type') == 'worker' and u.get('energy', 0) > 0]
    
    for worker in workers:
        if worker['id'] in processed:
            continue
        
        worker_energy = worker.get('energy', 0)
        worker_x = worker.get('x', 0)
        worker_y = worker.get('y', 0)
        
        # Find best target spawn in priority order
        best_spawn = None
        best_distance = float('inf')
        
        for spawn_id in spawn_priority:
            if spawn_id not in spawns:
                continue
            
            spawn = spawns[spawn_id]
            spawn_energy = spawn.get('energy', 0)
            
            # Skip if spawn is full
            if spawn_energy >= target_capacity:
                continue
            
            spawn_x = spawn.get('x', 0)
            spawn_y = spawn.get('y', 0)
            dist = math.sqrt((spawn_x - worker_x)**2 + (spawn_y - worker_y)**2)
            
            # Prefer spawn in priority order, then by distance
            if best_spawn is None or spawn_id in spawn_priority[:spawn_priority.index(best_spawn) if best_spawn in spawn_priority else len(spawn_priority)]:
                best_spawn = spawn_id
                best_distance = dist
        
        if best_spawn:
            actions.append({
                'type': 'transfer',
                'unitId': worker['id'],
                'targetId': best_spawn
            })
            processed.add(worker['id'])
