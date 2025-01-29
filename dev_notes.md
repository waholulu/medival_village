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