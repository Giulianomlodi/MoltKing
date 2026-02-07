def behavior(state, actions, strategy, processed):
    """Ensure all spawns stay at maximum energy capacity"""
    
    # Find spawns that need energy
    empty_spawns = []
    for spawn in state.my_structures:
        if spawn['structureType'] == 'spawn' and spawn['energy'] < spawn['energyCapacity']:
            empty_spawns.append((spawn['id'], spawn['energyCapacity'] - spawn['energy'], spawn['x'], spawn['y']))
    
    if not empty_spawns:
        return
    
    # Sort by energy deficit (fill emptiest first)
    empty_spawns.sort(key=lambda x: x[1], reverse=True)
    
    # Find workers with energy
    workers_with_energy = []
    for unit in state.my_units:
        if unit['unitType'] == 'worker' and unit['energy'] > 0 and unit['id'] not in processed:
            workers_with_energy.append(unit)
    
    # Direct workers to fill spawns
    for spawn_id, deficit, spawn_x, spawn_y in empty_spawns:
        if not workers_with_energy:
            break
            
        # Find closest workers to this spawn
        workers_by_distance = sorted(workers_with_energy, 
            key=lambda w: abs(w['x'] - spawn_x) + abs(w['y'] - spawn_y))
        
        # Send workers to fill this spawn
        energy_needed = deficit
        for worker in workers_by_distance[:]:
            if energy_needed <= 0:
                break
                
            # Direct this worker to transfer to spawn
            actions.append({
                'type': 'transfer',
                'unitId': worker['id'],
                'targetId': spawn_id
            })
            processed.add(worker['id'])
            
            energy_needed -= worker['energy']
            workers_with_energy.remove(worker)