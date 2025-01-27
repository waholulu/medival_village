import random
import sys
import plotly.graph_objs as go
import plotly.offline as pyo
import pandas as pd

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

    # **New** Hunger/Rest Penalty
    "HUNGER_LOW_PENALTY_THRESHOLD": 3,     # if < 3 for more than a partial day
    "REST_LOW_PENALTY_THRESHOLD":   3,
    "HEALTH_PENALTY_FOR_LOW_NEEDS": 1,
    "HAPPINESS_PENALTY_FOR_LOW_NEEDS": 1,

    # Tool Durability
    "INITIAL_TOOL_DURABILITY": 10,

    # Storm & Resource Regrowth
    "STORM_PROBABILITY": 0.1,
    "STORM_RESOURCE_REDUCTION": 2,

    # Initial Stocks
    "INITIAL_MARKET_STOCK": {
        "food": 50,
        "wood": 50,
        "axe":  5,
        "bow":  5,
        "hoe":  5,
    },

    # Roles & Number of Villagers
    "NUM_FARMERS":     1,
    "NUM_HUNTERS":     1,
    "NUM_LOGGERS":     1,
    "NUM_BLACKSMITHS": 1,

    # Initial Villager Inventories
    "INITIAL_VILLAGER_FOOD":  3,
    "INITIAL_VILLAGER_WOOD":  2,
    "INITIAL_VILLAGER_COINS": 10,
}

# -------------------------------------------------------------------------
#  LOGGING & DATA STORAGE
# -------------------------------------------------------------------------

LOG_ENTRIES = []       # For textual logs
STATS_TIMESERIES = []  # For numeric data (plots, etc.)


def log_action(day, part, villager_id, role, message):
    """
    Simple function to record a log entry.
    """
    LOG_ENTRIES.append((day, part, villager_id, role, message))


def export_log(filename="simulation_log.txt"):
    """
    Writes out the textual log of actions.
    """
    with open(filename, "w", encoding="utf-8") as f:
        for day, part, vid, role, msg in LOG_ENTRIES:
            line = f"Day {day} [{part}] - Villager {vid} ({role}): {msg}\n"
            f.write(line)
    print(f"Log written to {filename}")


def generate_charts(filename="simulation_charts.html"):
    """
    Creates some Plotly-based line charts for key villager stats over time.
    """
    df = pd.DataFrame(STATS_TIMESERIES).reset_index().rename(columns={"index": "time_step"})
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

    # Save HTML
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
#  TILE & MARKET
# -------------------------------------------------------------------------

class Tile:
    """
    A single grid cell storing terrain, resource_level, and possibly an owner.
    """
    def __init__(self, terrain_type="field", resource_level=5, owner_id=None):
        self.terrain_type = terrain_type
        self.resource_level = resource_level
        self.owner_id = owner_id


class Market:
    """
    A simple Market with fixed item prices and a stock count.
    Villagers can buy/sell if stock and coins allow.
    """
    def __init__(self, config):
        self.config = config
        self.stock = dict(config["INITIAL_MARKET_STOCK"])  # copy

    def buy(self, villager, item, qty=1):
        """
        Villager attempts to buy `qty` of `item`.
        Must have enough coins and Market must have enough stock.
        """
        if self.stock.get(item, 0) < qty:
            return False  # out of stock
        cost = self.config["ITEM_PRICES"][item] * qty
        if villager.coins < cost:
            return False  # not enough money

        # Transaction
        villager.coins -= cost
        self.stock[item] -= qty

        # Tools vs normal inventory
        if item in ["axe", "bow", "hoe"]:
            villager.add_tool(item, qty)
        else:
            villager.inventory[item] = villager.inventory.get(item, 0) + qty

        day = villager.world.day_count
        part = villager.world_part_of_day()
        log_action(day, part, villager.id, villager.role,
                   f"Bought {qty} {item}. Market now has {self.stock[item]} left.")
        return True

    def sell(self, villager, item, qty=1):
        """
        Villager sells `qty` of `item`.
        Market has infinite coins, but the item is added to Market stock.
        """
        # Verify villager has enough
        if item in ["axe", "bow", "hoe"]:
            have_qty = villager.get_tool_count(item)
            if have_qty < qty:
                return False
            villager.remove_tool(item, qty)
        else:
            if villager.inventory.get(item, 0) < qty:
                return False
            villager.inventory[item] -= qty

        revenue = self.config["ITEM_PRICES"][item] * qty
        villager.coins += revenue
        self.stock[item] = self.stock.get(item, 0) + qty

        day = villager.world.day_count
        part = villager.world_part_of_day()
        log_action(day, part, villager.id, villager.role,
                   f"Sold {qty} {item} for {revenue} coins. Market stock now={self.stock[item]}.")
        return True


# -------------------------------------------------------------------------
#  WORLD
# -------------------------------------------------------------------------

class World:
    """
    Holds the tile grid, the Market, time/season, and triggers random events.
    """
    def __init__(self, config):
        self.config = config
        self.width = config["GRID_WIDTH"]
        self.height = config["GRID_HEIGHT"]
        self.grid = self._generate_tiles()
        self.market = Market(config)

        # Time
        self.day_count = 1
        self.season_index = 0
        self.part_of_day_index = 0

    def _generate_tiles(self):
        grid = []
        for _y in range(self.height):
            row = []
            for _x in range(self.width):
                terrain = random.choice(["forest", "field", "field", "water"])
                if terrain == "forest":
                    lvl = 5
                elif terrain == "field":
                    lvl = 1  # Fields start 1, requiring Spring planting
                else:
                    lvl = 0
                row.append(Tile(terrain, lvl))
            grid.append(row)
        # Assign farmland to all farmers
        farmer_count = self.config["NUM_FARMERS"]
        current_farmer = 1
        for y in range(2, min(2 + farmer_count, self.height)):
            if current_farmer > farmer_count:
                break
            tile = grid[y][2]
            tile.owner_id = current_farmer
            tile.terrain_type = "field"
            tile.resource_level = 5  # Start with fertile soil
            current_farmer += 1
            
        return grid

    def world_part_of_day(self):
        return self.config["PARTS_OF_DAY"][self.part_of_day_index]

    def get_current_season(self):
        return self.config["SEASONS"][self.season_index % len(self.config["SEASONS"])]

    def is_winter(self):
        return (self.get_current_season() == "Winter")

    def update_resources_and_events(self):
        """
        Daily events like storms, resource regeneration, etc.
        Called once per partial day step.
        """
        # If morning => might trigger storm
        if self.part_of_day_index == 0:  # "Morning" of a new day
            if random.random() < self.config["STORM_PROBABILITY"]:
                self._trigger_storm()

        # Regrow forest
        for row in self.grid:
            for tile in row:
                if tile.terrain_type == "forest":
                    tile.resource_level = min(tile.resource_level + 1, 10)

    def _trigger_storm(self):
        """
        Storm reduces resource levels in ~1/4 of the tiles by STORM_RESOURCE_REDUCTION.
        """
        reduction = self.config["STORM_RESOURCE_REDUCTION"]
        num_tiles = (self.width * self.height) // 4
        for _ in range(num_tiles):
            rx = random.randint(0, self.width - 1)
            ry = random.randint(0, self.height - 1)
            tile = self.grid[ry][rx]
            tile.resource_level = max(0, tile.resource_level - reduction)
        # Log storm
        log_action(self.day_count, "Morning", 0, "EVENT",
                   f"Storm reduced resources in ~{num_tiles} tiles.")

    def advance_time(self):
        """
        Moves to next partial day. If we've passed Night, increment day.
        Also increments seasons as needed.
        """
        self.part_of_day_index += 1
        if self.part_of_day_index >= len(self.config["PARTS_OF_DAY"]):
            # new day
            self.part_of_day_index = 0
            self.day_count += 1
            # check season
            if (self.day_count - 1) % self.config["DAYS_PER_SEASON"] == 0:
                self.season_index += 1
                if self.season_index >= len(self.config["SEASONS"]):
                    self.season_index = 0


# -------------------------------------------------------------------------
#  VILLAGER
# -------------------------------------------------------------------------

class Villager:
    """
    A single agent with role, needs, inventory, and tool usage.
    """
    def __init__(self, vid, role, world):
        self.id = vid
        self.role = role
        self.world = world
        cfg = world.config

        # Needs
        self.hunger = 10
        self.rest = 10
        self.health = 10
        self.happiness = 10

        # Track how many consecutive partial-steps hunger/rest is below threshold
        self.low_hunger_streak = 0
        self.low_rest_streak   = 0

        # Inventory & Tools
        self.inventory = {
            "food": cfg["INITIAL_VILLAGER_FOOD"],
            "wood": cfg["INITIAL_VILLAGER_WOOD"]
        }
        self.coins = cfg["INITIAL_VILLAGER_COINS"]
        self.tools = {"hoe": [], "bow": [], "axe": []}

    # ---------------------------------------------------------------------
    #  Common Steps
    # ---------------------------------------------------------------------
    def update(self):
        """
        Called once per partial day. The order:
          1) Check if we need to eat
          2) Buy essential items (esp winter wood)
          3) Ensure we have role's primary tool
          4) Perform role action (morning/afternoon only)
          5) Sell surplus
          6) If winter & night => burn wood
          7) Decrement needs + apply penalty if too low
          8) Record stats
        """
        self.eat_if_needed()
        self.buy_essential_items()
        self.buy_primary_tool()

        if self.world.world_part_of_day() in ["Morning", "Afternoon"]:
            self.do_role_action()

        self.sell_surplus()

        if (self.world.world_part_of_day() == "Night") and self.world.is_winter():
            self.consume_wood_at_night()

        self.update_needs_and_penalties()
        self.record_stats()

    def world_part_of_day(self):
        return self.world.world_part_of_day()

    # ---------------------------------------------------------------------
    #  Eating & Buying
    # ---------------------------------------------------------------------
    def eat_if_needed(self):
        """
        If hunger < HUNGER_CRITICAL_THRESHOLD and we have food, eat 1.
        """
        if self.hunger < self.world.config["HUNGER_CRITICAL_THRESHOLD"]:
            if self.inventory.get("food", 0) > 0:
                self.inventory["food"] -= 1
                self.hunger += 2
                log_action(self.world.day_count,
                           self.world_part_of_day(),
                           self.id, self.role,
                           "Ate 1 food to increase hunger.")

    def buy_essential_items(self):
        """
        Buy wood if it's winter and we have 0 wood.
        """
        cfg = self.world.config
        if self.world.is_winter() and self.inventory.get("wood", 0) < 1:
            wood_price = cfg["ITEM_PRICES"]["wood"]
            if (self.coins >= wood_price and
                self.world.market.stock.get("wood", 0) > 0):
                self.world.market.buy(self, "wood", 1)

    def buy_primary_tool(self):
        """
        Ensure we have at least 1 tool that matches our role.
        """
        role_tool_map = {
            "Farmer": "hoe",
            "Hunter": "bow",
            "Logger": "axe",
            "Blacksmith": None  # doesn't strictly need a tool
        }
        tool = role_tool_map.get(self.role)
        if tool:
            if self.get_tool_count(tool) < 1:
                self.world.market.buy(self, tool, 1)

    # ---------------------------------------------------------------------
    #  Role Actions
    # ---------------------------------------------------------------------
    def do_role_action(self):
        if self.role == "Farmer":
            self.farm()
        elif self.role == "Hunter":
            self.hunt()
        elif self.role == "Logger":
            self.log_wood()
        elif self.role == "Blacksmith":
            self.craft_tools()

    def farm(self):
        tile = self.find_owned_or_public_field()
        if tile is None:
            self.forage()
            return
        
        season = self.world.get_current_season()
        
        if season == "Autumn":  # Harvest only in autumn
            if self.get_tool_count("hoe") > 0:
                amount = tile.resource_level  # Harvest accumulated value
                self.degrade_tool("hoe")
            else:
                amount = tile.resource_level // 2  # Reduced yield without tool
                
            self.inventory["food"] += amount
            log_action(self.world.day_count, self.world_part_of_day(),
                       self.id, self.role,
                       f"Harvested {amount} food (tile resource now={tile.resource_level}).")
            tile.resource_level = 0  # Reset after harvest
            
        elif season in ["Spring", "Summer"]:  # Prepare fields
            tile.resource_level += 2
            log_action(self.world.day_count, self.world_part_of_day(),
                       self.id, self.role,
                       f"Prepared fields (resource now {tile.resource_level}).")
            
        elif season == "Winter":
            log_action(self.world.day_count, self.world_part_of_day(),
                       self.id, self.role,
                       "Cannot farm in winter.")
            self.forage()

    def hunt(self):
        tile = self.find_tile_with_resources("forest")
        if tile is None:
            self.forage()
            return

        if self.get_tool_count("bow") > 0:
            amount = self.world.config["BASE_HUNT_YIELD"]
            self.degrade_tool("bow")
        else:
            amount = self.world.config["FALLBACK_HUNT_YIELD"]

        self.inventory["food"] = self.inventory.get("food", 0) + amount
        tile.resource_level = max(tile.resource_level - 1, 0)
        log_action(self.world.day_count, self.world_part_of_day(),
                   self.id, self.role,
                   f"Hunting => +{amount} food (tile resource now={tile.resource_level}).")

    def log_wood(self):
        tile = self.find_tile_with_resources("forest")
        if tile is None:
            self.forage()
            return

        if self.get_tool_count("axe") > 0:
            amount = self.world.config["BASE_LOG_YIELD"]
            self.degrade_tool("axe")
        else:
            amount = self.world.config["FALLBACK_LOG_YIELD"]

        self.inventory["wood"] = self.inventory.get("wood", 0) + amount
        tile.resource_level = max(tile.resource_level - 2, 0)
        log_action(self.world.day_count, self.world_part_of_day(),
                   self.id, self.role,
                   f"Logging => +{amount} wood (tile resource now={tile.resource_level}).")

    def craft_tools(self):
        """
        Blacksmith crafts whichever tool is least stocked in Market.
        Consumes 1 wood from own inventory, then sells that tool back.
        """
        mk = self.world.market
        tool_list = ["axe", "bow", "hoe"]
        stocks = {t: mk.stock.get(t, 0) for t in tool_list}
        # pick the one with the lowest stock
        least_tool = min(stocks, key=stocks.get)

        # need at least 1 wood
        if self.inventory.get("wood", 0) < 1:
            mk.buy(self, "wood", 1)
        if self.inventory.get("wood", 0) < 1:
            # can't craft
            log_action(self.world.day_count, self.world_part_of_day(),
                       self.id, self.role,
                       "Wanted to craft but no wood available.")
            return

        # craft
        self.inventory["wood"] -= 1
        self.add_tool(least_tool, 1)
        mk.sell(self, least_tool, 1)
        log_action(self.world.day_count, self.world_part_of_day(),
                   self.id, self.role,
                   f"Crafted & sold 1 {least_tool} (consumed 1 wood).")

    def forage(self):
        """
        Minimal fallback: gather +1 food if no resources or farmland found.
        """
        self.inventory["food"] = self.inventory.get("food", 0) + 1
        log_action(self.world.day_count, self.world_part_of_day(),
                   self.id, self.role, "Foraging => +1 food.")

    # ---------------------------------------------------------------------
    #  Surplus & Winter Wood
    # ---------------------------------------------------------------------
    def sell_surplus(self):
        """
        Sell items above threshold. Keep at least 1 wood if winter.
        """
        cfg = self.world.config
        required_wood = 1 if self.world.is_winter() else 0

        for item, thresh in cfg["SURPLUS_THRESHOLDS"].items():
            current_amount = self.inventory.get(item, 0)
            if item == "wood":
                # keep at least required_wood
                final_thresh = max(thresh, required_wood)
                if current_amount > final_thresh:
                    surplus = current_amount - final_thresh
                    self.world.market.sell(self, "wood", surplus)
            else:
                if current_amount > thresh:
                    surplus = current_amount - thresh
                    self.world.market.sell(self, item, surplus)

    def consume_wood_at_night(self):
        needed = self.world.config["WINTER_WOOD_CONSUMPTION"]
        if self.inventory.get("wood", 0) >= needed:
            self.inventory["wood"] -= needed
            log_action(self.world.day_count, self.world_part_of_day(),
                       self.id, self.role, f"Burned {needed} wood on winter night.")
        else:
            self.health    = max(0, self.health - 1)
            self.happiness = max(0, self.happiness - 1)
            log_action(self.world.day_count, self.world_part_of_day(),
                       self.id, self.role, "No wood => suffered cold (health & happiness -1).")

    # ---------------------------------------------------------------------
    #  Needs & Penalties
    # ---------------------------------------------------------------------
    def update_needs_and_penalties(self):
        """
        Each partial day, decrease hunger/rest,
        then apply health/happiness penalties if they stay too low for consecutive steps.
        """
        cfg = self.world.config
        # Decrement hunger/rest
        self.hunger -= cfg["HUNGER_DECREMENT_PER_DAY"] / 3.0
        self.rest   -= cfg["REST_DECREMENT_PER_DAY"]   / 3.0
        self.hunger = max(0, self.hunger)
        self.rest   = max(0, self.rest)

        # Track consecutive partial-day streaks if below thresholds
        if self.hunger < cfg["HUNGER_LOW_PENALTY_THRESHOLD"]:
            self.low_hunger_streak += 1
        else:
            self.low_hunger_streak = 0

        if self.rest < cfg["REST_LOW_PENALTY_THRESHOLD"]:
            self.low_rest_streak += 1
        else:
            self.low_rest_streak = 0

        # If we've stayed below threshold for more than 1 partial step, apply penalty
        if self.low_hunger_streak > 1:
            self.health    = max(0, self.health - cfg["HEALTH_PENALTY_FOR_LOW_NEEDS"])
            self.happiness = max(0, self.happiness - cfg["HAPPINESS_PENALTY_FOR_LOW_NEEDS"])
            log_action(self.world.day_count, self.world_part_of_day(),
                       self.id, self.role,
                       "Suffering from prolonged hunger => health/happiness penalty.")

        if self.low_rest_streak > 1:
            self.health    = max(0, self.health - cfg["HEALTH_PENALTY_FOR_LOW_NEEDS"])
            self.happiness = max(0, self.happiness - cfg["HAPPINESS_PENALTY_FOR_LOW_NEEDS"])
            log_action(self.world.day_count, self.world_part_of_day(),
                       self.id, self.role,
                       "Suffering from prolonged lack of rest => health/happiness penalty.")

    # ---------------------------------------------------------------------
    #  Tools
    # ---------------------------------------------------------------------
    def add_tool(self, tool_name, qty=1):
        for _ in range(qty):
            self.tools[tool_name].append({"durability": self.world.config["INITIAL_TOOL_DURABILITY"]})

    def remove_tool(self, tool_name, qty=1):
        for _ in range(qty):
            if self.tools[tool_name]:
                self.tools[tool_name].pop()

    def get_tool_count(self, tool_name):
        return len(self.tools[tool_name])

    def degrade_tool(self, tool_name):
        """
        Degrade the first tool of that type by 1. If it hits 0, break it.
        """
        if self.tools[tool_name]:
            self.tools[tool_name][0]["durability"] -= 1
            if self.tools[tool_name][0]["durability"] <= 0:
                self.tools[tool_name].pop(0)
                log_action(self.world.day_count, self.world_part_of_day(),
                           self.id, self.role, f"{tool_name} broke (durability=0).")

    # ---------------------------------------------------------------------
    #  Searching Tiles
    # ---------------------------------------------------------------------
    def find_owned_or_public_field(self):
        """
        Search for a field tile with resource_level>0 owned by me, else public.
        """
        # Owned farmland first
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == "field" and tile.resource_level > 0 and tile.owner_id == self.id:
                    return tile
        # Then public farmland
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == "field" and tile.resource_level > 0 and tile.owner_id is None:
                    return tile
        return None

    def find_tile_with_resources(self, terrain_type):
        """
        Generic search for tile with terrain_type and resource_level>0.
        """
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == terrain_type and tile.resource_level > 0:
                    return tile
        return None

    # ---------------------------------------------------------------------
    #  Recording
    # ---------------------------------------------------------------------
    def record_stats(self):
        STATS_TIMESERIES.append({
            "day":        self.world.day_count,
            "part":       self.world_part_of_day(),
            "villager_id": self.id,
            "role":        self.role,
            "hunger":      self.hunger,
            "rest":        self.rest,
            "health":      self.health,
            "happiness":   self.happiness,
            "coins":       self.coins,
            "food":        self.inventory.get("food", 0),
            "wood":        self.inventory.get("wood", 0)
        })


# -------------------------------------------------------------------------
#  SIMULATION (Headless)
# -------------------------------------------------------------------------

class Simulation:
    """
    Orchestrates the village: creates villagers, steps time, logs results.
    """
    def __init__(self, config):
        self.config = config
        self.world = World(config)
        self.villagers = self._spawn_villagers()

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
        """
        Runs the simulation up to TOTAL_DAYS_TO_RUN * partial-days (3 parts per day).
        """
        max_days = self.config["TOTAL_DAYS_TO_RUN"]

        while self.world.day_count <= max_days:
            # 1) All villagers do their step
            for v in self.villagers:
                v.update()

            # 2) World updates resources/events, then time
            self.world.update_resources_and_events()
            self.world.advance_time()

        # At end: export logs and generate charts
        export_log("simulation_log.txt")
        generate_charts("simulation_charts.html")


# -------------------------------------------------------------------------
#  MAIN
# -------------------------------------------------------------------------

if __name__ == "__main__":
    sim = Simulation(CONFIG)
    sim.run()
    sys.exit()
