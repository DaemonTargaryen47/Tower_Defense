from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import math

# Game constants
GRID_LENGTH = 700
TOWER_COST = [100, 250, 500]  # Costs for basic, assault, rocket towers
UPGRADE_COST = [50, 100, 200]  # Upgrade costs for each level
MAJOR_UPGRADE_LEVEL = 3  # Level at which major upgrade happens

# Game state
game_state = {
    'coins': 300,
    'health': 100,
    'wave': 1,
    'towers': [],
    'enemies': [],
    'bullets': [],
    'road_paths': [],
    'selected_tower_type': 0,  # 0=basic, 1=assault, 2=rocket
    'game_over': False,
    'spawn_timer': 0,
    'enemies_spawned': 0,
    'enemies_per_wave': 5,
    'active_roads': 1
}

# Camera settings
camera_pos = [0, 500, 500]
camera_angle_x = 45
camera_angle_y = 0
camera_distance = 500
fovY = 120

# Define path waypoints (3 separate paths)
path1 = [
    (-300, -700), (-300, 0),(-300,500),(200, 500)
]
path2 =[
    (-700,0),(-300, 0)
]

path3 = [
    (-300, -300), (0, -300), (0,0),(700,0)
]

all_paths = [path1, path2, path3]

class Tower:
    def __init__(self, x, z, tower_type):
        self.x = x
        self.z = z
        self.type = tower_type
        self.level = 1
        self.range = 150 + tower_type * 50
        self.damage = 10 + tower_type * 10
        self.fire_rate = 1.0 - tower_type * 0.2
        self.last_shot = 0
        self.color = (
            (1, 0, 0) if tower_type == 0 else 
            (0, 1, 0) if tower_type == 1 else 
            (0, 0, 1) )
        
    def update(self, current_time, enemies):
        # Check if it's time to shoot
        if current_time - self.last_shot > 1.0 / self.fire_rate:
            # Find closest enemy in range
            closest_enemy = None
            min_dist = float('inf')
            
            for enemy in enemies:
                dist = math.sqrt((self.x - enemy.x)**2 + (self.z - enemy.z)**2)
                if dist < self.range and dist < min_dist:
                    min_dist = dist
                    closest_enemy = enemy
            
            if closest_enemy:
                # Calculate bullet direction
                dx = closest_enemy.x - self.x
                dz = closest_enemy.z - self.z
                dist = math.sqrt(dx*dx + dz*dz)
                dx /= dist
                dz /= dist
                
                # Create bullet(s)
                bullets_to_fire = 2 if self.level >= MAJOR_UPGRADE_LEVEL else 1
                
                for _ in range(bullets_to_fire):
                    game_state['bullets'].append({
                        'x': self.x,
                        'z': self.z,
                        'dx': dx,
                        'dz': dz,
                        'speed': 10,
                        'damage': self.damage,
                        'type': self.type,
                        'distance': 0
                    })
                
                self.last_shot = current_time

class Enemy:
    def __init__(self, path_index):
        self.path_index = path_index
        self.path_pos = 0
        self.speed = 1 + random.random() * 0.5
        self.health = 50
        self.max_health = 50
        self.size = 20
        self.x, self.z = game_state['road_paths'][path_index][0]
        
    def update(self):
        path = game_state['road_paths'][self.path_index]
        target_pos = min(int(self.path_pos) + 1, len(path) - 1)
        target_x, target_z = path[target_pos]
        
        dx = target_x - self.x
        dz = target_z - self.z
        dist = math.sqrt(dx*dx + dz*dz)
        
        if dist < 1 and target_pos == len(path) - 1:
            # Reached the center tower
            game_state['health'] -= 10
            return False
        
        if dist > 0:
            dx /= dist
            dz /= dist
            move_dist = min(self.speed, dist)
            self.x += dx * move_dist
            self.z += dz * move_dist
            self.path_pos += move_dist / 50  # Assuming each path segment is 50 units
        
        return True

def init_game():
    game_state['road_paths'] = [
        # Path 1 (top-left to center) - zigzag
        [(-GRID_LENGTH, GRID_LENGTH), (-500, 400), (-300, 250), (-150, 150), (0, 0)],
        
        # Path 2 (bottom-right to center) - zigzag
        [(GRID_LENGTH, -GRID_LENGTH), (400, -500), (250, -300), (150, -150), (0, 0)],
        
        # Path 3 (top-right to center) - zigzag
        [(GRID_LENGTH, GRID_LENGTH), (400, 500), (250, 300), (150, 150), (0, 0)]
    ]
    
    # Add some towers for testing
    # game_state['towers'].append(Tower(-200, 200, 0))
    # game_state['towers'].append(Tower(200, -200, 1))
    # game_state['towers'].append(Tower(200, 200, 2))

def draw_tower(x,y):
    glPushMatrix()
    glColor3f(99/255, 102/255, 98/255)
    glTranslatef(x, y, 0)
    gluCylinder(gluNewQuadric(), 30, 30, 80, 30, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0,0,0)
    glTranslatef(x, y, 80)
    gluCylinder(gluNewQuadric(), 30, 37, 10, 30, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(161/255, 115/255, 55/255)
    glTranslatef(x, y, 80)
    gluCylinder(gluNewQuadric(), 37, 37, 10, 30, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(99/255, 102/255, 98/255)
    glTranslatef(x, y, 0)
    gluCylinder(gluNewQuadric(), 50, 30, 30, 30, 30)
    glPopMatrix()
    
    
    # Base (lower cylinder)
    glPushMatrix()
    glColor3f(99/255, 102/255, 98/255)  # Gray base
    glTranslatef(x, y, 0)
    gluCylinder(gluNewQuadric(), 35, 30, 20, 30, 30)
    glPopMatrix()

    # Mid ring (dark band)
    glPushMatrix()
    glColor3f(0, 0, 0)  # Black ring
    glTranslatef(x, y, 23)
    gluCylinder(gluNewQuadric(), 33, 33, 8, 30, 30)
    glPopMatrix()

 



    # Inner barrel (redish center using sphere for visual)
    glPushMatrix()
    glColor3f(0.5, 0, 0)  # Dark red
    glTranslatef(x, y, 5)
    glutSolidSphere(25, 25, 20)
    glPopMatrix()

    # # Spikes or block supports around base
    # num_blocks = 4
    # outer_radius = 44
    # for i in range(num_blocks):
    #     angle = i * (360 / num_blocks)
    #     rad = math.radians(angle)
    #     n_x = x + outer_radius * math.cos(rad)
    #     n_y = y + outer_radius * math.sin(rad)

    #     glPushMatrix()
    #     glColor3f(0.2, 0.2, 0.2)  # Dark supports
    #     glTranslatef(n_x, n_y, 0)
    #     glRotatef(-angle, 0, 0, 1)
    #     glScalef(1, 0.5, 3)
    #     glutSolidCube(10)
    #     glPopMatrix()
    
    num_blocks = 4
    outer_radius = 44  # Distance from center along Y-axis
    x_offset = 20      # X offset for spacing blocks on each side

    # Positions: (dx, dy) for each block
    positions = [
        (x_offset, outer_radius-10),   # Top right
        (-x_offset, outer_radius-10),  # Top left
        (x_offset, -outer_radius+10),  # Bottom right
        (-x_offset, -outer_radius+10)  # Bottom left
    ]

    for dx, dy in positions:
        n_x = x + dx
        n_y = y + dy
        # Calculate angle to face outward from the tower's center
        angle = math.degrees(math.atan2(dy, dx))
        
        glPushMatrix()
        glColor3f(0.2, 0.2, 0.2)  # Dark supports
        glTranslatef(n_x, n_y, 0)
        glRotatef(angle, 0, 0, 1)  # Rotate to face outward
        glScalef(1, 0.5, 3)
        glutSolidCube(15)
        glPopMatrix()
    # outer_offset = 44
    # for offset in [-outer_offset, outer_offset]:
    #     for side in [-1, 1]:  # Two blocks per side (offset slightly in X)
    #         glPushMatrix()
    #         glColor3f(0.2, 0.2, 0.2)  # Dark supports
    #         glTranslatef(x + side * 20, y + offset+(-side*10*), 0)  # offset in Y, slight spread in X
    #         glRotatef(-20*side, 0, 0, 1)  # No rotation needed now
    #         glScalef(1, 2, 2)
    #         glutSolidCube(15)
    #         glPopMatrix()


    # design2
    glPushMatrix()
    glColor3f(161/255, 115/255, 55/255)
    glTranslatef(x -40, y + 0, 0)
    glRotatef(-90, 0, 1, 0)
    gluCylinder(gluNewQuadric(), 17,25, 10, 20, 20)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(161/255, 115/255, 55/255)
    glTranslatef(x +50, y + 0, 0)
    glRotatef(-90, 0, 1, 0)
    gluCylinder(gluNewQuadric(), 25, 17, 10, 20, 20)
    glPopMatrix()
    

def draw_enemy(x, z, health_percent, size=20):
    glPushMatrix()
    # Base color based on health
    glColor3f(1, health_percent, health_percent)
    glTranslatef(x, size/2, z)
    glutSolidCube(size)
    
    # Health bar
    glPushMatrix()
    glColor3f(1, 0, 0)
    glTranslatef(0, size, 0)
    glScalef(size, 1, 1)
    glutSolidCube(1)
    
    glColor3f(0, 1, 0)
    glTranslatef(0, 0.1, 0)
    glScalef(health_percent, 1, 1)
    glutSolidCube(1)
    glPopMatrix()
    
    glPopMatrix()

def draw_bullet(x, z, bullet_type):
    glPushMatrix()
    if bullet_type == 0:  # Basic
        glColor3f(1, 1, 0)
        glTranslatef(x, 10, z)
        glutSolidSphere(5, 10, 10)
    elif bullet_type == 1:  # Assault
        glColor3f(1, 0.5, 0)
        glTranslatef(x, 10, z)
        glutSolidSphere(8, 10, 10)
    else:  # Rocket
        glColor3f(1, 0, 0)
        glTranslatef(x, 10, z)
        glutSolidSphere(12, 10, 10)
    glPopMatrix()

def draw_center_tower():
    # glPushMatrix()
    # glColor3f(0.5, 0.5, 1)
    # glTranslatef(0, 0, 0)
    # glutSolidCube(80)
    glTranslatef(200,500,0)
    # # Health indicator
    # health_percent = game_state['health'] / 100.0
    glBegin(GL_LINES)
    # X axis (red)
    glColor3f(1,0,0); glVertex3f(0,0,0); glVertex3f(500,0,0)
    # Y axis (green)
    glColor3f(0,1,0); glVertex3f(0,0,0); glVertex3f(0,500,0)
    # Z axis (blue)
    glColor3f(0,0,1); glVertex3f(0,0,0); glVertex3f(0,0,500)
    glEnd()
    
    
    
    # num_beams = 12
    # radius = 39.5
    # for i in range(num_beams):
    #     angle = i * (360 / num_beams)
    #     rad = math.radians(angle)
    #     x = radius * math.cos(rad)
    #     y = radius * math.sin(rad)
        
    #     glPushMatrix()
    #     glColor3f(0.6, 0.3, 0.1)  # Wood brown
    #     glTranslatef(x, y, 60)  # Cylinder height / 2
    #     glRotatef(angle, 0, 0, 1)
    #     glScalef(1, 1, -20)
    #     glutSolidCube(15)
    #     glPopMatrix()
        

    
    glPushMatrix()
    glColor3f(0.85, 0.85, 0.85)
    glTranslatef(0, 0, 0)
    gluCylinder(gluNewQuadric(), 67, 35, 180, 10, 10)
    glPopMatrix()
    
    # //top
    
    glPushMatrix()
    glColor3f(0.8, 0.8, 0.8)  # Slightly different stone color
    glTranslatef(0, 0, 170)
    gluCylinder(gluNewQuadric(), 45, 45, 30, 20, 20)
    glPopMatrix()

    # --- Top Roof Base (sloped, approximated) ---
    glPushMatrix()
    glColor3f(210/255, 10/255, 46/255)  # Red roof
    glTranslatef(0, 0, 200)
    gluCylinder(gluNewQuadric(), 68, 6, 50, 20, 20)
    glPopMatrix()

# --- Top Platform (Parapet Wall with Cubes) ---
    num_blocks = 12
    outer_radius = 40
    for i in range(num_blocks):
        angle = i * (360 / num_blocks)
        rad = math.radians(angle)
        x = outer_radius * math.cos(rad)
        y = outer_radius * math.sin(rad)

        glPushMatrix()
        glColor3f(0.6, 0.3, 0.1) 
        glTranslatef(x, y, 185)  # Top of tower shaft
        glRotatef(angle, 0, 0, 1)
        # glScalef(2, 0.5, 5)
        glutSolidCube(15)
        
        # glColor3f(0,0,0) 
        # glRotatef(angle, 0, 1, 0)
        # gluCylinder(gluNewQuadric(), 20, 8, 30, 10, 10)
        glPopMatrix()
    # //rectangle
    
    # glPushMatrix()
    # glTranslatef(30, 30, 60)
    # glColor3f(0.5, 0.5, 0.5)
    # glutSolidCube(30)
    # glPopMatrix()
    
    # glPushMatrix()
    # glTranslatef(-30, 30, 60)
    # glColor3f(0.5, 0.5, 0.5)
    # glutSolidCube(30)
    # glPopMatrix()
    
    # glPushMatrix()
    # glTranslatef(-30, -30, 60)
    # glColor3f(0.5, 0.5, 0.5)
    # glutSolidCube(30)
    # glPopMatrix()
    
    # glPushMatrix()
    # glTranslatef(30, -30, 60)
    # glColor3f(0.5, 0.5, 0.5)
    # glutSolidCube(30)
    # glPopMatrix()
    
    # glPushMatrix()
    # glColor3f(210/255,10/255,46/255)
    # glTranslatef(0, 0, 180)
    # gluCylinder(gluNewQuadric(), 70, 12, 60, 20, 20)
    # glPopMatrix()
    
    # glColor3f(0, 1, 0)
    # glTranslatef(0, 0.1, 0)
    # glScalef(health_percent, 1, 1)
    # glutSolidCube(1)
    # glPopMatrix()


def keyboardListener(key, x, y):
    global camera_angle_x, camera_angle_y, camera_distance
    if game_state['game_over'] and key == b'r':
        # Reset game
        game_state['coins'] = 300
        game_state['health'] = 100
        game_state['wave'] = 1
        game_state['towers'] = []
        game_state['enemies'] = []
        game_state['bullets'] = []
        game_state['game_over'] = False
        game_state['spawn_timer'] = 0
        game_state['enemies_spawned'] = 0
        game_state['enemies_per_wave'] = 5
        game_state['active_roads'] = 1
        return
    
    if game_state['game_over']:
        return
    
    # Tower selection
    if key == b'1':
        game_state['selected_tower_type'] = 0
    elif key == b'2':
        game_state['selected_tower_type'] = 1
    elif key == b'3':
        game_state['selected_tower_type'] = 2
        
    elif key == b'z':
        camera_distance-=50
    elif key == b'x':
        camera_distance+=50
        
    # Tower placement
    elif key == b' ':
        # Place tower at mouse position (simplified to near center for this demo)
        cost = TOWER_COST[game_state['selected_tower_type']]
        if game_state['coins'] >= cost:
            game_state['coins'] -= cost
            game_state['towers'].append(Tower(0, 100, game_state['selected_tower_type']))
    
    # Tower upgrade
    elif key == b'u':
        # Find tower near center (simplified for this demo)
        for tower in game_state['towers']:
            dist = math.sqrt(tower.x**2 + (tower.z-100)**2)
            if dist < 50:  # Close to our "selected" tower
                cost = UPGRADE_COST[tower.type]
                if game_state['coins'] >= cost:
                    game_state['coins'] -= cost
                    tower.level += 1
                    tower.damage += 5 + tower.type * 5
                    if tower.level % MAJOR_UPGRADE_LEVEL == 0:
                        tower.fire_rate *= 1.5  # Faster firing
                    break




def draw_paths():
    path_width = 110  # Width of the path
    glColor3f(146/255, 119/255, 60/255)  # Brown color for path
    
    for path in all_paths:
        glBegin(GL_QUAD_STRIP)
        for i in range(len(path) - 1):
            x1, z1 = path[i]
            x2, z2 = path[i + 1]

            dx = z1 - z2
            dz = x2 - x1
            length = (dx**2 + dz**2)**0.5
            if length > 0:
                dx = dx / length * path_width / 2
                dz = dz / length * path_width / 2

            glVertex3f(x1 + dx,z1 + dz,1)
            glVertex3f(x1 - dx,z1 - dz,1)
            glVertex3f(x2 + dx,z2 + dz,1)
            glVertex3f(x2 - dx,z2 - dz,1)
        glEnd()

def specialKeyListener(key, x, y):
    global camera_angle_x, camera_angle_y, camera_distance
    
    if key == GLUT_KEY_UP:
        camera_angle_x = min(camera_angle_x + 5, 90)
    elif key == GLUT_KEY_DOWN:
        camera_angle_x = max(camera_angle_x - 5, 10)
    elif key == GLUT_KEY_LEFT:
        camera_angle_y = (camera_angle_y + 5) % 360
    elif key == GLUT_KEY_RIGHT:
        camera_angle_y = (camera_angle_y - 5) % 360

def mouseListener(button, state, x, y):
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN and not game_state['game_over']:
        # Place tower at clicked position (would need proper 3D mouse projection)
        cost = TOWER_COST[game_state['selected_tower_type']]
        if game_state['coins'] >= cost:
            game_state['coins'] -= cost
            
            # Convert screen coords to world coords (simplified)
            world_x = (x - 500) * 1.2
            world_z = (400 - y) * 1.2
            
            # Check if position is valid (not on road)
            valid = True
            for path in game_state['road_paths']:
                for px, pz in path:
                    if math.sqrt((world_x - px)**2 + (world_z - pz)**2) < 50:
                        valid = False
                        break
                if not valid:
                    break
            
            if valid:
                game_state['towers'].append(Tower(world_x, world_z, game_state['selected_tower_type']))

def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    rad_x = math.radians(camera_angle_x)
    rad_y = math.radians(camera_angle_y)
    
    cam_x = camera_distance * math.sin(rad_y) * math.cos(rad_x)
    cam_y =  camera_distance * math.cos(rad_y) * math.cos(rad_x)
    cam_z =  camera_distance * math.sin(rad_x)
    
    gluLookAt(cam_x, cam_y, cam_z,
                0,0,0,
                0, 0, 1)

def update_game():
    if game_state['game_over']:
        return
    
    current_time = glutGet(GLUT_ELAPSED_TIME) / 1000.0
    
    # Spawn enemies
    if game_state['enemies_spawned'] < game_state['enemies_per_wave']:
        if current_time - game_state['spawn_timer'] > 1.0:  # Spawn every second
            game_state['spawn_timer'] = current_time
            path_index = random.randint(0, game_state['active_roads'] - 1)
            game_state['enemies'].append(Enemy(path_index))
            game_state['enemies_spawned'] += 1
    
    # Update towers
    for tower in game_state['towers']:
        tower.update(current_time, game_state['enemies'])
    
    # Update enemies
    game_state['enemies'] = [enemy for enemy in game_state['enemies'] if enemy.update()]
    
    # Update bullets
    new_bullets = []
    for bullet in game_state['bullets']:
        bullet['x'] += bullet['dx'] * bullet['speed']
        bullet['z'] += bullet['dz'] * bullet['speed']
        bullet['distance'] += bullet['speed']
        
        # Check for hits
        hit = False
        for enemy in game_state['enemies']:
            dist = math.sqrt((bullet['x'] - enemy.x)**2 + (bullet['z'] - enemy.z)**2)
            if dist < enemy.size:
                enemy.health -= bullet['damage']
                if bullet['type'] == 2:  # Rocket splash damage
                    for other in game_state['enemies']:
                        if other != enemy:
                            other_dist = math.sqrt((bullet['x'] - other.x)**2 + (bullet['z'] - other.z)**2)
                            if other_dist < 50:  # Splash radius
                                other.health -= bullet['damage'] * 0.5
                hit = True
                break
        
        # Remove bullet if it hit something or went too far
        if not hit and bullet['distance'] < 500:
            new_bullets.append(bullet)
    
    game_state['bullets'] = new_bullets
    
    # Remove dead enemies and award coins
    for enemy in game_state['enemies'][:]:
        if enemy.health <= 0:
            game_state['enemies'].remove(enemy)
            game_state['coins'] += 20
    
    # Check wave completion
    if (game_state['enemies_spawned'] >= game_state['enemies_per_wave'] and 
        len(game_state['enemies']) == 0):
        # Next wave
        game_state['wave'] += 1
        game_state['enemies_spawned'] = 0
        game_state['enemies_per_wave'] += 3
        game_state['coins'] += 100
        
        # Increase active roads every few waves
        if game_state['wave'] % 3 == 0 and game_state['active_roads'] < 3:
            game_state['active_roads'] += 1
    
    # Check game over
    if game_state['health'] <= 0:
        game_state['game_over'] = True

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1,1,1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)



def draw_trees(x,y):
    glPushMatrix()
    glColor3f(50/255, 70/255, 46/255)
    glTranslatef(x,y, 0)
    gluCylinder(gluNewQuadric(), 30, 2, 50, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(50/255, 70/255, 46/255)
    glTranslatef(x, y, 10)
    gluCylinder(gluNewQuadric(), 30, 2, 50, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(50/255, 70/255, 46/255)
    glTranslatef(x, y, 23)
    gluCylinder(gluNewQuadric(), 30, 2, 50, 10, 10)
    glPopMatrix()
def draw_rocks(x,y):
    
    glPushMatrix()
    glTranslatef(x, y, 0)
    glColor3f(178/255, 181/255, 177/255)
    glScalef(2,2,1)
    glutSolidCube(30)
    glPopMatrix()
    

    
    glPushMatrix()
    glTranslatef(x, y, 2)
    glColor3f(99/255, 102/255, 98/255)
    glutSolidCube(40)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(x,y,15)
    glColor3f(178/255, 181/255, 177/255)
    glutSolidCube(20)
    glPopMatrix()


def enemy1(x,y):
    # body
    glPushMatrix()
    glColor3f(10/255, 101/255, 34/255)
    glTranslatef(x,y,35)
    glutSolidSphere(40, 20, 20)
    glPopMatrix()
    
    # head
    glPushMatrix()
    glColor3f(20/255, 125/255, 48/255)
    glTranslatef(x,y-18, 72)
    glutSolidSphere(22, 20, 20)
    glPopMatrix()
    
    # hands
    glPushMatrix()
    glColor3f(20/255, 125/255, 48/255)
    glTranslatef(x+35,y,35)
    glRotatef(180, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 22, 7, 52, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(20/255, 125/255, 48/255)
    glTranslatef(x-35,y,35)
    glRotatef(180, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 22,6, 52, 10, 10)
    glPopMatrix()
    
    
    # eyes
    glPushMatrix()
    glColor3f(0, 0, 0)
    glTranslatef(x+5,y-36,72)
    glutSolidSphere(5, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0, 0, 0)
    glTranslatef(x-5,y-36,72)
    glutSolidSphere(5, 10, 10)
    glPopMatrix()
def mountain(x,y,z):
    glPushMatrix()
    glTranslatef(x,y,z)
    glColor3f(125/255, 109/255, 79/255)
    glutSolidCube(40)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(x,y,z+8)
    glColor3f(67/255, 94/255, 54/255)  # Grass color
    glutSolidCube(40)
    glPopMatrix()  
  
def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    
    setupCamera()
    draw_trees(-500,-300)
    draw_trees(-600,500)
    draw_trees(-400,100)
    draw_trees(-500,300)
    draw_trees(-200,200)
    draw_trees(100,-300)
    draw_trees(200,-200)
    draw_trees(200,200)
    draw_trees(-100,100)
    
    draw_rocks(200,-100)
    draw_rocks(-500,-100)
    draw_rocks(200,300)

    draw_tower(0,200)
    
    
    mountain(100,100,0)
    mountain(105,105,23)
    mountain(80,90,0)
    mountain(120,120,0)
    mountain(150,110,0)
    mountain(100,140,-10)
    
    
    enemy1(200,-280)
    # Draw ground
    glBegin(GL_QUADS)
    glColor3f(121/255, 166/255, 110/255)  # Grass color
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glEnd()
    
    # Draw roads
    # draw_roads()
    draw_paths()
    # Draw center tower
    draw_center_tower()
    
    # # Draw towers
    # for tower in game_state['towers']:
    #     draw_tower(tower.x, tower.z, tower.color)
    
    # # Draw enemies
    # for enemy in game_state['enemies']:
    #     draw_enemy(enemy.x, enemy.z, enemy.health / enemy.max_health)
    
    # # Draw bullets
    # for bullet in game_state['bullets']:
    #     draw_bullet(bullet['x'], bullet['z'], bullet['type'])
    
    # Draw UI
    draw_text(10, 770, f"Coins: {game_state['coins']}")
    draw_text(10, 740, f"Wave: {game_state['wave']}")
    draw_text(10, 710, f"Health: {game_state['health']}")
    draw_text(10, 680, f"Towers: {len(game_state['towers'])}")
    draw_text(10, 650, f"Selected: {'Basic' if game_state['selected_tower_type'] == 0 else 'Assault' if game_state['selected_tower_type'] == 1 else 'Rocket'} (1/2/3)")
    draw_text(10, 620, f"Place: Space | Upgrade: U")
    
    if game_state['game_over']:
        draw_text(400, 400, "GAME OVER - Press R to restart", GLUT_BITMAP_TIMES_ROMAN_24)
    
    glutSwapBuffers()

def idle():
    # update_game()
    glutPostRedisplay()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    wind = glutCreateWindow(b"3D Tower Defense")
    
    init_game()
    
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    
    glEnable(GL_DEPTH_TEST)
    
    glutMainLoop()

if __name__ == "__main__":
    main()
