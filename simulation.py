import random
import sys
import plotly.graph_objs as go
import plotly.offline as pyo
import pandas as pd
from collections import Counter

# -------------------------------------------------------------------------
#  CONFIG & CONSTANTS
# -------------------------------------------------------------------------

CONFIG = {
    "GRID_WIDTH": 10,
    "GRID_HEIGHT": 10,

    # Time & Seasons
    "DAYS_PER_SEASON": 3,  # 3 days => 4 seasons => 12 days/year
    "SEASONS": ["Spring", "Summer", "Autumn", "Winter"],
    "PARTS_OF_DAY": ["Morning", "Afternoon", "Night"],
    "TOTAL_DAYS_TO_RUN": 36,  # => 3 years

    # Market (Fixed Prices)
    "ITEM_PRICES": {
        "food": 1,
        "wood": 2,
        "axe":  5,
        "bow":  5,
        "hoe":  5,
    },

    # Surplus Thresholds
    "SURPLUS_THRESHOLDS": {
        "food": 5,
        "wood": 5
    },

    # Production Yields (with tool)
    "BASE_FARM_YIELD": 2,
    "BASE_HUNT_YIELD": 2,
    "BASE_LOG_YIELD":  2,

    # Fallback Yields
    "FALLBACK_FARM_YIELD": 1,
    "FALLBACK_HUNT_YIELD": 1,
    "FALLBACK_LOG_YIELD":  1,

    # Consumption & Needs
    "WINTER_WOOD_CONSUMPTION": 1,
    "HUNGER_DECREMENT_PER_DAY": 1,
    "REST_DECREMENT_PER_DAY":   1,
    "HUNGER_CRITICAL_THRESHOLD": 5,
    "REST_CRITICAL_THRESHOLD":    5,

    # Hunger/Rest Penalty
    "HUNGER_LOW_PENALTY_THRESHOLD": 3,
    "REST_LOW_PENALTY_THRESHOLD":   3,
    "HEALTH_PENALTY_FOR_LOW_NEEDS": 1,
    "HAPPINESS_PENALTY_FOR_LOW_NEEDS": 1,

    # Tool Durability
    "INITIAL_TOOL_DURABILITY": 10,

    # Storm & Resource Regrowth
    "STORM_PROBABILITY": 0.1,
    "STORM_RESOURCE_REDUCTION": 2,

    # A second example event
    "DISEASE_PROBABILITY": 0.05,
    "DISEASE_HEALTH_LOSS": 2,

    # Initial Stocks
    "INITIAL_MARKET_STOCK": {
        "food": 50,
        "wood": 50,
        "axe":  5,
        "bow":  5,
        "hoe":  5,
    },

    # Roles & Number of Villagers
    "NUM_FARMERS":     6,
    "NUM_HUNTERS":     2,
    "NUM_LOGGERS":     1,
    "NUM_BLACKSMITHS": 1,

    # Initial Villager Inventories
    "INITIAL_VILLAGER_FOOD":  3,
    "INITIAL_VILLAGER_WOOD":  2,
    "INITIAL_VILLAGER_COINS": 10,

    # New config additions
    "REST_RECOVERY_PER_NIGHT": 4,
    "HUNGER_WARNING_THRESHOLD": 3,
    "SKILL_GAIN_PER_ACTION": 0.3,
    "MIN_TOOL_DURABILITY_BONUS": 0.2,
    "MIN_WOOD_RESERVE_WINTER": 2,

    # Role->Preferred Tools
    "ROLE_TOOLS": {
        "Farmer": ["hoe"],
        "Hunter": ["bow"],
        "Logger": ["axe"],
        "Blacksmith": []
    },

    # Terrain distribution
    "TERRAIN_DISTRIBUTION": {
        "forest": {"chance": 0.3, "base_resource": 5},
        "field":  {"chance": 0.5, "base_resource": 1},
        "water":  {"chance": 0.2, "base_resource": 0}
    },

    "MAX_FIELD_RESOURCE": 20,
}

# -------------------------------------------------------------------------
#  LOGGING & STATISTICS
# -------------------------------------------------------------------------

class SimulationLog:
    def __init__(self):
        self.entries = []

    def log_action(self, day, part, villager_id, role, message):
        self.entries.append((day, part, villager_id, role, message))

    def export_log(self, filename="simulation_log.txt"):
        with open(filename, "w", encoding="utf-8") as f:
            for day, part, vid, role, msg in self.entries:
                line = f"Day {day} [{part}] - Villager {vid} ({role}): {msg}\n"
                f.write(line)
        print(f"Log written to {filename}")


class StatsCollector:
    def __init__(self):
        self.timeseries = []

    def record_villager_stats(self, villager):
        data_point = {
            "day":         villager.world.day_count,
            "part":        villager.world_part_of_day(),
            "villager_id": villager.id,
            "role":        villager.role,
            "hunger":      villager.status.hunger,
            "rest":        villager.status.rest,
            "health":      villager.status.health,
            "happiness":   villager.status.happiness,
            "coins":       villager.coins,
            "food":        villager.get_total_resource("food"),
            "wood":        villager.get_total_resource("wood")
        }
        self.timeseries.append(data_point)

    def generate_charts(self, filename="simulation_charts.html"):
        df = pd.DataFrame(self.timeseries).reset_index().rename(columns={"index": "time_step"})
        fig = go.Figure()

        # Plot each villager's hunger, health, etc. over time
        for vid in df["villager_id"].unique():
            subdf = df[df["villager_id"] == vid]
            fig.add_trace(go.Scatter(
                x=subdf["time_step"], y=subdf["hunger"],
                mode="lines", name=f"Villager {vid} - Hunger"
            ))
            fig.add_trace(go.Scatter(
                x=subdf["time_step"], y=subdf["health"],
                mode="lines", name=f"Villager {vid} - Health"
            ))
            fig.add_trace(go.Scatter(
                x=subdf["time_step"], y=subdf["happiness"],
                mode="lines", name=f"Villager {vid} - Happiness"
            ))

        fig.update_layout(title="Villagers' Hunger/Health/Happiness Over Time",
                          xaxis_title="Time Step",
                          yaxis_title="Value")

        html_div = pyo.plot(fig, include_plotlyjs=False, output_type='div')
        with open(filename, "w", encoding="utf-8") as f:
            f.write(
                "<html><head>"
                "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>"
                "</head><body>\n"
            )
            f.write(html_div)
            f.write("\n</body></html>")
        print(f"Charts generated: {filename}")


# -------------------------------------------------------------------------
#  ITEM CLASS
# -------------------------------------------------------------------------

class Item:
    """
    If durability > 0, treat it as a tool. Otherwise, it's a resource.
    quantity=1 for tools by default, but can be more for resources.
    """
    def __init__(self, name, quantity=1, durability=0):
        self.name = name
        self.quantity = quantity
        self.durability = durability

    def is_tool(self):
        return self.durability > 0

    def __repr__(self):
        return f"<Item {self.name}, qty={self.quantity}, dur={self.durability}>"


# -------------------------------------------------------------------------
#  ACTIONS CLASS
# -------------------------------------------------------------------------

class Action:
    """
    Encapsulate major logic for each action. They do skill gain for the villager,
    then produce or consume items, etc.
    """

    @staticmethod
    def farm(villager):
        tile = villager.find_owned_or_public_field()
        if not tile:
            Action.forage(villager)
            return
            
        max_field = villager.world.config["MAX_FIELD_RESOURCE"]
        # Check if field is already maximized
        if tile.resource_level >= max_field:
            villager.log("Field already maximized, foraging instead")
            Action.forage(villager)
            return

        villager.gain_skill()
        season = villager.world.get_current_season()
        if season == "Autumn":
            # Harvest
            amount = Action.get_yield_with_tool(
                villager,
                tool_name="hoe",
                base_yield=tile.resource_level,  # harvest all
                fallback_yield=max(1, tile.resource_level // 2)
            )
            amount = int(amount * villager.skill_level)
            villager.add_resource("food", amount)
            villager.world.log.log_action(
                villager.world.day_count, villager.world_part_of_day(),
                villager.id, villager.role,
                f"Harvested {amount} food (tile resource now=0)."
            )
            tile.resource_level = 0

        elif season in ["Spring", "Summer"]:
            # Add validation to prevent overfilling
            new_level = min(
                tile.resource_level + 2,
                villager.world.config["MAX_FIELD_RESOURCE"]
            )
            tile.resource_level = max(0, new_level)  # Prevent negative values
            villager.world.log.log_action(
                villager.world.day_count, villager.world_part_of_day(),
                villager.id, villager.role,
                f"Prepared fields (resource now {tile.resource_level})."
            )

        else:  # Winter
            villager.world.log.log_action(
                villager.world.day_count, villager.world_part_of_day(),
                villager.id, villager.role,
                "Cannot farm in winter, so foraging."
            )
            Action.forage(villager)

    @staticmethod
    def hunt(villager):
        villager.gain_skill()
        tile = villager.find_tile_with_resources("forest")
        if tile is None:
            return Action.forage(villager)

        cfg = villager.world.config
        amount = Action.get_yield_with_tool(
            villager,
            tool_name="bow",
            base_yield=cfg["BASE_HUNT_YIELD"],
            fallback_yield=cfg["FALLBACK_HUNT_YIELD"]
        )
        villager.add_resource("food", amount)

        tile.resource_level = max(tile.resource_level - 1, 0)
        villager.world.log.log_action(
            villager.world.day_count, villager.world_part_of_day(),
            villager.id, villager.role,
            f"Hunting => +{amount} food (tile resource now={tile.resource_level})."
        )

    @staticmethod
    def log_wood(villager):
        villager.gain_skill()
        tile = villager.find_tile_with_resources("forest")
        if tile is None:
            return Action.forage(villager)

        cfg = villager.world.config
        amount = Action.get_yield_with_tool(
            villager,
            tool_name="axe",
            base_yield=cfg["BASE_LOG_YIELD"],
            fallback_yield=cfg["FALLBACK_LOG_YIELD"]
        )
        villager.add_resource("wood", amount)

        tile.resource_level = max(tile.resource_level - 2, 0)
        villager.world.log.log_action(
            villager.world.day_count, villager.world_part_of_day(),
            villager.id, villager.role,
            f"Logging => +{amount} wood (tile resource now={tile.resource_level})."
        )

    @staticmethod
    def craft(villager):
        villager.gain_skill()
        tool_demand = Counter()
        for v in villager.world.villagers:
            tools_needed = CONFIG["ROLE_TOOLS"].get(v.role, [])
            tool_demand.update(tools_needed)

        if tool_demand:
            least_available_tool = min(
                tool_demand.keys(),
                key=lambda t: villager.world.market.stock.get(t, 0)
            )
            target_tool = least_available_tool
        else:
            target_tool = random.choice(["axe", "bow", "hoe"])

        # Need 1 wood to craft
        if villager.get_total_resource("wood") < 1:
            villager.world.market.buy(villager, "wood", 1)

        if villager.get_total_resource("wood") < 1:
            villager.world.log.log_action(
                villager.world.day_count, villager.world_part_of_day(),
                villager.id, villager.role,
                "Wanted to craft but no wood available."
            )
            return

        villager.remove_resource("wood", 1)
        villager.add_tool(target_tool, 1)
        villager.world.market.sell(villager, target_tool, 1)
        villager.world.log.log_action(
            villager.world.day_count, villager.world_part_of_day(),
            villager.id, villager.role,
            f"Crafted & sold 1 {target_tool} (consumed 1 wood)."
        )

    @staticmethod
    def forage(villager):
        villager.add_resource("food", 1)
        villager.world.log.log_action(
            villager.world.day_count, villager.world_part_of_day(),
            villager.id, villager.role,
            "Foraging => +1 food."
        )

    @staticmethod
    def get_yield_with_tool(villager, tool_name, base_yield, fallback_yield):
        """
        Helper to unify logic: if villager has a tool, degrade it and return base_yield.
        Otherwise, fallback_yield.
        """
        if villager.get_tool_count(tool_name) > 0:
            villager.degrade_tool(tool_name)
            # Apply skill multiplier to both base and fallback
            return int(base_yield * villager.skill_level)
        else:
            return int(fallback_yield * villager.skill_level)


# -------------------------------------------------------------------------
#  ROLE MANAGER
# -------------------------------------------------------------------------

class RoleManager:
    @staticmethod
    def do_role_action(villager):
        role = villager.role
        if role == "Farmer":
            Action.farm(villager)
        elif role == "Hunter":
            Action.hunt(villager)
        elif role == "Logger":
            Action.log_wood(villager)
        elif role == "Blacksmith":
            Action.craft(villager)
        else:
            Action.forage(villager)


# -------------------------------------------------------------------------
#  TILE & MARKET
# -------------------------------------------------------------------------

class Tile:
    def __init__(self, terrain_type="field", resource_level=5, owner_id=None):
        self.terrain_type = terrain_type
        self.resource_level = resource_level
        self.owner_id = owner_id


class Market:
    def __init__(self, prices, initial_stock, sim_log):
        self.prices = prices
        self.stock = dict(initial_stock)  # simple int-based stock
        self.log = sim_log

    def buy(self, villager, item_name, qty=1):
        if self.stock.get(item_name, 0) < qty:
            return False
        cost = self.prices[item_name] * qty
        if villager.coins < cost:
            return False

        villager.coins -= cost
        self.stock[item_name] -= qty

        if self.is_tool(item_name):
            villager.add_tool(item_name, qty)
        else:
            villager.add_resource(item_name, qty)

        day = villager.world.day_count
        part = villager.world_part_of_day()
        self.log.log_action(day, part, villager.id, villager.role,
                            f"Bought {qty} {item_name}. Market now has {self.stock[item_name]} left.")
        return True

    def sell(self, villager, item_name, qty=1):
        revenue = self.prices[item_name] * qty

        if self.is_tool(item_name):
            if villager.get_tool_count(item_name) < qty:
                return False
            villager.remove_tool(item_name, qty)
        else:
            if villager.get_total_resource(item_name) < qty:
                return False
            villager.remove_resource(item_name, qty)

        villager.coins += revenue
        self.stock[item_name] = self.stock.get(item_name, 0) + qty

        day = villager.world.day_count
        part = villager.world_part_of_day()
        self.log.log_action(day, part, villager.id, villager.role,
                            f"Sold {qty} {item_name} for {revenue} coins. Market stock now={self.stock[item_name]}.")
        return True

    def is_tool(self, item_name):
        return item_name in ["axe", "bow", "hoe"]


# -------------------------------------------------------------------------
#  EVENT MANAGER
# -------------------------------------------------------------------------

class EventManager:
    """
    Handles random events in the world (e.g. storms, diseases).
    """
    def __init__(self, config, sim_log):
        self.config = config
        self.log = sim_log

    def handle_morning_events(self, world):
        # Storm check
        if random.random() < self.config["STORM_PROBABILITY"]:
            self.trigger_storm(world)

        # Disease check
        if random.random() < self.config["DISEASE_PROBABILITY"]:
            self.trigger_disease(world)

    def trigger_storm(self, world):
        reduction = self.config["STORM_RESOURCE_REDUCTION"]
        num_tiles = (world.width * world.height) // 4
        for _ in range(num_tiles):
            rx = random.randint(0, world.width - 1)
            ry = random.randint(0, world.height - 1)
            tile = world.grid[ry][rx]
            tile.resource_level = max(0, tile.resource_level - reduction)

        self.log.log_action(world.day_count, "Morning", 0, "EVENT",
                            f"Storm reduced resources in ~{num_tiles} tiles.")

    def trigger_disease(self, world):
        """
        Simple example: pick a random villager to lose some health.
        """
        if not world.villagers:
            return
        victim = random.choice(world.villagers)
        if victim.status.health > 0:
            victim.status.health = max(0, victim.status.health - self.config["DISEASE_HEALTH_LOSS"])
            self.log.log_action(world.day_count, "Morning", victim.id, "EVENT",
                                f"Disease struck villager {victim.id} => health -{self.config['DISEASE_HEALTH_LOSS']}.")


# -------------------------------------------------------------------------
#  WORLD
# -------------------------------------------------------------------------

class World:
    def __init__(self, config, sim_log):
        self.config = config
        self.width = config["GRID_WIDTH"]
        self.height = config["GRID_HEIGHT"]

        self.log = sim_log
        self.grid = self._generate_tiles()

        self.market = Market(config["ITEM_PRICES"], config["INITIAL_MARKET_STOCK"], sim_log)
        self.event_manager = EventManager(config, sim_log)

        self.day_count = 1
        self.season_index = 0
        self.part_of_day_index = 0

        # We'll fill this later in Simulation when we spawn villagers
        self.villagers = []

    def _generate_tiles(self):
        # Use probabilities from config
        dist = self.config["TERRAIN_DISTRIBUTION"]
        # Example: "forest": {"chance":0.3, "base_resource":5}, etc.

        # Build a weighted list of (terrain_type, base_resource)
        weighted_list = []
        for t_type, info in dist.items():
            weighted_list.extend([(t_type, info["base_resource"])] * int(info["chance"] * 100))

        grid = []
        for _y in range(self.height):
            row = []
            for _x in range(self.width):
                t_type, base_res = random.choice(weighted_list)
                row.append(Tile(t_type, base_res))
            grid.append(row)
        return grid

    def world_part_of_day(self):
        return self.config["PARTS_OF_DAY"][self.part_of_day_index]

    def get_current_season(self):
        return self.config["SEASONS"][self.season_index % len(self.config["SEASONS"])]

    def is_winter(self):
        return (self.get_current_season() == "Winter")

    def update_resources_and_events(self):
        # If it's morning, the event manager may trigger storms or diseases
        if self.part_of_day_index == 0:  # "Morning"
            self.event_manager.handle_morning_events(self)

        # Resource regrowth
        for row in self.grid:
            for tile in row:
                if tile.terrain_type == "forest":
                    tile.resource_level = min(tile.resource_level + 1, 10)

    def advance_time(self):
        self.part_of_day_index += 1
        if self.part_of_day_index >= len(self.config["PARTS_OF_DAY"]):
            self.part_of_day_index = 0
            self.day_count += 1

            # Switch season after each set of DAYS_PER_SEASON
            if (self.day_count - 1) % self.config["DAYS_PER_SEASON"] == 0 and self.day_count > 1:
                self.season_index += 1
                self.season_index %= len(self.config["SEASONS"])


# -------------------------------------------------------------------------
#  VILLAGER NEEDS / STATUS
# -------------------------------------------------------------------------

class VillagerStatus:
    def __init__(self, initial_hunger=10, initial_rest=10,
                 initial_health=10, initial_happiness=10):
        self.hunger = initial_hunger
        self.rest = initial_rest
        self.health = initial_health
        self.happiness = initial_happiness


# -------------------------------------------------------------------------
#  VILLAGER
# -------------------------------------------------------------------------

class Villager:
    def __init__(self, vid, role, world):
        self.id = vid
        self.role = role
        self.world = world
        cfg = world.config

        self.status = VillagerStatus(10, 10, 10, 10)
        self.low_hunger_streak = 0
        self.low_rest_streak = 0

        self.coins = cfg["INITIAL_VILLAGER_COINS"]
        self.skill_level = 1.0

        # We store all items in a dict: item_name -> list[Item]
        # For resources, typically 1 Item object with .quantity
        # For tools, multiple Items with durability=some_value, quantity=1
        self.items = {
            "food": [Item("food", cfg["INITIAL_VILLAGER_FOOD"], 0)],
            "wood": [Item("wood", cfg["INITIAL_VILLAGER_WOOD"], 0)]
        }

    def morning_routine(self):
        if self.status.health <= 0:
            self.log_incapacitated()
            return
        self.eat_if_needed()
        self.buy_essential_items()
        self.buy_primary_tool()
        RoleManager.do_role_action(self)
        self.sell_surplus()

    def afternoon_routine(self):
        if self.status.health <= 0:
            return
        RoleManager.do_role_action(self)
        self.sell_surplus()

    def night_routine(self):
        if self.status.health <= 0:
            return
        if self.world.is_winter():
            self.consume_wood_at_night()
        self.update_needs_and_penalties()

    def update(self):
        part = self.world_part_of_day()
        if part == "Morning":
            self.morning_routine()
        elif part == "Afternoon":
            self.afternoon_routine()
        elif part == "Night":
            self.night_routine()

    # ---------------------------------------------------------------------
    #  BASIC NEEDS
    # ---------------------------------------------------------------------

    def eat_if_needed(self):
        cfg = self.world.config
        if self.status.hunger < cfg["HUNGER_CRITICAL_THRESHOLD"]:
            if self.get_total_resource("food") > 0:
                self.remove_resource("food", 1)
                self.status.hunger += 2
                self.log(f"Ate 1 food => hunger +2")

    def buy_essential_items(self):
        cfg = self.world.config
        # If winter and wood < 1, try to buy
        if self.world.is_winter() and self.get_total_resource("wood") < 1:
            wood_price = cfg["ITEM_PRICES"]["wood"]
            if self.coins >= wood_price and self.world.market.stock.get("wood", 0) > 0:
                self.world.market.buy(self, "wood", 1)

    def buy_primary_tool(self):
        # Each role can have multiple tools per config
        primary_tools = self.world.config["ROLE_TOOLS"].get(self.role, [])
        for tool_name in primary_tools:
            # Buy the tool if we have none
            if self.get_tool_count(tool_name) < 1:
                self.world.market.buy(self, tool_name, 1)

    def sell_surplus(self):
        cfg = self.world.config
        required_wood = 0
        if self.world.is_winter():
            required_wood = max(required_wood, cfg["MIN_WOOD_RESERVE_WINTER"])

        for item_name, thresh in cfg["SURPLUS_THRESHOLDS"].items():
            current_amount = self.get_total_resource(item_name)
            if item_name == "wood":
                final_thresh = max(thresh, required_wood)
                if current_amount > final_thresh:
                    surplus = current_amount - final_thresh
                    self.world.market.sell(self, "wood", surplus)
            else:
                if current_amount > thresh:
                    surplus = current_amount - thresh
                    self.world.market.sell(self, item_name, surplus)

    def consume_wood_at_night(self):
        needed = self.world.config["WINTER_WOOD_CONSUMPTION"]
        if self.get_total_resource("wood") >= needed:
            self.remove_resource("wood", needed)
            self.log(f"Burned {needed} wood on winter night.")
        else:
            self.status.health = max(0, self.status.health - 1)
            self.status.happiness = max(0, self.status.happiness - 1)
            self.log("No wood => suffered cold (health & happiness -1).")

    def update_needs_and_penalties(self):
        cfg = self.world.config
        # Rest recovery at Night
        self.status.rest += cfg["REST_RECOVERY_PER_NIGHT"]

        # Decrement hunger/rest gradually (1 day = 3 parts)
        self.status.hunger -= cfg["HUNGER_DECREMENT_PER_DAY"] / 3.0
        self.status.rest -= cfg["REST_DECREMENT_PER_DAY"] / 3.0

        self.status.hunger = max(0, self.status.hunger)
        self.status.rest = max(0, self.status.rest)

        # Track prolonged low-hunger or low-rest
        if self.status.hunger < cfg["HUNGER_LOW_PENALTY_THRESHOLD"]:
            self.low_hunger_streak += 1
        else:
            self.low_hunger_streak = 0

        if self.status.rest < cfg["REST_LOW_PENALTY_THRESHOLD"]:
            self.low_rest_streak += 1
        else:
            self.low_rest_streak = 0

        # Apply penalty if low hunger/rest is prolonged
        if self.low_hunger_streak > 1:
            self.status.health = max(0, self.status.health - cfg["HEALTH_PENALTY_FOR_LOW_NEEDS"])
            self.status.happiness = max(0, self.status.happiness - cfg["HAPPINESS_PENALTY_FOR_LOW_NEEDS"])
            self.log("Suffering from prolonged hunger => health/happiness penalty.")

        if self.low_rest_streak > 1:
            self.status.health = max(0, self.status.health - cfg["HEALTH_PENALTY_FOR_LOW_NEEDS"])
            self.status.happiness = max(0, self.status.happiness - cfg["HAPPINESS_PENALTY_FOR_LOW_NEEDS"])
            self.log("Suffering from prolonged lack of rest => health/happiness penalty.")

    # ---------------------------------------------------------------------
    #  Tools & Items
    # ---------------------------------------------------------------------

    def add_tool(self, tool_name, qty=1):
        for _ in range(qty):
            new_tool = Item(tool_name, quantity=1, durability=self.world.config["INITIAL_TOOL_DURABILITY"])
            self.items.setdefault(tool_name, []).append(new_tool)

    def remove_tool(self, tool_name, qty=1):
        lst = self.items.get(tool_name, [])
        # Remove up to 'qty' tools from the list
        removed = 0
        while removed < qty and lst:
            # pop the first tool
            lst.pop(0)
            removed += 1
        if not lst:
            self.items[tool_name] = []

    def get_tool_count(self, tool_name):
        """Return how many tool objects of this name exist."""
        lst = self.items.get(tool_name, [])
        return len([i for i in lst if i.is_tool()])

    def degrade_tool(self, tool_name):
        for item in self.items.get(tool_name, []):
            if item.name == tool_name and item.is_tool():
                item.durability -= 1
                if item.durability == 1:  # Warn before breaking
                    self.world.log.log_action(
                        self.world.day_count, self.world_part_of_day(),
                        self.id, self.role,
                        f"{tool_name} is about to break! (1 use left)"
                    )
                if item.durability <= 0:
                    self.world.log.log_action(
                        self.world.day_count, self.world_part_of_day(),
                        self.id, self.role,
                        f"{tool_name} broke! Durability expired."
                    )
                break

    # ---------------------------------------------------------------------
    #  Resources
    # ---------------------------------------------------------------------

    def add_resource(self, item_name, qty):
        if qty <= 0:
            return
        if item_name not in self.items:
            self.items[item_name] = [Item(item_name, qty)]
        else:
            # For resources, we typically have a single item object
            # with name=item_name. Increase its quantity.
            found = False
            for it in self.items[item_name]:
                if not it.is_tool():
                    it.quantity += qty
                    found = True
                    break
            if not found:
                # If we only had tools before, add a new resource item
                self.items[item_name].append(Item(item_name, qty))

    def remove_resource(self, item_name, qty):
        """Remove up to qty from the resource item."""
        if qty <= 0:
            return
        if item_name not in self.items:
            return
        for it in self.items[item_name]:
            if not it.is_tool():
                # This is a resource item
                if it.quantity >= qty:
                    it.quantity -= qty
                    return
                else:
                    # remove partial and continue
                    qty -= it.quantity
                    it.quantity = 0
        # Cleanup any zero-quantity resource items
        self.items[item_name] = [x for x in self.items[item_name] if x.quantity > 0 or x.is_tool()]

    def get_total_resource(self, item_name):
        """Sum quantity across all resource items of this name."""
        total = 0
        for it in self.items.get(item_name, []):
            if not it.is_tool():
                total += it.quantity
        return total

    # ---------------------------------------------------------------------
    #  Helpers
    # ---------------------------------------------------------------------

    def find_owned_or_public_field(self):
        # Try to find a field owned by this villager
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == "field" and tile.resource_level >= 0:
                    if tile.owner_id == self.id:
                        return tile
        # Otherwise find any unowned field
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == "field" and tile.resource_level > 0 and tile.owner_id is None:
                    return tile
        return None

    def find_tile_with_resources(self, terrain_type):
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == terrain_type and tile.resource_level > 0:
                    return tile
        return None

    def gain_skill(self):
        self.skill_level += self.world.config["SKILL_GAIN_PER_ACTION"]

    def world_part_of_day(self):
        return self.world.world_part_of_day()

    def log_incapacitated(self):
        self.log("Health is 0 => incapacitated, no actions.")

    def log(self, message):
        self.world.log.log_action(
            self.world.day_count,
            self.world_part_of_day(),
            self.id, self.role,
            message
        )

# -------------------------------------------------------------------------
#  SIMULATION
# -------------------------------------------------------------------------

class Simulation:
    def __init__(self, config):
        self.config = config

        self.sim_log = SimulationLog()
        self.stats_collector = StatsCollector()

        self.world = World(config, self.sim_log)
        self.villagers = self._spawn_villagers()
        # Let the world reference them (used by EventManager, etc.)
        self.world.villagers = self.villagers

        # Optional: assign farmland to farmers in a random manner
        self._assign_farmland_to_farmers()

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

    def _assign_farmland_to_farmers(self):
        """
        Example of a simple random farmland assignment: pick a random 'field'
        tile and mark the farmer as the owner. 
        """
        farmers = [v for v in self.villagers if v.role == "Farmer"]
        field_tiles = []
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == "field":
                    field_tiles.append(tile)
        random.shuffle(field_tiles)

        # For each farmer, assign one field tile
        for i, farmer in enumerate(farmers):
            if i < len(field_tiles):
                field_tiles[i].owner_id = farmer.id
                field_tiles[i].resource_level = 5

    def run(self):
        max_days = self.config["TOTAL_DAYS_TO_RUN"]
        while self.world.day_count <= max_days:
            # Each villager does their update for this part of the day
            for v in self.villagers:
                v.update()
                self.stats_collector.record_villager_stats(v)

            # Let the world handle events & resource regrowth
            self.world.update_resources_and_events()

            # Advance time
            self.world.advance_time()

        # When done, export logs & generate charts
        self.sim_log.export_log("simulation_log.txt")
        self.stats_collector.generate_charts("simulation_charts.html")


if __name__ == "__main__":
    sim = Simulation(CONFIG)
    sim.run()
    sys.exit()
