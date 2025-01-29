import random
import sys
import plotly.graph_objs as go
import plotly.offline as pyo
import pandas as pd
from collections import Counter, defaultdict

# -------------------------------------------------------------------------
#  CONFIG & CONSTANTS
# -------------------------------------------------------------------------

CONFIG = {
    "GRID_WIDTH": 32,
    "GRID_HEIGHT": 32,

    # Time & Seasons
    "DAYS_PER_SEASON": 3,  # 3 days => 4 seasons => 12 days/year
    "SEASONS": ["Spring", "Summer", "Autumn", "Winter"],
    "PARTS_OF_DAY": ["Morning", "Afternoon", "Night"],
    "TOTAL_DAYS_TO_RUN": 36,  # => 3 years

    # Centralized item definitions
    "ITEMS": {
        "food": {
            "type": "resource",
            "durability": 0,
            "price": 1,
            "spoilage": 3   # how many 'day-parts' before it spoils (example)
        },
        "cooked_food": {
            "type": "resource",
            "durability": 0,
            "price": 2,
            "spoilage": 6   # cooked food lasts longer
        },
        "wood": {
            "type": "resource",
            "durability": 0,
            "price": 2
        },
        "axe": {
            "type": "tool",
            "durability": 10,
            "price": 5
        },
        "bow": {
            "type": "tool",
            "durability": 10,
            "price": 5
        },
        "hoe": {
            "type": "tool",
            "durability": 10,
            "price": 5
        }
    },

    # Surplus Thresholds
    "SURPLUS_THRESHOLDS": {
        "food": 5,
        "wood": 5,
        "cooked_food": 5
    },

    # Production Yields
    "BASE_FARM_YIELD": 2,
    "BASE_HUNT_YIELD": 1,
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

    # Storm & Resource Regrowth
    "STORM_PROBABILITY": 0.1,
    "STORM_RESOURCE_REDUCTION": 2,
    "DISEASE_PROBABILITY": 0.05,
    "DISEASE_HEALTH_LOSS": 2,

    # Initial Stocks
    "INITIAL_MARKET_STOCK": {
        "food": 50,
        "wood": 50,
        "axe":  5,
        "bow":  5,
        "hoe":  5,
        "cooked_food": 0  # newly introduced item in the market
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

    # Additional
    "REST_RECOVERY_PER_NIGHT": 4,
    "HUNGER_WARNING_THRESHOLD": 3,
    "SKILL_GAIN_PER_ACTION": 0.08,  # example
    "MAX_SKILL_MULTIPLIER": 3.0,
    "MIN_WOOD_RESERVE_WINTER": 2,

    # Tools needed by each role
    "ROLE_TOOLS": {
        "Farmer": ["hoe"],
        "Hunter": ["bow"],
        "Logger": ["axe"],
        "Blacksmith": []
    },

    # Role -> Action mapping
    "ROLE_ACTIONS": {
        "Farmer": "farm",
        "Hunter": "hunt",
        "Logger": "log_wood",
        "Blacksmith": "craft",
        "default": "forage"
    },

    # Terrain distribution
    "TERRAIN_DISTRIBUTION": {
        "forest": {"chance": 0.3, "base_resource": 5},
        "field":  {"chance": 0.5, "base_resource": 1},
        "water":  {"chance": 0.2, "base_resource": 0}
    },

    "MAX_FIELD_RESOURCE": 40,

    # -----------------------------
    # NEW config entries (Monsters, Social)
    # -----------------------------
    "MONSTER_SPAWN_PROB": 0.05,   # 5% chance each morning
    "MARRIAGE_PROBABILITY": 0.05, # 5% chance each morning that 2 single villagers might marry
    "MAX_SPOILAGE_TICKS_PER_DAY": 3,  # convenience for day-part-based spoilage
    "MONSTER_TYPES": ["Wolf", "Bear", "Goblin"],
    "MONSTER_HEALTH_RANGE": [5, 10],
    "MONSTER_DAMAGE_RANGE": [1, 3],
    "COMBAT_MAX_ROUNDS": 3,
    "COOKING_CONVERSION_RATE": 1,
    "COOKING_PROBABILITY": 0.7,
    "INITIAL_HUNGER": 10,
    "INITIAL_REST": 10,
    "INITIAL_HEALTH": 10,
    "INITIAL_HAPPINESS": 10
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
            "wood":        villager.get_total_resource("wood"),
            "cooked_food": villager.get_total_resource("cooked_food")
        }
        self.timeseries.append(data_point)

    def generate_charts(self, filename="simulation_charts.html"):
        df = pd.DataFrame(self.timeseries).reset_index().rename(columns={"index": "time_step"})
        
        fig = go.Figure().set_subplots(
            rows=3, cols=1, shared_xaxes=True,
            subplot_titles=("Hunger Over Time", "Health Over Time", "Happiness Over Time"),
            vertical_spacing=0.1
        )

        season_change_interval = CONFIG["DAYS_PER_SEASON"] * 3  # 3 parts per day
        max_time = df["time_step"].max()
        seasons = CONFIG["SEASONS"]
        for i in range(0, max_time + 1, season_change_interval):
            for row in [1, 2, 3]:
                fig.add_vline(
                    x=i, line_dash="dot", line_color="gray",
                    annotation_text=seasons[(i // season_change_interval) % len(seasons)],
                    annotation_position="top left",
                    row=row, col=1
                )

        # Plot each metric
        for vid in df["villager_id"].unique():
            subdf = df[df["villager_id"] == vid]
            # Hunger
            fig.add_trace(go.Scatter(
                x=subdf["time_step"], y=subdf["hunger"],
                mode="lines", name=f"V{vid}", showlegend=True
            ), row=1, col=1)
            # Health
            fig.add_trace(go.Scatter(
                x=subdf["time_step"], y=subdf["health"],
                mode="lines", name=f"V{vid}", showlegend=False
            ), row=2, col=1)
            # Happiness
            fig.add_trace(go.Scatter(
                x=subdf["time_step"], y=subdf["happiness"],
                mode="lines", name=f"V{vid}", showlegend=False
            ), row=3, col=1)

        fig.update_layout(
            height=900,
            title_text="Villager Metrics Over Time with Seasonal Markers",
            hovermode="x unified"
        )
        fig.update_xaxes(title_text="Time Step", row=3, col=1)

        html_div = pyo.plot(fig, include_plotlyjs=False, output_type='div')
        with open(filename, "w", encoding="utf-8") as f:
            f.write("<html><head><script src='https://cdn.plot.ly/plotly-latest.min.js'></script></head><body>")
            f.write(html_div)
            f.write("</body></html>")
        print(f"Charts generated: {filename}")


# -------------------------------------------------------------------------
#  ITEM CLASS (added spoilage_tracking)
# -------------------------------------------------------------------------

class Item:
    """
    If durability > 0, treat it as a tool. Otherwise, it's a resource.
    quantity=1 for tools by default, but can be more for resources.
    'spoilage_left' is used if the item is perishable.
    """
    def __init__(self, name, quantity=1, durability=0):
        self.name = name
        self.quantity = quantity
        self.durability = durability

        # Initialize per-item spoilage if relevant
        item_def = CONFIG["ITEMS"].get(name, {})
        self.max_spoilage = item_def.get("spoilage", 0)  # how many ticks it lasts
        # For each resource item, track how much spoilage time is left
        self.spoilage_left = self.max_spoilage  

    def is_tool(self):
        return self.durability > 0

    def __repr__(self):
        return f"<Item {self.name}, qty={self.quantity}, dur={self.durability}, spoilage_left={self.spoilage_left}>"


# -------------------------------------------------------------------------
#  MONSTER CLASS (NEW)
# -------------------------------------------------------------------------

class Monster:
    """
    A simple monster/creature that can attack villagers.
    """
    def __init__(self, name, health, damage):
        self.name = name
        self.health = health
        self.damage = damage
        self.alive = True

    def attack_villager(self, villager):
        if not self.alive or villager.status.health <= 0:
            return

        # Multi-round combat
        for _ in range(3):  # Max 3 rounds
            villager_damage = random.randint(1, 3)
            monster_damage = random.randint(1, self.damage)
            
            self.health -= villager_damage
            villager.status.health = max(0, villager.status.health - monster_damage)
            
            if self.health <= 0 or villager.status.health <= 0:
                break

        self.alive = self.health > 0
        villager.log(f"Combat with {self.name}! Lost {monster_damage} HP. Monster {'fled' if self.alive else 'died'}.")

    def is_dead(self):
        return self.health <= 0


# -------------------------------------------------------------------------
#  ACTIONS CLASS (added cooking)
# -------------------------------------------------------------------------

class Action:
    @staticmethod
    def farm(villager):
        tile = villager.find_owned_or_public_field()
        if not tile:
            Action.forage(villager)
            return
        
        max_field = villager.world.config["MAX_FIELD_RESOURCE"]
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
            villager.add_item("food", amount)
            villager.world.log.log_action(
                villager.world.day_count, villager.world_part_of_day(),
                villager.id, villager.role,
                f"Harvested {amount} food (tile resource now=0)."
            )
            tile.resource_level = 0

        elif season in ["Spring", "Summer"]:
            # Calculate field growth using tools and skill
            amount = Action.get_yield_with_tool(
                villager,
                tool_name="hoe",
                base_yield=villager.world.config["BASE_FARM_YIELD"],
                fallback_yield=villager.world.config["FALLBACK_FARM_YIELD"]
            )
            new_level = min(tile.resource_level + amount, max_field)
            tile.resource_level = new_level
            villager.world.log.log_action(
                villager.world.day_count, villager.world_part_of_day(),
                villager.id, villager.role,
                f"Prepared fields (+{amount}), resource now {tile.resource_level}."
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
            fallback_yield=cfg["FALLBACK_HUNT_YIELD"],
            max_multiplier=3.0
        )
        villager.add_item("food", amount)
        tile.resource_level = max(tile.resource_level - 1, 0)
        villager.log(f"Hunting => +{amount} food (tile resource now={tile.resource_level}).")

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
        villager.add_item("wood", amount)
        tile.resource_level = max(tile.resource_level - 2, 0)
        villager.log(f"Logging => +{amount} wood (tile resource now={tile.resource_level}).")

    @staticmethod
    def craft(villager):
        tool_needs = defaultdict(int)
        market_stock = villager.world.market.stock
        
        # Consider existing market inventory when assessing needs
        for v in villager.world.villagers:
            for tname in CONFIG["ROLE_TOOLS"].get(v.role, []):
                # Only count need if market has less than 2 in stock
                if market_stock.get(tname, 0) < 2:
                    if v.get_tool_count(tname) < 1 or any(t.durability < 2 for t in v.items.get(tname, [])):
                        tool_needs[tname] += 1

        # Prioritize tools with lowest market stock relative to needs
        if tool_needs:
            target_tool = min(tool_needs.keys(), 
                            key=lambda t: villager.world.market.stock.get(t, 0)/tool_needs[t])
        else:
            return  # No crafting needed
            
        # Check for resource to craft (example: 1 wood needed)
        if villager.get_total_resource("wood") < 1:
            # Try buying wood
            success = villager.buy_item("wood", 1)
            if not success:
                villager.log("Not enough wood to craft.")
                return

        # Actually craft
        villager.remove_resource("wood", 1)
        villager.add_tool(target_tool, 1)
        # Sell the newly crafted tool
        villager.sell_item(target_tool, 1)
        villager.log(f"Crafted & sold 1 {target_tool} (consumed 1 wood).")

    @staticmethod
    def forage(villager):
        villager.add_item("food", 1)
        villager.log("Foraging => +1 food.")

    @staticmethod
    def cook_food(villager):
        """Now uses configurable conversion rate"""
        rate = villager.world.config["COOKING_CONVERSION_RATE"]
        if villager.get_total_resource("food") < rate:
            villager.log(f"Need {rate} food to cook")
            return

        villager.remove_resource("food", rate)
        villager.add_item("cooked_food", 1)
        villager.log(f"Cooked {rate} food => 1 cooked_food")

    @staticmethod
    def get_yield_with_tool(villager, tool_name, base_yield, fallback_yield, max_multiplier=3.0):
        if villager.get_tool_count(tool_name) > 0:
            villager.degrade_tool(tool_name)
            skill_bonus = min(villager.skill_level, villager.world.config["MAX_SKILL_MULTIPLIER"] - 1)
            tool_bonus = 1.0  
            effective_multiplier = min(1 + skill_bonus + tool_bonus, max_multiplier)
            return int(base_yield * effective_multiplier)
        else:
            return int(fallback_yield * villager.skill_level)


# -------------------------------------------------------------------------
#  ROLE MANAGER
# -------------------------------------------------------------------------

class RoleManager:
    @staticmethod
    def do_role_action(villager):
        cfg = villager.world.config
        role = villager.role
        action_name = cfg["ROLE_ACTIONS"].get(role, cfg["ROLE_ACTIONS"]["default"])
        action_fn = getattr(Action, action_name, Action.forage)
        action_fn(villager)


# -------------------------------------------------------------------------
#  TILE & MARKET
# -------------------------------------------------------------------------

class Tile:
    def __init__(self, terrain_type="field", resource_level=5, owner_id=None):
        self.terrain_type = terrain_type
        self.resource_level = resource_level
        self.owner_id = owner_id


class Market:
    def __init__(self, config, initial_stock, sim_log):
        self.config = config
        self.log = sim_log
        self.stock = dict(initial_stock)

    def attempt_buy(self, item_name, qty=1):
        available = self.stock.get(item_name, 0)
        if available < qty:
            return False, 0
        price = self.get_price(item_name)
        cost = price * qty
        return True, cost

    def finalize_buy(self, item_name, qty=1):
        self.stock[item_name] -= qty
        if self.stock[item_name] < 0:
            self.stock[item_name] = 0  # safeguard

    def attempt_sell(self, item_name, qty=1):
        price = self.get_price(item_name)
        revenue = price * qty
        return True, revenue

    def finalize_sell(self, item_name, qty=1):
        self.stock[item_name] = self.stock.get(item_name, 0) + qty

    def get_price(self, item_name):
        item_def = self.config["ITEMS"].get(item_name, {})
        return item_def.get("price", 1)

    def log_purchase(self, villager, item_name, qty):
        day = villager.world.day_count
        part = villager.world_part_of_day()
        left = self.stock.get(item_name, 0)
        self.log.log_action(day, part, villager.id, villager.role,
                            f"Bought {qty} {item_name}. Market now has {left} left.")

    def log_sale(self, villager, item_name, qty, revenue):
        day = villager.world.day_count
        part = villager.world_part_of_day()
        self.log.log_action(day, part, villager.id, villager.role,
                            f"Sold {qty} {item_name} for {revenue} coins. Market stock now={self.stock[item_name]}.")


# -------------------------------------------------------------------------
#  EVENT MANAGER (added monster spawning)
# -------------------------------------------------------------------------

class EventManager:
    def __init__(self, config, sim_log):
        self.config = config
        self.log = sim_log

    def handle_morning_events(self, world):
        # Storm
        if random.random() < self.config["STORM_PROBABILITY"]:
            self.trigger_storm(world)
        # Disease
        if random.random() < self.config["DISEASE_PROBABILITY"]:
            self.trigger_disease(world)
        # Monster Attack
        if random.random() < self.config["MONSTER_SPAWN_PROB"]:
            self.trigger_monster_attack(world)

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
        if not world.villagers:
            return
        victim = random.choice(world.villagers)
        if victim.status.health > 0:
            dmg = self.config["DISEASE_HEALTH_LOSS"]
            victim.status.health = max(0, victim.status.health - dmg)
            self.log.log_action(world.day_count, "Morning", victim.id, "EVENT",
                                f"Disease struck villager {victim.id} => health -{dmg}.")

    def trigger_monster_attack(self, world):
        """
        Spawn one monster, pick a random villager, do a quick attack.
        If monster is 'alive' after, it might remain in the world,
        but in this minimal approach we consider it killed in the counter-attack.
        """
        if not world.villagers:
            return
        monster_name = random.choice(world.config["MONSTER_TYPES"])
        health = random.randint(*world.config["MONSTER_HEALTH_RANGE"])
        damage = random.randint(*world.config["MONSTER_DAMAGE_RANGE"])
        new_monster = Monster(monster_name, health, damage)
        world.monsters.append(new_monster)

        # Attack a random villager
        victim = random.choice(world.villagers)
        self.log.log_action(world.day_count, "Morning", 0, "EVENT",
                            f"A {monster_name} spawned and attacks villager {victim.id}!")
        new_monster.attack_villager(victim)

        # If monster is dead, remove it
        if new_monster.is_dead():
            if new_monster in world.monsters:
                world.monsters.remove(new_monster)
        else:
            # If we wanted persistent monsters, they'd roam or attack again later
            pass


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

        self.market = Market(config, config["INITIAL_MARKET_STOCK"], sim_log)
        self.event_manager = EventManager(config, sim_log)

        self.day_count = 1
        self.season_index = 0
        self.part_of_day_index = 0
        self.villagers = []

        # track any active monsters
        self.monsters = []

    def _generate_tiles(self):
        dist = self.config["TERRAIN_DISTRIBUTION"]
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

    def update_resources_and_events(self, part_of_day):
        if part_of_day == "Morning":
            self.event_manager.handle_morning_events(self)
        # Resource regrowth for forest each part
        if part_of_day == "Night":
            for row in self.grid:
                for tile in row:
                    if tile.terrain_type == "forest":
                        tile.resource_level = min(tile.resource_level + 1, 10)

        # Resource regrowth for field each part
        for row in self.grid:
            for tile in row:
                if tile.terrain_type == "field":
                    tile.resource_level = min(tile.resource_level + 1, 10)

    def advance_time(self):
        self.part_of_day_index += 1
        if self.part_of_day_index >= len(self.config["PARTS_OF_DAY"]):
            self.part_of_day_index = 0
            self.day_count += 1
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
#  VILLAGER (extended for marriage & spoilage updates)
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

        # Relationship
        self.relationship_status = "single"  # or "married", "widowed"
        self.partner_id = None

        # Items: name -> list[Item]
        self.items = {
            "food": [Item("food", cfg["INITIAL_VILLAGER_FOOD"], 0)],
            "wood": [Item("wood", cfg["INITIAL_VILLAGER_WOOD"], 0)]
        }

    def perform_part_of_day(self, part_of_day):
        if self.status.health <= 0:
            if part_of_day == "Morning":
                self.log("Health is 0 => incapacitated, no actions.")
            return

        if part_of_day == "Morning":
            self.eat_if_needed()
            self.buy_essential_items()
            self.buy_primary_tool()
            RoleManager.do_role_action(self)
            # Example: some chance to cook if you have surplus raw food
            if self.get_total_resource("food") > 2:
                Action.cook_food(self)
            self.sell_surplus()

        elif part_of_day == "Afternoon":
            # Cook with morning's harvest before spoilage
            raw_food = self.get_total_resource("food")
            if raw_food > 0 and random.random() < 0.7:  # 70% chance to preserve excess
                Action.cook_food(self)
            RoleManager.do_role_action(self)
            self.sell_surplus()

        elif part_of_day == "Night":
            if self.world.is_winter():
                self.consume_wood_at_night()
            self.update_needs_and_penalties()

        # After each part, degrade spoilage
        self.update_spoilage()

    def update_spoilage(self):
        """
        Decrement spoilage_left for each resource item each part of day.
        If it reaches 0, the item is spoiled and removed.
        """
        for item_name, item_list in self.items.items():
            for item in item_list:
                if not item.is_tool() and item.spoilage_left > 0:
                    item.spoilage_left -= 1
                    if item.spoilage_left <= 0:
                        # This entire stack spoils
                        self.log(f"{item.quantity} {item.name} spoiled and is discarded.")
                        item.quantity = 0  # spoil it
            # Cleanup zero-qty
            self.items[item_name] = [i for i in item_list if i.quantity > 0]

    def eat_if_needed(self):
        cfg = self.world.config
        if self.status.hunger < cfg["HUNGER_CRITICAL_THRESHOLD"]:
            # Prefer consuming nearly spoiled food first
            for item in sorted(self.items.get("food", []) + self.items.get("cooked_food", []), 
                            key=lambda x: x.spoilage_left):
                if item.quantity > 0:
                    consumed = min(1, item.quantity)
                    self.remove_resource(item.name, consumed)
                    self.status.hunger += 3 if item.name == "cooked_food" else 2
                    self.log(f"Ate {consumed} {item.name} => hunger +{3 if item.name == 'cooked_food' else 2}")
                    return

    def buy_essential_items(self):
        cfg = self.world.config
        if self.world.is_winter() and self.get_total_resource("wood") < 1:
            self.buy_item("wood", 1)

    def buy_primary_tool(self):
        primary_tools = self.world.config["ROLE_TOOLS"].get(self.role, [])
        for tool_name in primary_tools:
            if self.get_tool_count(tool_name) < 1:
                self.buy_item(tool_name, 1)

    def sell_surplus(self):
        cfg = self.world.config
        required_wood = cfg["MIN_WOOD_RESERVE_WINTER"] if self.world.is_winter() else 0

        for item_name, thresh in cfg["SURPLUS_THRESHOLDS"].items():
            current_amount = self.get_total_resource(item_name)
            if item_name == "wood":
                final_thresh = max(thresh, required_wood)
                if current_amount > final_thresh:
                    surplus = current_amount - final_thresh
                    self.sell_item("wood", surplus)
            else:
                if current_amount > thresh:
                    surplus = current_amount - thresh
                    self.sell_item(item_name, surplus)

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
        self.status.rest += cfg["REST_RECOVERY_PER_NIGHT"]
        self.status.hunger -= (cfg["HUNGER_DECREMENT_PER_DAY"] / 3.0)
        self.status.rest -= (cfg["REST_DECREMENT_PER_DAY"] / 3.0)

        self.status.hunger = max(0, self.status.hunger)
        self.status.rest = max(0, self.status.rest)

        if self.status.hunger < cfg["HUNGER_LOW_PENALTY_THRESHOLD"]:
            self.low_hunger_streak += 1
        else:
            self.low_hunger_streak = 0

        if self.status.rest < cfg["REST_LOW_PENALTY_THRESHOLD"]:
            self.low_rest_streak += 1
        else:
            self.low_rest_streak = 0

        if self.low_hunger_streak > 1:
            self.status.health = max(0, self.status.health - cfg["HEALTH_PENALTY_FOR_LOW_NEEDS"])
            self.status.happiness = max(0, self.status.happiness - cfg["HAPPINESS_PENALTY_FOR_LOW_NEEDS"])
            self.log("Suffering from prolonged hunger => health/happiness penalty.")

        if self.low_rest_streak > 1:
            self.status.health = max(0, self.status.health - cfg["HEALTH_PENALTY_FOR_LOW_NEEDS"])
            self.status.happiness = max(0, self.status.happiness - cfg["HAPPINESS_PENALTY_FOR_LOW_NEEDS"])
            self.log("Suffering from prolonged lack of rest => health/happiness penalty.")

    # --- MARKET/TRANSACTION HELPERS ---

    def buy_item(self, item_name, qty=1):
        market = self.world.market
        success, cost = market.attempt_buy(item_name, qty)
        if not success or cost > self.coins:
            return False
        self.coins -= cost
        market.finalize_buy(item_name, qty)
        self.add_item(item_name, qty)
        market.log_purchase(self, item_name, qty)
        return True

    def sell_item(self, item_name, qty=1):
        market = self.world.market
        success, revenue = market.attempt_sell(item_name, qty)
        if not success:
            return False
        if item_name in self.world.config["ITEMS"]:
            if self.world.config["ITEMS"][item_name]["type"] == "tool":
                if self.get_tool_count(item_name) < qty:
                    return False
                self.remove_tool(item_name, qty)
            else:
                if self.get_total_resource(item_name) < qty:
                    return False
                self.remove_resource(item_name, qty)
        self.coins += revenue
        market.finalize_sell(item_name, qty)
        market.log_sale(self, item_name, qty, revenue)
        return True

    # --- TOOLS & ITEMS ---

    def add_tool(self, tool_name, qty=1):
        tool_dur = self.world.config["ITEMS"][tool_name]["durability"]
        for _ in range(qty):
            new_tool = Item(tool_name, 1, tool_dur)
            self.items.setdefault(tool_name, []).append(new_tool)

    def remove_tool(self, tool_name, qty=1):
        lst = self.items.get(tool_name, [])
        removed = 0
        while removed < qty and lst:
            lst.pop(0)
            removed += 1
        if not lst:
            self.items[tool_name] = []

    def get_tool_count(self, tool_name):
        return sum(1 for i in self.items.get(tool_name, []) if i.is_tool())

    def degrade_tool(self, tool_name):
        for item in self.items.get(tool_name, []):
            if item.is_tool():
                item.durability -= 1
                if item.durability == 1:
                    self.log(f"{tool_name} is about to break! (1 use left)")
                if item.durability <= 0:
                    self.log(f"{tool_name} broke! Durability expired.")
                break

    def add_item(self, item_name, qty):
        # For resources
        if item_name in self.world.config["ITEMS"] and self.world.config["ITEMS"][item_name]["type"] == "tool":
            self.add_tool(item_name, qty)
            return

        # For resources, create a new stack each time
        new_item = Item(item_name, qty)
        self.items.setdefault(item_name, []).append(new_item)

    def remove_resource(self, item_name, qty):
        # Sort by spoilage (oldest first) before removing
        if item_name in self.items:
            self.items[item_name].sort(key=lambda x: x.spoilage_left)
        
        while qty > 0 and self.items.get(item_name):
            oldest = self.items[item_name][0]
            remove = min(qty, oldest.quantity)
            oldest.quantity -= remove
            qty -= remove
            if oldest.quantity <= 0:
                self.items[item_name].pop(0)

    def get_total_resource(self, item_name):
        total = 0
        for it in self.items.get(item_name, []):
            if not it.is_tool():
                total += it.quantity
        return total

    # --- HELPERS ---

    def find_owned_or_public_field(self):
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == "field" and tile.resource_level > 0:
                    if tile.owner_id == self.id or tile.owner_id is None:
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

    def log(self, message):
        self.world.log.log_action(
            self.world.day_count,
            self.world_part_of_day(),
            self.id, self.role,
            message
        )


# -------------------------------------------------------------------------
#  SIMULATION (added marriage checks)
# -------------------------------------------------------------------------

class Simulation:
    def __init__(self, config):
        self.config = config

        self.sim_log = SimulationLog()
        self.stats_collector = StatsCollector()
        self.world = World(config, self.sim_log)

        self.villagers = self._spawn_villagers()
        self.world.villagers = self.villagers
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
        farmers = [v for v in self.villagers if v.role == "Farmer"]
        field_tiles = []
        for row in self.world.grid:
            for tile in row:
                if tile.terrain_type == "field":
                    field_tiles.append(tile)
        random.shuffle(field_tiles)

        for i, farmer in enumerate(farmers):
            if i < len(field_tiles):
                field_tiles[i].owner_id = farmer.id
                field_tiles[i].resource_level = 5

    def run(self):
        max_days = self.config["TOTAL_DAYS_TO_RUN"]
        while self.world.day_count <= max_days:
            for part in self.config["PARTS_OF_DAY"]:
                # Check for new marriages only in Morning, for example
                if part == "Morning":
                    self._check_for_marriages()

                for v in self.villagers:
                    v.perform_part_of_day(part)
                    self.stats_collector.record_villager_stats(v)

                self.world.update_resources_and_events(part)
                self.world.advance_time()

        # Export logs & charts
        self.sim_log.export_log("simulation_log.txt")
        self.stats_collector.generate_charts("simulation_charts.html")

    def _check_for_marriages(self):
        """
        Simple approach: with a small probability, pick two single villagers to marry.
        """
        if random.random() < self.config["MARRIAGE_PROBABILITY"]:
            singles = [v for v in self.villagers 
                       if v.relationship_status == "single" 
                       and v.status.health > 0  # New health check
                       and v.status.hunger < 10]  # Optional: basic needs met
            if len(singles) >= 2:
                # pick 2 distinct villagers
                v1, v2 = random.sample(singles, 2)
                v1.relationship_status = "married"
                v2.relationship_status = "married"
                v1.partner_id = v2.id
                v2.partner_id = v1.id

                self.sim_log.log_action(
                    self.world.day_count, "Morning", 0, "EVENT",
                    f"Villager {v1.id} and Villager {v2.id} got married!"
                )


if __name__ == "__main__":
    sim = Simulation(CONFIG)
    sim.run()
    sys.exit()
