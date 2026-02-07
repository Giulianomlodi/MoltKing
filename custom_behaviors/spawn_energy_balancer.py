def behavior(state, actions, strategy, processed):
    # Find low energy spawns and high energy sources
    low_energy_spawns = [i for i, energy in enumerate(state['structures']['spawn_energies']) if energy < 500]
    high_energy_workers = [worker for worker in state['units']['workers'] if worker['energy'] > 500]
    
    # Prioritize transferring energy to low-energy spawns
    for spawn_index in low_energy_spawns:
        for worker in high_energy_workers:
            if worker['id'] not in processed:
                actions.append({
                    'action_type': 'transfer',
                    'unit_id': worker['id'],
                    'target_id': state['structures']['spawns'][spawn_index]
                })
                processed.add(worker['id'])