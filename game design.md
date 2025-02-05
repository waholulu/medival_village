# **Medieval Village Simulation: Final, Unified Design (Revised & Enhanced)**

Below is an updated version of the design document, with additional detail to clarify each feature and mechanism—now **including** a seasonal farming cycle in which **harvesting occurs only in Autumn** while other seasons focus on planting and nurturing crops. The goal is to maintain a balanced, cohesive structure without introducing excessive complexity or tight coupling between modules.

---

## **1. Introduction**

### **1.1 Overview**
This simulation models a **small medieval village**. The core elements include:

- **Villagers** with individual needs (hunger, rest, health, happiness) and unique roles (Farmer, Hunter, Logger, Blacksmith).
- A **Market** with **fixed prices** for essential goods (food, wood, tools).
- A **tile-based** grid (the **World**) for farmland, forests, and other terrains, each with resource levels.
- **Weather events** and **short seasons** (3 days per season) that influence resource availability and villager behaviors.
- **Seasonal Farming Cycle**: Fields are planted/maintained in Spring and Summer, and **harvested only in Autumn**.

### **1.2 Goals**
1. **Low Coupling**: Keep villager logic, market transactions, and world updates modular.  
2. **Incremental Complexity**: Start with fundamental survival mechanics, then layer on roles, tool durability, market transactions, special events, and now a **season-based farming cycle**.  
3. **Sustainability & Fallback**: Provide fallback yields when tools break, encourage villagers to buy or craft new tools, and maintain a stable economy.  
4. **Transparency**: Enable **detailed logging**, plus optional **charting** (e.g., Plotly) for post-simulation analysis.

---

## **2. Key Features & Requirements**

1. **Villager Needs**  
   - **Hunger**: Gradually depletes; must be satisfied with food or villager health suffers.
     - Early warning system triggers eating at `HUNGER_WARNING_THRESHOLD` (3) before critical levels
     - Tracks consecutive partial-days below threshold to determine penalties
   - **Rest**: Decreases over partial-day cycles; recovers +4 points during night.
     - Tracks consecutive partial-days below threshold for penalties
     - Penalties only apply after multiple consecutive low-rest periods
   - **Health & Happiness**: Influenced by hunger, rest, cold (in winter), and random events.
     - Takes -1 penalty when needs remain low for consecutive periods

2. **Roles & Tools**  
   - **Farmer**  
     - Uses a **hoe** for maximum yield on farmland.  
     - **Seasonal Crop Cycle**:  
       - **Spring & Summer**: Planting, nurturing, or fertilizing crops (no immediate harvest).  
       - **Autumn**: **Harvest** occurs only in this season, yielding food based on tile resource levels and farmland preparation.  
       - **Winter**: Fields are mostly fallow; little to no farming output.  
   - **Hunter**  
     - Uses a **bow** to hunt animals in forests for food.  
   - **Logger**  
     - Uses an **axe** to gather wood from forests.  
   - **Blacksmith**  
     - Consumes wood/ore to **craft** tools, then sells them at the Market.  
   - **Tool Durability**: Tools have finite durability and need repair or replacement when they break.

3. **Market (Fixed Prices)**  
   - A unified **Market** that buys and sells food, wood, and tools.  
   - Prices remain **constant** (no dynamic supply-demand changes).  
   - The Market tracks its own stock of items (stock can be infinite or bounded, depending on the simulation goals).  
   - Villagers can **buy** if they have enough coins and if the item is in stock; they can always **sell** surplus to the Market.

4. **Farmland Ownership**  
   - Some tiles are **privately owned** by specific villagers.  
   - Farmers **prioritize** their owned farmland first, then use public or unowned fields if needed.
   - The **seasonal** cycle applies equally to both privately owned and public fields:  
     - **Spring & Summer**: Farmers can spend actions to improve their eventual Autumn harvest yields.  
     - **Autumn**: Farmers reap the harvest from owned or public fields that they have worked on.

5. **Short Seasons & Partial-Day Steps**  
   - Each **season** spans exactly **3 days** (Morning, Afternoon, Night).  
   - There are **4 seasons**, totaling **12 days** in a year.  
   - **Winter Requirements**: villagers must **burn wood** at night or suffer health/happiness penalties.  
   - **Farming Constraint**: The **harvest** only occurs in **Autumn**; farmland actions in Spring and Summer set up the yield potential for that harvest.

6. **Surplus Resource Selling**  
   - Villagers automatically sell **excess** resources (e.g., if holding more than 5 food or wood).  
   - This prevents resource hoarding and maintains a flow of goods in the Market.

7. **Weather & Random Events**  
   - **Storm System**:
     - Occurs only during morning periods
     - Reduces resource levels by 2 in affected tiles
     - Impacts approximately 25% of the map tiles
     - 10% chance of storm each morning
   - Additional events (e.g., pest infestations, droughts) can be integrated to impact farmland or forest resources.  
   - **Crop-Specific Weather Impact**: Spring or Summer storms or droughts may reduce the eventual Autumn harvest if farmland resource levels drop.


8. **Simulation & Logging**  
   - **Core** simulation (headless) updates villagers, the world, and the market each partial-day cycle.  
   - **Logs** record each villager's actions, transactions, tool usage, resource changes, and random events.  
   - Optional **plotting** (Plotly) at the simulation's end to visualize resources, villager status, and key metrics over time.

## **3. Architecture**

### **3.1 World**
- **Grid Structure**: 2D array of `Tile` objects, each storing:
  - `terrain_type` (e.g., `forest`, `field`, `water`)  
  - `resource_level` (how much wood or food can be gathered)  
  - `owner_id` (which villager owns the tile, if any)
- **Market**: Embedded `Market` instance managing:
  - **Fixed** `ITEM_PRICES` for food, wood, and tools.  
  - **Stock** availability for items.  
  - Buy/sell transactions with villagers.
- **Time & Seasons**:
  - Each day has **3 parts** (Morning, Afternoon, Night).  
  - Each partial-day tick, the simulation updates villager needs and performs role-specific actions.  
  - **Season Changes**: every 3 days triggers a new season, with winter requiring wood consumption and autumn enabling farmland harvests.
- **Weather & Events**:
  - **Random storms**: chance to reduce `resource_level` on certain tiles each day or each partial-day.  
  - Extendable with other events (drought, flood, pest), which can specifically target farmland growth in spring/summer.

### **3.2 Villager**
- **Attributes**: `hunger`, `rest`, `health`, `happiness`, plus `inventory` (food, wood, coins) and `tools` (each with a `durability`).  
- **Role**: Farmer, Hunter, Logger, or Blacksmith.  
- **Actions** (in typical daily order):
  1. **Eat**: If hunger is below a threshold, consume food from inventory (if available).  
  2. **Buy Essentials**: If needed tool is missing/broken or if short on wood during winter, attempt to buy from Market.  
  3. **Role Action**: (Farm/Hunt/Log/Craft) during Morning/Afternoon.  
     - **Farming**:  
       - **Spring & Summer**: Tending crops, incrementally raising `resource_level` on farmland for the upcoming Autumn harvest.  
       - **Autumn**: Actually **harvest** the crops, collecting food resources based on farmland `resource_level`.  
       - **Winter**: Minimal farm activity; might do other tasks or just rest.  
     - **Hunting**: Searching forests for food.  
     - **Logging**: Gathering wood from forest tiles.  
     - **Crafting**: Blacksmith forging tools, consuming wood/ore.  
     - If the correct tool is available, produce maximum yield or get maximum effect.  
     - If the tool is broken or missing, produce a reduced "fallback" yield/effect.  
     - Reduce tool durability by 1 if used.  
  4. **Sell Surplus**: If inventory for food/wood exceeds a threshold (e.g., >5).  
  5. **Night & Winter**: Burn wood if it's winter and night to avoid health/happiness penalties.  
  6. **Update Status**: Decrement hunger/rest, log actions, handle health/happiness changes based on events or resource availability.

### **3.3 Simulation**
- **Master Loop**: 
  - Moves through partial-day cycles (Morning, Afternoon, Night).  
  - For each villager, calls their `update()` method to handle daily actions.  
  - Updates the **World** for resource regeneration or depletion, triggers weather events, and changes seasons.  
- **Stop Condition**: runs until a specified day limit (e.g., 36 days = 3 years), or until all villagers die, or until a user-controlled exit condition.

### **3.4 Logging & Plotting**
- **Logging**:  
  - Each partial-day step records villager actions, Market buys/sells, storms, tool breakages.  
  - Optionally print to console or store in a text file for later review.
- **Plotting** (Optional, e.g., Plotly):  
  - At the simulation's end, generate charts that visualize:  
    - Villager hunger/health/coins over time.  
    - Resource availability across the grid (e.g., average wood in forests, farmland levels).  
    - Market stock levels (if relevant).

### **3.5 Pygame (View Layer)**
- Purely **visual**: Draws the tile map, villagers, and basic stats (day number, season, partial-day indicator).  
- **No** direct manipulation of game state: it listens to simulation updates and renders them.  
- Optional to enable or disable as needed.

### **3.6 Marriage System**
- Daily morning marriage checks with probability (CONFIG["MARRIAGE_PROBABILITY"])
- Requirements for marriage candidates:
  - Relationship status: single
  - Health > 5
  - Hunger > 4
- Married partners track each other via partner_id
- System events logged with marriage announcements

### **3.7 Cooked Food System**
- Conversion ratio: 2 raw food → 1 cooked food
- Separate item type with different properties:
  - Higher price (2 vs 1)
  - Separate inventory tracking
  - Spoilage system (currently disabled in config)

### **3.8 Skill Progression**
- Skill gain per action: 0.15 (CONFIG["SKILL_GAIN_PER_ACTION"])
- Maximum skill multiplier: 2.0× base efficiency
- Affects action efficiency but not tool durability
- Tracked per-role with individual skill levels

## **4. Implementation Details**

### **4.1 Villager Behavior**
- **Priority Logic**:
  1. Check immediate survival needs (eat if hungry).  
  2. Check for necessary items (tools, winter wood) and **buy** if needed.  
  3. Execute **role action** (farm, hunt, log, craft).  
     - **Farm** in Spring/Summer to raise resource levels, then **harvest** in Autumn.  
     - Reduce durability of the relevant tool if used.  
  4. **Sell Surplus** if inventory is too large.  
  5. **At night in winter**, burn wood if possible; else penalize health/happiness.  
- **Fallback**:  
  - If a role's tool is broken or absent, produce partial yield.  
  - Continue partial yield until a new tool is acquired.

### **4.2 Market Operations**
- **Fixed ITEM_PRICES**: A dictionary managing costs of all items
- **Tool Transactions**:
  - Tools are handled differently from regular items
  - Each new tool starts with full durability
  - Blacksmiths craft the tool type with lowest market stock
  - Requires 1 wood per tool crafted

### **4.3 Inventory Management**
- Stack-based inventory with quantity tracking
- Automatic cleanup of zero-quantity items
- Separate handling for tools vs resources:
  ```python:simulation.py
  startLine: 865
  endLine: 879
  ```

### **4.4 Field Management**
- Initial field resource level: 5 when assigned
- Field preparation yields:
  - Base +6 resources per action with tool
  - Fallback +1 without tool
- Maximum field resource cap: 40 (observed in logs)

### **4.5 Winter Handling**
- Mandatory wood burning during winter nights
- Cold penalties apply even to incapacitated villagers
- Minimum wood reserve check before selling surplus

### **4.6 Disease System**
- 5% daily disease probability (CONFIG["DISEASE_PROBABILITY"])
- Immediate 2 health point loss
- Can strike incapacitated villagers

### **4.7 Tool Breakage Flow**
- Warning system at durability=1
- Automatic removal of broken tools
- Fallback yields when tool-less:
  ```python:simulation.py
  startLine: 1096
  endLine: 1109
  ```

### **4.8 Market Operations**
- Initial stock quantities:
  - Tools: 5 each
  - Food/Wood: 50 each
  - Cooked food: 0
- Blacksmith crafting consumes 1 wood per tool

### **4.9 Action Priorities**
- Updated daily action sequence:
  1. Morning marriage checks
  2. Needs fulfillment (eating)
  3. Tool maintenance
  4. Role actions
  5. Surplus selling
  6. Night/winter handling
  ```python:simulation.py
  startLine: 1096
  endLine: 1109
  ```

### **4.10 Logging Details**
- Comprehensive action logging including:
  - Tool purchases/breakages
  - Cooking conversions
  - Disease events
  - Marriage announcements
  - Market transactions
  ```python:simulation.py
  startLine: 1040
  endLine: 1046
  ```

## **5. Config Updates**
These config parameters need documentation:

```python
"MARRIAGE_PROBABILITY",  # Currently undefined in shown config
"SKILL_GAIN_PER_ACTION": 0.15,
"MAX_SKILL_MULTIPLIER": 2.0,
"REST_RECOVERY_PER_NIGHT": 4,
"MIN_WOOD_RESERVE_WINTER": 2
```

These updates ensure the design document accurately reflects the changes made to the simulation script, particularly regarding the seasonal farming cycle and its implementation.

## **6. Additional Features**

1. **Tool Breakage Warnings**
   - Tools show "about to break" warnings when durability reaches 1
   - Full breakage messages appear when durability reaches 0
   - Broken tools are automatically removed from inventory

2. **Skill Progression System**
   - Villagers gain 0.3 skill points per action (CONFIG["SKILL_GAIN_PER_ACTION"])
   - Skill levels provide durability bonus: min 20% bonus to tools (CONFIG["MIN_TOOL_DURABILITY_BONUS"])

3. **Disease System**
   - 5% daily chance of disease (CONFIG["DISEASE_PROBABILITY"])
   - Diseases cause 2 health point loss (CONFIG["DISEASE_HEALTH_LOSS"])
   - Implemented in World event handling

4. **Farmland Initialization**
   - Fields start with resource_level 5 when assigned
   - Maximum field resource capped at 20 (CONFIG["MAX_FIELD_RESOURCE"])
   - Private fields assigned via _assign_farmland_to_farmers() method

5. **Winter Wood Reserves**
   - Villagers maintain minimum 2 wood reserve in winter (CONFIG["MIN_WOOD_RESERVE_WINTER"])
   - Affects wood burning priority during winter nights

6. **Inventory Stack Management**
   - Resources stack in single items with quantity tracking
   - Tools stored as separate inventory entries with individual durability
   - Automatic cleanup of zero-quantity resource items

7. **Market Stock Tracking**
   - Initial tool stocks: 5 each (CONFIG["INITIAL_MARKET_STOCK"])
   - Food/wood initial stock: 50 each
   - Blacksmiths craft tools based on lowest market stock

## **7. Updates Required to Design Document**

### **7.1 Marriage System Enhancements (Code Reference)**
- Marriage candidates require minimum health(>5) and hunger(>4) thresholds
- Married partners get linked via partner_id
- Marriage events are logged as system events

### **7.2 Cooked Food Mechanics**
- Cooked food has different properties from raw food (price=2 vs 1)
- Cooking conversion ratio: 2 raw food → 1 cooked food
- Cooked food has separate spoilage handling (disabled in config)

### **7.3 Skill System Implementation**
- Actual skill gain per action: 0.15 (vs documented 0.3)
- Max skill multiplier capped at 2.0× base efficiency
- Skill affects action efficiency but not tool durability

### **7.4 Event System Details**
- Storm reduces resources by 2 levels in affected tiles
- Disease causes immediate 2 health point loss
- Event probabilities: 10% storms, 5% diseases daily

### **7.5 Market Operations**
- Initial stock quantities:
  - Tools: 5 each
  - Food/Wood: 50 each
  - Cooked food: 0
- Blacksmiths consume 1 wood per tool crafted
- Market tracks transaction logs separately from system events

### **7.6 Winter Handling**
- Wood burning happens automatically if available
- Cold penalties apply even if villager is incapacitated
- Minimum wood reserve check happens before selling surplus

### **7.7 Tool Breakage Flow**
- Broken tools are automatically removed from inventory
- Villagers continue working with reduced efficiency when tool-less
- Warning system triggers at durability=1

### **7.8 Field Management**
- Private fields are assigned via _assign_farmland_to_farmers()
- Maximum field resource cap: 40 (CONFIG["MAX_FIELD_RESOURCE"])
- Field preparation yields +6 resources per action with tool

### **7.9 Inventory Management**
- Automatic selling happens when food/wood >5
- Cooked food is tracked separately from raw food
- Tools are stored with individual durability states



