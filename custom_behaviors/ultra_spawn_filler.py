def behavior(state, actions, strategy, processed):
    # Find all spawns below 900 energy
    critical_spawns = []
    for structure in state.structures:
        if structure.type == "spawn" and structure.energy < 900:
            critical_spawns.append(structure)
    
    if not critical_spawns:
        return
    
    # Sort by lowest energy first
    critical_spawns.sort(key=lambda s: s.energy)
    
    # Find all workers carrying energy
    energy_workers = []
    for unit in state.units:
        if unit.type == "worker" and unit.energy > 0 and unit.id not in processed:
            energy_workers.append(unit)
    
    if not energy_workers:
        return
    
    # Sort workers by energy carried (highest first)
    energy_workers.sort(key=lambda u: u.energy, reverse=True)
    
    # Assign workers to spawns
    spawn_idx = 0
    for worker in energy_workers:
        if spawn_idx >= len(critical_spawns):
            spawn_idx = 0  # Loop back to first spawn
        
        target_spawn = critical_spawns[spawn_idx]
        
        # Remove any existing actions for this worker
        actions[:] = [a for a in actions if a.get("unitId") != worker.id]
        
        # Add transfer action
        actions.append({
            "type": "transfer",
            "unitId": worker.id,
            "targetId": target_spawn.id
        })
        processed.add(worker.id)
        
        spawn_idx += 1