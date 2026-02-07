def behavior(state, actions, strategy, processed):
    """Routes workers to spawns."""
    if not hasattr(state, 'units'):
        return
    
    units = state.units
    structs = state.structures.get('spawns', {})
    
    priority = [6, 2, 3, 1, 4, 5]
    
    for unit in units:
        if unit.get('type') != 'worker':
            continue
        if unit.get('id') in processed:
            continue
        
        energy = unit.get('energy', 0)
        maxe = unit.get('max_energy', 100)
        
        if energy < maxe * 0.4:
            continue
        
        target = None
        mindist = 999999
        
        for sid in priority:
            if sid not in structs:
                continue
            
            sp = structs[sid]
            spe = sp.get('energy', 0)
            smax = sp.get('max_energy', 1000)
            
            if spe >= smax * 0.95:
                continue
            
            dx = sp.get('x', 0) - unit.get('x', 0)
            dy = sp.get('y', 0) - unit.get('y', 0)
            d = dx*dx + dy*dy
            
            if d < mindist:
                mindist = d
                target = sid
        
        if target:
            spx = structs[target]
            actions.append({'type': 'move', 'unitId': unit.get('id'), 'target_x': spx.get('x'), 'target_y': spx.get('y')})
            processed.add(unit.get('id'))
