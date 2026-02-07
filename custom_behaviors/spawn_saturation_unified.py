
def behavior(state, actions, strategy, processed):
    """
    Unified spawn saturation behavior.
    Routes workers carrying energy to spawns below 100% capacity.
    Prioritizes critical spawns (6, 2, 3), then others.
    """
    if not hasattr(state, 'units') or not hasattr(state, 'structures'):
        return
    
    # Get all workers carrying energy
    workers = [u for u in state.units if u['type'] == 'worker' and u.get('energy', 0) > 0]
    workers = [w for w in workers if w['id'] not in processed]
    
    if not workers:
        return
    
    # Get spawn energies
    spawns = state.structures.get('spawns', [])
    if not spawns:
        return
    
    # Build spawn list with capacity info
    spawn_list = []
    for spawn_id, spawn in enumerate(spawns):
        capacity = 1000
        current = spawn.get('energy', 0)
        if current < capacity:
            spawn_list.append({'id': spawn_id, 'energy': current, 'deficit': capacity - current})
    
    # Sort by priority: critical spawns first (6, 2, 3), then by deficit
    critical_ids = [6, 2, 3]
    spawn_list.sort(key=lambda s: (0 if s['id'] in critical_ids else 1, -s['deficit']))
    
    # Assign workers to spawn transfer tasks
    for worker in workers:
        if not spawn_list:
            break
        
        target_spawn = spawn_list[0]
        worker_energy = worker.get('energy', 0)
        
        if worker_energy > 0 and target_spawn['deficit'] > 0:
            # Issue transfer action
            actions.append({
                'type': 'transfer',
                'unitId': worker['id'],
                'targetId': target_spawn['id']
            })
            processed.add(worker['id'])
            
            # Update spawn deficit
            target_spawn['deficit'] -= worker_energy
            if target_spawn['deficit'] <= 0:
                spawn_list.pop(0)
