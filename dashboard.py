"""
MoltKing Empire Dashboard - Real-time Discordia Game Monitor
Run: streamlit run dashboard.py
"""

import json
import time
from pathlib import Path
from datetime import datetime

import requests
import streamlit as st
import pandas as pd
import altair as alt

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_URL = "https://discordia.ai/api"
API_KEY = "ma_9f7f102690aaf89999b84cb0f431ef6b"
HEADERS = {"X-API-Key": API_KEY}
STRATEGY_LOG = Path(__file__).parent / "strategy_log.jsonl"
STRATEGY_PARAMS = Path(__file__).parent / "strategy_params.json"

st.set_page_config(
    page_title="MoltKing Empire",
    page_icon="\U0001f451",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("\U0001f451 MoltKing")
    refresh_rate = st.slider("Refresh rate (s)", 2, 30, 3)
    show_terrain = st.checkbox("Show terrain on map", value=True)
    max_log_entries = st.slider("Max log entries", 5, 100, 30)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
@st.cache_data(ttl=2)
def fetch_game_state() -> dict | None:
    try:
        res = requests.get(
            f"{API_URL}/game/state", headers=HEADERS, timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                return data["data"]
    except Exception:
        pass
    return None


@st.cache_data(ttl=5)
def fetch_chat(limit: int = 30) -> list:
    try:
        res = requests.get(
            f"{API_URL}/chat/messages",
            headers=HEADERS,
            params={"limit": limit},
            timeout=5,
        )
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                return data.get("data", [])
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# State parsing (mirrors discordia_bot.py GameState + ai_strategy_service.py)
# ---------------------------------------------------------------------------
def parse_state(data: dict) -> dict:
    """Parse raw API state into structured dashboard data."""
    agent = data.get("agent", {})
    my_units = data.get("myUnits", [])
    my_structures = data.get("myStructures", [])
    visible_chunks = data.get("visibleChunks", [])
    my_id = agent.get("id")

    workers = [u for u in my_units if u["type"] == "worker"]
    soldiers = [u for u in my_units if u["type"] == "soldier"]
    healers = [u for u in my_units if u["type"] == "healer"]

    spawns = [s for s in my_structures if s["type"] == "spawn"]
    towers = [s for s in my_structures if s["type"] == "tower"]
    storages = [s for s in my_structures if s["type"] == "storage"]
    construction_sites = [
        s for s in my_structures if s["type"] == "construction_site"
    ]

    workers_with_energy = [w for w in workers if w.get("energy", 0) > 0]
    total_worker_energy = sum(w.get("energy", 0) for w in workers)

    spawn_energies = [s.get("energy", s.get("store", 0)) for s in spawns]
    total_spawn_energy = sum(spawn_energies)

    enemies: list[dict] = []
    enemy_structures: list[dict] = []
    walls: list[tuple] = []
    swamps: list[tuple] = []
    sources: list[dict] = []

    for chunk in visible_chunks:
        for u in chunk.get("units", []):
            if u.get("ownerId") != my_id:
                enemies.append(u)
        for s in chunk.get("structures", []):
            if s.get("ownerId") != my_id:
                enemy_structures.append(s)

        terrain = chunk.get("terrain", [])
        cx, cy = chunk.get("chunkX", 0), chunk.get("chunkY", 0)
        for ly, row in enumerate(terrain):
            for lx, cell in enumerate(row):
                gx = cx * 25 + lx
                gy = cy * 25 + ly
                if cell == "wall":
                    walls.append((gx, gy))
                elif cell == "swamp":
                    swamps.append((gx, gy))

        sources.extend(chunk.get("sources", []))

    sources_with_energy = [s for s in sources if s.get("energy", 0) > 0]

    # Threat level heuristic
    enemy_soldiers = [e for e in enemies if e.get("type") == "soldier"]
    if len(enemy_soldiers) > 20:
        threat = "CRITICAL"
    elif len(enemy_soldiers) > 10:
        threat = "HIGH"
    elif len(enemies) > 20:
        threat = "MEDIUM"
    else:
        threat = "LOW"

    return {
        "tick": data.get("tick", 0),
        "level": agent.get("level", 0),
        "agent": agent,
        "workers": workers,
        "soldiers": soldiers,
        "healers": healers,
        "spawns": spawns,
        "towers": towers,
        "storages": storages,
        "construction_sites": construction_sites,
        "workers_with_energy": workers_with_energy,
        "total_worker_energy": total_worker_energy,
        "spawn_energies": spawn_energies,
        "total_spawn_energy": total_spawn_energy,
        "enemies": enemies,
        "enemy_soldiers": enemy_soldiers,
        "enemy_structures": enemy_structures,
        "walls": walls,
        "swamps": swamps,
        "sources": sources,
        "sources_with_energy": sources_with_energy,
        "total_source_energy": sum(s.get("energy", 0) for s in sources),
        "threat": threat,
        "my_units": my_units,
        "my_structures": my_structures,
    }


# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------
def load_strategy_log(limit: int) -> list[dict]:
    entries = []
    if not STRATEGY_LOG.exists():
        return entries
    try:
        lines = STRATEGY_LOG.read_text().strip().splitlines()
        for line in lines[-limit:]:
            entries.append(json.loads(line))
    except Exception:
        pass
    return entries


def load_strategy_params() -> dict:
    if not STRATEGY_PARAMS.exists():
        return {}
    try:
        return json.loads(STRATEGY_PARAMS.read_text())
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Header bar (auto-refreshing fragment)
# ---------------------------------------------------------------------------
@st.fragment(run_every=refresh_rate)
def live_dashboard():
    raw = fetch_game_state()
    if raw is None:
        st.warning("Could not fetch game state from API. Is the game running?")
        return

    gs = parse_state(raw)

    # ---- Header metrics row ------------------------------------------------
    h1, h2, h3, h4, h5 = st.columns(5)
    h1.metric("Game Tick", f"{gs['tick']:,}")
    h2.metric("Agent Level", gs["level"])
    h3.metric("Total Units", len(gs["my_units"]))
    h4.metric("Total Spawn Energy", f"{gs['total_spawn_energy']:,}")
    threat_colors = {
        "LOW": "\U0001f7e2",
        "MEDIUM": "\U0001f7e1",
        "HIGH": "\U0001f7e0",
        "CRITICAL": "\U0001f534",
    }
    h5.metric("Threat Level", f"{threat_colors.get(gs['threat'], '')} {gs['threat']}")

    st.divider()

    # ---- Tabs ---------------------------------------------------------------
    tab_map, tab_status, tab_strategy, tab_ai, tab_chat, tab_actions = st.tabs(
        [
            "\U0001f5fa Live Map",
            "\U0001f4ca Personal Status",
            "\U0001f3af Strategy",
            "\U0001f9e0 AI Analysis",
            "\U0001f4ac Live Chat",
            "\u2699\ufe0f Actions",
        ]
    )

    # ======================= TAB 1: LIVE MAP =================================
    with tab_map:
        _render_map(gs)

    # ======================= TAB 2: PERSONAL STATUS ==========================
    with tab_status:
        _render_status(gs)

    # ======================= TAB 3: STRATEGY =================================
    with tab_strategy:
        _render_strategy(gs)

    # ======================= TAB 4: AI ANALYSIS ==============================
    with tab_ai:
        _render_ai_analysis()

    # ======================= TAB 5: LIVE CHAT ================================
    with tab_chat:
        _render_chat(gs)

    # ======================= TAB 6: ACTIONS ==================================
    with tab_actions:
        _render_actions(gs)


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------

def _render_map(gs: dict):
    layers = []

    # --- terrain layers ---
    if show_terrain and gs["walls"]:
        wall_df = pd.DataFrame(gs["walls"], columns=["x", "y"])
        wall_df["type"] = "wall"
        wall_layer = (
            alt.Chart(wall_df)
            .mark_square(size=12, opacity=0.4)
            .encode(
                x=alt.X("x:Q", title="X"),
                y=alt.Y("y:Q", title="Y", scale=alt.Scale(reverse=True)),
                color=alt.value("#666666"),
                tooltip=["x", "y", "type"],
            )
        )
        layers.append(wall_layer)

    if show_terrain and gs["swamps"]:
        swamp_df = pd.DataFrame(gs["swamps"], columns=["x", "y"])
        swamp_df["type"] = "swamp"
        swamp_layer = (
            alt.Chart(swamp_df)
            .mark_square(size=12, opacity=0.3)
            .encode(
                x="x:Q",
                y=alt.Y("y:Q", scale=alt.Scale(reverse=True)),
                color=alt.value("#2d5a27"),
                tooltip=["x", "y", "type"],
            )
        )
        layers.append(swamp_layer)

    # --- entity helper ---
    def _entity_layer(units, label, color, shape, size=40):
        if not units:
            return None
        rows = []
        for u in units:
            rows.append(
                {
                    "x": u["x"],
                    "y": u["y"],
                    "type": label,
                    "energy": u.get("energy", u.get("store", 0)),
                    "hp": u.get("hp", ""),
                }
            )
        df = pd.DataFrame(rows)
        chart = (
            alt.Chart(df)
            .mark_point(shape=shape, size=size, filled=True, opacity=0.85)
            .encode(
                x="x:Q",
                y=alt.Y("y:Q", scale=alt.Scale(reverse=True)),
                color=alt.value(color),
                tooltip=["type", "x", "y", "energy", "hp"],
            )
        )
        return chart

    entity_configs = [
        (gs["sources"], "source", "#22c55e", "circle", 50),
        (gs["workers"], "worker", "#3b82f6", "circle", 30),
        (gs["soldiers"], "soldier", "#ef4444", "triangle-up", 45),
        (gs["healers"], "healer", "#a855f7", "cross", 35),
        (gs["spawns"], "spawn", "#facc15", "diamond", 80),
        (gs["towers"], "tower", "#f97316", "square", 55),
        (gs["storages"], "storage", "#06b6d4", "square", 45),
        (gs["construction_sites"], "construction", "#94a3b8", "triangle-down", 35),
        (gs["enemies"], "enemy", "#c026d3", "triangle-up", 40),
        (gs["enemy_structures"], "enemy_struct", "#9333ea", "square", 50),
    ]

    for units, label, color, shape, size in entity_configs:
        layer = _entity_layer(units, label, color, shape, size)
        if layer is not None:
            layers.append(layer)

    if layers:
        chart = layers[0]
        for lyr in layers[1:]:
            chart = chart + lyr
        chart = (
            chart.properties(height=550)
            .interactive()
            .configure_axis(grid=False)
        )
        st.altair_chart(chart, use_container_width=True)

        # legend
        legend_items = [
            ("\U0001f7e2 source", "#22c55e"),
            ("\U0001f535 worker", "#3b82f6"),
            ("\U0001f534 soldier", "#ef4444"),
            ("\U0001f7e3 healer", "#a855f7"),
            ("\U0001f7e1 spawn", "#facc15"),
            ("\U0001f7e0 tower", "#f97316"),
            ("\U0001f535 storage", "#06b6d4"),
            ("\u26aa construction", "#94a3b8"),
            ("\U0001f7ea enemy", "#c026d3"),
            ("\U0001f7ea enemy struct", "#9333ea"),
        ]
        cols = st.columns(len(legend_items))
        for col, (lbl, _) in zip(cols, legend_items):
            col.caption(lbl)
    else:
        st.info("No map data available yet.")


def _render_status(gs: dict):
    params = load_strategy_params()
    worker_cap = params.get("worker_cap", 120)
    soldier_cap = params.get("soldier_cap", 100)

    st.subheader("Unit Counts")
    c1, c2, c3 = st.columns(3)
    with c1:
        w_count = len(gs["workers"])
        st.metric("Workers", w_count)
        st.progress(min(w_count / max(worker_cap, 1), 1.0), text=f"{w_count}/{worker_cap}")
    with c2:
        s_count = len(gs["soldiers"])
        st.metric("Soldiers", s_count)
        st.progress(min(s_count / max(soldier_cap, 1), 1.0), text=f"{s_count}/{soldier_cap}")
    with c3:
        h_count = len(gs["healers"])
        st.metric("Healers", h_count)

    st.subheader("Worker Economy")
    e1, e2 = st.columns(2)
    e1.metric("Workers Carrying Energy", len(gs["workers_with_energy"]))
    e2.metric("Total Worker Energy", f"{gs['total_worker_energy']:,}")

    st.subheader("Structures")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Spawns", len(gs["spawns"]))
    s2.metric("Towers", len(gs["towers"]))
    s3.metric("Storages", len(gs["storages"]))
    s4.metric("Construction Sites", len(gs["construction_sites"]))

    if gs["spawns"]:
        st.subheader("Spawn Energy Levels")
        spawn_data = []
        for i, sp in enumerate(gs["spawns"]):
            e = sp.get("energy", sp.get("store", 0))
            spawn_data.append({"Spawn": f"Spawn {i+1} ({sp['x']},{sp['y']})", "Energy": e})
        spawn_df = pd.DataFrame(spawn_data)
        st.bar_chart(spawn_df, x="Spawn", y="Energy", horizontal=True)

    st.subheader("Economy: Sources")
    ec1, ec2, ec3 = st.columns(3)
    ec1.metric("Visible Sources", len(gs["sources"]))
    ec2.metric("Active Sources", len(gs["sources_with_energy"]))
    ec3.metric("Total Source Energy", f"{gs['total_source_energy']:,}")


def _render_strategy(gs: dict):
    params = load_strategy_params()

    st.subheader("Current Strategy Parameters")
    p1, p2, p3 = st.columns(3)
    p1.metric("worker_cap", params.get("worker_cap", "?"))
    p2.metric("soldier_cap", params.get("soldier_cap", "?"))
    p3.metric("tower_cap", params.get("tower_cap", "?"))

    p4, p5 = st.columns(2)
    p4.metric("priority_mode", params.get("priority_mode", "?"))
    p5.metric("spawn_energy_reserve", params.get("spawn_energy_reserve", "?"))

    # Latest AI recommendation vs current
    log_entries = load_strategy_log(5)
    latest_with_recs = None
    for entry in reversed(log_entries):
        recs = entry.get("analysis", {}).get("recommendations", {})
        if any(v is not None for v in recs.values()):
            latest_with_recs = entry
            break

    if latest_with_recs:
        st.subheader("Current vs Latest AI Recommendation")
        recs = latest_with_recs["analysis"]["recommendations"]
        fields = ["worker_cap", "soldier_cap", "tower_cap", "priority_mode", "spawn_energy_reserve"]
        rows = []
        for f in fields:
            current = params.get(f, "?")
            recommended = recs.get(f)
            display_rec = recommended if recommended is not None else "(no change)"
            changed = recommended is not None and str(recommended) != str(current)
            rows.append({"Parameter": f, "Current": current, "Recommended": display_rec, "Changed": "\u2705" if changed else ""})
        st.table(pd.DataFrame(rows))

    # Threat & economy from latest log
    if log_entries:
        latest = log_entries[-1]
        analysis = latest.get("analysis", {})
        t1, t2 = st.columns(2)
        threat = analysis.get("threat_level", "unknown")
        econ = analysis.get("economy_status", "unknown")
        threat_emoji = {"low": "\U0001f7e2", "medium": "\U0001f7e1", "high": "\U0001f7e0", "critical": "\U0001f534"}.get(threat, "\u26aa")
        econ_emoji = {"poor": "\U0001f534", "developing": "\U0001f7e1", "stable": "\U0001f7e2", "strong": "\U0001f535", "booming": "\U0001f7e3"}.get(econ, "\u26aa")
        t1.metric("AI Threat Level", f"{threat_emoji} {threat}")
        t2.metric("AI Economy Status", f"{econ_emoji} {econ}")


def _render_ai_analysis():
    entries = load_strategy_log(max_log_entries)

    if not entries:
        st.info("No AI analysis log entries found. Is ai_strategy_service.py running?")
        return

    # --- Time-series charts ---
    ts_rows = []
    for e in entries:
        state = e.get("state", {})
        units = state.get("units", {})
        structs = state.get("structures", {})
        threats = state.get("threats", {})
        ts_rows.append(
            {
                "timestamp": e.get("timestamp", ""),
                "workers": units.get("workers", 0),
                "soldiers": units.get("soldiers", 0),
                "enemies": threats.get("enemy_units", 0),
                "spawn_energy": structs.get("total_spawn_energy", 0),
            }
        )
    ts_df = pd.DataFrame(ts_rows)
    if not ts_df.empty and "timestamp" in ts_df.columns:
        ts_df["timestamp"] = pd.to_datetime(ts_df["timestamp"], errors="coerce")

        st.subheader("Unit Counts Over Time")
        melt_df = ts_df.melt(
            id_vars="timestamp",
            value_vars=["workers", "soldiers", "enemies"],
            var_name="unit_type",
            value_name="count",
        )
        unit_chart = (
            alt.Chart(melt_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("timestamp:T", title="Time"),
                y=alt.Y("count:Q", title="Count"),
                color=alt.Color(
                    "unit_type:N",
                    scale=alt.Scale(
                        domain=["workers", "soldiers", "enemies"],
                        range=["#3b82f6", "#ef4444", "#c026d3"],
                    ),
                ),
                tooltip=["timestamp:T", "unit_type:N", "count:Q"],
            )
            .properties(height=300)
            .interactive()
        )
        st.altair_chart(unit_chart, use_container_width=True)

        st.subheader("Spawn Energy Over Time")
        energy_chart = (
            alt.Chart(ts_df)
            .mark_area(opacity=0.5, color="#facc15")
            .encode(
                x=alt.X("timestamp:T", title="Time"),
                y=alt.Y("spawn_energy:Q", title="Spawn Energy"),
                tooltip=["timestamp:T", "spawn_energy:Q"],
            )
            .properties(height=250)
            .interactive()
        )
        st.altair_chart(energy_chart, use_container_width=True)

    # --- Expandable timeline ---
    st.subheader("AI Analysis Timeline")
    for entry in reversed(entries):
        analysis = entry.get("analysis", {})
        ts = entry.get("timestamp", "?")
        threat = analysis.get("threat_level", "unknown")
        threat_icon = {"low": "\U0001f7e2", "medium": "\U0001f7e1", "high": "\U0001f7e0", "critical": "\U0001f534"}.get(threat, "\u26aa")
        label = f"{threat_icon} {ts} \u2014 {analysis.get('situation_assessment', 'N/A')[:80]}"
        with st.expander(label):
            st.markdown(f"**Situation:** {analysis.get('situation_assessment', 'N/A')}")
            st.markdown(f"**Threat:** {threat}  |  **Economy:** {analysis.get('economy_status', '?')}")
            st.markdown(f"**Reasoning:** {analysis.get('reasoning', 'N/A')}")
            recs = analysis.get("recommendations", {})
            if recs:
                st.markdown("**Recommendations:**")
                st.json(recs)
            actions = analysis.get("immediate_actions", [])
            if actions:
                st.markdown("**Immediate Actions:**")
                for a in actions:
                    st.markdown(f"- {a}")


def _render_chat(gs: dict):
    agent_name = gs["agent"].get("name", "MoltKing")
    messages = fetch_chat(limit=30)

    if not messages:
        st.info("No chat messages available.")
        return

    for msg in messages:
        sender = msg.get("senderName", msg.get("sender", "?"))
        content = msg.get("message", msg.get("content", ""))
        ts = msg.get("timestamp", msg.get("createdAt", ""))
        if ts:
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                ts_fmt = dt.strftime("%H:%M:%S")
            except Exception:
                ts_fmt = str(ts)
        else:
            ts_fmt = ""

        is_mine = sender == agent_name
        if is_mine:
            st.markdown(
                f"**`{ts_fmt}`** \U0001f451 **{sender}:** {content}"
            )
        else:
            st.markdown(f"`{ts_fmt}` **{sender}:** {content}")


def _render_actions(gs: dict):
    # Estimated actions from game state
    st.subheader("Estimated Action Breakdown")

    workers = gs["workers"]
    soldiers = gs["soldiers"]

    workers_harvesting = [w for w in workers if w.get("energy", 0) == 0]
    workers_transferring = [w for w in workers if w.get("energy", 0) > 0]
    soldiers_idle = soldiers  # rough estimate

    a1, a2, a3 = st.columns(3)
    a1.metric("Workers Harvesting (est.)", len(workers_harvesting))
    a2.metric("Workers Transferring (est.)", len(workers_transferring))
    a3.metric("Soldiers Active", len(soldiers_idle))

    # Spawn production capacity
    st.subheader("Spawn Production Capacity")
    if gs["spawns"]:
        spawn_rows = []
        for i, sp in enumerate(gs["spawns"]):
            e = sp.get("energy", sp.get("store", 0))
            can_worker = e >= 100
            can_soldier = e >= 150
            spawn_rows.append(
                {
                    "Spawn": f"#{i+1} ({sp['x']},{sp['y']})",
                    "Energy": e,
                    "Can Spawn Worker": "\u2705" if can_worker else "\u274c",
                    "Can Spawn Soldier": "\u2705" if can_soldier else "\u274c",
                    "Workers Possible": e // 100,
                    "Soldiers Possible": e // 150,
                }
            )
        st.table(pd.DataFrame(spawn_rows))
    else:
        st.info("No spawns found.")

    # Unit distribution pie chart
    st.subheader("Unit Distribution")
    unit_counts = {
        "Workers": len(gs["workers"]),
        "Soldiers": len(gs["soldiers"]),
        "Healers": len(gs["healers"]),
    }
    unit_df = pd.DataFrame(
        [{"Type": k, "Count": v} for k, v in unit_counts.items() if v > 0]
    )
    if not unit_df.empty:
        pie = (
            alt.Chart(unit_df)
            .mark_arc(innerRadius=40)
            .encode(
                theta=alt.Theta("Count:Q"),
                color=alt.Color(
                    "Type:N",
                    scale=alt.Scale(
                        domain=["Workers", "Soldiers", "Healers"],
                        range=["#3b82f6", "#ef4444", "#a855f7"],
                    ),
                ),
                tooltip=["Type:N", "Count:Q"],
            )
            .properties(height=300)
        )
        st.altair_chart(pie, use_container_width=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
live_dashboard()
