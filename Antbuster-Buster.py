import subprocess
import os
import time
import pyautogui
import psutil
import pygetwindow as gw
import mss
import win32gui
import win32process
import win32con
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import easyocr
import keyboard
import threading
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import json
import random
import warnings

warnings.filterwarnings(
    "ignore",
    message=(
        "You are using `torch.load` with `weights_only=False`.*"
    ),
    category=FutureWarning,
)

class FlashProjectorInstance:

    instance_list = []
    def __init__(self, projector_path, swf_path):
        self.projector_path = projector_path
        self.swf_path = swf_path
        self.process = None
        self.flash_window = None
        self.game_PID = None
        self.hwnd = None

    def launch_flash_projector(self):
        if not os.path.exists(self.projector_path):
            print(f"Flash Projector not found at: {self.projector_path}")
            return
        
        try:
            self.process = subprocess.Popen(self.projector_path)
            print("Flash Projector launched successfully.")
            
            time.sleep(1)

            pyautogui.hotkey('ctrl', 'o') 
            time.sleep(0.5) 
            
            pyautogui.typewrite(self.swf_path)
            pyautogui.press('enter')

            self.game_PID = self.get_window_pid()

            if self.game_PID is not None:
                self.update_instance_dictionary(self.game_PID)
                print(f"Game PID is {self.game_PID}.")

            self.hwnd = self.get_hwnd_by_pid(self.game_PID)
            self.calculate_screen_location(self.game_PID)
            print("Game loaded successfully.")

        
        except Exception as e:
            print(f"Failed to launch Flash Projector: {e}")

    def get_window_pid(self):
        projector_name = "Windows-Flash-Projector.exe"
        print(f"Searching for PID of '{projector_name}'...")

            #iterate over all running processes
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            try:
                if proc.info['pid'] in self.instance_list:
                    continue
                if proc.info['name'] == projector_name:
                    print(f"Found {projector_name} with PID: {proc.info['pid']}")
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                #if the process has terminated or access is denied, skip it
                continue

        print(f"{projector_name} is not running.")
        return None
    
    def get_hwnd_by_pid(self, pid):
        hwnd_list = []
        
        def callback(hwnd, hwnd_list):
            #get the process ID for the current window handle
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            
            #if the PID matches, add the hwnd to the list
            if found_pid == pid:
                hwnd_list.append(hwnd)

        win32gui.EnumWindows(callback, hwnd_list)
        #enumerate all top-level windows and use the callback to find the hwnd
        win32gui.EnumWindows(callback, hwnd_list)
        if hwnd_list:
            hwnd = hwnd_list[0]
            print(f"Success: Found HWND {hwnd} for PID {pid}")
            return hwnd
        else:
            print(f"Failure: No HWND found for PID {pid}")
            return None
        
    def resize_window(self, width, height):
        if self.hwnd:
            #use SetWindowPos to resize the window
            win32gui.SetWindowPos(self.hwnd, None, 0, 0, width, height, win32con.SWP_NOMOVE | win32con.SWP_NOZORDER)
            print(f"Resized window to {width}x{height}.")
        else:
            print("Error: HWND is not set. Cannot resize window.")
        
    def move_window(self, x, y):
        if self.hwnd:
            #use SetWindowPos to move the window
            win32gui.SetWindowPos(self.hwnd, None, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
            print(f"Moved window to ({x}, {y}).")
        else:
            print("Error: HWND is not set. Cannot move window.")

    def get_screen_size(self):
        screen_width, screen_height = pyautogui.size()
        print(f"Screen size: {screen_width} x {screen_height}")
        return screen_width, screen_height

    def get_window_size(self):
        if self.hwnd:
            #get the window rectangle (left, top, right, bottom)
            rect = win32gui.GetWindowRect(self.hwnd)
            width = rect[2] - rect[0]  # right - left
            height = rect[3] - rect[1]  # bottom - top
            print(f"Current window size: {width} x {height}")
            return rect
        else:
            print("Error: HWND is not set. Cannot get window size.")
            return None

    def get_pid_index(self, pid):
        """Returns the index of the PID in the instance list, or -1 if not found."""
        try:
            index = self.instance_list.index(pid)
            return index
        except ValueError:
            return -1  #PID is not found
        
    def calculate_screen_location(self, pid):
        index = self.get_pid_index(pid)
        x = None
        y = None
        if index <= 2:
            y = 0
            x = (index) * 500
        else:
            y = 520
            x = (index - 3) * 500
        self.move_window(x, y)

    @classmethod
    def update_instance_dictionary(cls, pid):   
        #add the PID and reference to the current instance in the shared list
        cls.instance_list.append(pid)
        print(f"Updated instance list with PID: {pid}. Current list: {cls.instance_list}")

class TowerGrid:
    def __init__(self):
        self.number_of_towers = 0
        self.map_grid = [["V" for _ in range(25)] for _ in range(20)] # V for open space
        self.tower_locations = []
        self.defineInaccessable()
        self.base_tower_cost = [
            30, 45, 67, 100, 150, 225, 337, 505, 757, 1135, 
            1702, 2553, 3829, 5743, 8614, 12921, 19381, 29071, 
            43606, 65409, 98113, 147619, 220753, 331129, 496693, 
            745039, 1117558
        ]

    def defineInaccessable(self):
        self.defineX(0, y_list = [0,1,2,3,4,5])
        self.defineX(1, y_list = [0,1,2,3,4,5])
        self.defineX(2, y_list = [0,1,2,3,4,5])
        self.defineX(3, y_list = [0,1,2,3,4,5])
        self.defineX(4, y_list = [0,1,2,3,4])
        self.defineX(5, y_list = [0,1,2,3])

        self.defineX(16, y_list = [16, 17])
        self.defineX(17, y_list = [15, 16, 17, 18, 19])
        self.defineX(18, y_list = [15, 16, 17, 18, 19])
        self.defineX(19, y_list = [14, 15, 16, 17, 18, 19])
        self.defineX(20, y_list = [14, 15, 16, 17, 18, 19])
        self.defineX(21, y_list = [13, 14, 15, 16, 17, 18, 19])
        self.defineX(22, y_list = [13, 14, 15, 16, 17, 18, 19])
        self.defineX(23, y_list = [12, 13, 14, 15, 16, 17, 18, 19])
        self.defineX(24, y_list = [12, 13, 14, 15, 16, 17, 18, 19])

    def display_map_grid(self):
        x_v, y_v = [], []
        x_xp, y_xp = [], []
        
        for row in range(len(self.map_grid)):
            for col in range(len(self.map_grid[row])):
                if self.map_grid[row][col] == "V":
                    x_v.append(col)
                    y_v.append(row)
                elif self.map_grid[row][col] in ["X", "P"]:
                    x_xp.append(col)
                    y_xp.append(row)
        
        plt.plot(x_v, y_v, "bo", label="Accessible (V)")  # Blue for "V"
        plt.plot(x_xp, y_xp, "ro", label="Blocked (X/P)")  # Red for "X" and "P"
        
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Map Grid of Accessible and Blocked Locations")
        plt.legend()
        plt.grid(True)
        plt.show()

    def defineX(self, x, y_list):
        for item in y_list:
            self.map_grid[item][x] = "X"  #X for completely inaccessible

    def getValidTowerLocations(self): 
        valid_locations = []
        for row in range(len(self.map_grid)):
            for col in range(len(self.map_grid[row])):
                if self.map_grid[row][col] == "V":
                    valid_locations.append((row, col))
        return valid_locations

    def add_tower(self, x, y):
        tower = Tower()
        if self.map_grid[y][x] == "V":
            self.map_grid[y][x] = tower
            self.mark_tower_square(x, y, "V", "P")
            self.number_of_towers += 1
            self.tower_locations.append((x, y))
            #print(f"added at x:{x}, y:{y}")
            #self.display_map_grid()
            return "added"
        else:
            print("invalid location - grid")
            return "invalid"

    def upgrade_tower(self, x, y, num):
        if isinstance(self.map_grid[y][x], Tower):
            tower = self.map_grid[y][x]
            upgrade_status = tower.upgrade_tower(num)

            #if upgrade_status == "upgraded":
                #print("tower upgraded - grid")
            #elif upgrade_status == "max":
                #print("tower max level - grid")
            
        else:
            print("tower not found - grid")

    def downgrade_tower(self, x, y):
        if isinstance(self.map_grid[y][x], Tower):
            tower = self.map_grid[y][x]
            result = tower.downgrade_tower()
            return result
        else:
            return "invalid"

    #x, y, what the current value to replace is ("V"=new tower, "P"=delete tower), 
    #what to replace as ("P"=new tower, "V"=delete tower)
    def mark_tower_square(self, x, y, current, new): 
        for i in range(y - 1, y + 2):
            for j in range(x - 1, x + 2):
                if 0 <= i < len(self.map_grid) and 0 <= j < len(self.map_grid[0]) and (i, j) != (y, x):
                    if self.map_grid[i][j] == current:
                        self.map_grid[i][j] = new  

    def get_new_tower_cost(self):
        return self.base_tower_cost[self.number_of_towers]
    
    def get_tower_locations(self):
        return self.tower_locations

    def get_possible_upgrades(self, current_money):
        possible_upgrades = []  #less or equal than current money
        wait_upgrades = []      #too expensive

        for x, y in self.tower_locations:
            tower = self.map_grid[y][x]
            if isinstance(tower, Tower):
                upgrades, wait = tower.get_upgrade_info(current_money)

                #add upgrades if they exist
                if upgrades and upgrades[0] is not None:  #check for nonempty and not None
                    possible_upgrades.append(((x, y), upgrades))

                #add wait options if they exist
                if wait and wait[0] is not None:  #check for nonempty and not None
                    wait_upgrades.append(((x, y), wait))

        return possible_upgrades, wait_upgrades
    
    def grid_to_tensor(self):
        grid_tensor = torch.zeros((len(self.map_grid), len(self.map_grid[0])), dtype=torch.int)

        for y, row in enumerate(self.map_grid):
            for x, cell in enumerate(row):
                if cell == "V":
                    grid_tensor[y, x] = 0  #open space
                elif cell == "X" or cell == "P":
                    grid_tensor[y, x] = 1  #inaccessible space
                elif isinstance(cell, Tower):
                    grid_tensor[y, x] = cell.get_current_node() + 2  #offset by 2 for tower levels

        return grid_tensor.float().unsqueeze(0).unsqueeze(0)

class Tower:
    def __init__(self):
        self.current_node = 0
        self.tree = {
            0: [1, 2, 3],       #Base Tower

            1: [4, 5, 6],       #Heavy Cannon 1
            2: [7, 8, 9],       #Quick Cannon 1
            3: [10, 11, 12],    #Double Cannon 1

            4: [13, 14],    #Heavy Cannon 2
            5: [15, 16],    #Impact Cannon 1
            6: [17, 18],    #Double Heavy Cannon 1

            7: [19, 20],    #Quick Cannon 2
            8: [21, 22],    #Sniper Cannon 1
            9: [23, 24],    #Long Range Cannon 1

            10: [25, 26],   #Double Cannon 2
            11: [27, 28],   #Quick Cannon 1
            12: [29, 30],   #Triple Cannon 1

            13: [31],       #Heavy Cannon 3
            14: [32],       #Missile Launcher 1

            15: [33],       #Impact Cannon 2
            16: [34],       #Ice Cannon 1

            17: [35],       #Double Heavy Cannon 2
            18: [36],       #Sonic Pulse 1

            19: [37],       #Quick Cannon 3
            20: [38],       #Flame Thrower 1

            21: [39],       #Sniper Cannon 2
            22: [40],       #Laser Cannon 1

            23: [41],       #Long Range Cannon 2
            24: [42],       #Electric Cannon 1

            25: [43],       #Double Cannon 3
            26: [44],       #Boomerang 1

            27: [45],       #Double Quick Cannon 2
            28: [46],       #Machine Gun 1

            29: [47],       #Triple Cannon 2
            30: [48],       #Poison Spray 1
        }

        self.values = {         #number to select, cost to upgrade to, parent, level
            0: (0,0, None, 0),           #Base Tower

            1: (1, 60, 0, 1),         #Quick Cannon 1
            2: (2, 40, 0, 1),         #Double Cannon 1
            3: (3, 40, 0, 1),         #Double Cannon 1

            4: (1, 60, 1, 2),         #Heavy Cannon 2
            5: (2, 48, 1, 2),         #Impact Cannon 1
            6: (3, 50, 1, 2),         #Double Heavy Cannon 1

            7: (1, 80, 2, 2),         #Quick Cannon 2
            8: (2, 80, 2, 2),        #Sniper Cannon 1
            9: (3, 65, 2, 2),         #Long Range Cannon 1

            10: (1, 60, 3, 2),       #Double Cannon 2
            11: (2, 80, 3, 2),       #Quick Cannon 1
            12: (3, 92, 3, 2),       #Triple Cannon 1

            13: (1, 168, 4, 3),       #Heavy Cannon 3
            14: (2, 712, 4, 3),       #Missile Launcher 1

            15: (1, 170, 5, 3),       #Impact Cannon 2
            16: (2, 340, 5, 3),       #Ice Cannon 1

            17: (1, 264, 6, 3),      #Double Heavy Cannon 2
            18: (2, 528, 5, 3),       #Sonic Pulse 1

            19: (1, 312, 7, 3),      #Quick Cannon 3
            20: (2, 600, 7, 3),      #Flame Thrower 1

            21: (1, 312, 8, 3),      #Sniper Cannon 2
            22: (2, 420, 8, 3),       #Laser Cannon 1

            23: (1, 462, 9, 3),      #Long Range Cannon 2
            24: (2, 615, 9, 3),      #Electric Cannon 1

            25: (1, 380, 10, 3),      #Double Cannon 3
            26: (2, 563, 10, 3),       #Boomerang 1

            27: (1, 320, 11, 3),       #Double Quick Cannon 2
            28: (2, 528, 11, 3),     #Machine Gun 1

            29: (1, 462, 12, 3),    #Triple Cannon 2
            30: (2, 498, 12, 3),      #Poison Spray 1

            31: (1, 980, 13, 4),      #Heavy Cannon 4
            32: (1, 1274, 14, 4),
            33: (1, 1029, 15, 4),
            34: (1, 1256, 16, 4),
            35: (1, 1024, 17, 4),
            36: (1, 1188, 18, 4),
            37: (1, 832, 19, 4),
            38: (1, 1125, 20, 4),
            39: (1, 1020, 21, 4),
            40: (1, 1217, 22, 4),
            41: (1, 1134, 23, 4),
            42: (1, 1224, 24, 4),
            43: (1, 960, 25, 4),
            44: (1, 1116, 26, 4),
            45: (1, 1012, 27, 4),
            46: (1, 1253, 28, 4),
            47: (1, 1188, 29, 4),
            48: (1, 2000, 30, 4)
        }
        
    def upgrade_tower(self, num):
        status = None
        if self.get_current_level() == 4:
            #print("tower max level, cannot upgrade further")
            status = "max"
        else:
            for child in self.tree.get(self.current_node, []):  #go through child list
                if self.values[child][0] == num:                #find child with matching number
                    self.current_node = child                   #set node to child
                    status = "upgraded"

                    level = self.get_current_level()
                    node = self.current_node
                    #print(f"tower upgraded to node: {node} w level: {level}")
                    break
        return status

    def downgrade_tower(self):
        parent = self.values.get(self.current_node, (None, None, None))[2]
        if parent is not None:
            self.current_node = parent
            print(f"Tower downgraded to node {parent}")
        else:
            print("Tower deleted")

    def print_tower(self):
        level = self.get_current_level()
        print(f"Current Node: {level}")

    def get_current_level(self):
        return self.values[self.current_node][3]

    def get_current_node(self):
        return self.current_node

    def get_upgrade_info(self, current_money):
        upgrades_list = []
        wait_list = []

        #if max level, return empty lists
        if self.get_current_level() == 4:
            return [], []

        #possible upgrades -> upgrades_list, impossible -> wait_list
        for child in self.tree.get(self.current_node, []):
            upgrade_cost = self.values[child][1]
            select_number = self.values[child][0]

            if int(current_money) >= int(upgrade_cost):
                upgrades_list.append((select_number, upgrade_cost))
            else:
                wait_list.append((select_number, upgrade_cost))

        return upgrades_list, wait_list

class ImageProcessor:
    def __init__(self):
        self.reader = easyocr.Reader(['en'])

    #used for testing pixel locations
    def display_window(self, bbox):
        while True:
            if keyboard.is_pressed('space'):
                img = self.take_screenshot(bbox)
                plt.imshow(img)
                plt.axis('on')
                plt.show()

                keyboard.wait('space', suppress=True) 

    def take_screenshot(self, bbox):
        with mss.mss() as sct:
            screenshot = sct.grab(bbox)
            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            return img 

    def print_text_from_img(self, img):
        result = self.reader.readtext(np.array(img))
        if result:
            print("Detected text:", result[0][1])
        else:
            print("No text detected.")

    def detect_text_in_img(self, img):
        result = self.reader.readtext(np.array(img))
        if result:
            text_only = [item[1] for item in result]
            return text_only
        else:
            return None

    def detect_end_game(self, img, text):
        result = self.reader.readtext(np.array(img))
        if result:
            for item in result:         #check if result is "Total:", if so remove total and return the remaining
                detected_text = item[1]             #which should be the score
                if detected_text.startswith(text):
                    remaining_text = detected_text[len(text):].strip()
                    return remaining_text
        return None

    
class Actions:
    def __init__(self, FLASH_PROJECTOR_PATH, ANTBUSTER_SWF_PATH):
        self.grid = None

        self.projector_instance = FlashProjectorInstance(FLASH_PROJECTOR_PATH, ANTBUSTER_SWF_PATH)
        self.projector_instance.launch_flash_projector()

        # (left, top, right, bottom)
        self.window_bbox = self.projector_instance.get_window_size() #whole window
        self.map_bbox    = (0, 40, 516, 530)                    #map only
        self.money_bbox  = (436, 460, 500, 490)                 #money area
        self.game_over_bbox = (186, 320, 262, 345)
        self.end_score_bbox = (262, 320, 350, 345)

        self.total_end_game_bbox = (180, 320, 350, 345) #use instead of other end game stuff for now

        self.start_game_button = 350, 400
        self.to_menu_button = 320, 400

        self.tower_size = 20 
        self.tower_start = 15, 45

        self.processor = ImageProcessor()

    def click_menu_button(self, pixel_location):
        pyautogui.moveTo(pixel_location[0], pixel_location[1])
        time.sleep(.1)

        pyautogui.click()
        time.sleep(.1)

    def upgrade_tower(self, x, y, num):
        pixel_location = self.translate_tower_location(x, y)

        pyautogui.moveTo(pixel_location[0], pixel_location[1])
        time.sleep(.1)

        pyautogui.click()
        time.sleep(.1)

        pyautogui.press(str(num))
        time.sleep(.1)
        self.grid.upgrade_tower(x, y, num)
        #print("upgrade success - action")

    def place_new_tower(self, x, y):
        pixel_location = self.translate_tower_location(x, y)

        pyautogui.press('0')
        time.sleep(.1)

        pyautogui.moveTo(pixel_location[0], pixel_location[1])
        time.sleep(.1)

        pyautogui.click()
        time.sleep(.1)
        self.grid.add_tower(x, y)
        #print("new success - action")

    def get_text_from_img(self, processor, bbox):
        img = processor.take_screenshot(bbox)
        return processor.detect_text_in_img(img)

    #awful hardcoding but screw it
    def detect_game_over(self):
        img = self.processor.take_screenshot(self.total_end_game_bbox)
        return self.processor.detect_end_game(img, "Total:")

    def translate_tower_location(self, x, y):
        return (x * self.tower_size) + self.tower_start[0], (y * self.tower_size) + self.tower_start[1]

    def test_place_tower(self):
        while (True):
            if keyboard.is_pressed('space'):
                x=10
                for i in range(0, 25, 2):
                    self.place_new_tower(x, i)
                    time.sleep(.5)

    def get_valid_moves(self, money):
        possible_upgrades = self.grid.get_possible_upgrades()   #list of all possible upgrades
        capable_upgrades = []                                   #list of all upgrades capable of doing (within price range)
        incapable_upgrades = []                                 #list of all upgrades that are too expensive
        new_tower_cost = self.grid.get_new_tower_cost()

        for tower in possible_upgrades:
            (x, y), upgrades = tower

            for upgrade in upgrades:
                select_number, upgrade_cost = upgrade

                if money >= upgrade_cost:
                    capable_upgrades.append(((x,y), select_number))
                    #print(f"{x}, {y}, {upgrade_cost}")
                else:
                    incapable_upgrades.append(((x,y), select_number, upgrade_cost))

        return new_tower_cost, capable_upgrades, incapable_upgrades
    
    def set_new_tower_grid(self, grid):
        self.grid = grid

class GameInstance:
    def __init__(self, actions):
        self.actions = actions
        self.money = 300
        self.score = 0
        self.game_running = True

    def start_threads(self):
        #self.money_thread = threading.Thread(target=self.run_set_money)
        self.game_over_thread = threading.Thread(target=self.run_check_game_over)
    
        #self.money_thread.start()
        self.game_over_thread.start()

    def set_money(self):
        money = self.actions.get_text_from_img(self.actions.processor, self.actions.money_bbox)
        if money != None:
            self.money = int(money[0])
        else:
            self.money = 0  #sometimes ocr detects low numbers as none, just set to 0 for now

    def check_game_over(self):
        result = self.actions.detect_game_over()

        if result == None:
            return
        else:
            self.score = result
            self.game_running = False
            self.actions.click_menu_button(self.actions.to_menu_button)

    def run_set_money(self):
        while self.game_running:
            self.set_money()
            time.sleep(.25)

    def run_check_game_over(self):
        while self.game_running:
            self.check_game_over()
            time.sleep(.5)

    def get_money(self):
        return self.money
    
    def get_score(self):
        return self.score

class AntbusterEnv:
    def __init__(self, FLASH_PROJECTOR_PATH, ANTBUSTER_SWF_PATH, tower_decision_net):
        self.actions = Actions(FLASH_PROJECTOR_PATH, ANTBUSTER_SWF_PATH)
        self.grid = None
        self.game_instance = None
        self.tower_decision_net = tower_decision_net
        self.decision_delay = 0
        self.tower_decision_net.train()      #testing set to eval

    #resets grid and game instance for each new game, and clicks menu start button
    def start_new_game(self):
        self.grid = TowerGrid()
        self.game_instance = GameInstance(self.actions)

        self.actions.set_new_tower_grid(self.grid)

        self.actions.click_menu_button(self.actions.start_game_button)  
        time.sleep(2)
        self.game_instance.start_threads()

    def play_game(self, decision_delay, epsilon, log_decisions=False, action_sampling=False):
        self.start_new_game()
        action_log = []

        self.epsilon = epsilon
        self.decision_delay = decision_delay

        #get q values, interprate, execute chosen and log q
        while self.game_instance.game_running:
            valid_placement_probs, valid_upgrade_probs, wait_placement_probs, wait_upgrade_probs = self.get_choices()
            chosen_action = self.get_sample_choice(valid_placement_probs, valid_upgrade_probs, wait_placement_probs, wait_upgrade_probs, epsilon)

            action_log.append(chosen_action)
            self.execute_choice(chosen_action)

            time.sleep(self.decision_delay)
        score = self.game_instance.get_score()
        return score, action_log

    def get_sample_choice(self, valid_placement_probs, valid_upgrade_probs, wait_placement_probs, wait_upgrade_probs, epsilon):
        action_types = []
        if valid_placement_probs:
            action_types.append(valid_placement_probs)
        if valid_upgrade_probs:
            action_types.append(valid_upgrade_probs)
        if wait_placement_probs:
            action_types.append(wait_placement_probs)
        if wait_upgrade_probs:
            action_types.append(wait_upgrade_probs)

        if random.random() < epsilon:
            #exploration (chose random action)
            sampled_action_type = random.choice(action_types)
            chosen_action = random.choice(sampled_action_type)
        else:
            #exploitation (chose best action)
            best_choices = [
                action for action_list in action_types for action in action_list
            ]

            chosen_action = max(best_choices, key=lambda x: x[0])  

        return chosen_action

    def execute_choice(self, choice):
        if choice[1] == "place":
            #print(f"place {choice[2][1]}, {choice[2][0]}")
            self.actions.place_new_tower(choice[2][0], choice[2][1])
        elif choice[1] == "upgrade":
            #print(f"upgrade {choice[2][1]}, {choice[2][0]}")
            self.actions.upgrade_tower(choice[2][0], choice[2][1], choice[3])
        elif choice[1] == "wupgrade":
            self.wait_for_choice(choice[4])
            if self.game_instance.game_running:
                self.actions.upgrade_tower(choice[2][0], choice[2][1], choice[3])
        elif choice[1] == "wplace":
            self.wait_for_choice(choice[3])
            if self.game_instance.game_running:
                self.actions.place_new_tower(choice[2][0], choice[2][1])

    #wait until money is greater than cost of chosen action
    def wait_for_choice(self, cost):
        while self.game_instance.get_money() < cost and self.game_instance.game_running:
            self.game_instance.set_money()
            time.sleep(self.decision_delay)
        
    def get_choices(self):
        self.game_instance.set_money()
        current_money = self.game_instance.get_money()

        valid_locations = self.grid.getValidTowerLocations()
        tower_locations, invalid_locations = self.grid.get_possible_upgrades(current_money)
        new_tower_cost = self.grid.get_new_tower_cost()

        tensor = self.grid.grid_to_tensor()

        self.tower_decision_net(tensor, new_tower_cost, current_money, tower_locations, invalid_locations)

        valid_placement_probs, valid_upgrade_probs, wait_placement_probs, wait_upgrade_probs = self.tower_decision_net.make_decision_lists(
            tensor, valid_locations, tower_locations, invalid_locations, new_tower_cost, current_money)

        return valid_placement_probs, valid_upgrade_probs, wait_placement_probs, wait_upgrade_probs

    def plot(self, valid_placement_probs):
        x_coords = [coord[2][1] for coord in valid_placement_probs]  #x coordinates from (y, x)
        y_coords = [coord[2][0] for coord in valid_placement_probs]  #y coordinates from (y, x)
        probabilities = [coord[0] for coord in valid_placement_probs]  #placement probabilities

        plt.figure(figsize=(8, 6))
        scatter = plt.scatter(x_coords, y_coords, c=probabilities, cmap="viridis", marker="o", edgecolor="k")
        plt.colorbar(scatter, label="Placement Probability")
        plt.xlabel("X Coordinate")
        plt.ylabel("Y Coordinate")
        plt.title("Valid Placement Probabilities")
        plt.gca().invert_yaxis() 

        plt.xticks(range(25))
        plt.yticks(range(20)) 
        plt.grid(True, which='both')
        plt.show()
        
class TowerDecisionNet(nn.Module):
    def __init__(self):
        super(TowerDecisionNet, self).__init__()
        #convolutional layers to extract spatial features from the grid
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)     #1 (grid) -> 16
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)    #16 -> 32
        self.conv3 = nn.Conv2d(32, 64, kernel_size=3, padding=1)    #32 -> 64

        #fully connected layers for current_money and new_tower_cost
        self.money_fc = nn.Linear(1, 32)  #1 -> 32
        self.cost_fc = nn.Linear(1, 32)   #1 -> 32

        #final layer for placing new towers
        self.place_conv = nn.Conv2d(128, 1, kernel_size=1)  #outputs 1 channel for place probs

        #fully connected layers for upgrades and waiting
        self.upgrade_fc = nn.Linear(64, 3)  #outputs 3 channels for valid upgrades
        self.wait_fc = nn.Linear(64, 3)     #outputs 3 channels for wait upgrades

    def forward(self, x, new_tower_cost, current_money, possible_tower_upgrades, too_expensive_upgrades):
        base = x
        #convert cost and money to tensors, should maybe change this to do before theyre passed
        if isinstance(current_money, int):
            current_money = torch.tensor([current_money], dtype=torch.float32, device=x.device)
        if isinstance(new_tower_cost, int):
            new_tower_cost = torch.tensor([new_tower_cost], dtype=torch.float32, device=x.device)
        
        #process grid features
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        grid_features = F.relu(self.conv3(x))  #[batch, 64, height, width]

        #process current_money and reshape
        money_features = F.relu(self.money_fc(current_money.view(-1, 1)))  #[batch, 32]
        money_features = money_features.view(-1, 32, 1, 1)  #reshape for broadcasting

        #process new_tower_cost and reshape
        cost_features = F.relu(self.cost_fc(new_tower_cost.view(-1, 1)))  #[batch, 32]
        cost_features = cost_features.view(-1, 32, 1, 1)  #reshape for broadcasting

        #concat grid, money, and cost features
        combined_features = torch.cat(
            (
                grid_features,
                money_features.expand(-1, -1, grid_features.size(2), grid_features.size(3)),
                cost_features.expand(-1, -1, grid_features.size(2), grid_features.size(3))
            ), dim=1
        )

        #generate probabilities for placing new towers
        place_map = torch.sigmoid(self.place_conv(combined_features)).squeeze(1)  #[batch, height, width]

        #generate probabilities for upgrading towers
        tower_upgrade_map = {}
        if possible_tower_upgrades:
            for (col, row), upgrade_info in possible_tower_upgrades:
                if base[0, 0, row, col] >= 2:  #check for tower
                    tower_features = grid_features[:, :, row, col]  #[batch, 64]
                    upgrade_probs = F.softmax(self.upgrade_fc(tower_features), dim=-1)  #[batch, 3]
                    tower_upgrade_map[(row, col)] = upgrade_probs.squeeze(0).tolist()

        #generate probabilities for waiting to upgrade towers
        tower_wait_map = {}
        if too_expensive_upgrades:
            for (col, row), upgrade_info in too_expensive_upgrades:
                if base[0, 0, row, col] >= 2:  #check for a tower
                    tower_features = grid_features[:, :, row, col]  #[batch, 64]
                    wait_probs = F.softmax(self.wait_fc(tower_features), dim=-1)  #[batch, 3]
                    tower_wait_map[(row, col)] = wait_probs.squeeze(0).tolist()

        return place_map, tower_upgrade_map, tower_wait_map

    def make_decision_lists(self, grid_tensor, valid_placement_locations, possible_tower_upgrades, too_expensive_upgrades, new_tower_cost, current_money):
        place_map, tower_upgrade_map, tower_wait_map = self.forward(
            grid_tensor, new_tower_cost, current_money, possible_tower_upgrades, too_expensive_upgrades
        )

        valid_placement_probs = []
        valid_upgrade_probs = []
        wait_placement_probs = []
        wait_upgrade_probs = []

        #collect placement probabilities, if it cant afford new tower place the probs in wait
        if current_money >= new_tower_cost:
            for (y, x) in valid_placement_locations:
                placement_prob = place_map[0, y, x].item()
                valid_placement_probs.append((placement_prob, "place", (x, y)))
        else:
            for (y, x) in valid_placement_locations:
                placement_prob = place_map[0, y, x].item()
                wait_placement_probs.append((placement_prob, "wplace", (x, y), new_tower_cost))

        #collect valid upgrade probabilities
        for (x, y), upgrade_info in possible_tower_upgrades:
            if (y, x) in tower_upgrade_map:
                specific_probs = tower_upgrade_map[(y, x)]
                
                for id, (upgrade_number, upgrade_cost) in enumerate(upgrade_info):
                    if id < len(specific_probs):
                        specific_prob = specific_probs[id]
                        valid_upgrade_probs.append((specific_prob, "upgrade", (x, y), upgrade_number, upgrade_cost))

        #collect too expensive probabilities for wait
        for (x, y), upgrade_info in too_expensive_upgrades:
            if (y, x) in tower_wait_map:
                specific_probs = tower_wait_map[(y, x)]
                
                for id, (upgrade_number, upgrade_cost) in enumerate(upgrade_info):
                    if id < len(specific_probs):
                        specific_prob = specific_probs[id]
                        wait_upgrade_probs.append((specific_prob, "wupgrade", (x, y), upgrade_number, upgrade_cost))

        return valid_placement_probs, valid_upgrade_probs, wait_placement_probs, wait_upgrade_probs

class AntBusterTrainer:
    def __init__(self, env, tower_decision_net, log_file, model_save_location, delay_between_actions, learning_rate=1e-4, gamma=0.99, epsilon=1.0, epsilon_decay=0.995, epsilon_min=0.1):
        self.tower_decision_net = tower_decision_net
        self.env = env
        self.gamma = gamma
        self.optimizer = optim.Adam(self.env.tower_decision_net.parameters(), lr=learning_rate)
        self.log_file = log_file
        self.model_save_location = model_save_location
        self.delay = delay_between_actions

        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        if not os.path.exists(log_file):
            with open(log_file, 'w') as file:
                json.dump({"games": []}, file)
      
    def train(self, num_games):
        game_attempts = 0

        #load model
        try:
            trainer.load_model(self.model_save_location)
        except FileNotFoundError:
            print(f"Model file not found at {self.model_save_location}. Starting with a fresh model.")

        while game_attempts < num_games:
            

            time.sleep(1)   #delay between games to prevent issues with loading


            start_time = time.time()    #log game time

            score, action_log = self.env.play_game(self.delay, self.epsilon, True)  #play one game and get score & action

            end_time = time.time()
            game_time = end_time - start_time

            q_values = [entry[0] for entry in action_log]  

            try:
                score = float(score)  #if value fails to convert to float (bad int), skip and play another
            except (ValueError, TypeError):
                print(f"Invalid score encountered: {score} on attempt {game_attempts + 1}. Disregarding and trying again.")
                continue
            
            reward = self.compute_discounted_rewards(score, len(q_values))  #calculate score per action

            state_action_values = torch.tensor(q_values, requires_grad=True)    
            loss = F.mse_loss(state_action_values, reward)          #calculate loss


            self.optimizer.zero_grad()
            loss.backward() 
            self.optimizer.step()

            game_attempts += 1

            
            self.log_game_metrics(score, loss.item(), game_time, self.epsilon, action_log)
            print(f"Game {game_attempts}/{num_games}, Score: {score}, Loss: {loss.item()}, Exploration Rate: {self.epsilon}")
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
            self.save_model(self.model_save_location)

    def compute_discounted_rewards(self, final_score, num_steps):
        rewards = [0] * num_steps
        cumulative_reward = float(final_score)
        for t in reversed(range(num_steps)):
            rewards[t] = cumulative_reward
            cumulative_reward *= self.gamma
        return torch.tensor(rewards, dtype=torch.float32)

    def log_game_metrics(self, score, loss, game_time, epsilon, action_log):
        place_data = []
        upgrade_data = []
        actions = []

        for entry in action_log:
            if entry[1] == "place" or entry[1] == "wplace":
                x, y = entry[2][0], entry[2][1]
                place_data.append({"x": x, "y": y})
            elif entry[1] == "upgrade" or entry[1] == "wupgrade":
                x, y = entry[2][0], entry[2][1]
                num_selected = entry[3]
                upgrade_data.append({"x": x, "y": y, "upgrade num": num_selected})
                
            actions.append(entry[1])

        try:
            with open(self.log_file, 'r') as file:
                log_data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            log_data = {"games": []}

        #determine the next game number, should be last + 1
        if log_data["games"]:
            last_game_num = log_data["games"][-1]["game"]
            game_num = last_game_num + 1
        else:
            game_num = 1

        game_data = {
            "game" : game_num,
            "score" : score,
            "loss" : loss,
            "game time" : game_time,
            "explore rate" : epsilon,
            "actions" : actions,
            "tower locations" : place_data,
            "upgrades" : upgrade_data
        }

        with open(self.log_file, 'r') as file:
            log_data = json.load(file)

        log_data["games"].append(game_data)

        with open(self.log_file, 'w') as file:
            json.dump(log_data, file, indent=4)


    def save_model(self, path):
        torch.save(self.env.tower_decision_net.state_dict(), path)

    def load_model(self, path):
        self.env.tower_decision_net.load_state_dict(torch.load(path))

if __name__ == "__main__":
    FLASH_PROJECTOR_PATH = r""
    ANTBUSTER_SWF_PATH = r""
    MODEL_SAVE_LOCATION = r""
    JSON_SAVE_LOCATION = r""
    
    tower_decision_net = TowerDecisionNet()

    env = AntbusterEnv(FLASH_PROJECTOR_PATH, ANTBUSTER_SWF_PATH, tower_decision_net)

    trainer = AntBusterTrainer(env, tower_decision_net, JSON_SAVE_LOCATION, MODEL_SAVE_LOCATION, delay_between_actions=.5, epsilon=0.5)
    time.sleep(8)

    trainer.train(10)
