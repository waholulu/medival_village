import random
import sys
import plotly.graph_objs as go
import plotly.offline as pyo
import pandas as pd
from collections import defaultdict
import webbrowser
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# CONFIGURATION & CONSTANTS
# -----------------------------------------------------------------------------

CONFIG = {
    # -----------------------------------------------------
    # Environment and Simulation Time
    # -----------------------------------------------------
    "GRID_WIDTH": 32,
    "GRID_HEIGHT": 32,
    "DAYS_PER_SEASON": 3,  # 3 days => 4 seasons => 12 days/year
    "SEASONS": ["Spring", "Summer", "Autumn", "Winter"],
    "PARTS_OF_DAY": ["Morning", "Afternoon", "Night"],
    "TOTAL_DAYS_TO_RUN": 96,

    # -----------------------------------------------------
    # Terrain and Field Management
    # -----------------------------------------------------
    "TERRAIN_DISTRIBUTION": {
        "forest": {"chance": 0.3, "base_resource": 5},
        "field": {"chance": 0.5, "base_resource": 1},
        "water": {"chance": 0.2, "base_resource": 0}
    },
    "MAX_FIELD_RESOURCE": 30,
    "WINTER_FIELD_LOSS": 0.5,

    # -----------------------------------------------------
    # Item and Tool Definitions
    # -----------------------------------------------------
    "ITEMS": {
        "food": {"type": "resource", "durability": 0, "price": 1, "spoilage": 0},
        "cooked_food": {"type": "resource", "durability": 0, "price": 2, "spoilage": 0},
        "wood": {"type": "resource", "durability": 0, "price": 1, "spoilage": 0},
        "axe": {"type": "tool", "durability": 10, "price": 5, "spoilage": 0},
        "bow": {"type": "tool", "durability": 20, "price": 5, "spoilage": 0},
        "hoe": {"type": "tool", "durability": 20, "price": 5, "spoilage": 0},
        "herb": {"type": "resource", "durability": 0, "price": 1, "spoilage": 0}
    },

    # -----------------------------------------------------
    # Production Yields
    # -----------------------------------------------------
    "BASE_FARM_YIELD": 1.5,
    "FALLBACK_FARM_YIELD": 1,
    "BASE_HUNT_YIELD": 1,
    "FALLBACK_HUNT_YIELD": 1,
    "BASE_LOG_YIELD": 2,
    "FALLBACK_LOG_YIELD": 1,
    "MAX_LOG_WOOD_YIELD_MULTIPLIER": 3.0,
    "TOOL_YIELD_BASE": 1.0,  # Added to (1 + skill_bonus)

    # -----------------------------------------------------
    # Consumption and Needs
    # -----------------------------------------------------
    "HUNGER_DECREMENT_PER_DAY": 2,
    "REST_DECREMENT_PER_DAY": 1,
    "HUNGER_CRITICAL_THRESHOLD": 5,
    "REST_CRITICAL_THRESHOLD": 5,
    "HUNGER_LOW_PENALTY_THRESHOLD": 3,
    "REST_LOW_PENALTY_THRESHOLD": 3,
    "HEALTH_PENALTY_FOR_LOW_NEEDS": 1,
    "HAPPINESS_PENALTY_FOR_LOW_NEEDS": 1,
    "NO_WOOD_PENALTY": 0.5,

    # -----------------------------------------------------
    # Initial Stocks and Inventories
    # -----------------------------------------------------
    "INITIAL_MARKET_STOCK": {
        "food": 50,
        "wood": 100,
        "axe": 10,
        "bow": 10,
        "hoe": 10,
        "cooked_food": 0,
        "herb": 100
    },
    "INITIAL_VILLAGER_FOOD": 3,
    "INITIAL_VILLAGER_WOOD": 2,
    "INITIAL_VILLAGER_COINS": 10,

    # -----------------------------------------------------
    # Market Dynamics
    # -----------------------------------------------------
    "MARKET_MAX_STOCK": {
        "food": 99999,
        "cooked_food": 99999,
        "wood": 99999,
        "axe": 200,
        "bow": 200,
        "hoe": 200,
        "herb": 99999
    },
    "MARKET_PRICE_DECAY": 0.95,

    # -----------------------------------------------------
    # Inventory Management (Surplus)
    # -----------------------------------------------------
    "SURPLUS_THRESHOLDS": {"food": 10, "wood": 10, "cooked_food": 10},
    "SPECIAL_SURPLUS_THRESHOLDS": {"Blacksmith": {"wood": 100}},

    # -----------------------------------------------------
    # Villager Roles and Numbers
    # -----------------------------------------------------
    "NUM_FARMERS": 10,
    "NUM_HUNTERS": 4,
    "NUM_LOGGERS": 3,
    "NUM_BLACKSMITHS": 3,

    # -----------------------------------------------------
    # Role Tools and Action Mapping
    # -----------------------------------------------------
    "ROLE_TOOLS": {
        "Farmer": ["hoe"],
        "Hunter": ["bow"],
        "Logger": ["axe"],
        "Blacksmith": []
    },
    "ROLE_ACTIONS": {
        "Farmer": "farm",
        "Hunter": "hunt",
        "Logger": "log_wood",
        "Blacksmith": "craft",
        "default": "forage"
    },

    # -----------------------------------------------------
    # Environmental Events and Adversity
    # -----------------------------------------------------
    "STORM_PROBABILITY": 0.1,
    "STORM_RESOURCE_REDUCTION": 2,
    "DISEASE_PROBABILITY": 0.05,
    "DISEASE_HEALTH_LOSS": 2,

    # -----------------------------------------------------
    # Monsters, Combat, and Cooking
    # -----------------------------------------------------
    "MONSTER_SPAWN_PROB": 0.05,
    "MONSTER_TYPES": ["Wolf", "Bear", "Goblin"],
    "MONSTER_HEALTH_RANGE": [5, 10],
    "MONSTER_DAMAGE_RANGE": [1, 3],
    "COMBAT_MAX_ROUNDS": 3,
    "COOKING_CONVERSION_RATE": 1,
    "COOKING_PROBABILITY": 0.9,

    # -----------------------------------------------------
    # Villager Personal Attributes
    # -----------------------------------------------------
    "INITIAL_HUNGER": 10,
    "INITIAL_REST": 10,
    "INITIAL_HEALTH": 80,
    "INITIAL_HAPPINESS": 10,
    "MAX_HEALTH": 100,

    # -----------------------------------------------------
    # Recovery, Skills, and Efficiency
    # -----------------------------------------------------
    "REST_RECOVERY_PER_NIGHT": 4,
    "SKILL_GAIN_PER_ACTION": 0.05,
    "MAX_SKILL_MULTIPLIER": 1.5,
    "MIN_WOOD_RESERVE_WINTER": 12,
    "WINTER_WOOD_CONSUMPTION": 2,
    "TOOL_REPAIR_WOOD": 0.5,
    "NIGHT_HEALTH_RECOVERY": 0.2,

    # -----------------------------------------------------
    # Emergency and Health Recovery
    # -----------------------------------------------------
    "EMERGENCY_HEALTH_THRESHOLD": 5,
    "EMERGENCY_COOKED_FOOD_HUNGER_BOOST": 3,
    "EMERGENCY_COOKED_FOOD_HEALTH_BOOST": 2,
    "HERB_HEALTH_BOOST": 4,
    "USE_HERB_HEALTH_THRESHOLD": 10,

    # -----------------------------------------------------
    # Social Mechanics (Marriage)
    # -----------------------------------------------------
    "MARRIAGE_PROBABILITY": 0.05,
    "MARRIAGE_HEALTH_THRESHOLD": 7,
    "MARRIAGE_HUNGER_THRESHOLD": 6,
    "MARRIAGE_FOOD_THRESHOLD": 3,
    "MARRIAGE_WOOD_THRESHOLD": 5,

    # -----------------------------------------------------
    # Spoilage and Safety Stock
    # -----------------------------------------------------
    "MAX_SPOILAGE_TICKS_PER_DAY": 1,
    "RAW_FOOD_SAFETY": 2,
    "SAFETY_STOCK": {"food": 3, "cooked_food": 3, "wood": 3},

    # -----------------------------------------------------
    # Resource Harvesting and Trading
    # -----------------------------------------------------
    "LOGWOOD_RESOURCE_DECREASE": 2,
    "FORAGE_FOOD_GAIN": 1,
    "HUNT_MAX_HARVEST": 3,

    # -----------------------------------------------------
    # Advanced and Additional Configurations
    # -----------------------------------------------------
    "LOW_NEEDS_STREAK_THRESHOLD": 1,
    "MAX_FOREST_RESOURCE": 100,
    "STORM_AFFECTED_TILE_DIVISOR": 5,
    "MAX_REST": 100,

    # -----------------------------------------------------
    # Logging and Visualization
    # -----------------------------------------------------
    "LOG_FILENAME": "simulation_log.txt",
    "CHART_FILENAME": "simulation_charts.html",
    "CHART_HEIGHT": 1600
}

# -----------------------------------------------------------------------------
# LOGGING & STATISTICS
# -----------------------------------------------------------------------------

class SimulationLog:
    def __init__(self):
        self.entries = []

    def log_action(self, day, part, villager_id, role, message):
        self.entries.append((day, part, villager_id, role, message))

    def export_log(self, filename=CONFIG["LOG_FILENAME"]):
        daily_logs = defaultdict(list)
        for day, part, villager_id, role, message in self.entries:
            daily_logs[(day, villager_id, role)].append(f"{part}: {message}")
        with open(filename, "w", encoding="utf-8") as f:
            for key in sorted(daily_logs, key=lambda x: (x[0], x[1])):
                day, villager_id, role = key
                messages_str = "; ".join(daily_logs[key])
                if villager_id == 0:
                    f.write(f"Day {day} [SYSTEM]: {messages_str}\n")
                else:
                    f.write(f"Day {day} - Villager {villager_id} ({role}): {messages_str}\n")
        print(f"Log written to {filename}")

class StatsCollector:
    def __init__(self):
        self.timeseries = []

    def record_villager_stats(self, villager):
        self.timeseries.append({
            "day": villager.world.day_count,
            "part": villager.world.world_part_of_day(),
            "villager_id": villager.id,
            "role": villager.role,
            "hunger": villager.status.hunger,
            "rest": villager.status.rest,
            "health": villager.status.health,
            "happiness": villager.status.happiness,
            "coins": villager.coins,
            "food": villager.get_item_count("food"),
            "wood": villager.get_item_count("wood"),
            "cooked_food": villager.get_item_count("cooked_food")
        })

    def _build_html_template(self, html_div, full_log, num_farmers, num_hunters, num_loggers, num_blacksmiths):
        return f"""
        <html>
          <head>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
              body {{ font-family: Arial, sans-serif; margin: 20px; }}
              #logBox {{
                width: 100%;
                height: 300px;
                overflow: auto;
                resize: vertical;
              }}
              #controls {{
                margin-top: 20px;
              }}
            </style>
          </head>
          <body>
            <!-- Plotly Chart -->
            {html_div}
        
            <!-- Additional UI Controls -->
            <div id="controls">
              <div>
                <label for="logSizeSlider">Log Box Height:</label>
                <input type="range" id="logSizeSlider" min="100" max="800" value="300">
                <span id="sliderValue">300px</span>
              </div>
              <div style="margin-top: 10px;">
                <label for="villagerFilter">Filter by Villager:</label>
                <select id="villagerFilter" multiple style="width: 300px;">
                  <option value="all" selected>All</option>
                </select>
              </div>
              <div style="margin-top: 10px;">
                <textarea id="logBox" readonly>{full_log}</textarea>
              </div>
            </div>
        
            <script>
              document.addEventListener('DOMContentLoaded', function() {{
                // Log box height slider
                var slider = document.getElementById('logSizeSlider');
                var logBox = document.getElementById('logBox');
                var sliderValue = document.getElementById('sliderValue');
                slider.addEventListener('input', function() {{
                  logBox.style.height = slider.value + "px";
                  sliderValue.textContent = slider.value + "px";
                }});
        
                // Populate villager filter dropdown with names.
                var villagerFilter = document.getElementById('villagerFilter');
                var options = [];
                options.push({{value: 'all', label: 'All'}});
                var numFarmers = {num_farmers};
                var numHunters = {num_hunters};
                var numLoggers = {num_loggers};
                var numBlacksmiths = {num_blacksmiths};
                var id = 1;
                for (var i = 0; i < numFarmers; i++) {{
                   options.push({{value: id.toString(), label: 'Villager ' + id + ' (Farmer)'}});
                   id++;
                }}
                for (var i = 0; i < numHunters; i++) {{
                   options.push({{value: id.toString(), label: 'Villager ' + id + ' (Hunter)'}});
                   id++;
                }}
                for (var i = 0; i < numLoggers; i++) {{
                   options.push({{value: id.toString(), label: 'Villager ' + id + ' (Logger)'}});
                   id++;
                }}
                for (var i = 0; i < numBlacksmiths; i++) {{
                   options.push({{value: id.toString(), label: 'Villager ' + id + ' (Blacksmith)'}});
                   id++;
                }}
                options.forEach(function(opt) {{
                    var optionElem = document.createElement('option');
                    optionElem.value = opt.value;
                    optionElem.textContent = opt.label;
                    if(opt.value === 'all') {{
                      optionElem.selected = true;
                    }}
                    villagerFilter.appendChild(optionElem);
                }});
        
                // Prepare log filtering.
                var fullLogContent = document.getElementById('logBox').value;
                var logLines = fullLogContent.split('\\n');
        
                function updateLogDisplay() {{
                  var selectedOptions = Array.from(villagerFilter.selectedOptions).map(function(opt) {{
                    return opt.value;
                  }});
        
                  if (selectedOptions.includes('all')) {{
                    document.getElementById('logBox').value = logLines.join('\\n');
                  }} else {{
                    var filteredLog = logLines.filter(function(line) {{
                      var match = line.match(/Villager (\\d+)/);
                      if (match) {{
                        var vid = match[1];
                        return selectedOptions.includes(vid);
                      }}
                      return false;
                    }});
                    document.getElementById('logBox').value = filteredLog.join('\\n');
                  }}
                }}
        
                villagerFilter.addEventListener('change', updateLogDisplay);
              }});
            </script>
          </body>
        </html>
        """

    def generate_charts(self, filename=CONFIG["CHART_FILENAME"]):
        df = pd.DataFrame(self.timeseries)
        part_order = {p: i for i, p in enumerate(CONFIG["PARTS_OF_DAY"])}
        df["sim_time"] = (df["day"] - 1) * len(CONFIG["PARTS_OF_DAY"]) + df["part"].map(part_order)

        fig = make_subplots(
            rows=6, cols=1, shared_xaxes=True,
            subplot_titles=[
                "Hunger Over Time (Individual)",
                "Health Over Time (Individual)",
                "Happiness Over Time (Individual)",
                "Average Coins Over Time by Role",
                "Average Health Over Time by Role",
                "Average Happiness Over Time by Role"
            ],
            vertical_spacing=0.05
        )

        season_change_interval = CONFIG["DAYS_PER_SEASON"]
        max_sim_time = int(df["sim_time"].max())
        seasons = CONFIG["SEASONS"]
        for i in range(0, max_sim_time + 1, season_change_interval * len(CONFIG["PARTS_OF_DAY"])):
            for row in range(1, 7):
                fig.add_vline(
                    x=i,
                    line_dash="dot",
                    line_color="gray",
                    annotation_text=seasons[(i // (season_change_interval * len(CONFIG["PARTS_OF_DAY"]))) % len(seasons)],
                    annotation_position="top left",
                    row=row, col=1
                )

        for vid in df["villager_id"].unique():
            subdf = df[df["villager_id"] == vid].sort_values("sim_time")
            fig.add_trace(
                go.Scatter(
                    x=subdf["sim_time"],
                    y=subdf["hunger"],
                    mode="lines",
                    name=f"V{vid}",
                    legendgroup=f"V{vid}"
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=subdf["sim_time"],
                    y=subdf["health"],
                    mode="lines",
                    name=f"V{vid}",
                    showlegend=False,
                    legendgroup=f"V{vid}"
                ),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=subdf["sim_time"],
                    y=subdf["happiness"],
                    mode="lines",
                    name=f"V{vid}",
                    showlegend=False,
                    legendgroup=f"V{vid}"
                ),
                row=3, col=1
            )

        avg_coins = df.groupby(["role", "sim_time"], as_index=False)["coins"].mean()
        for role in avg_coins["role"].unique():
            role_df = avg_coins[avg_coins["role"] == role].sort_values("sim_time")
            fig.add_trace(
                go.Scatter(
                    x=role_df["sim_time"],
                    y=role_df["coins"],
                    mode="lines",
                    name=f"{role} Avg Coins"
                ),
                row=4, col=1
            )

        avg_health = df.groupby(["role", "sim_time"], as_index=False)["health"].mean()
        for role in avg_health["role"].unique():
            role_df = avg_health[avg_health["role"] == role].sort_values("sim_time")
            fig.add_trace(
                go.Scatter(
                    x=role_df["sim_time"],
                    y=role_df["health"],
                    mode="lines",
                    name=f"{role} Avg Health"
                ),
                row=5, col=1
            )

        avg_happiness = df.groupby(["role", "sim_time"], as_index=False)["happiness"].mean()
        for role in avg_happiness["role"].unique():
            role_df = avg_happiness[avg_happiness["role"] == role].sort_values("sim_time")
            fig.add_trace(
                go.Scatter(
                    x=role_df["sim_time"],
                    y=role_df["happiness"],
                    mode="lines",
                    name=f"{role} Avg Happiness"
                ),
                row=6, col=1
            )

        fig.update_layout(height=CONFIG["CHART_HEIGHT"], title_text="Villager Metrics Over Time with Seasonal Markers", hovermode="x unified")
        fig.update_xaxes(title_text="Simulation Time (Day Part)", row=6, col=1)

        html_div = pyo.plot(fig, include_plotlyjs=False, output_type='div')

        try:
            with open(CONFIG["LOG_FILENAME"], "r", encoding="utf-8") as log_file:
                full_log = log_file.read()
        except Exception as e:
            full_log = "Simulation log not found."

        num_farmers = CONFIG.get("NUM_FARMERS", 0)
        num_hunters = CONFIG.get("NUM_HUNTERS", 0)
        num_loggers = CONFIG.get("NUM_LOGGERS", 0)
        num_blacksmiths = CONFIG.get("NUM_BLACKSMITHS", 0)

        html_template = self._build_html_template(html_div, full_log, num_farmers, num_hunters, num_loggers, num_blacksmiths)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"Charts and log monitor generated: {filename}")

# -----------------------------------------------------------------------------
# ITEM CLASS
# -----------------------------------------------------------------------------

class Item:
    def __init__(self, name, quantity, durability=None):
        self.name = name
        self.quantity = quantity
        self.durability = durability
        item_config = CONFIG["ITEMS"].get(name, {})
        self.spoilage_rate = item_config.get("spoilage", 0)

    def is_tool(self):
        return self.durability is not None and self.durability > 0

    def degrade_spoilage(self, ticks=1):
        if self.spoilage_rate <= 0:
            return 0
        self.spoilage_rate -= ticks
        if self.spoilage_rate <= 0:
            spoiled = self.quantity
            self.quantity = 0
            return spoiled
        return 0

    def __repr__(self):
        return f"<Item {self.name}, qty={self.quantity}, dur={self.durability}, spoilage={self.spoilage_rate}>"

    def is_repairable(self):
        return self.is_tool() and self.durability < CONFIG["ITEMS"][self.name]["durability"]

# -----------------------------------------------------------------------------
# MONSTER CLASS
# -----------------------------------------------------------------------------

class Monster:
    def __init__(self, name, health, damage):
        self.name = name
        self.health = health
        self.damage = damage
        self.alive = True

    def attack_villager(self, villager):
        if not self.alive or villager.status.health <= 0:
            return
        total_damage = 0
        last_monster_damage = 0
        for _ in range(3):
            villager_damage = random.randint(1, 3)
            monster_damage = random.randint(1, self.damage)
            last_monster_damage = monster_damage
            self.health -= villager_damage
            actual_damage = min(monster_damage, villager.status.health)
            total_damage += actual_damage
            villager.status.health = max(0, villager.status.health - monster_damage)
            if self.health <= 0 or villager.status.health <= 0:
                break
        self.alive = self.health > 0
        villager.log(f"Combat with {self.name}! Total lost HP: {total_damage}. Monster {'fled' if self.alive else 'died'}.")

    def is_dead(self):
        return self.health <= 0

# -----------------------------------------------------------------------------
# ACTIONS CLASS
# -----------------------------------------------------------------------------

class Action:
    @staticmethod
    def farm(villager):
        tile = villager.find_field_tile()
        if not tile:
            Action.forage(villager)
            return
        max_field = villager.world.config["MAX_FIELD_RESOURCE"]
        if tile.resource_level >= max_field:
            villager.world.log.log_action(
                villager.world.day_count, villager.world.world_part_of_day(),
                villager.id, villager.role,
                "Field at max resource, foraging instead."
            )
            Action.forage(villager)
            return

        villager.gain_skill()
        season = villager.world.get_current_season()
        if season == "Autumn":
            amount = min(tile.resource_level, max_field)
            amount = Action.get_yield_with_tool(villager, "hoe", amount, max(1, amount // 2))
            amount = int(amount * villager.skill_level)
            villager.add_item("food", amount)
            tile.resource_level = 0
            villager.world.log.log_action(
                villager.world.day_count, villager.world.world_part_of_day(),
                villager.id, villager.role,
                f"Harvested {amount} food (tile resource now=0)."
            )
        elif season in ["Spring", "Summer"]:
            cfg = villager.world.config
            amount = Action.get_yield_with_tool(villager, "hoe", cfg["BASE_FARM_YIELD"], cfg["FALLBACK_FARM_YIELD"])
            tile.resource_level = min(tile.resource_level + amount, max_field)
            villager.world.log.log_action(
                villager.world.day_count, villager.world.world_part_of_day(),
                villager.id, villager.role,
                f"Prepared fields (+{amount}), resource now {tile.resource_level}."
            )
        else:  # Winter
            tile.resource_level = int(tile.resource_level * villager.world.config["WINTER_FIELD_LOSS"])
            villager.world.log.log_action(
                villager.world.day_count, villager.world.world_part_of_day(),
                villager.id, villager.role,
                f"Winter field loss: resources now {tile.resource_level}."
            )
            Action.forage(villager)

    @staticmethod
    def hunt(villager):
        tile = villager.find_tile_with_resources("forest")
        if tile and tile.resource_level > 0:
            harvest = min(CONFIG["HUNT_MAX_HARVEST"], tile.resource_level)
            tile.resource_level -= harvest
            villager.add_item("food", harvest)
            villager.log(f"Hunting => +{harvest} food (tile resource now={tile.resource_level}).")
        else:
            Action.forage(villager)

    @staticmethod
    def log_wood(villager):
        villager.gain_skill()
        tile = villager.find_tile_with_resources("forest")
        if tile is None:
            Action.forage(villager)
            return
        cfg = villager.world.config
        max_multiplier = cfg.get("MAX_LOG_WOOD_YIELD_MULTIPLIER", 3.0)
        amount = Action.get_yield_with_tool(
            villager, "axe",
            cfg["BASE_LOG_YIELD"],
            cfg["FALLBACK_LOG_YIELD"],
            max_multiplier
        )
        villager.add_item("wood", amount)
        tile.resource_level = max(tile.resource_level - CONFIG["LOGWOOD_RESOURCE_DECREASE"], 0)
        villager.log(f"Logging => +{amount} wood (tile resource now={tile.resource_level}).")

    @staticmethod
    def craft(villager):
        cfg = villager.world.config
        # Attempt to repair existing tools.
        for tool_list in villager.inventory["tools"].values():
            for item in tool_list:
                if item.is_tool() and item.is_repairable():
                    wood_needed = (cfg["ITEMS"][item.name]["durability"] - item.durability) * cfg["TOOL_REPAIR_WOOD"]
                    if villager.world.market.get_stock("wood") >= wood_needed:
                        item.durability = cfg["ITEMS"][item.name]["durability"]
                        villager.world.market.remove_stock("wood", wood_needed)
                        villager.log(f"Repaired {item.name} using {wood_needed} wood")
                        return
        # Craft a new tool if needed.
        tool_needs = defaultdict(int)
        for v in villager.world.villagers:
            for tname in cfg["ROLE_TOOLS"].get(v.role, []):
                if v.get_item_count(tname) < 1:
                    tool_needs[tname] += 1
        for tool, need in sorted(tool_needs.items(), key=lambda x: -x[1]):
            if villager.world.market.get_stock("wood") >= 1:
                success, revenue, actual_qty = villager.world.market.attempt_sell(tool, 1)
                if success:
                    villager.world.market.remove_stock("wood", 1)
                    villager.coins += revenue
                    villager.log(f"Crafted and sold 1 {tool} for {revenue} coins (consumed 1 wood)")
                    return

    @staticmethod
    def forage(villager):
        villager.add_item("food", CONFIG["FORAGE_FOOD_GAIN"])
        villager.log(f"Foraging => +{CONFIG['FORAGE_FOOD_GAIN']} food.")

    @staticmethod
    def cook_food(villager):
        rate = villager.world.config["COOKING_CONVERSION_RATE"]
        if villager.get_item_count("food") < rate:
            villager.log(f"Need {rate} food to cook.")
            return
        villager.remove_item("food", rate)
        villager.add_item("cooked_food", 1)
        villager.log(f"Cooked {rate} food => 1 cooked_food")

    @staticmethod
    def get_yield_with_tool(villager, tool_name, base_yield, fallback_yield, max_multiplier=3.0):
        if villager.get_item_count(tool_name) > 0:
            villager.degrade_item(tool_name)
            skill_bonus = min(villager.skill_level, villager.world.config["MAX_SKILL_MULTIPLIER"] - 1)
            effective_multiplier = min(1 + skill_bonus + villager.world.config["TOOL_YIELD_BASE"], max_multiplier)
            return int(base_yield * effective_multiplier)
        else:
            return int(fallback_yield * villager.skill_level)

    @staticmethod
    def purchase_food_if_needed(villager):
        if villager.get_item_count("food") == 0:
            success, cost = villager.world.market.attempt_buy("food", 1)
            if success and villager.coins >= cost:
                villager.coins -= cost
                villager.world.market.finalize_buy("food", 1)
                villager.add_item("food", 1)
                villager.world.market.log_purchase(villager, "food", 1)
                villager.log(f"Purchased 1 food from market (cost: {cost} coins) due to low food supply.")
            else:
                villager.log("Unable to purchase food: insufficient funds or market shortage.")

# -----------------------------------------------------------------------------
# ROLE MANAGER
# -----------------------------------------------------------------------------

class RoleManager:
    @staticmethod
    def do_role_action(villager):
        Action.purchase_food_if_needed(villager)
        cfg = villager.world.config
        action_name = cfg["ROLE_ACTIONS"].get(villager.role, cfg["ROLE_ACTIONS"]["default"])
        action_fn = getattr(Action, action_name, Action.forage)
        action_fn(villager)

# -----------------------------------------------------------------------------
# TILE & MARKET CLASSES
# -----------------------------------------------------------------------------

class Tile:
    def __init__(self, terrain_type="field", resource_level=5):
        self.terrain_type = terrain_type
        self.resource_level = resource_level

class Market:
    def __init__(self, config, initial_stock, sim_log):
        self.config = config
        self.log = sim_log
        self.stock = dict(initial_stock)

    def _attempt_transaction(self, item_name, qty, is_buy=True):
        if is_buy:
            available = self.get_stock(item_name)
            if available == 0:
                return False, 0, 0
            # For wood, allow purchasing a partial amount if there isn't enough stock.
            if item_name == "wood":
                actual_qty = min(qty, available)
            else:
                if available < qty:
                    return False, 0, 0
                actual_qty = qty
            price = self.get_price(item_name)
            return True, price * actual_qty, actual_qty
        else:
            price = self.get_price(item_name)
            return True, price * qty, qty

    def attempt_buy(self, item_name, qty=1):
        return self._attempt_transaction(item_name, qty, is_buy=True)

    def finalize_buy(self, item_name, qty=1):
        self.stock[item_name] = max(0, self.stock.get(item_name, 0) - qty)

    def attempt_sell(self, item_name, qty=1):
        return self._attempt_transaction(item_name, qty, is_buy=False)

    def finalize_sell(self, item_name, qty=1):
        self.add_stock(item_name, qty)

    def get_price(self, item_name):
        base_price = self.config["ITEMS"].get(item_name, {}).get("price", 1)
        max_stock = self.config["MARKET_MAX_STOCK"].get(item_name, 999999)
        if self.stock.get(item_name, 0) >= max_stock:
            return base_price * self.config["MARKET_PRICE_DECAY"]
        return base_price

    def get_stock(self, item_name):
        return self.stock.get(item_name, 0)

    def add_stock(self, item_name, qty):
        max_allowed = self.config["MARKET_MAX_STOCK"].get(item_name, 999999)
        current = self.stock.get(item_name, 0)
        new_total = current + qty
        if new_total > max_allowed:
            self.stock[item_name] = max_allowed
            overflow = new_total - max_allowed
            if overflow > 0:
                self.log.log_action(0, "SYSTEM", 0, "MARKET",
                                    f"Market reached max capacity for {item_name}, overflow of {overflow} discarded.")
        else:
            self.stock[item_name] = new_total

    def remove_stock(self, item_name, qty):
        self.stock[item_name] = max(0, self.stock.get(item_name, 0) - qty)

    def log_purchase(self, villager, item_name, qty):
        day = villager.world.day_count
        part = villager.world.world_part_of_day()
        left = self.stock.get(item_name, 0)
        self.log.log_action(day, part, villager.id, villager.role,
                             f"Bought {qty} {item_name}. Market now has {left} left.")

    def log_sale(self, villager, item_name, qty, revenue):
        day = villager.world.day_count
        part = villager.world.world_part_of_day()
        self.log.log_action(day, part, villager.id, villager.role,
                             f"Sold {qty} {item_name} for {revenue} coins. Market stock now={self.stock.get(item_name, 0)}.")

# -----------------------------------------------------------------------------
# EVENT MANAGER
# -----------------------------------------------------------------------------

class EventManager:
    def __init__(self, config, sim_log):
        self.config = config
        self.log = sim_log

    def handle_morning_events(self, world):
        if random.random() < self.config["STORM_PROBABILITY"]:
            self.trigger_storm(world)
        if random.random() < self.config["DISEASE_PROBABILITY"]:
            self.trigger_disease(world)
        if random.random() < self.config["MONSTER_SPAWN_PROB"]:
            self.trigger_monster_attack(world)

    def trigger_storm(self, world):
        reduction = self.config["STORM_RESOURCE_REDUCTION"]
        num_tiles = (world.width * world.height) // self.config["STORM_AFFECTED_TILE_DIVISOR"]
        for _ in range(num_tiles):
            rx = random.randint(0, world.width - 1)
            ry = random.randint(0, world.height - 1)
            tile = world.grid[ry][rx]
            tile.resource_level = max(0, tile.resource_level - reduction)
        self.log.log_action(world.day_count, "Morning", 0, "EVENT",
                           f"Storm reduced resources in ~{num_tiles} tiles.")

    def trigger_disease(self, world):
        if not world.villagers:
            return
        victim = random.choice(world.villagers)
        if victim.status.health > 0:
            dmg = self.config["DISEASE_HEALTH_LOSS"]
            victim.status.health = max(0, victim.status.health - dmg)
            self.log.log_action(world.day_count, "Morning", victim.id, "EVENT",
                                 f"Disease struck villager {victim.id} => health -{dmg}.")

    def trigger_monster_attack(self, world):
        if not world.villagers:
            return
        monster_name = random.choice(world.config["MONSTER_TYPES"])
        health = random.randint(*world.config["MONSTER_HEALTH_RANGE"])
        damage = random.randint(*world.config["MONSTER_DAMAGE_RANGE"])
        monster = Monster(monster_name, health, damage)
        world.monsters.append(monster)
        victim = random.choice(world.villagers)
        self.log.log_action(world.day_count, "Morning", 0, "EVENT",
                             f"A {monster_name} spawned and attacks villager {victim.id}!")
        monster.attack_villager(victim)
        if monster.is_dead():
            world.monsters.remove(monster)

# -----------------------------------------------------------------------------
# WORLD CLASS
# -----------------------------------------------------------------------------

class World:
    def __init__(self, config, sim_log):
        self.config = config
        self.width = config["GRID_WIDTH"]
        self.height = config["GRID_HEIGHT"]
        self.log = sim_log
        self.grid = self._generate_tiles()
        self.market = Market(config, config["INITIAL_MARKET_STOCK"], sim_log)
        self.event_manager = EventManager(config, sim_log)
        self.day_count = 1
        self.part_of_day_index = 0
        self.villagers = []
        self.monsters = []
    
    @property
    def current_tick(self):
        # Compute the current tick as (day - 1) * (number of parts) + current part index.
        return (self.day_count - 1) * len(self.config["PARTS_OF_DAY"]) + self.part_of_day_index

    def _generate_tiles(self):
        dist = self.config["TERRAIN_DISTRIBUTION"]
        weighted_list = [(t_type, info["base_resource"])
                         for t_type, info in dist.items()
                         for _ in range(int(info["chance"] * 100))]
        return [
            [Tile(*random.choice(weighted_list)) for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def world_part_of_day(self):
        return self.config["PARTS_OF_DAY"][self.part_of_day_index]

    def get_current_season(self):
        season_index = ((self.day_count - 1) // self.config["DAYS_PER_SEASON"]) % len(self.config["SEASONS"])
        return self.config["SEASONS"][season_index]

    def is_winter(self):
        return self.get_current_season() == "Winter"

    def update_resources_and_events(self, part_of_day):
        if part_of_day == "Morning":
            self.event_manager.handle_morning_events(self)
        if part_of_day == "Night":
            self.regrow_resources()
        for villager in self.villagers:
            if villager.status.health <= 0:
                self.log.log_action(
                    self.day_count, self.world_part_of_day(),
                    villager.id, villager.role, "Perished from poor health"
                )
        self.villagers = [v for v in self.villagers if v.status.health > 0]

    def regrow_resources(self):
        for row in self.grid:
            for tile in row:
                if tile.terrain_type == "forest":
                    tile.resource_level = min(tile.resource_level + 1, self.config["MAX_FOREST_RESOURCE"])

    def advance_time(self):
        self.part_of_day_index += 1
        if self.part_of_day_index >= len(self.config["PARTS_OF_DAY"]):
            self.part_of_day_index = 0
            self.day_count += 1

# -----------------------------------------------------------------------------
# VILLAGER NEEDS / STATUS
# -----------------------------------------------------------------------------

class VillagerStatus:
    def __init__(self, hunger, rest, health, happiness):
        self.hunger = hunger
        self.rest = rest
        self.health = health
        self.happiness = happiness

# -----------------------------------------------------------------------------
# VILLAGER CLASS
# -----------------------------------------------------------------------------

class Villager:
    def __init__(self, vid, role, world):
        self.id = vid
        self.role = role
        self.world = world
        cfg = world.config
        self.status = VillagerStatus(cfg["INITIAL_HUNGER"], cfg["INITIAL_REST"],
                                     cfg["INITIAL_HEALTH"], cfg["INITIAL_HAPPINESS"])
        self.low_hunger_streak = 0
        self.low_rest_streak = 0
        self.coins = cfg["INITIAL_VILLAGER_COINS"]
        self.skill_level = 1.0
        self.relationship_status = "single"
        self.partner_id = None
        # Use separate buckets for resources and tools.
        self.inventory = {"resources": defaultdict(int), "tools": defaultdict(list)}
        if cfg["INITIAL_VILLAGER_FOOD"] > 0:
            self.add_item("food", cfg["INITIAL_VILLAGER_FOOD"])
        if cfg["INITIAL_VILLAGER_WOOD"] > 0:
            self.add_item("wood", cfg["INITIAL_VILLAGER_WOOD"])
        self.max_skill = {
            "Farmer": cfg["MAX_SKILL_MULTIPLIER"],
            "Hunter": cfg["MAX_SKILL_MULTIPLIER"],
            "Logger": cfg["MAX_SKILL_MULTIPLIER"]
        }

    def adjust_health(self, delta):
        max_health = self.world.config.get("MAX_HEALTH", 100)
        new_health = self.status.health + delta
        new_health = max(0, new_health)
        self.status.health = min(new_health, max_health)

    def add_item(self, item_name, quantity=1):
        if quantity <= 0:
            return
        item_def = self.world.config["ITEMS"].get(item_name, {})
        durability = item_def.get("durability", 0)
        if durability > 0:
            for _ in range(quantity):
                self.inventory["tools"][item_name].append(Item(item_name, 1, durability))
        else:
            self.inventory["resources"][item_name] += quantity

    def remove_item(self, item_name, quantity=1):
        if quantity <= 0:
            return 0
        item_def = self.world.config["ITEMS"].get(item_name, {})
        durability = item_def.get("durability", 0)
        removed = 0
        if durability > 0:
            tools_list = self.inventory["tools"].get(item_name, [])
            while tools_list and removed < quantity:
                tools_list.pop(0)
                removed += 1
            if not tools_list and item_name in self.inventory["tools"]:
                del self.inventory["tools"][item_name]
        else:
            current = self.inventory["resources"].get(item_name, 0)
            removed = min(current, quantity)
            self.inventory["resources"][item_name] = current - removed
            if self.inventory["resources"][item_name] == 0:
                del self.inventory["resources"][item_name]
        return removed

    def get_item_count(self, item_name):
        item_def = self.world.config["ITEMS"].get(item_name, {})
        durability = item_def.get("durability", 0)
        if durability > 0:
            return len(self.inventory["tools"].get(item_name, []))
        else:
            return self.inventory["resources"].get(item_name, 0)

    def degrade_item(self, item_name):
        item_def = self.world.config["ITEMS"].get(item_name, {})
        durability = item_def.get("durability", 0)
        if durability <= 0:
            return
        tools_list = self.inventory["tools"].get(item_name, [])
        if tools_list:
            tool = tools_list[0]
            tool.durability -= 1
            if tool.durability == 1:
                self.log(f"{item_name} is about to break! (1 use left)")
            if tool.durability <= 0:
                self.log(f"{item_name} broke! Durability expired.")
                tools_list.pop(0)
            if not tools_list:
                del self.inventory["tools"][item_name]

    def update_spoilage(self):
        """
        Updates spoilage of resource items.
        Every item with spoilage > 0 will be checked; if the current tick is a multiple 
        of its spoilage rate, those items are removed and logged.
        """
        current_tick = self.world.current_tick  # Make sure that current_tick is updated appropriately in advance_time
        for item_name in list(self.inventory["resources"].keys()):
            spoilage_rate = self.world.config["ITEMS"].get(item_name, {}).get("spoilage", 0)
            if spoilage_rate > 0 and (current_tick % spoilage_rate == 0):
                quantity = self.inventory["resources"][item_name]
                self.log.log_action(
                    self.world.day_count, self.world.world_part_of_day(),
                    self.id, self.role, f"{quantity} {item_name}(s) spoiled and were discarded."
                )
                # Remove all of the spoiled item
                self.remove_item(item_name, quantity)

    def handle_morning(self):
        if self.status.health < self.world.config["EMERGENCY_HEALTH_THRESHOLD"]:
            self.emergency_recover()
        self.eat_if_needed()
        self.sell_surplus()
        self.buy_essential_items()
        self.buy_primary_tool()
        RoleManager.do_role_action(self)
        
        # Only cook if raw food exceeds the safety reserve
        raw_food_count = self.get_item_count("food")
        raw_food_safety = self.world.config.get("RAW_FOOD_SAFETY", 2)
        if raw_food_count > raw_food_safety:
            Action.cook_food(self)
        
        if (self.status.health < self.world.config["USE_HERB_HEALTH_THRESHOLD"] and 
            self.get_item_count("herb") > 0):
            self.use_herb()

    def handle_afternoon(self):
        RoleManager.do_role_action(self)
        self.sell_surplus()

    def handle_night(self):
        if self.world.world_part_of_day() != "Night":
            self.log("Attempted to sleep outside of night time. Action not permitted.")
            return
        if self.world.is_winter():
            self.consume_wood_at_night()
        self.adjust_health(self.world.config["NIGHT_HEALTH_RECOVERY"])
        self.log(f"Slept during the night => health +{self.world.config['NIGHT_HEALTH_RECOVERY']}")
        self.update_needs_and_penalties()

    def perform_part_of_day(self, part_of_day):
        if self.status.health <= 0:
            if part_of_day == "Morning":
                self.log("Health is 0 => incapacitated, no actions.")
            return
        actions = {
            "Morning": self.handle_morning,
            "Afternoon": self.handle_afternoon,
            "Night": self.handle_night
        }
        action = actions.get(part_of_day, lambda: None)
        action()
        self.update_spoilage()

    def eat_if_needed(self):
        while self.status.hunger < 7:
            if self.get_item_count("cooked_food") > 0:
                self.remove_item("cooked_food", 1)
                self.status.hunger += 3
                self.adjust_health(2)
                self.log("Ate 1 cooked_food => hunger +3, health +2")
            elif self.get_item_count("food") > 0:
                self.remove_item("food", 1)
                self.status.hunger += 2
                self.log("Ate 1 food => hunger +2")
            else:
                break

    def buy_essential_items(self):
        target_food = max(3, self.get_item_count("cooked_food"))
        if self.get_item_count("cooked_food") < target_food:
            self.buy_item("cooked_food", 1)
        
        # Wood purchase logic
        required_wood = self.world.config["MIN_WOOD_RESERVE_WINTER"] if self.world.is_winter() else 3
        current_wood = self.get_item_count("wood")
        
        if current_wood < required_wood:
            needed = required_wood - current_wood
            # Attempt to buy whatever is available if full amount isn't in market
            success = self.buy_item("wood", needed)
            if not success:
                # Try buying whatever remaining stock exists
                market_stock = self.world.market.get_stock("wood")
                if market_stock > 0:
                    self.buy_item("wood", market_stock)

    def buy_primary_tool(self):
        if self.world.get_current_season() == "Winter" and self.get_item_count("wood") < self.world.config["MIN_WOOD_RESERVE_WINTER"]:
            return
        for tool_name in self.world.config["ROLE_TOOLS"].get(self.role, []):
            if self.get_item_count(tool_name) < 1:
                self.buy_item(tool_name, 1)

    def sell_item(self, item_name, qty=1):
        market = self.world.market
        success, revenue, actual_qty = market.attempt_sell(item_name, qty)
        if not success or self.get_item_count(item_name) < qty:
            return False
        self.remove_item(item_name, qty)
        self.coins += revenue
        market.finalize_sell(item_name, qty)
        market.log_sale(self, item_name, qty, revenue)
        return True

    def sell_surplus(self):
        """
        Sells any items in the inventory that exceed the safety stock.
        Uses config SAFETY_STOCK values (defaulting to a preset if not specified)
        so that the villager keeps enough for personal use.
        """
        cfg = self.world.config
        # Define a safety stock for each item if not already in the config.
        safety_stock = cfg.get("SAFETY_STOCK", {"food": 3, "cooked_food": 3, "wood": 3})
        # Iterate over resources only (tools typically are not sold automatically)
        for item_name in list(self.inventory["resources"].keys()):
            current = self.get_item_count(item_name)
            reserve = safety_stock.get(item_name, 0)
            if current > reserve:
                quantity_to_sell = current - reserve
                self.sell_item(item_name, quantity_to_sell)

    def consume_wood_at_night(self):
        needed = self.world.config["WINTER_WOOD_CONSUMPTION"]
        if self.get_item_count("wood") >= needed:
            self.remove_item("wood", needed)
            self.log(f"Burned {needed} wood on winter night.")
        else:
            penalty = self.world.config.get("NO_WOOD_PENALTY", 1)
            self.status.health = max(0, self.status.health - penalty)
            self.status.happiness = max(0, self.status.happiness - penalty)
            self.log(f"No wood => suffered cold (health & happiness -{penalty}).")

    def update_needs_and_penalties(self):
        cfg = self.world.config
        self.status.rest += cfg["REST_RECOVERY_PER_NIGHT"]
        parts = len(cfg["PARTS_OF_DAY"])
        self.status.hunger = max(0, self.status.hunger - (cfg["HUNGER_DECREMENT_PER_DAY"] / parts))
        self.status.rest = max(0, self.status.rest - (cfg["REST_DECREMENT_PER_DAY"] / parts))
        max_rest = cfg.get("MAX_REST", 100)
        self.status.rest = min(self.status.rest, max_rest)
        self.low_hunger_streak = self.low_hunger_streak + 1 if self.status.hunger < cfg["HUNGER_LOW_PENALTY_THRESHOLD"] else 0
        self.low_rest_streak = self.low_rest_streak + 1 if self.status.rest < cfg["REST_LOW_PENALTY_THRESHOLD"] else 0
        if self.low_hunger_streak > cfg["LOW_NEEDS_STREAK_THRESHOLD"]:
            self.status.health = max(0, self.status.health - cfg["HEALTH_PENALTY_FOR_LOW_NEEDS"])
            self.status.happiness = max(0, self.status.happiness - cfg["HAPPINESS_PENALTY_FOR_LOW_NEEDS"])
            self.log("Suffering from prolonged hunger => health/happiness penalty.")
        if self.low_rest_streak > cfg["LOW_NEEDS_STREAK_THRESHOLD"]:
            self.status.health = max(0, self.status.health - cfg["HEALTH_PENALTY_FOR_LOW_NEEDS"])
            self.status.happiness = max(0, self.status.happiness - cfg["HAPPINESS_PENALTY_FOR_LOW_NEEDS"])
            self.log("Suffering from prolonged lack of rest => health/happiness penalty.")

    def buy_item(self, item_name, qty=1):
        market = self.world.market
        # Unpack the result tuple: (success, cost, actual_qty)
        success, cost, actual_qty = market.attempt_buy(item_name, qty)
        if not success or cost > self.coins:
            return False
        self.coins -= cost
        market.finalize_buy(item_name, actual_qty)
        self.add_item(item_name, actual_qty)
        market.log_purchase(self, item_name, actual_qty)
        return True

    def find_field_tile(self):
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == "field" and tile.resource_level > 0:
                    return tile
        return None

    def find_tile_with_resources(self, terrain_type):
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == terrain_type and tile.resource_level > 0:
                    return tile
        return None

    def gain_skill(self):
        max_skill = self.max_skill.get(self.role, 1.5)
        self.skill_level = min(max_skill, self.skill_level + self.world.config["SKILL_GAIN_PER_ACTION"])

    def log(self, message):
        self.world.log.log_action(
            self.world.day_count,
            self.world.world_part_of_day(),
            self.id, self.role,
            message
        )

    def log_daily_summary(self):
        summary = (
            f"End of day summary - Hunger: {self.status.hunger}, Rest: {self.status.rest}, "
            f"Health: {self.status.health}, Happiness: {self.status.happiness}, Coins: {self.coins}, "
            f"Inventory: (food: {self.get_item_count('food')}, wood: {self.get_item_count('wood')}, "
            f"cooked_food: {self.get_item_count('cooked_food')})"
        )
        self.log(summary)

    def use_herb(self):
        if self.get_item_count("herb") > 0:
            self.remove_item("herb", 1)
            self.adjust_health(self.world.config["HERB_HEALTH_BOOST"])
            self.log(f"Used 1 herb => health +{self.world.config['HERB_HEALTH_BOOST']}")

    def emergency_recover(self):
        if self.status.health < self.world.config["EMERGENCY_HEALTH_THRESHOLD"]:
            if self.get_item_count("food") >= self.world.config["COOKING_CONVERSION_RATE"]:
                self.log("Emergency: Health critically low - Attempting to cook food for recovery.")
                Action.cook_food(self)
                if self.get_item_count("cooked_food") > 0:
                    self.remove_item("cooked_food", 1)
                    self.status.hunger += self.world.config["EMERGENCY_COOKED_FOOD_HUNGER_BOOST"]
                    self.adjust_health(self.world.config["EMERGENCY_COOKED_FOOD_HEALTH_BOOST"])
                    self.log(f"Emergency: Ate 1 cooked_food => hunger +{self.world.config['EMERGENCY_COOKED_FOOD_HUNGER_BOOST']}, health +{self.world.config['EMERGENCY_COOKED_FOOD_HEALTH_BOOST']}")
            else:
                self.log("Emergency: Health critically low and no food available for cooking - Attempting to buy herb.")
                if self.buy_item("herb", 1):
                    self.use_herb()
                else:
                    self.log("Emergency: Unable to buy herb for recovery.")

# -----------------------------------------------------------------------------
# SIMULATION
# -----------------------------------------------------------------------------

class Simulation:
    def __init__(self, config):
        self.config = config
        self.sim_log = SimulationLog()
        self.stats_collector = StatsCollector()
        self.world = World(config, self.sim_log)
        self.villagers = self._spawn_villagers()
        self.world.villagers = self.villagers

    def _spawn_villagers(self):
        villagers = []
        vid = 1
        for _ in range(self.config["NUM_FARMERS"]):
            villagers.append(Villager(vid, "Farmer", self.world))
            vid += 1
        for _ in range(self.config["NUM_HUNTERS"]):
            villagers.append(Villager(vid, "Hunter", self.world))
            vid += 1
        for _ in range(self.config["NUM_LOGGERS"]):
            villagers.append(Villager(vid, "Logger", self.world))
            vid += 1
        for _ in range(self.config["NUM_BLACKSMITHS"]):
            villagers.append(Villager(vid, "Blacksmith", self.world))
            vid += 1
        return villagers

    def run(self):
        max_days = self.config["TOTAL_DAYS_TO_RUN"]
        while self.world.day_count <= max_days:
            for part in self.config["PARTS_OF_DAY"]:
                if part == "Morning":
                    self._check_for_marriages()
                for v in self.villagers:
                    v.perform_part_of_day(part)
                    self.stats_collector.record_villager_stats(v)
                if part == "Night":
                    for v in self.villagers:
                        v.log_daily_summary()
                self.world.update_resources_and_events(part)
                self.world.advance_time()
        self.sim_log.export_log(self.world.config["LOG_FILENAME"])
        self.stats_collector.generate_charts(self.world.config["CHART_FILENAME"])
        webbrowser.open(self.world.config["CHART_FILENAME"])

    def _check_for_marriages(self):
        if random.random() < self.config["MARRIAGE_PROBABILITY"]:
            singles = [
                v for v in self.villagers
                if v.relationship_status == "single"
                and v.status.health > self.config["MARRIAGE_HEALTH_THRESHOLD"]
                and v.status.hunger > self.config["MARRIAGE_HUNGER_THRESHOLD"]
                and v.get_item_count("food") > self.config["MARRIAGE_FOOD_THRESHOLD"]
                and v.get_item_count("wood") > self.config["MARRIAGE_WOOD_THRESHOLD"]
            ]
            if len(singles) >= 2:
                v1, v2 = random.sample(singles, 2)
                v1.relationship_status = v2.relationship_status = "married"
                v1.partner_id, v2.partner_id = v2.id, v1.id
                self.sim_log.log_action(
                    self.world.day_count, "Morning", 0, "EVENT",
                    f"Villager {v1.id} and Villager {v2.id} got married!"
                )

if __name__ == "__main__":
    sim = Simulation(CONFIG)
    sim.run()
    sys.exit()
