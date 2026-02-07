def behavior(state, actions, strategy, processed):
    """Fill critically low spawns with extreme urgency"""
    
    # Find spawns with less than 100 energy
    critical_spawns = []
    for spawn_id, spawn in state.structures.items():
        if spawn['type'] == 'spawn' and spawn.get('energy', 0) < 100:
            critical_spawns.append((spawn_id, spawn))
    
    if not critical_spawns:
        return
    
    # Sort by energy level (lowest first)
    critical_spawns.sort(key=lambda x: x[1].get('energy', 0))
    
    # Find workers with energy
    workers_with_energy = []
    for unit_id, unit in state.units.items():
        if (unit['type'] == 'worker' and 
            unit.get('energy', 0) > 0 and 
            unit_id not in processed):
            workers_with_energy.append((unit_id, unit))
    
    if not workers_with_energy:
        return
    
    # Assign workers to critical spawns
    for spawn_id, spawn in critical_spawns:
        spawn_x, spawn_y = spawn['x'], spawn['y']
        
        # Find closest workers
        available_workers = [(uid, u) for uid, u in workers_with_energy if uid not in processed]
        if not available_workers:
            break
            
        # Sort by distance to this spawn
        available_workers.sort(key=lambda x: abs(x[1]['x'] - spawn_x) + abs(x[1]['y'] - spawn_y))
        
        # Assign up to 10 closest workers to this spawn
        for i, (worker_id, worker) in enumerate(available_workers[:10]):
            # If worker is adjacent to spawn, transfer
            if abs(worker['x'] - spawn_x) <= 1 and abs(worker['y'] - spawn_y) <= 1:
                actions.append({
                    'type': 'transfer',
                    'unitId': worker_id,
                    'targetId': spawn_id
                })
            else:
                # Move towards spawn
                dx = spawn_x - worker['x']
                dy = spawn_y - worker['y']
                
                if abs(dx) > abs(dy):
                    direction = 'east' if dx > 0 else 'west'
                elif dy != 0:
                    direction = 'south' if dy > 0 else 'north'
                else:
                    continue
                
                actions.append({
                    'type': 'move',
                    'unitId': worker_id,
                    'direction': direction
                })
            
            processed.add(worker_id)