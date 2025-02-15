# Medieval Village Simulation: Updated & Detailed Design Document

This **design document** describes the full set of features, systems, and data flows in the **Medieval Village Simulation**. It is aligned with the current **Python implementation** that uses a single configuration dictionary (`CONFIG`), along with classes like `World`, `Villager`, `Market`, `EventManager`, and so forth. The simulation is turn-based, advancing in partial-day increments (Morning, Afternoon, Night), while handling resource consumption, tool usage, production activities, weather, disease, combat, and marriage events.

---

## 1. Overview

The simulation’s **main objective** is to model the **daily survival and economic activities** of a small medieval village. Each villager has specific **needs** (hunger, rest, health, happiness) and a **role** (Farmer, Hunter, Logger, Blacksmith). The environment is represented by a **2D grid** of tiles where each tile has terrain (forest, field, water) and a resource level. The simulation aims to explore how villagers interact with **market dynamics**, **tool usage**, **seasons**, and **random events** (storms, disease, monster attacks) to maintain a stable village over a given duration.

**Key points:**
1. **Seasonal Cycle**: 3 days per season (Spring, Summer, Autumn, Winter), repeated.
2. **Time Step**: Each day has 3 parts (Morning, Afternoon, Night).
3. **Villager Roles**: Distinct actions for each role, plus fallback (forage) if needed.
4. **Events**: Random storms, diseases, monsters that affect resource levels or villager health.
5. **Market**: Villagers buy/sell items (food, wood, tools, herbs, cooked food) to meet daily needs or earn coins.
6. **Marriage**, **Cooking**, **Tool Repair**, **Skill Progression**, **Spoilage**, **Logging**, and **Chart Visualization** add depth to the simulation.

---

## 2. Key Features

### 2.1 Villager Attributes & Needs

Each villager tracks:
- **Hunger** (`status.hunger`):
  - Default initial value: 10.
  - Depletes by `HUNGER_DECREMENT_PER_DAY` spread over Morning/Afternoon/Night.
  - Affects health/happiness if it stays below certain thresholds for multiple partial-days.

- **Rest** (`status.rest`):
  - Default initial value: 10.
  - Depletes by `REST_DECREMENT_PER_DAY` daily, recovers by `REST_RECOVERY_PER_NIGHT` each Night.
  - Low rest over multiple parts of the day leads to health/happiness penalties.

- **Health** (`status.health`):
  - Default initial value: 80. Capped at `MAX_HEALTH` = 100.
  - Decreases from starvation, cold weather (no wood in Winter), disease, monster attacks, or extended low rest/hunger.
  - Increases slightly overnight (`NIGHT_HEALTH_RECOVERY`) if alive and not severely cold.

- **Happiness** (`status.happiness`):
  - Default initial value: 10.
  - Decreases if hunger or rest are consistently low, if cold in winter nights (no wood), or if health is critically low.
  - Kept above zero if basic needs are met and negative events are avoided.

- **Coins**:
  - Used to buy supplies from the Market.
  - Earned by selling surplus items or crafting/selling tools.

- **Inventory**: 
  - **Resources**: A dictionary `{ item_name: quantity }` (e.g., `"food": 5, "wood": 2, "cooked_food": 1, "herb": 0 }`.
  - **Tools**: A dictionary `{ tool_name: [Item, Item, ...] }`, where each `Item` represents a single tool with individual **durability**.

- **Skill Level** (`skill_level`):
  - Starts at 1.0. Each role-related action (farm/hunt/log/craft) grants `SKILL_GAIN_PER_ACTION` (0.05).
  - Productivity or yields are adjusted by `min(skill_level, (MAX_SKILL_MULTIPLIER - 1))`.

- **Relationship Status**:
  - Either `"single"` or `"married"`.
  - If married, stores a `partner_id`.

### 2.2 Roles and Their Actions

1. **Farmer**  
   - Primary tool: **hoe**.  
   - **Spring & Summer**: Increases resource level of farmland tiles (planting/maintenance).  
   - **Autumn**: Harvests farmland tiles. The entire resource level of the tile is converted into food. The tile’s resource becomes 0 (or partially depleted).  
   - **Winter**: Farmland resources degrade, minimal farming yield. May do fallback foraging.

2. **Hunter**  
   - Primary tool: **bow**.  
   - Hunts in **forest** tiles for food, reducing tile resource level.  
   - Yields are typically smaller than a full farm harvest, but consistent across seasons.

3. **Logger**  
   - Primary tool: **axe**.  
   - Cuts wood in forest tiles, reducing the tile’s resource level by a configured amount (`LOGWOOD_RESOURCE_DECREASE`).  
   - Gathers wood for personal or Market use, crucial in winter for heating.

4. **Blacksmith**  
   - No required primary tool to operate, but may fix or craft any tool.  
   - Repairs villagers’ broken or damaged tools if enough **wood** is available in the Market.  
   - Crafts new tools if Market stock is low, then sells them for coins.  
   - If no crafting or repairs are needed, may do fallback actions (forage).

5. **Fallback: Forage**  
   - If a villager cannot perform their role action (e.g., no farmland or no forest resources), they gather a small amount of food from the environment (`FORAGE_FOOD_GAIN`).

### 2.3 The Market

- Holds an internal `stock` dictionary `{ item_name: quantity }`.
- **Prices** come from `CONFIG["ITEMS"][item_name]["price"]`.
- If stock exceeds `MARKET_MAX_STOCK[item_name]`, the price is multiplied by `MARKET_PRICE_DECAY` (e.g., 0.95).
- **Buy**:  
  - Villager attempts to buy an item. If enough stock and villager has enough coins, the transaction proceeds.  
  - Market reduces its stock, villager gains the item. Villager’s coin count decreases by `price * quantity`.
- **Sell**:  
  - Villager sells an item if they have surplus.  
  - Market’s stock increases, villager’s inventory decreases. Villager’s coins increase by `price * quantity`.

### 2.4 Seasonal Cycle

- **Seasons** = `[Spring, Summer, Autumn, Winter]`, each lasting 3 days.
- **Spring & Summer**:
  - Farmers increase farmland resource levels for a future harvest.
  - Forests regrow slightly at night.
- **Autumn**:
  - Farmers harvest farmland, gaining food.
- **Winter**:
  - Farmland resource levels shrink by `WINTER_FIELD_LOSS`.
  - **Wood** is consumed each Night (`WINTER_WOOD_CONSUMPTION`) to keep villagers warm.
  - If no wood is available, villagers lose health and happiness from cold.

### 2.5 Events & Random Hazards

1. **Storms** (`STORM_PROBABILITY`=0.1):
   - Occur in Morning.  
   - Randomly affects around `(width * height) / STORM_AFFECTED_TILE_DIVISOR` tiles, each losing `STORM_RESOURCE_REDUCTION` resource levels.

2. **Disease** (`DISEASE_PROBABILITY`=0.05):
   - Random villager suffers `DISEASE_HEALTH_LOSS` (2) health damage.

3. **Monster Attacks** (`MONSTER_SPAWN_PROB`=0.05):
   - Spawns a **Monster** (Wolf, Bear, Goblin) with random health/damage (within config ranges).  
   - Immediately attacks a random villager in up to `COMBAT_MAX_ROUNDS` of combat.  
   - Villager’s health decreases per monster damage roll; monster can die or remain alive (though typically removed if it flees or is killed).

### 2.6 Cooking & Herbs

- **Cooking**:
  - Converts a certain quantity of raw food into **cooked_food** (`COOKING_CONVERSION_RATE`=1).  
  - Cooked food is more beneficial (+3 hunger, +2 health in emergency, higher market price).  
  - Villager performs cooking if they have extra raw food and a high enough probability (`COOKING_PROBABILITY`=0.9).

- **Herbs**:
  - If health is critically low, a villager may consume an herb (`HERB_HEALTH_BOOST`=4).
  - Herbs can be bought from or sold to the Market if available.

### 2.7 Marriage

- Each morning, there is a `MARRIAGE_PROBABILITY` chance to check for potential marriages:
  - Among single villagers with adequate thresholds:
    - `health` > `MARRIAGE_HEALTH_THRESHOLD`
    - `hunger` > `MARRIAGE_HUNGER_THRESHOLD`
    - `get_item_count("food")` > `MARRIAGE_FOOD_THRESHOLD`
    - `get_item_count("wood")` > `MARRIAGE_WOOD_THRESHOLD`
  - Pairs up two random qualifying singles. Both become `relationship_status = "married"`, each storing the other’s `partner_id`.

### 2.8 Tool System

- **Durability**:
  - Each tool item has a fixed max durability.  
  - Using it for its intended action (farming with a hoe, hunting with a bow, logging with an axe) reduces durability by 1.  
  - If durability hits 0, the tool breaks and is removed from inventory.  
  - A warning logs when a tool hits durability=1.

- **Repair**:
  - Blacksmiths can repair a damaged tool if there is enough wood in the Market to cover `TOOL_REPAIR_WOOD` * (missing durability).  
  - On repair, the tool is fully restored to max durability.

- **Fallback Yield**:
  - If the correct tool is missing or broken, actions yield a reduced amount (`FALLBACK_FARM_YIELD`, `FALLBACK_LOG_YIELD`, etc.).

### 2.9 Surplus & Safety Stock

- **Surplus Thresholds** (`SURPLUS_THRESHOLDS`):
  - E.g., if a villager has more than 10 food, they may sell the excess automatically.  
  - Encourages a steady flow of goods to and from the Market.

- **Winter Reserve**:
  - If it’s winter, villagers try to keep a minimum amount of wood (`MIN_WOOD_RESERVE_WINTER`) for heating at night before selling any surplus.

### 2.10 Spoilage

- Some items may have a nonzero `spoilage` rate.  
- If `(current_tick % spoilage_rate) == 0`, the item spoils and is discarded entirely.  
- By default, `food` and `herb` have spoilage = 0, so it’s effectively disabled.

---

## 3. Class Architecture

### 3.1 `Simulation`

- **Attributes**:  
  - `config`: The master `CONFIG` dictionary.  
  - `sim_log`: An instance of `SimulationLog` for recording events/actions.  
  - `stats_collector`: A `StatsCollector` that captures villager status over time.  
  - `world`: A `World` instance containing all tiles, Market, EventManager, and day/time tracking.

- **Methods**:
  - `__init__()`: Initializes the World and spawns villagers.  
  - `run()`: Main loop over `TOTAL_DAYS_TO_RUN`, dividing each day into 3 parts:
    1. Morning: Possibly handle marriages, daily events, have villagers act.
    2. Afternoon: Villagers act again.  
    3. Night: Villagers rest, burn wood if winter, then gather final stats.  
  - After finishing, exports logs and generates charts.

### 3.2 `World`

- **Attributes**:
  - `config`: Shared dictionary of parameters.
  - `width`, `height`: Grid size from config.  
  - `grid`: 2D array of `Tile`s.  
  - `market`: A `Market` instance.  
  - `event_manager`: An `EventManager` instance.
  - `day_count`: The current simulation day (starting at 1).
  - `part_of_day_index`: 0 (Morning), 1 (Afternoon), or 2 (Night).
  - `villagers`: A list of all villager objects.
  - `monsters`: Any active monsters in the world (added if a monster spawns).

- **Key Methods**:
  - `_generate_tiles()`: Creates the grid based on `TERRAIN_DISTRIBUTION`.  
  - `update_resources_and_events(part_of_day)`:  
    - If `Morning`, triggers event checks (storm/disease/monsters).  
    - If `Night`, regenerates some forest resources.  
    - Removes dead villagers from the list if health ≤ 0.
  - `advance_time()`: Moves to next partial day or increments the day count if moving from Night to the next Morning.
  - `get_current_season()`: Derives the season from `(day_count - 1) // DAYS_PER_SEASON`.
  - `is_winter()`: Checks if the current season is `"Winter"`.

### 3.3 `EventManager`

- **Methods**:
  - `handle_morning_events(world)`:  
    1. Check for storm probability; reduce tile resources.  
    2. Check for disease probability; inflict damage on a random villager.  
    3. Check for monster spawn probability; spawn and attack.  
  - `trigger_storm(world)`, `trigger_disease(world)`, `trigger_monster_attack(world)`: detailed subroutines.

### 3.4 `Villager`

- **Attributes**: `id`, `role`, `world`, `status`, `coins`, `skill_level`, `relationship_status`, `partner_id`, `inventory`.
- **Methods**:
  - **Daily Cycle**:
    - `perform_part_of_day(part_of_day)`: Delegates to `handle_morning()`, `handle_afternoon()`, or `handle_night()`.
  - **Morning**:
    - Attempt **emergency_recover** if health is very low.
    - **eat_if_needed**, **buy_essential_items**, **buy_primary_tool**, then role action via `RoleManager.do_role_action(villager)`.
    - Optionally cook food if raw food > `RAW_FOOD_SAFETY`.
    - Use an herb if health < `USE_HERB_HEALTH_THRESHOLD`.
  - **Afternoon**:
    - Repeat role action or fallback if needed, then attempt to **sell_surplus**.
  - **Night**:
    - If winter, call `consume_wood_at_night()`.
    - Recover health partially, update hunger/rest.  
  - **Role Actions** (farm/hunt/log_wood/craft/forage) are in `Action` class.  
  - **Inventory Helpers**: `add_item`, `remove_item`, `get_item_count`, `degrade_item`.  
  - **Spoilage**: `update_spoilage()` checks whether resources spoil based on current tick vs. item spoilage rate.
  - **Logging**: `log(message)` convenience method.

### 3.5 `Action` Utility Class

- `farm(villager)`, `hunt(villager)`, `log_wood(villager)`, `craft(villager)`, `forage(villager)`, `cook_food(villager)`, etc.  
- Implements logic such as **yield** calculations, tool usage/durability reduction, fallback to foraging, logging messages, etc.
- **Season-Specific** logic in `farm(villager)`:
  - Spring/Summer: Increase farmland resource up to `MAX_FIELD_RESOURCE`.  
  - Autumn: Harvest farmland fully, converting the tile’s `resource_level` to food.  
  - Winter: Field resources degrade; fallback forage.

### 3.6 `Market`

- **Attributes**: `stock` (dict), `config`, `log` (shared `SimulationLog`).
- **Buy/Sell** flow:
  - `_attempt_transaction(item_name, qty, is_buy=True)`: Internal logic for checking stock or computing cost.  
  - `attempt_buy(item_name, qty)`: Returns `(success, total_cost, actual_qty)`.
  - `finalize_buy(item_name, qty)`: Deduct from stock.  
  - `attempt_sell(item_name, qty)`: Returns `(success, revenue, actual_qty)`.
  - `finalize_sell(item_name, qty)`: Increase stock, discard overflow if maxed out.  
  - `get_price(item_name)`: Base price with optional decay.  
  - `log_purchase(villager, item_name, qty)`, `log_sale(villager, item_name, qty, revenue)`: records transactions.

### 3.7 Logging & Charting

1. **SimulationLog**:
   - Stores a list of `(day, part, villager_id, role, message)` tuples.
   - `export_log(filename)`: Writes lines sorted by `(day, villager_id)`.
     - Day 0 is used for system-level or market messages if needed.

2. **StatsCollector**:
   - Gathers each villager’s stats after their part-of-day action:
     - Hunger, rest, health, happiness, coins, counts of key items.
   - `generate_charts(filename)`:  
     - Builds multi-plot charts using Plotly:
       - Individual lines for hunger, health, happiness over time.
       - Averages by role for coins, health, and happiness.
       - Seasonal lines (dotted vertical lines) marking season changes.
     - Embeds the simulation log in an HTML with a filterable log box.

---

## 4. Core Simulation Flow

Below is a **high-level** pseudocode structure showing how the simulation progresses each day:

Initialize Simulation(config): world = World(config) villagers = spawnVillagers() # Create roles as per config world.villagers = villagersday_count = 1 while day_count <= config["TOTAL_DAYS_TO_RUN"]: for part in ["Morning", "Afternoon", "Night"]: if part == "Morning": # Check marriage, handle weather/disease/monsters simulation.check_for_marriages() eventManager.handle_morning_events(world)
yaml
Copy
    # Each villager acts
    for villager in world.villagers:
        villager.perform_part_of_day(part)

    # If this part is Night, log daily summary for each villager
    if part == "Night":
        for villager in world.villagers:
            villager.log_daily_summary()

    # Update environment, remove dead villagers, regrow resources if needed
    world.update_resources_and_events(part)

    # Advance time
    world.advance_time()  # increments part_of_day_index or day_count
Finalize: sim_log.export_log("simulation_log.txt") stats_collector.generate_charts("simulation_charts.html")
markdown
Copy

---

## 5. Extended Details and Additional Mechanics

1. **Emergency Recovery**:
   - If health is below `EMERGENCY_HEALTH_THRESHOLD` (5), villager tries to:
     - Cook food if possible and eat it for a health boost, OR
     - Buy and use an herb if no food is available.
   - Logged as emergency actions in the simulation log.

2. **Cold Penalty in Winter**:
   - Each Night in Winter, a villager must burn `WINTER_WOOD_CONSUMPTION` wood if they have it.
   - If they do not, they lose health and happiness (`NO_WOOD_PENALTY`=0.5).

3. **Combat Flow** (Monster Attack):
   - A monster with random (health, damage) spawns and selects a random villager.
   - They trade up to 3 attack rounds:
     - Villager deals 1–3 damage each round; monster deals 1–(monster.damage).
     - If the villager’s health hits 0, that villager “dies” (removed from the simulation).
     - If monster’s health hits 0, it is removed from the world.  
   - Logged under an “EVENT” role with details.

4. **Spoilage Implementation**:
   - Each partial day, `villager.update_spoilage()` checks each resource’s spoilage rate.
   - If `current_tick % spoilage_rate == 0`, the full quantity is discarded.
   - Default rates are often 0, disabling spoilage.

5. **Marriage Effects** (Future Expansions):
   - Currently, being “married” does not change daily actions beyond the log.
   - Potential expansions might let spouses share inventory, or benefit from health/happiness synergy.

6. **Tool Repair vs. Crafting**:
   - Blacksmith checks each tool in inventory; if it is not at max durability, tries to repair with `TOOL_REPAIR_WOOD`.
   - If no repairs needed, crafts the tool with greatest shortage in the Market, sells it for coins.

7. **Skill Gain**:
   - Each role action increments `skill_level` by `SKILL_GAIN_PER_ACTION` (0.05).
   - Effective yield multiplier for certain actions = `1 + skill_bonus + TOOL_YIELD_BASE`, capped by `max_multiplier` = 3.0 for logging or `MAX_SKILL_MULTIPLIER` for farming/hunting.
   - Example: Farmer with skill=1.15 → skill_bonus=0.15, plus base=1, plus `TOOL_YIELD_BASE`=1.0 => total=2.15 if allowed by max multiplier.

---

## 6. Configuration Highlights

Below are some **notable** config entries (see code for the full list):

- **Terrain & Field**:
  - `TERRAIN_DISTRIBUTION`: Probabilities for forest, field, water.
  - `MAX_FIELD_RESOURCE`=30; farmland cannot exceed this resource level.
  - `WINTER_FIELD_LOSS`=0.5; farmland resource halves in winter if a farmer attempts to farm it.

- **Items**:
  - `"food"`, `"cooked_food"`, `"wood"`, `"herb"` as resources with price/spoilage.
  - `"axe"`, `"bow"`, `"hoe"` as tools, each with defined durability and price.

- **Season & Time**:
  - `DAYS_PER_SEASON`=3, `SEASONS`=["Spring","Summer","Autumn","Winter"].
  - `PARTS_OF_DAY`=["Morning","Afternoon","Night"].

- **Roles**:
  - `NUM_FARMERS`=10, `NUM_HUNTERS`=4, `NUM_LOGGERS`=3, `NUM_BLACKSMITHS`=3.
  - `ROLE_TOOLS` mapping each role to a preferred tool.

- **Market**:
  - `MARKET_MAX_STOCK`: Maximum capacity for each item.
  - `MARKET_PRICE_DECAY`=0.95 if over capacity.

- **Events**:
  - `STORM_PROBABILITY`=0.1, `DISEASE_PROBABILITY`=0.05, `MONSTER_SPAWN_PROB`=0.05.
  - `STORM_RESOURCE_REDUCTION`=2, `DISEASE_HEALTH_LOSS`=2.

- **Marriage**:
  - `MARRIAGE_PROBABILITY`=0.05, thresholds for health/hunger/food/wood.

- **Cooking**:
  - `COOKING_CONVERSION_RATE`=1 (1 raw food => 1 cooked_food),
  - `COOKING_PROBABILITY`=0.9.

- **Logging**:
  - `LOG_FILENAME`="simulation_log.txt", `CHART_FILENAME`="simulation_charts.html".

---

## 7. Simulation Execution & Outputs

1. **Run** the simulation (for example, `python simulation.py`) → it instantiates all objects, spawns villagers, and executes day/part cycles until `TOTAL_DAYS_TO_RUN` is reached.
2. **Logging**:
   - Detailed textual logs stored in `simulation_log.txt`:
     - Day-based lines listing each villager’s events, plus system-level events for storms, diseases, marriages, etc.
3. **Charts**:
   - An HTML file `simulation_charts.html` is generated with multiple subplots:
     - Individual hunger, health, happiness lines per villager.
     - Average coins/health/happiness by role.
     - Vertical dotted lines marking season changes.
   - The final HTML contains a filterable log box and optional UI elements to resize or filter by villager ID.

4. **Possible Extensions** (not fully implemented yet):
   - **Family Mechanics**: Married villagers pooling resources, or affecting each other’s happiness if one is sick.
   - **Advanced Pricing**: True supply/demand-based market with price adjustments.
   - **Additional Resources**: More refined items (iron, stone, etc.), specialized farmland seeds, livestock, etc.
   - **AI Behavior**: More complex decision-making for trades or tool usage.

---

## 8. Conclusion

This **detailed design** captures the **current state** of the Medieval Village Simulation, reflecting all major code features:

- **Individual villager states** (hunger, rest, health, happiness, skill, marriage).
- **Role-based production** (Farmer, Hunter, Logger, Blacksmith).
- **Seasonal farmland** mechanics (plant in Spring/Summer, harvest in Autumn, degrade in Winter).
- **Random events** (storms, disease, monsters) that challenge survival.
- **Market system** for buying/selling goods with partial price decay if overstocked.
- **Marriage system** for pairing villagers with sufficient resources.
- **Cooking, tool repair, skill progression**, and **spoilage** for deeper realism.
- **Comprehensive logging** and **Plotly charts** for post-run analysis.

This document ensures all implemented logic is fully described and offers a clear reference for future enhancements or debug