def behavior(state, actions, strategy, processed):
    spawns = state.structures['spawns']
    spawn_energies = state.structures['spawn_energies']
    
    # Find spawns that need energy
    low_energy_spawns = [i for i, energy in enumerate(spawn_energies) if energy < 800]
    
    if low_energy_spawns:
        workers_carrying_energy = [w for w in state.units['workers'] if w.carrying_energy > 0]
        
        for spawn_index in low_energy_spawns:
            for worker in workers_carrying_energy:
                if worker.id not in processed:
                    actions.append({
                        'action': 'transfer',
                        'unitId': worker.id,
                        'targetId': spawns[spawn_index].id
                    })
                    processed.add(worker.id)
                    break