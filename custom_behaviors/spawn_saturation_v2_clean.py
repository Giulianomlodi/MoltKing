def behavior(state, actions, strategy, processed):
    """
    Clean spawn saturation v2: Route all available workers to spawns efficiently.
    Priority: spawn 6 > spawns 2,3 > others.
    """
    if not hasattr(state, 'spawns') or not hasattr(state, 'units'):
        return
    
    spawns = state.spawns if isinstance(state.spawns, list) else []
    workers = [u for u in state.units if u.get('type') == 'worker' and u.get('energy', 0) >= 65]
    
    if not workers or not spawns:
        return
    
    # Build spawn targets: sort by (is_critical, energy_level)
    critical_ids = [6, 2, 3]
    spawn_targets = []
    for idx, spawn in enumerate(spawns):
        spawn_id = spawn.get('id')
        energy = spawn.get('energy', 0)
        is_critical = (idx + 1) in critical_ids
        spawn_targets.append({
            'id': spawn_id,
            'idx': idx,
            'energy': energy,
            'priority': (is_critical, -energy)  # Critical first, then lowest energy
        })
    
    spawn_targets.sort(key=lambda x: x['priority'])
    
    # Route workers to spawns
    for worker in workers:
        if worker.get('id') in processed:
            continue
        
        for spawn in spawn_targets:
            if spawn['energy'] < 1000:  # Not full
                actions.append({
                    'type': 'move',
                    'unitId': worker.get('id'),
                    'targetId': spawn['id']
                })
                processed.add(worker.get('id'))
                break
