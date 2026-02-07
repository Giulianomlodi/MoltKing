def behavior(state, actions, strategy, processed):
    """Keep all spawns topped off with energy at all times"""
    
    # Get all spawns that need energy
    spawns_needing_energy = []
    for spawn in state.my_structures:
        if spawn.structure_type == "spawn":
            energy_deficit = spawn.max_energy - spawn.energy
            if energy_deficit > 0:
                spawns_needing_energy.append((spawn, energy_deficit))
    
    if not spawns_needing_energy:
        return
    
    # Sort by energy deficit (fill emptiest first)
    spawns_needing_energy.sort(key=lambda x: x[1], reverse=True)
    
    # Get workers carrying energy
    workers_with_energy = []
    for unit in state.my_units:
        if unit.unit_type == "worker" and unit.energy > 0 and unit.id not in processed:
            workers_with_energy.append(unit)
    
    if not workers_with_energy:
        return
    
    # Sort workers by energy carried (use fullest workers first)
    workers_with_energy.sort(key=lambda x: x.energy, reverse=True)
    
    # Assign workers to spawns
    for spawn, deficit in spawns_needing_energy:
        if not workers_with_energy:
            break
            
        # Calculate how many workers we need for this spawn
        workers_needed = min(len(workers_with_energy), max(1, deficit // 100))
        
        # Assign workers
        for i in range(workers_needed):
            if not workers_with_energy:
                break
                
            worker = workers_with_energy.pop(0)
            
            # Check if worker is adjacent to spawn
            if abs(worker.x - spawn.x) <= 1 and abs(worker.y - spawn.y) <= 1:
                # Transfer energy
                actions.append({
                    "type": "transfer",
                    "unitId": worker.id,
                    "targetId": spawn.id
                })
            else:
                # Move toward spawn
                dx = spawn.x - worker.x
                dy = spawn.y - worker.y
                
                if abs(dx) > abs(dy):
                    direction = "east" if dx > 0 else "west"
                elif dy != 0:
                    direction = "south" if dy > 0 else "north"
                else:
                    direction = "east" if dx > 0 else "west"
                
                actions.append({
                    "type": "move",
                    "unitId": worker.id,
                    "direction": direction
                })
            
            processed.add(worker.id)