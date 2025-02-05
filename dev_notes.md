# Development Notes

## 2024-03-XX - Initial Village Simulation Implementation

### Major Components Added:
1. Core Simulation Framework
- World class with grid-based environment
- Time system with days, seasons, and parts of day
- Market system for trading resources and tools
- Event system for random occurrences (storms, diseases)

2. Villager System
- Multiple roles (Farmer, Hunter, Logger, Blacksmith)
- Need-based AI (hunger, rest, health, happiness)
- Inventory management for tools and resources
- Skill progression system

3. Resource Management
- Grid-based resource distribution
- Seasonal effects on resource gathering
- Tool durability system
- Supply and demand based market

4. Logging & Analytics
- Detailed action logging system
- Statistical data collection
- Plotly-based visualization of villager stats

### Key Features:
- Dynamic weather events affecting resource availability
- Tool crafting and trading system
- Seasonal farming mechanics
- Health and happiness tracking
- Skill progression affecting work efficiency
- Land ownership system for farmers

### Technical Implementation:
- Object-oriented design with clear class responsibilities
- Configurable parameters via CONFIG dictionary
- Modular action system for different roles
- Statistical tracking and visualization

## Development Notes

### 2024 Update - Medieval Village Simulation Enhancements

Major changes and additions:

1. **Monster System**
   - Added new Monster class for combat encounters
   - Implemented monster spawning system with configurable probabilities
   - Added different monster types (Wolf, Bear, Goblin)
   - Combat system with multi-round battles

2. **Food System Improvements**
   - Added food spoilage system with configurable timers
   - Implemented cooking mechanics (raw food → cooked food)
   - Cooked food lasts longer and provides better nutrition
   - Added spoilage tracking per item stack

3. **Social System**
   - Added basic marriage system
   - Villagers can now have relationship statuses (single, married, widowed)
   - Marriage probability checks during morning time
   - Partner tracking via IDs

4. **Configuration Updates**
   - Added new configuration parameters for monsters and combat
   - Added spoilage configuration for different food types
   - Added marriage probability settings
   - Added cooking conversion rates and probabilities

5. **Statistics & Logging**
   - Enhanced logging system to track social events
   - Added monster encounter logging
   - Added spoilage tracking in logs
   - Marriage event logging

6. **Code Structure**
   - Improved modularization of systems
   - Better separation of concerns between different mechanics
   - Enhanced error handling and edge cases
   - Added safeguards for health checks in social interactions

These changes significantly enhance the simulation's complexity and realism, adding new dynamics to the village life simulation 

## Updates since last git push

### Simulation.py Change Summary (Refactored on 2024-03-XX)
- **Marriage System Integration**:  
  - Introduced a new `_check_for_marriages` method in the `Simulation` class.
  - This method is now called during the Morning cycle so that villagers meeting the health, hunger, food, and wood thresholds (as set in the configuration) can get married. Marriage events are logged as part of the simulation's social dynamics.

- **Daily Summary Logging Enhancement**:  
  - Modified the simulation loop to invoke `log_daily_summary()` for each villager during the Night phase.
  - This addition provides more granular end-of-day statistics by recording hunger, rest, health, happiness, coins, and inventory details at the close of each simulated day.

- **Improved Action and Statistics Recording**:  
  - Adjusted the simulation loop within the `run()` method to record villager statistics immediately after each action.
  - This update ensures that the time-series data feeding the Plotly charts is more accurate and reflects the precise state of each villager throughout the simulation.

- **Refined Time Advancement and Resource Updates**:  
  - Reorganized the order of operations in the simulation loop: environmental resources are updated and events are processed at the end of each part-of-day cycle before advancing the time.
  - This results in a smoother simulation cycle and more consistent triggering of events.

*These changes collectively enhance the simulation realism, improve logging fidelity, and provide better support for social dynamics among villagers.* 