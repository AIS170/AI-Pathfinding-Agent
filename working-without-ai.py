#!/usr/bin/python3
# ^^ note the python directive on the first line
# COMP3411/9814 agent initiation file 
# requires the host to be running before the agent
# typical initiation would be (file in working directory, port = 31415)
#        python3 agent.py -p 31415
# created by Leo Hoare
# with slight modifications by Alan Blair

import sys
import socket

# declaring visible grid to agent
view = [['' for _ in range(5)] for _ in range(5)]
global_map = {}  # key: (x, y), value: tile char ('.', '^', 'T', 'a', etc.)
starting_pos = (0, 0)
curr_pos = (0, 0)  # starting position
current_dir = '^'     # one of ['^', '>', 'v', '<']
inventory = {}
on_raft = False

directions = ['^', '>', 'v', '<']  # clockwise order
dir_map = {
    '^': (0, -1),
    '>': (1, 0),
    'v': (0, 1),
    '<': (-1, 0)
}

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


def attempt_unlock_door():
    global inventory
    tile, front_pos = get_front_tile()
    if tile == '-':
        if inventory.get('k', 0) > 0:
            print("Door unlocked! 🔓")
            inventory['k'] -= 1
            if inventory['k'] == 0:
                del inventory['k']
            global_map[front_pos] = ' '  # Door becomes empty space\
        else:
            print("You need a key (k) to unlock this door.")
    else:
        print("No door in front to unlock.")


def update_global_map():
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
            global_map[(x, y)] = view[i][j]

def check_inventory_pickup():
    global inventory
    item = global_map.get(curr_pos)

    if item in ['a', 'k', 'd']:
        inventory[item] = inventory.get(item, 0) + 1
        print(f"Picked up: {item}")
        # Once picked up, we can mark the tile as empty
        global_map[curr_pos] = ' '

# function to take get action from AI or user
def get_action(view):

    ## REPLACE THIS WITH AI CODE TO CHOOSE ACTION ##
    direction = view[2][2]
    delta = {'^': (-1, 0), 'v': (1, 0), '<': (0, -1), '>': (0, 1)}
    dx, dy = delta.get(direction, (0, 0))
    front_tile = view[2 + dx][2 + dy]

    if front_tile == '-' and inventory.get('k', 0) > 0:
        return 'U'
    
    if should_use_dynamite_smart():
        return 'B'

    if front_tile == 'T':
        if inventory.get('a', 0) > 0:
            return 'C'
        else:
            print("Tree ahead! You need an axe (a) to chop it down using C.")
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
    while True:
        inp = input("Enter Action(s): ")
        inp.strip()
        final_string = ''
        for char in inp:
            if char in ['f','l','r','c','u','b','F','L','R','C','U','B']:
                final_string += char
                if final_string:
                     return final_string[0]

def attempt_chop_tree():
    global inventory
    tile, front_pos = get_front_tile()
    if tile == 'T':
        if inventory.get('a', 0) > 0:
            print("Tree chopped down! You now have a raft.")
            inventory['raft'] = inventory.get('raft', 0) + 1
            global_map[front_pos] = ' '  # Clear the tree
        else:
            print("You need an axe (a) to chop down this tree!")
    else:
        print("No tree in front to chop.")

def attempt_blast():
    global inventory
    if inventory.get('d', 0) > 0:
        inventory['d'] -= 1
        print("BOOM!")
        if inventory['d'] == 0:
            del inventory['d']
    else:
        print("No dynamite (d) to use!")


def should_use_dynamite_smart():
    if inventory.get('d', 0) == 0:
        return False

    dx, dy = dir_map[current_dir]
    front_x, front_y = curr_pos[0] + dx, curr_pos[1] + dy
    front_tile = global_map.get((front_x, front_y), '?')

    if front_tile != '*':
        return False  # no wall in front

    # Look at 3 tiles beyond the wall
    beyond_items = []
    offsets = []

    if current_dir in ['^', 'v']:
        # scan left, center, right on next row
        for side_dx in [-1, 0, 1]:
            x = front_x + side_dx
            y = front_y + dy
            offsets.append((x, y))
    elif current_dir in ['<', '>']:
        # scan up, center, down on next column
        for side_dy in [-1, 0, 1]:
            x = front_x + dx
            y = front_y + side_dy
            offsets.append((x, y))

    for (x, y) in offsets:
        tile = global_map.get((x, y), '?')
        print(f"Scanning area beyond wall at ({x},{y}): '{tile}'")
        if tile in ['a', 'k', 'd', '$', 'T']:
            beyond_items.append((tile, x, y))

    if beyond_items:
        print(f"Auto-blasting smart: valuable item(s) near wall: {beyond_items}")
        return True

    return False




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
            action = get_action(view) # gets new actions
            sock.send(action.encode('utf-8'))
            action = action.upper()  # Ensure correct case for direction logic

            update_global_map()
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
            

    sock.close()
#!/usr/bin/python3
# ^^ note the python directive on the first line
# COMP3411/9814 agent initiation file 
# requires the host to be running before the agent
# typical initiation would be (file in working directory, port = 31415)
#        python3 agent.py -p 31415
# created by Leo Hoare
# with slight modifications by Alan Blair

import sys
import socket
from collections import deque

# declaring visible grid to agent
view = [['' for _ in range(5)] for _ in range(5)]
global_map = {}  # key: (x, y), value: tile char ('.', '^', 'T', 'a', etc.)
starting_pos = (0, 0)
curr_pos = (0, 0)  # starting position
current_dir = '^'     # one of ['^', '>', 'v', '<']
inventory = {}
on_raft = False

directions = ['^', '>', 'v', '<']  # clockwise order
dir_map = {
    '^': (0, -1),
    '>': (1, 0),
    'v': (0, 1),
    '<': (-1, 0)
}
PASSABLE_TILES = [' ', 'a', 'k', 'd', '$']


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


def attempt_unlock_door():
    global inventory
    tile, front_pos = get_front_tile()
    if tile == '-':
        if inventory.get('k', 0) > 0:
            print("Door unlocked! 🔓")
            inventory['k'] -= 1
            if inventory['k'] == 0:
                del inventory['k']
            global_map[front_pos] = ' '  # Door becomes empty space\
        else:
            print("You need a key (k) to unlock this door.")
    else:
        print("No door in front to unlock.")


def update_global_map():
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
            global_map[(x, y)] = view[i][j]

def check_inventory_pickup():
    global inventory
    item = global_map.get(curr_pos)

    if item in ['a', 'k', 'd']:
        inventory[item] = inventory.get(item, 0) + 1
        print(f"Picked up: {item}")
        # Once picked up, we can mark the tile as empty
        global_map[curr_pos] = ' '

# function to take get action from AI or user
def get_action(view):
    global action_queue, current_dir

    ## REPLACE THIS WITH AI CODE TO CHOOSE ACTION ##
    direction = view[2][2]
    delta = {'^': (-1, 0), 'v': (1, 0), '<': (0, -1), '>': (0, 1)}
    dx, dy = delta.get(direction, (0, 0))
    front_tile = view[2 + dx][2 + dy]
    action_queue = deque()

    reachable_tools, blocked_tools = detect_visible_tools()
    
    if action_queue:
        return action_queue.popleft()
    
    path = find_closest_tool_path()
    if path:
        print(f"Path to tool: {path}")
        moves = generate_move_sequence(path, curr_pos, current_dir)
        print(f"Generated move sequence: {moves}")
        action_queue.extend(moves)
        return action_queue.popleft()

    if reachable_tools:
        print("Reachable tools in view:")
        for tool, pos in reachable_tools:
            print(f" - {tool} at {pos}")
    if blocked_tools:
        print("Blocked tools in view (obstacles in way):")
        for tool, pos in blocked_tools:
            print(f" - {tool} at {pos}")


    if front_tile == '-' and inventory.get('k', 0) > 0:
        return 'U'
    
    if should_use_dynamite_smart():
        return 'B'

    if front_tile == 'T':
        if inventory.get('a', 0) > 0:
            return 'C'
        else:
            print("Tree ahead! You need an axe (a) to chop it down using C.")
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
    while True:
        inp = input("Enter Action(s): ")
        inp.strip()
        final_string = ''
        for char in inp:
            if char in ['f','l','r','c','u','b','F','L','R','C','U','B']:
                final_string += char
                if final_string:
                     return final_string[0]

def attempt_chop_tree():
    global inventory
    tile, front_pos = get_front_tile()
    if tile == 'T':
        if inventory.get('a', 0) > 0:
            print("Tree chopped down! You now have a raft.")
            inventory['raft'] = inventory.get('raft', 0) + 1
            global_map[front_pos] = ' '  # Clear the tree
        else:
            print("You need an axe (a) to chop down this tree!")
    else:
        print("No tree in front to chop.")

def attempt_blast():
    global inventory
    if inventory.get('d', 0) > 0:
        inventory['d'] -= 1
        print("BOOM!")
        if inventory['d'] == 0:
            del inventory['d']
    else:
        print("No dynamite (d) to use!")


def should_use_dynamite_smart():
    if inventory.get('d', 0) == 0:
        return False

    dx, dy = dir_map[current_dir]
    front_x, front_y = curr_pos[0] + dx, curr_pos[1] + dy
    front_tile = global_map.get((front_x, front_y), '?')

    if front_tile != '*':
        return False  # no wall in front

    # Look at 3 tiles beyond the wall
    beyond_items = []
    offsets = []

    if current_dir in ['^', 'v']:
        # scan left, center, right on next row
        for side_dx in [-1, 0, 1]:
            x = front_x + side_dx
            y = front_y + dy
            offsets.append((x, y))
    elif current_dir in ['<', '>']:
        # scan up, center, down on next column
        for side_dy in [-1, 0, 1]:
            x = front_x + dx
            y = front_y + side_dy
            offsets.append((x, y))

    for (x, y) in offsets:
        tile = global_map.get((x, y), '?')
        print(f"Scanning area beyond wall at ({x},{y}): '{tile}'")
        if tile in ['a', 'k', 'd', '$', 'T']:
            beyond_items.append((tile, x, y))

    if beyond_items:
        print(f"Auto-blasting smart: valuable item(s) near wall: {beyond_items}")
        return True

    return False

def detect_visible_tools():
    visible_tools = []
    for (x, y), tile in global_map.items():
        if tile in ['a', 'k', 'd', '$'] and is_tile_reachable((x, y)):
            visible_tools.append((tile, x, y))
    return visible_tools

def is_tile_reachable(pos):
    tile = global_map.get(pos, '?')
    
    # Assume reachable if it's empty or a tool or treasure
    if tile in [' ', '.', '^', 'a', 'k', 'd', '$']:
        return True
    elif tile == '*':
        return False  # Wall
    elif tile == 'T':
        return 'a' in inventory  # Need axe
    elif tile == '-':
        return 'k' in inventory  # Need key
    elif tile == '~':
        return 'raft' in inventory  # Need raft
    else:
        return False  # Unknown or blocked
    
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

        # Explore neighbors (N, S, E, W)
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

def find_closest_tool_path():

    targets = [pos for (tile, pos) in detect_visible_tools()[0]]  # Only reachable tools
    if not targets:
        return None

    visited = set()
    queue = deque([(curr_pos, [])])  # (position, path)

    while queue:
        pos, path = queue.popleft()
        if pos in visited:
            continue
        visited.add(pos)

        if pos in targets:
            return path + [pos]  # path includes goal

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

def generate_move_sequence(path, current_pos, current_dir):
    moves = []
    dir_now = current_dir
    pos = current_pos

    for next_pos in path[1:]:  # skip current_pos
        required_dir = direction_to(pos, next_pos)
        while dir_now != required_dir:
            # Turn left or right to align
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
            

    sock.close()
