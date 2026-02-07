
def behavior(state, actions, strategy, processed):
    """
    Core spawn saturation behavior: Keep spawns 85-100% full.
    Routes workers to transfer energy to critical spawns first.
    """
    if not state.structures.spawns:
        return
    
    # Define spawn capacity (standard = 1000)
    SPAWN_CAPACITY = 1000
    FILL_THRESHOLD = 0.85
    
    # Identify spawns needing energy (prioritize critical ones)
    critical_spawn_ids = [6, 2, 3]
    spawns_needing_energy = []
    
    for spawn in state.structures.spawns:
        spawn_id = spawn.id
        current_energy = spawn.energy
        capacity_ratio = current_energy / SPAWN_CAPACITY
        
        if capacity_ratio < FILL_THRESHOLD:
            priority = 0
            if spawn_id in critical_spawn_ids:
                priority = 10 - critical_spawn_ids.index(spawn_id)
            spawns_needing_energy.append((priority, spawn_id, current_energy))
    
    # Sort by priority (higher first)
    spawns_needing_energy.sort(reverse=True)
    
    # Route workers with energy to transfer
    workers_available = [w for w in state.units.workers 
                        if w.energy > 50 and w.id not in processed]
    
    for priority, spawn_id, spawn_energy in spawns_needing_energy[:3]:
        for worker in workers_available:
            if worker.id in processed:
                continue
            
            # Issue transfer action
            transfer_action = {
                "type": "transfer",
                "unit_id": worker.id,
                "target_id": spawn_id
            }
            actions.append(transfer_action)
            processed.add(worker.id)
            workers_available.remove(worker)
            
            if not workers_available:
                break
