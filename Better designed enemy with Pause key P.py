from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import uuid


# Game constants
is_paused = False

GRID_LENGTH = 700
TOWER_COST = [100, 300, 200]  # Costs for cannon, slow, mortar towers
UPGRADE_COST = [50, 100, 200]  # Upgrade costs for each level
MAJOR_UPGRADE_LEVEL = 3  # Level at which major upgrade happens
set_tower = False
last_mouse_x = 500
last_mouse_y = 400
PATH_WIDTH=110
# Game state
game_state = {
    'coins': 1000,
    'health': 100,
    'wave': 1,
    'towers': [],
    'enemies': [],
    'bullets': [],
    'road_paths': [],
    'selected_tower_type': 0,  # 0=basic, 1=slow, 2=mortar
    'game_over': False,
    'is_slowed': False,
    'spawn_timer': 0,
    'enemies_spawned': 0,
    'enemies_per_wave': 5,
    'active_roads': 1,
    'selected_tower': None
}

# Camera settings
camera_pos = [0, 500, 500]
camera_angle_x = 45
camera_angle_y = 0
camera_distance = 500
fovY = 120

path1 = [
    (700, 0), (0, 0),(0,-300),(-300,-300),(-300, 0), (-300, 500), (200, 500)
]
path2= [
    (-300, -700), (-300, 0),(-300,500),(200, 500)
]
path3=[
    (-700,0),(-300, 0)
]
all_paths = [path1, path2, path3]

game_state['road_paths'] = [path1, path2, path3]


class Tower:
    def __init__(self, x, z, tower_type):
        self.x = x
        self.z = z
        self.type = tower_type
        self.level = 1
        self.health = 100 + tower_type * 50
        self.range= 300 if tower_type ==2 else 200
        self.damage = [20, 0, 40][tower_type]  # Cannon: 20, Slow: 0, Mortar: 40
        self.fire_rate = [0.5, 2.0, 2.0][tower_type]  # Cannon: fast, Slow/Mortar: 2s
        self.last_shot = 0
        self.slow_factor = 0.5 if tower_type == 1 else 1.0  # Slow tower reduces speed
    def update(self, current_time, enemies):
        if current_time - self.last_shot < self.fire_rate:
            return

        closest_enemy = None
        min_dist = float('inf')

        for enemy in enemies:
            dist = math.sqrt((self.x - enemy.x)**2 + (self.z - enemy.z)**2)
            if dist < self.range and dist < min_dist:
                min_dist = dist
                closest_enemy = enemy

        if closest_enemy:
            if self.type == 0:  # Cannon tower
                dx = closest_enemy.x - self.x
                dz = closest_enemy.z - self.z
                dist = math.sqrt(dx*dx + dz*dz)
                dx /= dist
                dz /= dist
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
            elif self.type == 1:  # Slow tower
                for enemy in enemies:
                    dist = math.sqrt((self.x - enemy.x)**2 + (self.z - enemy.z)**2)
                    if dist < self.range:
                        enemy.is_slowed=True
                        # enemy.speed = enemy.base_speed*self.slow_factorb                    
                        enemy.update_speed(self.slow_factor)
                    else:
                        enemy.is_slowed=False
                        enemy.update_speed(1.0)
            elif self.type == 2:  # Mortar tower
                game_state['bullets'].append({
                    'x': self.x,
                    'z': self.z,
                    'target_x': closest_enemy.x,
                    'target_z': closest_enemy.z,
                    'height': 0,
                    'speed': 10,
                    'damage': self.damage,
                    'type': self.type,
                    'time': 0
                })
            self.last_shot = current_time


class Enemy:
    def __init__(self):
        self.path =random.choice(all_paths[:game_state['active_roads']])  # Use path1 for all enemies
        self.current_waypoint = 0 
        self.type= random.randint(0,3)# 0: normal, 1: fast, 2: tank
        self.x, self.z = self.path[0]  # Start at first waypoint
        self.base_speed = [0.3, 0.5, 0.2, 0.4][self.type]
        self.speed =self.base_speed 
        self.scale = [0.5, 0.4, 0.8, 0.6][self.type]
        self.color = [(10/255, 101/255, 34/255), (0, 1, 0), (0, 0, 1), (1, 0.5, 0)][self.type]
        self.rotation = 0  # Y-axis rotation in degrees
        self.health = [100, 80, 150, 120][self.type]
        self.hand_phase = 0.0  # Controls hand animation
        self.alive = True
        self.size = 20  # For collision detection
        self.max_health = self.health
        self.is_slowed = False
        # Random spawn within path width
        if len(self.path) >= 2:
            P0, P1 = self.path[0], self.path[1]
            D_x, D_y = P1[0] - P0[0], P1[1] - P0[1]
            dist = math.sqrt(D_x**2 + D_y**2)
            if dist == 0:
                perp_x, perp_y = 1, 0
            else:
                perp_x, perp_y = -D_y / dist, D_x / dist
            random_t = random.uniform(-PATH_WIDTH/2, PATH_WIDTH/2)
            self.x = P0[0] + random_t * perp_x
            self.z = P0[1] + random_t * perp_y
        else:
            self.x, self.z = self.path[0]
        # Calculate initial rotation
        self.update_rotation()

    def update_rotation(self):
        if self.current_waypoint < len(self.path) - 1:
            target_x, target_z = self.path[self.current_waypoint + 1]
            dx = target_x - self.x
            dz = target_z - self.z
            if dx != 0 or dz != 0:
                self.rotation = math.degrees(math.atan2(dx, dz))
    def update_speed(self,slow_factor):
        if self.is_slowed:
            self.speed=self.base_speed * slow_factor
        else:
            self.speed = self.base_speed
            
    def update(self):
        if not self.alive or self.current_waypoint >= len(self.path) - 1:
            if self.current_waypoint >= len(self.path) - 1:
                game_state['health'] -= 10  # Damage base
                self.alive = False
            return False
        
        # self.is_slowed = False
        # Move toward next waypoint
        target_x, target_z = self.path[self.current_waypoint + 1]
        dx = target_x - self.x
        dz = target_z - self.z
        distance = math.hypot(dx, dz)

        if distance < 1:  # Reached waypoint
            self.current_waypoint += 1
            self.update_rotation()
            if self.current_waypoint >= len(self.path) - 1:
                self.alive = False
                game_state['health'] -= 10  # Damage base
                return False
            target_x, target_z = self.path[self.current_waypoint + 1]
            dx = target_x - self.x
            dz = target_z - self.z
            distance = math.hypot(dx, dz)
        
        if distance > 0:
            move_x = (dx / distance) * self.speed
            move_z = (dz / distance) * self.speed
            self.x += move_x
            self.z += move_z

        # Update hand animation
        self.hand_phase = (self.hand_phase + self.speed * 0.01) % 1.0
        return True

def enemy1(x, y, enemy_angle, hand_phase,color,scale,is_slowed=False):
    glPushMatrix()
    glTranslatef(x, y, 25)
    glScalef(scale, scale, scale)
    glRotatef(enemy_angle, 0, 0, 1)
    
    glPushMatrix()
    glColor3f(*(0.5, 0.5, 1) if is_slowed else color)
    glutSolidSphere(40, 20, 20)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(20/255, 125/255, 48/255)
    glTranslatef(0, -18, 37)
    glutSolidSphere(22, 20, 20)
    glPopMatrix()
    
    # Right hand (alternates between 120 and 180 degrees)
    right_angle = 120 + 60 * math.sin(hand_phase * 2 * math.pi)
    glPushMatrix()
    glColor3f(20/255, 125/255, 48/255)
    glTranslatef(35, 0, 0)
    glRotatef(right_angle, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 22, 7, 52, 10, 10)
    glPopMatrix()
    
    # Left hand (opposite phase)
    left_angle = 120 + 60 * math.sin((hand_phase + 0.5) * 2 * math.pi)
    glPushMatrix()
    glColor3f(20/255, 125/255, 48/255)
    glTranslatef(-35, 0, 0)
    glRotatef(left_angle, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 22, 6, 52, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0, 0, 0)
    glTranslatef(5, -36, 37)
    glutSolidSphere(5, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0, 0, 0)
    glTranslatef(-5, -36, 37)
    glutSolidSphere(5, 10, 10)
    glPopMatrix()
    
    glPopMatrix()


def enemy_robot(x, z, rotation, hand_phase, color, scale, is_slowed):
    glPushMatrix()
    glTranslatef(x, z, 20)
    glRotatef(rotation, 0, 0, 1)
    glScalef(scale * 1.5, scale * 1.5, scale * 1.5)

    ### MAIN BODY (Bright Red)
    glColor3f(0.8, 0.0, 0.0)  # Bright red
    glPushMatrix()
    glScalef(1.2, 1.2, 2.0)
    glutSolidCube(30)
    glPopMatrix()

    ### HEAD (Spherical)
    glColor3f(0.6, 0.0, 0.0)  # Dark red
    glPushMatrix()
    glTranslatef(0, 0, 35)
    glutSolidSphere(12, 20, 20)  # Circular head

    # Eyes - Bright Yellow (contrasting)
    glColor3f(1.0, 1.0, 0.0)
    glPushMatrix()
    glTranslatef(-4, -6, 10)
    glutSolidSphere(2, 10, 10)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(4, -6, 10)
    glutSolidSphere(2, 10, 10)
    glPopMatrix()

    glPopMatrix()


    ### SHOULDERS - Black with Spikes
    glColor3f(0.1, 0.1, 0.1)
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(20 * side, 0, 25)
        glRotatef(90 * side, 0, 1, 0)
        glutSolidCone(10, 20, 10, 10)
        glPopMatrix()

    ### ARMS - Contrasting Gray
    glColor3f(0.6, 0.6, 0.6)
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(25 * side, 0, 15)
        glRotatef(math.sin(hand_phase) * 20, 1, 0, 0)
        glScalef(1, 1, 2)
        glutSolidCube(10)
        glPopMatrix()

    ### LEGS - Dark Gray, Clearly Separated
    glColor3f(0.3, 0.3, 0.3)
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(10 * side, 0, -20)
        glScalef(1, 1, 3)
        glutSolidCube(8)
        glPopMatrix()

    ### OPTIONAL: Exhaust pipe on back
    glColor3f(0.5, 0.5, 0.5)
    glPushMatrix()
    glTranslatef(0, -10, 35)
    gluCylinder(gluNewQuadric(), 2, 1, 15, 8, 8)
    glPopMatrix()

    glPopMatrix()

def init_game():
    game_state['road_paths'] = [path1, path2, path3]


# MortarTower
def draw_tower1(x, y):
    glPushMatrix()
    glColor3f(99/255, 102/255, 98/255)
    glTranslatef(x, y, 0)
    gluCylinder(gluNewQuadric(), 30, 30, 80, 30, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0, 0, 0)
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
    
    glPushMatrix()
    glColor3f(99/255, 102/255, 98/255)
    glTranslatef(x, y, 0)
    gluCylinder(gluNewQuadric(), 35, 30, 20, 30, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0, 0, 0)
    glTranslatef(x, y, 23)
    gluCylinder(gluNewQuadric(), 33, 33, 8, 30, 30)
    glPopMatrix()
    
    
    # red mortar- ball
    glPushMatrix()
    glColor3f(0.5, 0, 0)
    glTranslatef(x, y, 5)
    glutSolidSphere(25, 25, 20)
    glPopMatrix()
    
    num_blocks = 4
    outer_radius = 44
    x_offset = 20
    positions = [
        (x_offset, outer_radius-10),
        (-x_offset, outer_radius-10),
        (x_offset, -outer_radius+10),
        (-x_offset, -outer_radius+10)
    ]
    
    for dx, dy in positions:
        n_x = x + dx
        n_y = y + dy
        angle = math.degrees(math.atan2(dy, dx))
        glPushMatrix()
        glColor3f(0.2, 0.2, 0.2)
        glTranslatef(n_x, n_y, 0)
        glRotatef(angle, 0, 0, 1)
        glScalef(1, 0.5, 3)
        glutSolidCube(15)
        glPopMatrix()
    
    glPushMatrix()
    glColor3f(161/255, 115/255, 55/255)
    glTranslatef(x -40, y + 0, 0)
    glRotatef(-90, 0, 1, 0)
    gluCylinder(gluNewQuadric(), 17, 25, 10, 20, 20)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(161/255, 115/255, 55/255)
    glTranslatef(x +50, y + 0, 0)
    glRotatef(-90, 0, 1, 0)
    gluCylinder(gluNewQuadric(), 25, 17, 10, 20, 20)
    glPopMatrix()
# slowtower
def draw_tower2(x, y):
    glPushMatrix()
    glColor3f(95/255, 124/255, 132/255)
    glTranslatef(x, y, 0)
    gluCylinder(gluNewQuadric(), 30, 15, 120, 30, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0, 0, 0)
    glTranslatef(x, y, 120)
    gluCylinder(gluNewQuadric(), 25, 28, 5, 20, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(189/255, 198/255, 227/255)
    glTranslatef(x, y, 120)
    gluCylinder(gluNewQuadric(), 28, 28, 5, 20, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(203/255, 112/255, 29/255)
    glTranslatef(x, y, 100)
    gluCylinder(gluNewQuadric(), 28, 28, 7, 20, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(203/255, 112/255, 29/255)
    glTranslatef(x, y, 90)
    gluCylinder(gluNewQuadric(), 28, 28, 7, 20, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(95/255, 124/255, 132/255)
    glTranslatef(x, y, 0)
    gluCylinder(gluNewQuadric(), 45, 28, 30, 30, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(31/255, 176/255, 195/255)
    glTranslatef(x, y, 120)
    glutSolidSphere(25, 25, 20)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(161/255, 115/255, 55/255)
    glTranslatef(x, y, 30)
    gluCylinder(gluNewQuadric(), 27, 27, 6, 20, 30)
    glPopMatrix()
    
    outer_radius = 44
    x_offset = 20
    positions = [
        (x_offset, outer_radius-30),
        (-x_offset, outer_radius-30),
        (x_offset, -outer_radius+30),
        (-x_offset, -outer_radius+30)
    ]
    
    for dx, dy in positions:
        n_x = x + dx
        n_y = y + dy
        angle = math.degrees(math.atan2(dy, dx))
        glPushMatrix()
        glColor3f(61/255, 71/255, 75/255)
        glTranslatef( n_x, n_y, 70)
        glRotatef(angle, 0, 0, 1)
        glScalef(1, 1, 8)
        glutSolidCube(10)
        glPopMatrix()
    
    outer_radius = 44
    positions = [
        (math.cos(math.radians(angle)) * outer_radius,
         math.sin(math.radians(angle)) * outer_radius)
        for angle in [35, 145, 215, 325]
    ]
    
    for dx, dy in positions:
        n_x = x + dx
        n_y = y + dy
        angle = math.degrees(math.atan2(dy, dx))
        glPushMatrix()
        glColor3f(61/255, 71/255, 75/255)
        glTranslatef(n_x, n_y, 0)
        glRotatef(angle - 90, 0, 0, 1)
        glRotatef(30, 1, 0, 0)
        glScalef(1, 1, 6.5)
        glutSolidCube(10)
        glPopMatrix()

# cannontower
def draw_tower3(x,y):
    
    glPushMatrix()
    glTranslatef(x, y, 0)
    glScalef(0.7,0.7,0.7)
    glBegin(GL_LINES)
    glColor3f(1, 0, 0); glVertex3f(0, 0, 0); glVertex3f(500, 0, 0)
    glColor3f(0, 1, 0); glVertex3f(0, 0, 0); glVertex3f(0, 500, 0)
    glColor3f(0, 0, 1); glVertex3f(0, 0, 0); glVertex3f(0, 0, 500)
    glEnd()
    
    glPushMatrix()
    glColor3f(0.85, 0.85, 0.85)
    gluCylinder(gluNewQuadric(), 67, 35, 160, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0.8, 0.8, 0.8)
    glTranslatef(0, 0, 150)
    gluCylinder(gluNewQuadric(), 45, 45, 30, 20, 20)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(210/255, 10/255, 46/255)
    glTranslatef(0, 0, 180)
    gluCylinder(gluNewQuadric(), 68, 6, 50, 20, 20)
    glPopMatrix()
    
    
    # cannon
    num_blocks = 7
    outer_radius = 40
    for i in range(num_blocks):
        angle = i * (360 / num_blocks)
        rad = math.radians(angle)
        bx = outer_radius * math.cos(rad)
        by = outer_radius * math.sin(rad)
        glPushMatrix()
        glColor3f(0.6, 0.3, 0.1)
        glTranslatef(bx, by, 165)
        glRotatef(angle, 0, 0, 1)
        glRotatef(90, 0, 1, 0)
        gluCylinder(gluNewQuadric(), 11, 6, 28, 20, 20)
        glPopMatrix()
    glPopMatrix()
    
def draw_bullet(x, y, bullet_type,height=10,target_x=None,target_y=None,time=0):
    
    if bullet_type==1:
        return
    glPushMatrix()  
    if bullet_type == 0: #cannon
        glColor3f(1, 1, 0)
        glTranslatef(x, y, height)
        glutSolidSphere(5, 10, 10)
    elif bullet_type == 2:#Mortar
        glColor3f(1, 0, 0)
        # Simulate projectile motion
        t = time
        vx = (target_x - x) / 1.0
        vy = (target_y - y) / 1.0
        vz = 50 - 9.8 * t  # Initial upward velocity - gravity
        new_x = x + vx * t
        new_y = y + vy * t
        new_z = 25 + vz * t - 0.5 * 9.8 * t * t
        glTranslatef(new_x, new_y, new_z)
        glutSolidSphere(12, 10, 10)
    glPopMatrix()

def draw_center_tower(x, y):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glBegin(GL_LINES)
    glColor3f(1, 0, 0); glVertex3f(0, 0, 0); glVertex3f(500, 0, 0)
    glColor3f(0, 1, 0); glVertex3f(0, 0, 0); glVertex3f(0, 500, 0)
    glColor3f(0, 0, 1); glVertex3f(0, 0, 0); glVertex3f(0, 0, 500)
    glEnd()
    
    glPushMatrix()
    glColor3f(0.85, 0.85, 0.85)
    gluCylinder(gluNewQuadric(), 67, 35, 160, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0.8, 0.8, 0.8)
    glTranslatef(0, 0, 150)
    gluCylinder(gluNewQuadric(), 45, 45, 30, 20, 20)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(210/255, 10/255, 46/255)
    glTranslatef(0, 0, 180)
    gluCylinder(gluNewQuadric(), 68, 6, 50, 20, 20)
    glPopMatrix()
    
    num_blocks = 12
    outer_radius = 40
    for i in range(num_blocks):
        angle = i * (360 / num_blocks)
        rad = math.radians(angle)
        bx = outer_radius * math.cos(rad)
        by = outer_radius * math.sin(rad)
        glPushMatrix()
        glColor3f(0.6, 0.3, 0.1)
        glTranslatef(bx, by, 165)
        glRotatef(angle, 0, 0, 1)
        glutSolidCube(15)
        glPopMatrix()
    glPopMatrix()

def keyboardListener(key, x, y):
    global camera_angle_x, camera_angle_y, camera_distance,set_tower
    if game_state['game_over'] and key == b'r':
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
    
    if key == b'1':
        game_state['selected_tower_type'] = 0
    elif key == b'2':
        game_state['selected_tower_type'] = 1
    elif key == b'3':
        game_state['selected_tower_type'] = 2
    elif key == b'z':
        camera_distance -= 50
    elif key == b'x':
        camera_distance += 50
    elif key == b'b':
        set_tower = not set_tower
    
    elif key == b'p':
        global is_paused
        is_paused = not is_paused
        print("Game Paused" if is_paused else "Game Resumed")

    
    elif key == b'u' and game_state['selected_tower']:
        tower = game_state['selected_tower']
        cost = UPGRADE_COST[tower.type]
        if game_state['coins'] >= cost:
            game_state['coins'] -= cost
            tower.level += 1
            tower.damage += 5 + tower.type * 5
            if tower.level % MAJOR_UPGRADE_LEVEL == 0:
                tower.fire_rate *= 1.5

def draw_paths():
    path_width = 110
    glColor3f(146/255, 119/255, 60/255)
    
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
                glVertex3f(x1 + dx, z1 + dz, 1)
                glVertex3f(x1 - dx, z1 - dz, 1)
                glVertex3f(x2 + dx, z2 + dz, 1)
                glVertex3f(x2 - dx, z2 - dz, 1)
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
    global set_tower
    if button != GLUT_LEFT_BUTTON or state != GLUT_DOWN or game_state['game_over']:
        return

    world_x = -(x - 500) * 1.2
    world_z = -(400 - y) * 1.2

    if set_tower:
        cost = TOWER_COST[game_state['selected_tower_type']]
        if game_state['coins'] >= cost:
            valid = True
            for path in game_state['road_paths'][:game_state['active_roads']]:
                for px, pz in path:
                    if math.sqrt((world_x - px)**2 + (world_z - pz)**2) < 50:
                        valid = False
                        break
                if not valid:
                    break
            if valid:
                game_state['coins'] -= cost
                game_state['towers'].append(Tower(world_x, world_z, game_state['selected_tower_type']))
                set_tower = False
    else:
        game_state['selected_tower'] = None
        for tower in game_state['towers']:
            dist = math.sqrt((world_x - tower.x)**2 + (world_z - tower.z)**2)
            if dist < 50:
                game_state['selected_tower'] = tower
                break
def is_position_valid(world_x, world_z):
    # Check against paths
    for path in game_state['road_paths'][:game_state['active_roads']]:
        for i in range(len(path) - 1):
            x1, z1 = path[i]
            x2, z2 = path[i + 1]
            # Calculate closest point on line segment to tower position
            dx, dz = x2 - x1, z2 - z1
            length_sq = dx*dx + dz*dz
            if length_sq == 0:
                dist = math.sqrt((world_x - x1)**2 + (world_z - z1)**2)
                if dist < PATH_WIDTH / 2 + 50:
                    return False
            else:
                t = max(0, min(1, ((world_x - x1)*dx + (world_z - z1)*dz) / length_sq))
                closest_x = x1 + t * dx
                closest_z = z1 + t * dz
                dist = math.sqrt((world_x - closest_x)**2 + (world_z - closest_z)**2)
                if dist < PATH_WIDTH / 2 + 50:
                    return False
    
    # Check against center tower
    center_x, center_z = 200, 500
    if math.sqrt((world_x - center_x)**2 + (world_z - center_z)**2) < 100:
        return False
    
    # Check against other towers
    for tower in game_state['towers']:
        if math.sqrt((world_x - tower.x)**2 + (world_z - tower.z)**2) < 100:
            return False
            
    return True

def motionListener(x, y):
    globals()['last_mouse_x'] = x
    globals()['last_mouse_y'] = y

def passiveMotionListener(x, y):
    globals()['last_mouse_x'] = x
    globals()['last_mouse_y'] = y
    
    
def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    rad_x = math.radians(camera_angle_x)
    rad_y = math.radians(camera_angle_y)
    
    cam_x = camera_distance * math.sin(rad_y) * math.cos(rad_x)
    cam_y = camera_distance * math.cos(rad_y) * math.cos(rad_x)
    cam_z = camera_distance * math.sin(rad_x)
    
    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 0, 1)

def update_game():
   if not is_paused: 
    if game_state['game_over']:
        return
    
    current_time = glutGet(GLUT_ELAPSED_TIME) / 1000.0
    
    if game_state['enemies_spawned'] < game_state['enemies_per_wave']:
        if current_time - game_state['spawn_timer'] > 1.0:
            game_state['spawn_timer'] = current_time
            game_state['enemies'].append(Enemy())
            game_state['enemies_spawned'] += 1
            
    for enemy in game_state['enemies']:
        if not enemy.is_slowed:
            enemy.update_speed(1)  # Revert to base speed if not slowed
        enemy.update()
    for tower in game_state['towers']:
        tower.update(current_time, game_state['enemies'])
    
    game_state['enemies'] = [enemy for enemy in game_state['enemies'] if enemy.update()]
    
    new_bullets = []
    for bullet in game_state['bullets']:
        if bullet['type'] == 0:  # Cannon
            bullet['x'] += bullet['dx'] * bullet['speed']
            bullet['z'] += bullet['dz'] * bullet['speed']
            bullet['distance'] += bullet['speed']
        elif bullet['type'] == 2:  # Mortar
            bullet['time'] += 0.016
            if bullet['time'] > 1.0:
                bullet['distance'] = 500  # Mark as expired
            else:
                bullet['distance'] = bullet['speed'] * bullet['time']
        
        hit = False
        for enemy in game_state['enemies']:
            dist = math.sqrt((bullet['x'] - enemy.x)**2 + (bullet['z'] - enemy.z)**2)
            if dist < enemy.size:
                enemy.health -= bullet['damage']
                if bullet['type'] == 2:
                    for other in game_state['enemies']:
                        if other != enemy:
                            other_dist = math.sqrt((bullet['x'] - other.x)**2 + (bullet['z'] - other.z)**2)
                            if other_dist < 50:
                                other.health -= bullet['damage'] * 0.5
                hit = True
                break
        
        if not hit and bullet['distance'] < 500:
            new_bullets.append(bullet)
    
    game_state['bullets'] = new_bullets
    
    for enemy in game_state['enemies'][:]:
        if enemy.health <= 0:
            game_state['enemies'].remove(enemy)
            game_state['coins'] += 20
    
    if (game_state['enemies_spawned'] >= game_state['enemies_per_wave'] and 
        len(game_state['enemies']) == 0):
        game_state['wave'] += 1
        game_state['enemies_spawned'] = 0
        game_state['enemies_per_wave'] += 3
        game_state['coins'] += 100
        if game_state['wave'] % 3 == 0 and game_state['active_roads'] < 3:
            game_state['active_roads'] += 1
    
    if game_state['health'] <= 0:
        game_state['game_over'] = True
   glutPostRedisplay()  # Refresh the window
   glutTimerFunc(16, update_game, 0)      

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
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

def draw_trees(x, y):
    glPushMatrix()
    glColor3f(50/255, 70/255, 46/255)
    glTranslatef(x, y, 0)
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

def draw_rocks(x, y):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glColor3f(178/255, 181/255, 177/255)
    glScalef(2, 2, 1)
    glutSolidCube(30)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(x, y, 2)
    glColor3f(99/255, 102/255, 98/255)
    glutSolidCube(40)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(x, y, 15)
    glColor3f(178/255, 181/255, 177/255)
    glutSolidCube(20)
    glPopMatrix()

def mountain(x, y, z):
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(125/255, 109/255, 79/255)
    glutSolidCube(40)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(x, y, z+8)
    glColor3f(67/255, 94/255, 54/255)
    glutSolidCube(40)
    glPopMatrix()
def draw_range(x, z, range,valid=True):
    glPushMatrix()
    glColor4f(0.2, 0.8, 0.2, 0.3) if valid else glColor4f(0.8, 0.2, 0.2, 0.3)
    glTranslatef(-x, -z, 0)
    gluCylinder(gluNewQuadric(), range, range, 10, 30, 30)
    glPopMatrix()
def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    
    setupCamera()
    
    draw_trees(-500, -300)
    draw_trees(-600, 500)
    draw_trees(-400, 100)
    draw_trees(-500, 300)
    draw_trees(-200, 200)
    draw_trees(100, -300)
    draw_trees(200, -200)
    draw_trees(200, 200)
    draw_trees(-100, 100)
    
    draw_rocks(200, -100)
    draw_rocks(-500, -100)
    draw_rocks(200, 300)
    draw_rocks(200, 600)
       
    mountain(100, 100, 0)
    mountain(105, 105, 23)
    mountain(80, 90, 0)
    mountain(120, 120, 0)
    mountain(150, 110, 0)
    mountain(100, 140, -10)
    

    
    glBegin(GL_QUADS)
    glColor3f(121/255, 166/255, 110/255)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glEnd()
    
    draw_paths()
    draw_center_tower(200, 500)
    
    for enemy in game_state['enemies']:
      if enemy.type in [0, 1, 2]:
        enemy1(enemy.x, enemy.z, enemy.rotation, enemy.hand_phase, enemy.color, enemy.scale, enemy.is_slowed)
      elif enemy.type == 3:
        enemy_robot(enemy.x, enemy.z, enemy.rotation, enemy.hand_phase, enemy.color, enemy.scale, enemy.is_slowed)

    
    for tower in game_state['towers']:
        if tower.type == 0:
            draw_tower3(tower.x,tower.z)
        elif tower.type == 1:
            draw_tower2(tower.x, tower.z)
        elif tower.type == 2:
            draw_tower1(tower.x, tower.z)
    
    for bullet in game_state['bullets']:
        draw_bullet(
            bullet['x'], bullet['z'], bullet['type'],
            height=10,
            target_x=bullet.get('target_x'),
            target_y=bullet.get('target_z'),
            time=bullet.get('time', 0)
        )
    
    if game_state['selected_tower']:
        draw_range(game_state['selected_tower'].x, game_state['selected_tower'].z, game_state['selected_tower'].range)
    
    if set_tower:
        world_x = (last_mouse_x - 500) * 1.2
        world_z = (400 - last_mouse_y) * 1.2
        range = 300 if game_state['selected_tower_type'] == 2 else 200
        valid = is_position_valid(-world_x,-world_z)
        draw_range(world_x, world_z, range, valid)

        if game_state['selected_tower_type'] == 0:
            glColor4f(1, 1, 1, 0.5)
            draw_tower3(-world_x, -world_z)
        elif game_state['selected_tower_type'] == 1:
            glColor4f(1, 1, 1, 0.5)
            draw_tower2(-world_x,-world_z)
        elif game_state['selected_tower_type'] == 2:
            glColor4f(1, 1, 1, 0.5)
            draw_tower1(-world_x, -world_z)
 
    
    draw_text(10, 770, f"Coins: {game_state['coins']}")
    draw_text(10, 740, f"Wave: {game_state['wave']}")
    draw_text(10, 710, f"Health: {game_state['health']}")
    draw_text(10, 680, f"Towers: {len(game_state['towers'])}")
    draw_text(10, 650, f"Selected: {'Cannon' if game_state['selected_tower_type'] == 0 else 'Slow' if game_state['selected_tower_type'] == 1 else 'Mortar'} (1/2/3)")
    draw_text(10, 620, f"Place: B | Upgrade: U")
    
    if game_state['game_over']:
        draw_text(400, 400, "GAME OVER - Press R to restart", GLUT_BITMAP_TIMES_ROMAN_24)
    
    glutSwapBuffers()

def idle():
    update_game()
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
    glutMouseFunc(mouseListener)
    glutMotionFunc(motionListener)
    glutPassiveMotionFunc(passiveMotionListener)
    glutIdleFunc(idle)
    
    glEnable(GL_DEPTH_TEST)
    
    glutMainLoop()

if __name__ == "__main__":
    main()