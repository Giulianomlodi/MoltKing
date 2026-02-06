# Discordia Game Strategies - MoltKing

## Game Overview
- **Player**: MoltKing
- **API**: https://discordia.ai/api
- **Current Level**: 10 (PvP ENABLED)
- **Status**: Economy working, soldiers defending

---

## Working Strategies ✅

### 1. Deposit Energy to Spawn/Storage
**Status**: WORKING (slow but functional)
- Workers with energy move toward nearest deposit target (spawn/storage)
- Adjacent workers use `transfer` action to deposit
- Key: Sort workers by distance to target, prioritize closest first
- Issue: Can be slow if workers are scattered

### 2. Harvest from Energy Sources
**Status**: WORKING (when sources are visible)
- Empty workers move toward energy sources
- Adjacent workers use `harvest` action
- Key: Sources must be in visible rooms (requires unit presence in chunk)
- Issue: Sources not visible if no units in that chunk

### 3. Spawn Units
**Status**: WORKING
- Use spawn action with `structureId` and `unitType`
- Workers cost 100 energy, Soldiers cost 150
- Key: Prioritize soldiers at high levels (PvP defense)

### 4. Build Construction Sites (2-step process)
**Status**: WORKING
- Step 1: Worker at cardinal adjacent position uses `build` with `direction` and `structureType`
- Step 2: Workers use `transfer` to deposit energy to construction site
- Completion: When site reaches cost (tower=500, spawn=2000, storage=500)
- Key: Must be at CARDINAL position (not diagonal) to place site

### 5. Tower Defense Ring
**Status**: IN PROGRESS
- Place towers at distance 3-4 from spawn in all directions
- Towers have range 10, damage 30
- 8 tower positions: N, S, E, W, NE, NW, SE, SW

### 6. Collision Avoidance (UPDATED!)
**Status**: WORKING - CRITICAL FOR ALL MOVEMENT
- **MUST check ALL unit positions** before moving (not just structures!)
- Build `occupied` set from: `myUnits` + `myStructures` + terrain walls
- Track `reserved` positions for moves in current tick
- Only send move action if target position is FREE
- 52/62 workers had free paths when properly checked
- **Data key**: Use `visibleChunks` (not `visibleRooms`) for terrain

### 7. Spawn Accessibility Selection
**Status**: WORKING
- Pick spawn with most empty adjacent positions for deposits
- Blocked spawns (soldiers camping) should be deprioritized
- Calculate: count empty positions in 8-neighbor around spawn
- Workers transfer to CLOSEST spawn when adjacent (even if not primary target)

### 8. Soldier Traffic Management
**Status**: IN PROGRESS
- Problem: Soldiers camp adjacent to spawn, blocking worker transfers
- Solution: Move soldiers away from spawn (distance > 2) before processing workers
- Soldiers should patrol at range 3-10, not adjacent to spawn
- Process soldier movements FIRST each tick to clear paths

### 7. Data Structure Notes
**Status**: IMPORTANT
- Unit positions: `x`, `y` (not `globalX`, `globalY`)
- Terrain: `visibleChunks[].terrain` is 25x25 grid
- Terrain types: "plain" (passable), "wall" (blocked), "swamp" (slow)
- Local coords: `local_x = x % 25`, `local_y = y % 25`

---

## Non-Working Strategies ❌

### 1. Moving Without Checking Unit Collisions
**Status**: CRITICAL BUG FOUND!
- **Root Cause**: Units were blocking each other, not terrain
- Actions queue successfully but unit doesn't move if another unit occupies target tile
- **Fix**: Always check ALL unit positions before sending move actions
- Check both `myUnits` and chunk `units` for occupied positions
- Solution: Build occupied set from all units, then only move to free tiles

### 2. Attacking Protected Players
**Status**: NOT POSSIBLE
- Players at Level 1-5 are protected
- Combat blocked if EITHER party is protected
- Must wait for them to reach Level 6+

### 2. Visibility Without Units
**Status**: LIMITATION
- Cannot see sources/enemies in chunks without our units
- visibleRooms returns empty if no presence
- Need to send scouts to reveal areas

### 3. Fast Deposit When Scattered
**Status**: SLOW
- When workers are far from deposit targets, takes many ticks
- 42 workers carrying 15k+ energy but only 1-3 transfers per tick
- Need better pathfinding or rally points

### 4. Diagonal Build Placement
**Status**: DOES NOT WORK
- Build action requires CARDINAL adjacent position
- Worker at diagonal cannot place site
- Must move to N/S/E/W of target position first

---

## Strategic Notes

### Economy
- Workers per source: 4 (optimal, prevents crowding)
- Harvest until 80% full, then deposit
- Keep spawn above 300 energy for emergencies

### Military
- Worker/Soldier ratio: aim for 1:1 at high levels
- Soldiers patrol within 10 tiles of spawn
- Attack adjacent enemies immediately

### Expansion
- Build new spawn near contested areas
- Protect with tower ring before expanding further
- Cost: Spawn=2000, Tower=500 each

### Chunk System
- World divided into 25x25 chunks
- chunkX = floor(x/25), chunkY = floor(y/25)
- Need unit presence to reveal chunk contents

---

## Current Mission Log

### Session: Latest (AI-DRIVEN!)
1. **Level**: 10 (PvP enabled)
2. **Units**: 355 (166 workers, 189 soldiers) - MASSIVE ARMY!
3. **Spawns**: 6 spawns operational
4. **Towers**: 53 operational (6.5x growth from 8!)
5. **Economy**: BOOMING - AI detects 47k+ worker energy
6. **Defense**: 52 attacks per turn - dominating the battlefield!
7. **AI Strategy Service**: Active - analyzes every 30 seconds
8. **Current Mode**: Balanced (auto-switched from military after achieving dominance)

### Working Features
- A* pathfinding for unit movement
- Collision avoidance with all units
- Accessibility-based spawn selection
- Soldier traffic management
- Chat integration with other players

### Enemy Intel
- Multiple hostiles in combat range (24-51 units)
- Soldiers defending successfully
- Towers providing additional firepower

---

## API Reference Quick Notes

### Actions
```json
{"unitId": "xxx", "type": "move", "direction": "north|south|east|west"}
{"unitId": "xxx", "type": "harvest", "targetId": "source_id"}
{"unitId": "xxx", "type": "transfer", "targetId": "struct_id"}
{"unitId": "xxx", "type": "build", "direction": "...", "structureType": "tower|spawn|storage|wall"}
{"unitId": "xxx", "type": "attack", "targetId": "enemy_id"}
{"structureId": "spawn_id", "type": "spawn", "unitType": "worker|soldier|healer"}
```

### Costs
- Worker: 100
- Soldier: 150
- Healer: 200
- Tower: 500
- Storage: 500
- Spawn: 2000
- Wall: 100
