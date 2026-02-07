def behavior(state, actions, strategy, processed):
    # Get all spawn structures
    spawns = [s for s in state.structures if s['type'] == 'spawn']
    
    # Find workers carrying energy
    workers_with_energy = [u for u in state.units 
                          if u['type'] == 'worker' 
                          and u['energy'] > 0 
                          and u['id'] not in processed]
    
    # Sort spawns by energy level (lowest first)
    spawns_sorted = sorted(spawns, key=lambda s: s['energy'])
    
    # Sort workers by energy they're carrying (highest first)
    workers_sorted = sorted(workers_with_energy, key=lambda w: w['energy'], reverse=True)
    
    # Prioritize filling spawns that are not full
    for spawn in spawns_sorted:
        spawn_id = spawn['id']
        spawn_energy = spawn['energy']
        spawn_capacity = 1000
        
        # If spawn is not full
        if spawn_energy < spawn_capacity:
            # Calculate how many workers we need
            energy_needed = spawn_capacity - spawn_energy
            
            # Find workers close enough to this spawn
            for worker in workers_sorted[:]:
                if worker['id'] in processed:
                    continue
                    
                # Check if worker is close enough to transfer (range 1)
                dist = ((worker['x'] - spawn['x'])**2 + (worker['y'] - spawn['y'])**2)**0.5
                
                if dist <= 1.5:  # Transfer range is 1, adding buffer
                    # Transfer energy to the spawn
                    actions.append({
                        'type': 'transfer',
                        'unitId': worker['id'],
                        'targetId': spawn_id
                    })
                    processed.add(worker['id'])
                    energy_needed -= worker['energy']
                    workers_sorted.remove(worker)
                    
                    # If we've assigned enough workers, move to next spawn
                    if energy_needed <= 0:
                        break
                elif dist <= 10:  # Move closer to transfer
                    # Calculate direction to move
                    dx = spawn['x'] - worker['x']
                    dy = spawn['y'] - worker['y']
                    
                    direction = None
                    if abs(dx) > abs(dy):
                        direction = 'east' if dx > 0 else 'west'
                    else:
                        direction = 'south' if dy > 0 else 'north'
                    
                    actions.append({
                        'type': 'move',
                        'unitId': worker['id'],
                        'direction': direction
                    })
                    processed.add(worker['id'])
                    workers_sorted.remove(worker)
                    
                    # If we've assigned enough workers, move to next spawn
                    if energy_needed <= 0:
                        break
    
    # Redirect any remaining workers with energy toward the lowest energy spawn
    if workers_sorted and spawns:
        lowest_spawn = spawns_sorted[0]
        for worker in workers_sorted:
            if worker['id'] in processed:
                continue
                
            # Calculate direction to move toward spawn
            dx = lowest_spawn['x'] - worker['x']
            dy = lowest_spawn['y'] - worker['y']
            
            direction = None
            if abs(dx) > abs(dy):
                direction = 'east' if dx > 0 else 'west'
            else:
                direction = 'south' if dy > 0 else 'north'
            
            actions.append({
                'type': 'move',
                'unitId': worker['id'],
                'direction': direction
            })
            processed.add(worker['id'])