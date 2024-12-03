# Antbuster-Buster
A **Reinforcement Learning Model** designed to play the flash game **Antbuster** autonomously.

## Concept
This is my first attempt at designing a RL model, designed for my batchlor thesis. The physical implementation of game interaction was a clear oversight but this was more of a conceptual piece rather than a practical application. In the future, I intend to create a simulation based implementation of this concept. 

## Prerequisites
To get started, you'll need the following:
- **Windows Flash Player**
- A **modified SWF file** of the game Antbuster.

Not nessecary to run but I have also included my "Trained" model and its json log

## How It Works
1. **Game Setup**:  
   The program opens an instance of the Flash Player, loads the game, and moves the game window to the top-left corner of the screen (coordinates `0,0`).
   
2. **Action Implementation**:  
   The model physically implements actions by simulating your cursor's movement and clicks. This ensures the AI interacts with the game just as a human would.

3. **File Management**:  
   - A **model file** and a **JSON log file** will be automatically created if they don’t already exist.
   - Actions and data from each game played is stored in the json file, including score, gametime, and actions taken along with associated coordinates and upgrade choices
   - Make sure to set a save location for these files before running the program.  
   
4. **Training & Exploration**:  
   The AI uses reinforcement learning with an **epsilon-greedy algorithm** to balance exploration (trying new actions) and exploitation (choosing the best-known actions).  
   - Adjust the **epsilon** value in the trainer function to modify the explore rate. Learn more about the epsilon-greedy algorithm [here](https://www.geeksforgeeks.org/epsilon-greedy-algorithm-in-reinforcement-learning/).
   - Adjust **delay_between_games** to speed up gameplay as you wish
   - **Note:** Cheat Engines' speedhack works on the flashplayer to speed up gameplay

## Known Issues & Future Improvements
- **Scaling Limitations**:  
  - The current implementation assumes a **1920x1080 screen resolution**.  
  - All pixel-based locations and scaling are hardcoded for this resolution.  
  - Future updates will include either:  
    - **Dynamic scaling** to fit any screen size automatically.  
    - **User-configurable settings** for custom screen resolutions and scaling preferences.

-**Threading Issues**:
  -Ending the program prematurely will not gracefully exit the thread, will be fixed in the future
  
-**GUI Implementation**:
  -A configurable GUI to adjust settings will be added at some point this year
