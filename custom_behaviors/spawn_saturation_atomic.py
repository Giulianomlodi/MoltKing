def behavior(state, actions, strategy, processed):
    """
    Route workers with sufficient energy to fill spawns in priority order.
    Only acts on workers not yet commanded. Greedy nearest-neighbor logic.
    """
    if not hasattr(state, 'units') or not hasattr(state, 'structures'):
        return
    
    # Priority spawn order
    priority_spawns = [6, 2, 3, 1, 4, 5]
    
    # Get workers carrying energy >= 50%
    workers = [u for u in state.units 
               if u.get('type') == 'worker' 
               and u.get('id') not in processed
               and u.get('energy', 0) >= 50]
    
    if not workers:
        return
    
    # Get spawn positions and current energies
    spawns = {}
    for spawn in state.structures.get('spawns', []):
        spawn_id = spawn.get('id')
        if spawn_id:
            spawns[spawn_id] = {
                'x': spawn.get('x'),
                'y': spawn.get('y'),
                'energy': spawn.get('energy', 0),
                'capacity': 1000
            }
    
    # Route each worker to nearest critical spawn with space
    for worker in workers:
        wx, wy = worker.get('x', 0), worker.get('y', 0)
        best_spawn = None
        best_distance = float('inf')
        
        for spawn_id in priority_spawns:
            if spawn_id not in spawns:
                continue
            spawn = spawns[spawn_id]
            if spawn['energy'] >= spawn['capacity']:
                continue  # Skip full spawns
            
            dist = ((spawn['x'] - wx) ** 2 + (spawn['y'] - wy) ** 2) ** 0.5
            if dist < best_distance:
                best_distance = dist
                best_spawn = spawn_id
        
        if best_spawn is not None:
            # Move worker toward best spawn
            spawn = spawns[best_spawn]
            actions.append({
                'type': 'move',
                'unitId': worker['id'],
                'direction': 'toward',
                'targetX': spawn['x'],
                'targetY': spawn['y']
            })
            processed.add(worker['id'])
