
def behavior(state, actions, strategy, processed):
    """
    Emergency spawn fill behavior.
    Routes workers with sufficient energy to the emptiest critical spawns.
    """
    if not hasattr(state, 'structures') or not state.structures:
        return
    
    # Get spawn energies
    spawns = state.structures.get('spawns', [])
    if not spawns:
        return
    
    spawn_energies = state.structures.get('spawn_energies', [])
    if not spawn_energies:
        return
    
    # Identify critical spawns (empty or low)
    critical_spawns = []
    for idx, energy in enumerate(spawn_energies):
        if energy < 800:  # Below safe threshold
            critical_spawns.append((idx, energy))
    
    if not critical_spawns:
        return  # All spawns healthy, behavior dormant
    
    # Sort by energy (lowest first)
    critical_spawns.sort(key=lambda x: x[1])
    
    # Get workers with sufficient energy
    workers = [u for u in state.units.get('workers', []) if u.get('energy', 0) >= 100]
    
    if not workers or not critical_spawns:
        return
    
    # Route workers to lowest-energy spawn
    target_spawn_idx = critical_spawns[0][0]
    target_spawn = spawns[target_spawn_idx] if target_spawn_idx < len(spawns) else None
    
    if not target_spawn:
        return
    
    # Create transfer actions for first 30 workers
    for worker in workers[:30]:
        if 'id' in worker and 'id' in target_spawn:
            actions.append({
                'type': 'transfer',
                'unitId': worker['id'],
                'targetId': target_spawn['id']
            })
            processed.add(worker['id'])
