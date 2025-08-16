#!/usr/bin/python3
# ^^ note the python directive on the first line
# COMP3411/9814 agent initiation file 
# requires the host to be running before the agent
# typical initiation would be (file in working directory, port = 31415)
#        python3 agent.py -p 31415
# created by Leo Hoare
# with slight modifications by Alan Blair

# I created a very basic program for the agent to complete the levels of the raft game. I mainly used Breadth-First Search, as I didn't have much time'
# 'the assignment (I'm legit submitting late ☠️). for find_path_to() I have used a slight configuration of A* search but it is mainly still BFS. 
# It marks the location of special objects and landmarks (e.g. starting_pos) and then generates a path to that goal. I have converted paths into
# instructions for the agent to follow. I used a dictionary to efficiently manage the agent's inventory so items can be incremented and decremented'
# 'correctly. For the BFS algorithm I used queues and lists to store actions and paths. I also utilised a dictionary for the global_map to store the states'
# 'of the levels. Sets were used to store which walls were blasted to make sure the same wall is not blasted again (although is other logic preventing it).'
# ''
# 'I have utilised many helper functions to ensure readability and modularity. Another design decision I implemented was to store the agent's starting_pos
# as (0, 0) so the agent can always return to spawn after collecting treasure efficiently. If the agent cannot think of any moves it spins around in a
# circle by inputting 'L' repeatedy. The treasure is only prioritised once the map is fully explored to find the best possible path. If the treasure is
# found before exploration is complete the agent returns to spawn. If I had more time I would have effectively implemented A* and finished the rest of the
# test cases.

import sys
import socket
from collections import deque
import time

# declaring visible grid to agent
view = [['' for _ in range(5)] for _ in range(5)]

# states
global_map = {}  # key: (x, y), value: tile char ('.', '^', 'T', 'a', etc.)
starting_pos = (0, 0)
curr_pos = (0, 0)  # starting position
current_dir = '^'     # one of ['^', '>', 'v', '<']
inventory = {}
on_raft = False
treasure_collected = False
treasure_found = False
treasure_pos = None

directions = ['^', '>', 'v', '<']
dir_map = {
    '^': (0, -1),
    '>': (1, 0),
    'v': (0, 1),
    '<': (-1, 0)
}

PASSABLE_TILES = [' ', 'a', 'k', 'd', '$']

# map inputs and directions
def turn(direction, turn_cmd):
    idx = directions.index(direction)
    if turn_cmd == 'L':
        return directions[(idx - 1) % 4]
    elif turn_cmd == 'R':
        return directions[(idx + 1) % 4]
    return direction

def move_forward(pos, direction):
    dx, dy = dir_map[direction]
    return (pos[0] + dx, pos[1] + dy)

def get_front_tile():
    dx, dy = dir_map[current_dir]
    front_pos = (curr_pos[0] + dx, curr_pos[1] + dy)
    return global_map.get(front_pos, '?'), front_pos

# ensures the agent can move forward safely
def attempt_move_forward():
    global curr_pos, on_raft, inventory
    tile, front_pos = get_front_tile()

    if tile == '*':
        print("Wall ahead! Either change direction or throw a bomb!")
        return

    if tile == '~':
        if inventory.get('raft', 0) > 0:
            print("Using a raft to move onto water.")
            curr_pos = front_pos
            on_raft = True
        else:
            print("Water ahead, but you have no raft! You'll drown!")
            return

    else:  # Normal land or other passable tile
        curr_pos = front_pos
        if on_raft and tile != '~':
            print("Stepped back onto land. Raft is now gone.")
            on_raft = False
            inventory['raft'] -= 1
            if inventory['raft'] == 0:
                del inventory['raft']

# Once key is obtained agent unlocks door
def attempt_unlock_door():
    global inventory
    tile, front_pos = get_front_tile()
    if tile == '-':
        if inventory.get('k', 0) > 0:
            print("Door unlocked! 🔓")
            inventory['k'] -= 1
            if inventory['k'] == 0:
                del inventory['k']
            global_map[front_pos] = ' '  
        else:
            print("You need a key (k) to unlock this door.")
    else:
        print("No door in front to unlock.")

def attempt_chop_tree():
    global inventory
    tile, front_pos = get_front_tile()
    if tile == 'T':
        if inventory.get('a', 0) > 0:
            print("Tree chopped down! You now have a raft.")
            inventory['raft'] = inventory.get('raft', 0) + 1
            global_map[front_pos] = ' '  
        else:
            print("You need an axe (a) to chop down this tree!")
    else:
        print("No tree in front to chop.")

# scans which wall should be blown up
# makes sure if d = 1, only wall with one layer (no obstacles behind) is blown up
# makes sure there is a tool on the other side of the wall, or a Tree to make a raft
blasted_walls = set()
def should_use_dynamite_smart():
    global inventory, blasted_walls

    if inventory.get('d', 0) == 0:
        return False

    dx, dy = dir_map[current_dir]
    wall_pos = (curr_pos[0] + dx, curr_pos[1] + dy)
    if wall_pos in blasted_walls:
        return False

    front_tile = global_map.get(wall_pos, '?')
    if front_tile != '*':
        return False

    scan_offsets = [(-1, -1), (-1, 0), (-1, 1),
                    (0, -1),  (0, 0),  (0, 1),
                    (1, -1),  (1, 0),  (1, 1)]
    
    valuable_items = []
    for ox, oy in scan_offsets:
        target_x = wall_pos[0] + ox
        target_y = wall_pos[1] + oy
        tile = global_map.get((target_x, target_y), '?')
        if tile in ['a', 'k', 'd', '$']:  
            if (ox, oy) == (0, 0) and tile == 'T':
                continue
            valuable_items.append((tile, (target_x, target_y)))

    if valuable_items:
        print(f"Blasting wall at {wall_pos} — Valuable item(s) behind: {valuable_items}")
        blasted_walls.add(wall_pos)
        return True

    return False

def attempt_blast():
    global inventory
    if inventory.get('d', 0) > 0:
        inventory['d'] -= 1
        print("BOOM!")
        if inventory['d'] == 0:
            del inventory['d']
    else:
        print("No dynamite (d) to use!")

# As agent explores the global map, it updates via view
def update_global_map():
    global treasure_found, treasure_pos
    for i in range(5):
        for j in range(5):
            dx, dy = j - 2, i - 2
            if current_dir == '^':
                x, y = curr_pos[0] + dx, curr_pos[1] + dy
            elif current_dir == 'v':
                x, y = curr_pos[0] - dx, curr_pos[1] - dy
            elif current_dir == '<':
                x, y = curr_pos[0] + dy, curr_pos[1] - dx
            elif current_dir == '>':
                x, y = curr_pos[0] - dy, curr_pos[1] + dx

            tile = view[i][j]
            global_map[(x, y)] = tile

            if tile == '$' and not treasure_found:
                treasure_found = True
                treasure_pos = (x, y)
                print(f"Treasure spotted at {treasure_pos}!")

# Checks for item pickip
def check_inventory_pickup():
    global inventory, treasure_collected
    item = global_map.get(curr_pos)

    if item in ['a', 'k', 'd', '$']:
        if item == '$':
            treasure_collected = True
            print(f'Treasure: {treasure_collected}')
        inventory[item] = inventory.get(item, 0) + 1
        print(f"Picked up: {item}")
        global_map[curr_pos] = ' '

# checks all cells are explored before finding $
def all_passable_explored():
    for (x, y), tile in global_map.items():
        if tile in PASSABLE_TILES:
            for dx, dy in dir_map.values():
                if global_map.get((x + dx, y + dy), '?') == '?':
                    return False
    return True

# BFS A* hybrid for goal
def find_path_to(destination_pos):
    visited = set()
    queue = deque([(curr_pos, [])])  

    while queue:
        pos, path = queue.popleft()
        if pos in visited:
            continue
        visited.add(pos)

        if pos == destination_pos:
            return path + [pos]  

        for dx, dy in dir_map.values():
            nx, ny = pos[0] + dx, pos[1] + dy
            tile = global_map.get((nx, ny), '?')
            if tile in PASSABLE_TILES or tile == '$':
                queue.append(((nx, ny), path + [pos]))

    return None

def detect_visible_tools():
    visible_tools = []
    for (x, y), tile in global_map.items():
        if tile in ['a', 'k', 'd', '$'] and is_tile_reachable((x, y)):
            visible_tools.append((tile, x, y))
    return visible_tools

def is_tile_reachable(pos):
    tile = global_map.get(pos, '?')
    
    if tile in [' ', '.', '^', 'a', 'k', 'd', '$']:
        return True
    elif tile == '*':
        return False  
    elif tile == 'T':
        return 'a' in inventory 
    elif tile == '-':
        return 'k' in inventory  
    elif tile == '~':
        return 'raft' in inventory  
    else:
        return False  

# checks if path is viable
def is_tile_reachable_bfs(start_pos, goal_pos, allowed_tiles=PASSABLE_TILES):
    visited = set()
    queue = deque([start_pos])

    while queue:
        x, y = queue.popleft()
        if (x, y) == goal_pos:
            return True

        if (x, y) in visited:
            continue
        visited.add((x, y))

        
        for dx, dy in dir_map.values():
            nx, ny = x + dx, y + dy
            tile = global_map.get((nx, ny), '?')
            if tile in allowed_tiles and (nx, ny) not in visited:
                queue.append((nx, ny))

    return False
    
def detect_visible_tools():
    reachable = []
    blocked = []

    for i in range(5):
        for j in range(5):
            tile = view[i][j]
            if tile in ['a', 'k', 'd', '$']:
                dx, dy = j - 2, i - 2

                if current_dir == '^':
                    x, y = curr_pos[0] + dx, curr_pos[1] + dy
                elif current_dir == 'v':
                    x, y = curr_pos[0] - dx, curr_pos[1] - dy
                elif current_dir == '<':
                    x, y = curr_pos[0] + dy, curr_pos[1] - dx
                elif current_dir == '>':
                    x, y = curr_pos[0] - dy, curr_pos[1] + dx

                pos = (x, y)
                reachable_flag = is_tile_reachable_bfs(curr_pos, pos)
                print(f"Checking tool '{tile}' at {pos} — Reachable: {reachable_flag}")
                if reachable_flag:
                    reachable.append((tile, pos))
                else:
                    blocked.append((tile, pos))

    return reachable, blocked

# BFS path to tool in view and global map
def find_closest_tool_path():

    targets = [pos for (tile, pos) in detect_visible_tools()[0]]  
    if not targets:
        return None

    visited = set()
    queue = deque([(curr_pos, [])])  

    while queue:
        pos, path = queue.popleft()
        if pos in visited:
            continue
        visited.add(pos)

        if pos in targets:
            return path + [pos]  

        for dx, dy in dir_map.values():
            nx, ny = pos[0] + dx, pos[1] + dy
            if (nx, ny) not in visited:
                tile = global_map.get((nx, ny), '?')
                if tile in PASSABLE_TILES or tile in ['a', 'k', 'd', '$']:
                    queue.append(((nx, ny), path + [pos]))

    return None

def direction_to(from_pos, to_pos):
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    for dir_symbol, (ddx, ddy) in dir_map.items():
        if (dx, dy) == (ddx, ddy):
            return dir_symbol
    return None

# Generates moves for path
def generate_move_sequence(path, current_pos, current_dir):
    moves = []
    dir_now = current_dir
    pos = current_pos

    for next_pos in path[1:]:  # skip current_pos
        required_dir = direction_to(pos, next_pos)
        while dir_now != required_dir:
            
            idx_now = directions.index(dir_now)
            idx_req = directions.index(required_dir)
            if (idx_now - idx_req) % 4 == 1:
                moves.append('L')
                dir_now = turn(dir_now, 'L')
            else:
                moves.append('R')
                dir_now = turn(dir_now, 'R')
        moves.append('F')
        pos = next_pos
    return moves

# Exploration BFS, no goal just look around for a goal
def find_exploration_path():
    visited = set()
    queue = deque([(curr_pos, [])])

    while queue:
        pos, path = queue.popleft()
        if pos in visited:
            continue
        visited.add(pos)

        
        for dx, dy in dir_map.values():
            nx, ny = pos[0] + dx, pos[1] + dy
            if global_map.get((nx, ny), '?') == '?':
                return path + [pos]  

        for dx, dy in dir_map.values():
            nx, ny = pos[0] + dx, pos[1] + dy
            tile = global_map.get((nx, ny), '?')
            if tile in PASSABLE_TILES and (nx, ny) not in visited:
                queue.append(((nx, ny), path + [pos]))

    return None  

# function to take get action from AI or user
def get_action(view):
    global action_queue, current_dir
    
    direction = view[2][2]
    delta = {'^': (-1, 0), 'v': (1, 0), '<': (0, -1), '>': (0, 1)}
    dx, dy = delta.get(direction, (0, 0))
    front_tile = view[2 + dx][2 + dy]
    action_queue = deque()

    reachable_tools, blocked_tools = detect_visible_tools()

    if treasure_collected:
        print("Treasure collected. Heading back to start!")
        path_home = find_path_to(starting_pos)
        if path_home:
            moves = generate_move_sequence(path_home, curr_pos, current_dir)
            print(f"Returning path: {path_home}, moves: {moves}")
            action_queue.extend(moves)
            return action_queue.popleft()
        else:
            print("❗ Can't find path to starting point!")
            return 'L'

    if front_tile == '-' and inventory.get('k', 0) > 0:
        return 'U'
    
    if should_use_dynamite_smart():
        return 'B'

    if front_tile == 'T':
        if inventory.get('a', 0) > 0:
            return 'C'
        else:
            print("Tree ahead! You need an axe (a) to chop it down using C.")
    
    if treasure_found and all_passable_explored():
        path = find_path_to(treasure_pos)
        if path:
            print(f"Heading to treasure at {treasure_pos}")
            moves = generate_move_sequence(path, curr_pos, current_dir)
            action_queue.extend(moves)
            return action_queue.popleft()
    
    if action_queue:
        return action_queue.popleft()
    
    path = find_closest_tool_path()
    if path:
        print(f"Path to tool: {path}")
        moves = generate_move_sequence(path, curr_pos, current_dir)
        print(f"Generated move sequence: {moves}")
        action_queue.extend(moves)
        return action_queue.popleft()
    
    explore_path = find_exploration_path()
    if explore_path:
        print(f"Exploring towards: {explore_path}")
        moves = generate_move_sequence(explore_path, curr_pos, current_dir)
        action_queue.extend(moves)
        return action_queue.popleft()

    dx, dy = dir_map[current_dir]
    front_pos = (curr_pos[0] + dx, curr_pos[1] + dy)
    beyond_pos = (curr_pos[0] + 2*dx, curr_pos[1] + 2*dy)
    front_tile_map = global_map.get(front_pos, '?')
    beyond_tile = global_map.get(beyond_pos, '?')

    if front_tile_map in PASSABLE_TILES and beyond_tile == '?':
        print("Peeking into unknown by moving forward.")
        return 'F'
    
    if front_tile_map in PASSABLE_TILES:
        print("Nothing better to do, moving forward.")
        return 'F'
    
    if reachable_tools:
        print("Reachable tools in view:")
        for tool, pos in reachable_tools:
            print(f" - {tool} at {pos}")
    if blocked_tools:
        print("Blocked tools in view (obstacles in way):")
        for tool, pos in blocked_tools:
            print(f" - {tool} at {pos}")

    # obstacle and treasure handling
    elif front_tile == '-':
        print("Door ahead! You need a key (k) to unlock it using U.")
    elif front_tile == '*':
        print("Wall ahead! Either change direction or throw a bomb!")
    elif front_tile == '~':
        if on_raft:
            print('Travelling on raft!')
        elif inventory.get('raft', 0) > 0:
            return 'F'
        else:
            print("Water ahead! You need a raft to move onto it safely.")
    elif front_tile == '$':
        print("Treasure is right in front of you!")
    elif front_tile == '.':
        print("Edge of the map ahead! Moving forward will cause death.")
    else:
        print(f"Clear path ahead: '{front_tile}'")
    
    # input loop to take input from user (only returns if this is valid)
    # while True:
    #     inp = input("Enter Action(s): ")
    #     inp.strip()
    #     final_string = ''
    #     for char in inp:
    #         if char in ['f','l','r','c','u','b','F','L','R','C','U','B']:
    #             final_string += char
    #             if final_string:
    #                  return final_string[0]
    return 'L'

# helper function to print the grid
def print_grid(view):
    print('+-----+')
    for ln in view:
        print("|"+str(ln[0])+str(ln[1])+str(ln[2])+str(ln[3])+str(ln[4])+"|")
    print('+-----+')

def print_agent_state():
    print("=== Agent State ===")
    print(f'Starting: {starting_pos}')
    print(f"Position: {curr_pos}")
    print(f"Direction: {current_dir}")
    # Placeholder for future inventory
    if inventory:
        items = ', '.join(f"{k}:{v}" for k, v in inventory.items())
    else:
        items = "None"
    print(f"Inventory: {inventory}")
    print("===================")

# a map for the agent to keep track of everything
def print_global_map():
    print("=== Global Map ===")
    
    if not global_map:
        print("[No tiles explored yet]")
        return

    min_x = min(x for x, y in global_map)
    max_x = max(x for x, y in global_map)
    min_y = min(y for x, y in global_map)
    max_y = max(y for x, y in global_map)

    for y in range(min_y, max_y + 1):
        row = ''
        for x in range(min_x, max_x + 1):
            if (x, y) == curr_pos:
                row += current_dir  # Show agent here
            else:
                row += global_map.get((x, y), '?')
        print(row)

    print("===================")


if __name__ == "__main__":

    # checks for correct amount of arguments 
    if len(sys.argv) != 3:
        print("Usage Python3 "+sys.argv[0]+" -p port \n")
        sys.exit(1)

    port = int(sys.argv[2])

    # checking for valid port number
    if not 1025 <= port <= 65535:
        print('Incorrect port number')
        sys.exit()

    # creates TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
         # tries to connect to host
         # requires host is running before agent
         sock.connect(('localhost',port))
    except (ConnectionRefusedError):
         print('Connection refused, check host is running')
         sys.exit()

    # navigates through grid with input stream of data
    i=0
    j=0
    while True:
        data=sock.recv(100)
        if not data:
            exit()
        for ch in data:
            if (i==2 and j==2):
                view[i][j] = '^'
                view[i][j+1] = chr(ch)
                j+=1 
            else:
                view[i][j] = chr(ch)
            j+=1
            if j>4:
                j=0
                i=(i+1)%5
        if j==0 and i==0:
            print_grid(view) # COMMENT THIS OUT ON SUBMISSION
            print_agent_state()
            print_global_map()
            print(f'On raft: {on_raft}')
            update_global_map()
            action = get_action(view) # gets new actions
            sock.send(action.encode('utf-8'))
            action = action.upper()  # Ensure correct case for direction logic

            if action == 'L' or action == 'R':
                current_dir = turn(current_dir, action)
            elif action == 'F':
                attempt_move_forward()
                check_inventory_pickup()
            elif action == 'C':
                attempt_chop_tree()
            elif action == 'U':
                attempt_unlock_door()
            elif action == 'B':
                attempt_blast()
            time.sleep(0)

    sock.close()
