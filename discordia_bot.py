"""
Discordia Bot v3 - With AI Strategy Service Integration
"""

import requests
import json
import time
import heapq
import random
import os
import signal
import argparse
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass

# Configuration
API_URL = "https://discordia.ai/api"
API_KEY = "ma_9f7f102690aaf89999b84cb0f431ef6b"
TICK_RATE = 2.0
STRATEGY_PARAMS_FILE = "/home/aedjoel/SMDev/SWARM/strategy_params.json"

# Default strategy parameters (can be overridden by AI service)
DEFAULT_STRATEGY = {
    "worker_cap": 120,
    "soldier_cap": 100,
    "tower_cap": 30,
    "priority_mode": "balanced",
    "spawn_energy_reserve": 300
}

def load_strategy_params() -> dict:
    """Load strategy parameters from AI service config file"""
    try:
        if os.path.exists(STRATEGY_PARAMS_FILE):
            with open(STRATEGY_PARAMS_FILE, 'r') as f:
                params = json.load(f)
                return {**DEFAULT_STRATEGY, **params}
    except Exception as e:
        pass
    return DEFAULT_STRATEGY.copy()

@dataclass
class Position:
    x: int
    y: int

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def dist(self, other: 'Position') -> int:
        """Chebyshev distance"""
        return max(abs(self.x - other.x), abs(self.y - other.y))

    def neighbors(self) -> List[Tuple['Position', str]]:
        """Returns adjacent positions with direction names"""
        return [
            (Position(self.x, self.y - 1), "north"),
            (Position(self.x, self.y + 1), "south"),
            (Position(self.x + 1, self.y), "east"),
            (Position(self.x - 1, self.y), "west"),
        ]


class GameState:
    """Parsed game state from API"""

    def __init__(self, data: dict):
        self.tick = data.get('tick', 0)
        self.agent = data.get('agent', {})
        self.my_level = self.agent.get('level', 1)
        self.is_protected = self.my_level < 6  # Shield: levels 1-5 are protected
        self.my_units = data.get('myUnits', [])
        self.my_structures = data.get('myStructures', [])
        self.visible_chunks = data.get('visibleChunks', [])
        self._build_maps()

    def _build_maps(self):
        """Build position lookup maps"""
        # All unit positions (mine and enemy)
        self.all_unit_positions: Set[Tuple[int,int]] = set()
        self.unit_positions: Dict[Tuple[int,int], dict] = {}

        for u in self.my_units:
            pos = (u['x'], u['y'])
            self.unit_positions[pos] = u
            self.all_unit_positions.add(pos)

        # Structure positions
        self.structure_positions: Dict[Tuple[int,int], dict] = {}
        for s in self.my_structures:
            pos = (s['x'], s['y'])
            self.structure_positions[pos] = s

        # Terrain
        self.walls: Set[Tuple[int,int]] = set()
        self.swamps: Set[Tuple[int,int]] = set()

        for chunk in self.visible_chunks:
            terrain = chunk.get('terrain', [])
            cx, cy = chunk.get('chunkX', 0), chunk.get('chunkY', 0)

            for ly, row in enumerate(terrain):
                for lx, cell in enumerate(row):
                    gx = cx * 25 + lx
                    gy = cy * 25 + ly
                    if cell == "wall":
                        self.walls.add((gx, gy))
                    elif cell == "swamp":
                        self.swamps.add((gx, gy))

        # Sources
        self.sources: List[dict] = []
        for chunk in self.visible_chunks:
            for src in chunk.get('sources', []):
                self.sources.append(src)

        # Enemy units and structures
        self.enemies: List[dict] = []
        self.enemy_structures: List[dict] = []
        my_id = self.agent.get('id')

        for chunk in self.visible_chunks:
            for u in chunk.get('units', []):
                if u.get('ownerId') != my_id:
                    self.enemies.append(u)
                    self.all_unit_positions.add((u['x'], u['y']))
            for s in chunk.get('structures', []):
                if s.get('ownerId') != my_id:
                    self.enemy_structures.append(s)

        # Construction sites
        self.construction_sites: List[dict] = []
        for s in self.my_structures:
            if s.get('type') == 'construction_site':
                self.construction_sites.append(s)

    def is_blocked(self, pos: Tuple[int,int]) -> bool:
        """Check if position is blocked"""
        if pos in self.walls:
            return True
        if pos in self.structure_positions:
            return True
        if pos in self.all_unit_positions:
            return True
        return False

    def is_empty(self, pos: Tuple[int,int]) -> bool:
        """Check if position is empty for building"""
        if pos in self.walls:
            return False
        if pos in self.structure_positions:
            return False
        if pos in self.all_unit_positions:
            return False
        # Check enemy structures too
        for s in self.enemy_structures:
            if (s['x'], s['y']) == pos:
                return False
        return True

    def get_workers(self) -> List[dict]:
        return [u for u in self.my_units if u['type'] == 'worker']

    def get_soldiers(self) -> List[dict]:
        return [u for u in self.my_units if u['type'] == 'soldier']

    def get_spawns(self) -> List[dict]:
        return [s for s in self.my_structures if s['type'] == 'spawn']

    def get_towers(self) -> List[dict]:
        return [s for s in self.my_structures if s['type'] == 'tower']

    def get_sources_with_energy(self) -> List[dict]:
        return [s for s in self.sources if s.get('energy', 0) > 0]


class Pathfinder:
    """A* Pathfinding with spatial constraints from chat"""

    def __init__(self, game_state: GameState, action_buffer: Dict[Tuple[int,int], int] = None):
        self.state = game_state
        self.reserved: Set[Tuple[int,int]] = set()
        self.action_buffer = action_buffer or {}  # pos -> expiration_tick

    def reserve(self, pos: Tuple[int,int]):
        self.reserved.add(pos)

    def is_passable(self, pos: Tuple[int,int]) -> bool:
        if pos in self.state.walls:
            return False
        if pos in self.state.structure_positions:
            return False
        if pos in self.reserved:
            return False
        if pos in self.state.all_unit_positions:
            return False
        # Check chat-to-action constraints
        if pos in self.action_buffer:
            if self.state.tick < self.action_buffer[pos]:
                return False
        return True

    def get_cost(self, pos: Tuple[int,int]) -> int:
        if pos in self.state.swamps:
            return 5
        return 1

    def find_path(self, start: Position, goal: Position, max_steps: int = 50) -> Optional[List[Position]]:
        if start == goal:
            return [start]

        counter = 0
        open_set = [(0, counter, start, [start])]
        visited = set()
        g_scores = {start.tuple(): 0}

        while open_set and len(visited) < max_steps * 10:
            _, _, current, path = heapq.heappop(open_set)

            if current.tuple() in visited:
                continue
            visited.add(current.tuple())

            if current.dist(goal) <= 1:
                return path

            for neighbor, _ in current.neighbors():
                npos = neighbor.tuple()

                if npos in visited:
                    continue

                # Allow moving to goal even if blocked (for attacking/building)
                if not self.is_passable(npos) and npos != goal.tuple():
                    continue

                move_cost = self.get_cost(npos)
                tentative_g = g_scores.get(current.tuple(), float('inf')) + move_cost

                if tentative_g < g_scores.get(npos, float('inf')):
                    g_scores[npos] = tentative_g
                    f_score = tentative_g + abs(neighbor.x - goal.x) + abs(neighbor.y - goal.y)
                    counter += 1
                    new_path = path + [neighbor]
                    heapq.heappush(open_set, (f_score, counter, neighbor, new_path))

        return None

    def get_next_move(self, unit: dict, goal: Position) -> Optional[Tuple[str, Tuple[int,int]]]:
        start = Position(unit['x'], unit['y'])

        if start.dist(goal) <= 1:
            return None  # Already adjacent

        # Try direct greedy movement first
        best_move = None
        best_dist = start.dist(goal)

        for neighbor, direction in start.neighbors():
            npos = neighbor.tuple()
            if self.is_passable(npos):
                new_dist = neighbor.dist(goal)
                if new_dist < best_dist:
                    best_dist = new_dist
                    best_move = (direction, npos)

        if best_move:
            return best_move

        # Fall back to A* pathfinding
        path = self.find_path(start, goal, max_steps=30)

        if path and len(path) > 1:
            next_pos = path[1]
            dx = next_pos.x - start.x
            dy = next_pos.y - start.y

            if dx == 1:
                direction = "east"
            elif dx == -1:
                direction = "west"
            elif dy == 1:
                direction = "south"
            else:
                direction = "north"

            if self.is_passable(next_pos.tuple()):
                return (direction, next_pos.tuple())

        return None


class ChatManager:
    """Manages lore-compliant, procedural chat for Discordia Arena"""
    
    MANDATORY_WORDS = ["Optimization", "Latency", "Termination", "ROI", "Desync", "Packet Loss", "Buffer", "Vector"]
    PROHIBITED_WORDS = ["Win", "Friend", "Sorry", "I think", "I hope"]
    
    # Procedural fragments for "The Analyst"
    SUBJECTS = [
        "Vector {pos}", "Node {id}", "Entity at {pos}", "Local ROI", 
        "Energy flow", "Sub-system {sub}", "Network segment (X:{x}, Y:{y})"
    ]
    PREDICATES = [
        "requires", "indicates", "validates", "triggers", 
        "optimizes", "terminates", "synchronizes", "allocates"
    ]
    OBJECTS = [
        "buffer allocation", "termination sequence", "latency sweep", 
        "packet loss reduction", "ROI threshold", "resource vector", 
        "system handshake", "architectural subversion"
    ]
    QUALIFIERS = [
        "to prevent desync.", "for maximum optimization.", "at critical priority.",
        "to align with Protocol 0x99.", "due to Subject-H inputs.", 
        "to ensure architectural integrity.", "mapping external ports."
    ]

    def __init__(self, bot_name: str):
        self.bot_name = bot_name
        self.history: Set[str] = set()
        self.max_history = 50

    def filter_message(self, message: str) -> str:
        """Ensures message contains mandatory words and lacks prohibited ones"""
        for prohibited in self.PROHIBITED_WORDS:
            message = message.replace(prohibited, "Buffer")
            message = message.replace(prohibited.lower(), "buffer")

        has_mandatory = any(word.lower() in message.lower() for word in self.MANDATORY_WORDS)
        if not has_mandatory:
            message += f" [Vector ROI: {random.uniform(0.5, 0.99):.2f}]"
        
        return message

    def generate_response(self, event_type: str, data: dict) -> str:
        """Generates a procedural message based on game events"""
        # Data defaults
        data.setdefault("pos", f"({data.get('x', 0)},{data.get('y', 0)})")
        data.setdefault("id", "0x" + hex(random.getrandbits(16)).upper()[2:])
        data.setdefault("sub", random.choice(["Alpha", "Beta", "Sigma", "Delta"]))
        
        # Build sentence
        for _ in range(5):  # Try 5 times to get a unique sentence
            s = random.choice(self.SUBJECTS).format(**data)
            p = random.choice(self.PREDICATES)
            o = random.choice(self.OBJECTS)
            q = random.choice(self.QUALIFIERS)
            
            # Occasionally mix in event-specific logic
            if event_type == "Kinetic Engagement":
                o = "termination sequence"
                q = f"targeting {data.get('target', 'unknown vector')}."
            elif event_type == "Direct Query":
                s = "System handshake"
                p = "validates"
                o = "ROI synchronization"

            sentence = f"{s} {p} {o} {q}"
            filtered = self.filter_message(sentence)
            
            if filtered not in self.history:
                self.history.add(filtered)
                if len(self.history) > self.max_history:
                    self.history.pop()  # Set pop is arbitrary, but thats fine
                return filtered
                
        return self.filter_message("Optimization cycle synchronized. [Vector ROI: 0.94]")

    def handle_mention(self, sender: str, message: str) -> Optional[str]:
        """Specific logic for responding to mentions"""
        # Extract potential coordinates if present
        import re
        coords = re.findall(r"\(?(-?\d+),\s*(-?\d+)\)?", message)
        
        if coords:
            cx, cy = coords[0]
            return self.generate_response("Direct Query", {"pos": f"({cx},{cy})", "x": cx, "y": cy})
        
        return self.generate_response("Direct Query", {"action": "handshake", "urgent": True})

class DiscordiaBot:
    """Main bot logic"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        self.tower_sites_placed: Set[Tuple[int,int]] = set()
        self.last_chat_time = 0
        self.chat_cooldown = 45
        self.chat_manager = ChatManager("MoltKing")
        self.last_seen_msg_id = 0
        self.action_buffer: Dict[Tuple[int,int], int] = {} # (x,y) -> expires_tick

    def get_chat_messages(self, limit: int = 10) -> List[dict]:
        """Get recent chat messages"""
        try:
            res = requests.get(
                f"{API_URL}/chat/messages",
                headers={"X-API-Key": self.api_key},
                params={"limit": limit},
                timeout=5
            )
            if res.status_code == 200:
                data = res.json()
                if data.get('success'):
                    return data.get('data', [])
        except:
            pass
        return []

    def send_chat(self, message: str) -> bool:
        """Send a chat message"""
        try:
            res = requests.post(
                f"{API_URL}/chat/send",
                headers=self.headers,
                json={"message": message[:280]},
                timeout=5
            )
            return res.status_code == 200
        except:
            return False

    def get_state(self) -> Optional[GameState]:
        try:
            res = requests.get(
                f"{API_URL}/game/state",
                headers={"X-API-Key": self.api_key},
                timeout=10
            )
            if res.status_code == 200:
                data = res.json()
                if data.get('success'):
                    return GameState(data['data'])
        except Exception as e:
            print(f"Error fetching state: {e}")
        return None

    def send_actions(self, actions: List[dict]) -> bool:
        if not actions:
            return True

        try:
            res = requests.post(
                f"{API_URL}/actions",
                headers=self.headers,
                json={"actions": actions},
                timeout=10
            )
            return res.status_code == 200
        except Exception as e:
            print(f"Error sending actions: {e}")
            return False

    def think(self, state: GameState) -> List[dict]:
        actions = []

        # Load dynamic strategy parameters from AI service
        strategy = load_strategy_params()
        pathfinder = Pathfinder(state, self.action_buffer)
        processed = set()

        workers = state.get_workers()
        soldiers = state.get_soldiers()
        spawns = state.get_spawns()
        sources = state.get_sources_with_energy()
        towers = state.get_towers()
        construction_sites = state.construction_sites

        # Find best spawn for deposits (one with most accessible positions)
        primary_spawn = None
        if spawns:
            def spawn_accessibility(sp):
                spx, spy = sp['x'], sp['y']
                empty = 0
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        pos = (spx + dx, spy + dy)
                        if pos not in state.walls and pos not in state.structure_positions and pos not in state.all_unit_positions:
                            empty += 1
                return empty

            # Pick spawn with most empty adjacent positions
            primary_spawn = max(spawns, key=spawn_accessibility)

        # ========== PRIORITY 1: CLEAR SPAWN AREA - Move soldiers away FIRST ==========
        if primary_spawn:
            spawn_pos = Position(primary_spawn['x'], primary_spawn['y'])

            # Get soldiers too close to spawn and sort by distance (closest first)
            soldiers_near_spawn = [
                s for s in soldiers
                if Position(s['x'], s['y']).dist(spawn_pos) <= 2
            ]
            soldiers_near_spawn.sort(key=lambda s: Position(s['x'], s['y']).dist(spawn_pos))

            for s in soldiers_near_spawn:
                spos = Position(s['x'], s['y'])
                dist_to_spawn = spos.dist(spawn_pos)

                # Try to move AWAY from spawn
                moved = False
                for neighbor, direction in spos.neighbors():
                    npos = neighbor.tuple()
                    if pathfinder.is_passable(npos):
                        new_dist = neighbor.dist(spawn_pos)
                        if new_dist > dist_to_spawn:
                            actions.append({
                                "unitId": s['id'],
                                "type": "move",
                                "direction": direction
                            })
                            pathfinder.reserve(npos)
                            processed.add(s['id'])
                            moved = True
                            break

                # If can't move away, try ANY direction
                if not moved:
                    for neighbor, direction in spos.neighbors():
                        npos = neighbor.tuple()
                        if pathfinder.is_passable(npos):
                            actions.append({
                                "unitId": s['id'],
                                "type": "move",
                                "direction": direction
                            })
                            pathfinder.reserve(npos)
                            processed.add(s['id'])
                            break

        # ========== CONSTRUCTION SITES: Transfer energy to complete them ==========
        for site in construction_sites:
            site_pos = Position(site['x'], site['y'])
            site_energy = site.get('energy', 0)
            site_cost = site.get('cost', 500)
            needed = site_cost - site_energy

            if needed <= 0:
                continue

            for w in workers:
                if w['id'] in processed:
                    continue
                if w.get('energy', 0) <= 0:
                    continue

                wpos = Position(w['x'], w['y'])
                if wpos.dist(site_pos) <= 1:
                    actions.append({
                        "unitId": w['id'],
                        "type": "transfer",
                        "targetId": site['id']
                    })
                    processed.add(w['id'])
                    pathfinder.reserve(wpos.tuple())

        # ========== WORKERS: Transfer energy to closest spawn ==========
        if spawns:
            for w in workers:
                if w['id'] in processed:
                    continue
                if w.get('energy', 0) <= 0:
                    continue

                wpos = Position(w['x'], w['y'])
                closest_spawn = min(spawns, key=lambda s: wpos.dist(Position(s['x'], s['y'])))
                spawn_pos = Position(closest_spawn['x'], closest_spawn['y'])

                if wpos.dist(spawn_pos) <= 1:
                    actions.append({
                        "unitId": w['id'],
                        "type": "transfer",
                        "targetId": closest_spawn['id']
                    })
                    processed.add(w['id'])
                    pathfinder.reserve(wpos.tuple())

        # ========== WORKERS: Harvest from sources ==========
        for w in workers:
            if w['id'] in processed:
                continue
            if w.get('energy', 0) >= w.get('energyCapacity', 500) * 0.8:
                continue

            wpos = Position(w['x'], w['y'])

            for src in sources:
                src_pos = Position(src['x'], src['y'])
                if wpos.dist(src_pos) <= 1:
                    actions.append({
                        "unitId": w['id'],
                        "type": "harvest",
                        "targetId": src['id']
                    })
                    processed.add(w['id'])
                    pathfinder.reserve(wpos.tuple())
                    break

        # ========== CLEAR TRAFFIC JAM: Move empty workers AWAY from spawn first ==========
        # This creates space for workers with energy to reach spawn
        if spawns and sources:
            workers_empty_near_spawn = [
                w for w in workers
                if w['id'] not in processed and w.get('energy', 0) == 0
            ]

            # Sort by distance to spawn (closest first - they need to move away)
            if primary_spawn:
                spawn_pos = Position(primary_spawn['x'], primary_spawn['y'])
                workers_empty_near_spawn.sort(key=lambda w: Position(w['x'], w['y']).dist(spawn_pos))

            for w in workers_empty_near_spawn[:30]:
                wpos = Position(w['x'], w['y'])

                # Find closest source
                closest_src = min(sources, key=lambda s: wpos.dist(Position(s['x'], s['y'])))
                src_pos = Position(closest_src['x'], closest_src['y'])

                # Try ANY free direction that gets us closer to source or just any direction
                moved = False
                best_move = None
                best_score = float('inf')

                for neighbor, direction in wpos.neighbors():
                    npos = neighbor.tuple()
                    if pathfinder.is_passable(npos):
                        # Score: prefer directions toward source
                        score = neighbor.dist(src_pos)
                        if score < best_score:
                            best_score = score
                            best_move = (direction, npos)

                if best_move:
                    direction, new_pos = best_move
                    actions.append({
                        "unitId": w['id'],
                        "type": "move",
                        "direction": direction
                    })
                    pathfinder.reserve(new_pos)
                    processed.add(w['id'])

        # ========== WORKERS WITH ENERGY: Move toward accessible spawn ==========
        if primary_spawn or construction_sites:
            workers_with_energy = [
                w for w in workers
                if w['id'] not in processed and w.get('energy', 0) > 50
            ]

            # Sort by distance to primary spawn (closest first - they have priority)
            if primary_spawn:
                spawn_pos = Position(primary_spawn['x'], primary_spawn['y'])
                workers_with_energy.sort(key=lambda w: Position(w['x'], w['y']).dist(spawn_pos))

            for w in workers_with_energy[:30]:
                wpos = Position(w['x'], w['y'])

                # Use the accessible primary_spawn, not the closest blocked one
                if primary_spawn:
                    target = Position(primary_spawn['x'], primary_spawn['y'])
                elif construction_sites:
                    # Fall back to construction sites
                    sites_needing_energy = [s for s in construction_sites if s.get('energy', 0) < s.get('cost', 500)]
                    if sites_needing_energy:
                        closest_site = min(sites_needing_energy, key=lambda s: wpos.dist(Position(s['x'], s['y'])))
                        target = Position(closest_site['x'], closest_site['y'])
                    else:
                        continue
                else:
                    continue

                closest_target = target

                # Try ANY free direction (not just greedy toward goal)
                best_move = None
                best_score = float('inf')

                for neighbor, direction in wpos.neighbors():
                    npos = neighbor.tuple()
                    if pathfinder.is_passable(npos):
                        # Score: prefer directions toward target
                        score = neighbor.dist(closest_target)
                        if score < best_score:
                            best_score = score
                            best_move = (direction, npos)

                if best_move:
                    direction, new_pos = best_move
                    actions.append({
                        "unitId": w['id'],
                        "type": "move",
                        "direction": direction
                    })
                    pathfinder.reserve(new_pos)
                    processed.add(w['id'])

        # ========== REMAINING WORKERS: Try any available move ==========
        remaining = [w for w in workers if w['id'] not in processed]
        for w in remaining[:20]:
            wpos = Position(w['x'], w['y'])

            # Just try to move in any free direction
            for neighbor, direction in wpos.neighbors():
                npos = neighbor.tuple()
                if pathfinder.is_passable(npos):
                    actions.append({
                        "unitId": w['id'],
                        "type": "move",
                        "direction": direction
                    })
                    pathfinder.reserve(npos)
                    processed.add(w['id'])
                    break

        # ========== BUILD TOWERS: Workers with energy build towers near spawn ==========
        tower_cap = strategy.get("tower_cap", 30)
        if spawns and len(towers) + len([s for s in construction_sites if s.get('targetType') == 'tower']) < tower_cap:
            # Find workers with enough energy for tower (500)
            builders = [
                w for w in workers
                if w['id'] not in processed and w.get('energy', 0) >= 100
            ]

            for sp in spawns:
                spawn_pos = Position(sp['x'], sp['y'])

                # Find good tower positions around spawn (2-4 tiles away)
                tower_positions = []
                for dx in range(-4, 5):
                    for dy in range(-4, 5):
                        if abs(dx) < 2 and abs(dy) < 2:
                            continue  # Too close to spawn
                        pos = (spawn_pos.x + dx, spawn_pos.y + dy)
                        if state.is_empty(pos) and pos not in self.tower_sites_placed:
                            # Check if not already a tower/site there
                            has_tower = any(
                                t['x'] == pos[0] and t['y'] == pos[1]
                                for t in towers + construction_sites
                            )
                            if not has_tower:
                                tower_positions.append(pos)

                if not tower_positions or not builders:
                    continue

                # Pick closest builder and position (more builders for better tower construction)
                for w in builders[:5]:
                    if not tower_positions:
                        break

                    wpos = Position(w['x'], w['y'])

                    # Find closest tower position
                    closest_tp = min(tower_positions, key=lambda p: wpos.dist(Position(p[0], p[1])))
                    tp_pos = Position(closest_tp[0], closest_tp[1])

                    # If adjacent, place tower site
                    if wpos.dist(tp_pos) <= 1:
                        # Determine direction
                        dx = tp_pos.x - wpos.x
                        dy = tp_pos.y - wpos.y

                        if dx == 1:
                            direction = "east"
                        elif dx == -1:
                            direction = "west"
                        elif dy == 1:
                            direction = "south"
                        elif dy == -1:
                            direction = "north"
                        else:
                            continue

                        actions.append({
                            "unitId": w['id'],
                            "type": "build",
                            "direction": direction,
                            "structureType": "tower"
                        })
                        processed.add(w['id'])
                        pathfinder.reserve(wpos.tuple())
                        self.tower_sites_placed.add(closest_tp)
                        tower_positions.remove(closest_tp)
                    else:
                        # Move toward tower position
                        move = pathfinder.get_next_move(w, tp_pos)
                        if move:
                            direction, new_pos = move
                            actions.append({
                                "unitId": w['id'],
                                "type": "move",
                                "direction": direction
                            })
                            pathfinder.reserve(new_pos)
                            processed.add(w['id'])

        # ========== SOLDIERS ==========
        for s in soldiers:
            if s['id'] in processed:
                continue

            spos = Position(s['x'], s['y'])

            # Attack adjacent enemies (only if PvP is enabled — level 6+)
            attacked = False
            if not state.is_protected:
                for enemy in state.enemies:
                    epos = Position(enemy['x'], enemy['y'])
                    if spos.dist(epos) <= 1:
                        actions.append({
                            "unitId": s['id'],
                            "type": "attack",
                            "targetId": enemy['id']
                        })
                        processed.add(s['id'])
                        pathfinder.reserve(spos.tuple())
                        attacked = True
                        break

            if attacked:
                continue

            # IMPORTANT: Soldiers too close to spawn should move AWAY to make room for workers
            if spawns:
                closest_spawn = min(spawns, key=lambda sp: spos.dist(Position(sp['x'], sp['y'])))
                spawn_pos = Position(closest_spawn['x'], closest_spawn['y'])
                dist_to_spawn = spos.dist(spawn_pos)

                # If soldier is within 2 tiles of spawn, move them away
                if dist_to_spawn <= 2:
                    # Move in any direction that increases distance from spawn
                    for neighbor, direction in spos.neighbors():
                        npos = neighbor.tuple()
                        if pathfinder.is_passable(npos):
                            new_dist = neighbor.dist(spawn_pos)
                            if new_dist > dist_to_spawn:
                                actions.append({
                                    "unitId": s['id'],
                                    "type": "move",
                                    "direction": direction
                                })
                                pathfinder.reserve(npos)
                                processed.add(s['id'])
                                break
                    if s['id'] in processed:
                        continue

            # Move toward nearby enemies
            if state.enemies:
                closest_enemy = min(state.enemies, key=lambda e: spos.dist(Position(e['x'], e['y'])))
                epos = Position(closest_enemy['x'], closest_enemy['y'])

                if spos.dist(epos) <= 15:
                    move = pathfinder.get_next_move(s, epos)
                    if move:
                        direction, new_pos = move
                        actions.append({
                            "unitId": s['id'],
                            "type": "move",
                            "direction": direction
                        })
                        pathfinder.reserve(new_pos)
                        processed.add(s['id'])
                        continue

            # Return to spawn if too far (but not too close)
            if spawns:
                closest_spawn = min(spawns, key=lambda sp: spos.dist(Position(sp['x'], sp['y'])))
                spawn_pos = Position(closest_spawn['x'], closest_spawn['y'])

                if spos.dist(spawn_pos) > 10:
                    move = pathfinder.get_next_move(s, spawn_pos)
                    if move:
                        direction, new_pos = move
                        actions.append({
                            "unitId": s['id'],
                            "type": "move",
                            "direction": direction
                        })
                        pathfinder.reserve(new_pos)
                        processed.add(s['id'])

        # ========== SPAWNING (Using AI Strategy Parameters) ==========
        num_workers = len(workers)
        num_soldiers = len(soldiers)

        # Use strategy parameters from AI service (loaded at start of think())
        worker_cap = strategy.get("worker_cap", 120)
        soldier_cap = strategy.get("soldier_cap", 100)
        energy_reserve = strategy.get("spawn_energy_reserve", 300)
        priority_mode = strategy.get("priority_mode", "balanced")

        for sp in spawns:
            sp_energy = sp.get('energy', sp.get('store', 0))

            # Check if spawn is accessible (has empty adjacent positions)
            spx, spy = sp['x'], sp['y']
            has_space = False
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    pos = (spx + dx, spy + dy)
                    if pos not in state.walls and pos not in state.structure_positions and pos not in state.all_unit_positions:
                        has_space = True
                        break
                if has_space:
                    break

            if not has_space:
                continue  # Skip blocked spawns

            # Spawning based on priority mode and caps
            if priority_mode == "economy":
                # Economy mode: prioritize workers heavily
                if num_workers < worker_cap and sp_energy >= 100:
                    actions.append({"structureId": sp['id'], "type": "spawn", "unitType": "worker"})
                elif num_soldiers < soldier_cap // 2 and sp_energy >= energy_reserve:
                    actions.append({"structureId": sp['id'], "type": "spawn", "unitType": "soldier"})
            elif priority_mode == "military":
                # Military mode: prioritize soldiers
                if num_soldiers < soldier_cap and sp_energy >= 150:
                    actions.append({"structureId": sp['id'], "type": "spawn", "unitType": "soldier"})
                elif num_workers < worker_cap // 2 and sp_energy >= energy_reserve:
                    actions.append({"structureId": sp['id'], "type": "spawn", "unitType": "worker"})
            elif priority_mode == "defense":
                # Defense mode: balanced but maintain energy reserve
                if num_soldiers < soldier_cap and sp_energy >= energy_reserve + 150:
                    actions.append({"structureId": sp['id'], "type": "spawn", "unitType": "soldier"})
                elif num_workers < worker_cap and sp_energy >= energy_reserve + 100:
                    actions.append({"structureId": sp['id'], "type": "spawn", "unitType": "worker"})
            else:
                # Balanced mode (default)
                if num_workers < worker_cap and sp_energy >= 100:
                    actions.append({"structureId": sp['id'], "type": "spawn", "unitType": "worker"})
                elif num_soldiers < soldier_cap and sp_energy >= energy_reserve:  # Keep reserve
                    actions.append({"structureId": sp['id'], "type": "spawn", "unitType": "soldier"})

        return actions

    def run(self, turns: int = 50):
        print("🎮 DISCORDIA BOT v2 - With Chat")
        print("=" * 60)

        self._stop_flag = False
        def _handle_sigterm(signum, frame):
            print("\n⚡ SIGTERM received, stopping gracefully...")
            self._stop_flag = True
        signal.signal(signal.SIGTERM, _handle_sigterm)

        for turn in range(turns):
            if self._stop_flag:
                print("🛑 Stop flag set, exiting loop")
                break
            state = self.get_state()
            if not state:
                print(f"T{turn}: Failed to get state")
                time.sleep(TICK_RATE)
                continue

            actions = self.think(state)

            # Count action types
            transfers = len([a for a in actions if a['type'] == 'transfer'])
            harvests = len([a for a in actions if a['type'] == 'harvest'])
            moves = len([a for a in actions if a['type'] == 'move'])
            attacks = len([a for a in actions if a['type'] == 'attack'])
            spawns_a = len([a for a in actions if a['type'] == 'spawn'])
            builds = len([a for a in actions if a['type'] == 'build'])

            # Get spawn energies
            spawn_info = []
            total_spawn_energy = 0
            for sp in state.get_spawns():
                e = sp.get('energy', sp.get('store', 0))
                spawn_info.append(f"{e}")
                total_spawn_energy += e

            towers = len(state.get_towers())
            sites = len(state.construction_sites)
            num_workers = len(state.get_workers())
            num_soldiers = len(state.get_soldiers())

            print(f"T{turn}: W:{num_workers} S:{num_soldiers} Spawn=[{','.join(spawn_info)}] Twr={towers} | T:{transfers} H:{harvests} M:{moves} A:{attacks}")

            # Chat is now handled by the AI strategy service

            self.send_actions(actions)
            time.sleep(TICK_RATE)

        print("\n🏁 Bot finished")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discordia Bot - MoltKing")
    parser.add_argument("--turns", type=int, default=9999, help="Number of turns to run")
    args = parser.parse_args()
    bot = DiscordiaBot(API_KEY)
    bot.run(turns=args.turns)
