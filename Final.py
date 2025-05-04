from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import uuid


# Game constants
GRID_LENGTH = 700
TOWER_COST = [300, 300, 200,250,280]  # Costs for cannon, slow, energy,fire,ice towers
set_tower = False
last_mouse_x = 500
last_mouse_y = 400
PATH_WIDTH=110
selecting_tower = False
is_paused = False
# Game state
game_state = {
    'coins': 300,
    'health': 100,
    'wave': 1,
    'towers': [],
    'enemies': [],
    'bullets': [],
    'road_paths': [],
    'selected_tower_type': 0,  # 0=cannon, 1=slow, 2=Energy,3=Fire,4=Ice
    'game_over': False,
    'is_slowed': False,
    'spawn_timer': 0,
    'enemies_spawned': 0,
    'enemies_per_stage': 5,
    'active_roads' : 1,
    'selected_tower': None,
    'stage': 1,
    'stage_timer': 0,
    'available_towers': [0]  # Only cannon at start
}

# Camera settings
camera_pos = [0, 500, 500]
camera_angle_x = 45
camera_angle_y = 0
camera_distance = 500
fovY = 120



path1 = [
    (700, 0), (0, 0),(0,-300),(-300,-300),(-300, 0), (-300, 300), (350, 300)
]
path2= [
    (-300, -700), (-300, 0),(-300,300),(350, 300)
]
path3=[
    (-700,0),(-300, 0),(-300,300),(350,300)
]
all_paths = [path1, path2, path3]

game_state['road_paths'] = [path1, path2, path3]


class Tower:
    def __init__(self, x, z, tower_type):
        self.x = x
        self.z = z
        self.type = tower_type
        self.level = 1
        self.range= [300,150,250,200,200][tower_type]
        self.damage = [35, 0, 10,10,0][tower_type]  # Cannon: 20, Slow: 0, Energy: 30,Fire: 20,Ice:10
        self.fire_rate = [0.5, 1.5, 4.0, 1.8, 2.0][tower_type]  # Cannon: fast, Slow/Mortar: 2s
        self.last_shot = 0
        self.slow_factor = 0.5 if tower_type == 1 else 1.0  # Slow tower reduces speed
        self.angle = 0  # For energy tower beam direction
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
            dx = closest_enemy.x - self.x
            dz = closest_enemy.z - self.z
            dist = math.sqrt(dx*dx + dz*dz)
            if dist == 0:
                return
            dx /= dist
            dz /= dist
            self.angle=math.degrees(math.atan2(dx,dz))
            
            if self.type == 0:  # Cannon tower
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
                        enemy.update_speed(self.slow_factor)
                        
            elif self.type == 2:  # Energy
                game_state['bullets'].append({
                    'x': self.x,
                    'z': self.z,
                    'dx': dx,
                    'dz': dz,
                    'speed': 0,  # Beam is instantaneous
                    'damage': self.damage,
                    'type': self.type,
                    'distance': 0,
                    'hits_left': 1000,
                    'time': current_time
                })
            elif self.type == 3:  # Fire
                game_state['bullets'].append({
                    'x': self.x,
                    'z': self.z,
                    'dx': dx,
                    'dz': dz,
                    'speed': 8,
                    'damage': self.damage,
                    'type': self.type,
                    'distance': 0
                })
            elif self.type == 4:  # Ice
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
    def __init__(self,enemy_type,is_boss=False):
        
        if game_state['stage'] == 1:
            self.path = all_paths[0]  # path1

        elif game_state['stage'] == 2:
            self.path = all_paths[1]  # path2

        elif game_state['stage'] == 3:
            self.path = all_paths[0]  # path1

        elif game_state['stage'] == 4:
            self.path = all_paths[2]  # path3
  
        elif game_state['stage'] == 5:
            self.path = random.choice(all_paths)  # Randomly choose from all paths
        else:
            self.path = all_paths[0]  # Default to path1
        # game_state['active_roads']=self.path
        self.current_waypoint = 0 
        self.type= enemy_type  #0 for normal enemy 1 for boss enemey
        self.x, self.z = self.path[0]  # Start at first waypoint
        self.base_speed = [1, 1.5, 1][enemy_type] if not is_boss else [0.5, 0.8, 0.6][enemy_type]
        self.speed =self.base_speed 
        self.rotation = 0  # Y-axis rotation in degrees
        self.health = [150, 100, 200][enemy_type] if not is_boss else [300, 200, 350][enemy_type]
        self.hand_phase = 0.0  # Controls hand animation
        self.alive = True
        self.size = 20  # For collision detection
        self.max_health = self.health
        self.is_boss=is_boss
        self.is_slowed = False
        self.is_burn=False
        self.is_frozen= False
        self.freeze_end_time=0
        self.burn_damage = 0
        self.burn_end_time=0
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
                if abs(dx) > abs(dz):  # Primarily x-axis movement
                    self.rotation = math.degrees(math.atan2(dx, dz)) # Align negative x-axis with movement
                else:  # Primarily z-axis movement
                    if dz > 0:  # Moving up (positive z-axis)
                        self.rotation = -180  # Desired: negative z-axis (down)
                    elif dz < 0:  # Moving down (negative z-axis)
                        self.rotation = 0  # Desired: positive z-axis (up)
            
          
            
    def update_speed(self,slow_factor):
        if slow_factor < 1.0:  # Slow tower is affecting this enemy
            self.is_slowed = True
            self.speed = self.base_speed * slow_factor
        else:
            self.is_slowed = False
            self.speed = self.base_speed
            
    def update(self,current_time):
        if not self.alive or self.current_waypoint >= len(self.path) - 1:
            if self.current_waypoint >= len(self.path) - 1:
                game_state['health'] -= 10  # Damage base
                self.alive = False
            return False
        
        if self.is_frozen and current_time<self.freeze_end_time:
            return True
        
        if self.is_frozen and current_time>=self.freeze_end_time:
            self.is_frozen = False
        
        if self.is_burn and current_time >= self.burn_end_time:
            self.is_burn = False
            self.burn_damage = 0
        # Move toward next waypoint
        if self.burn_damage > 0 and current_time < self.burn_end_time:
            self.health -= self.burn_damage * 0.016  # Approx 60 FPS
            if self.health <= 0:
                self.alive = False
                return False
        elif current_time >= self.burn_end_time:
            self.is_burn = False
            
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

def enemy_monster(x, y, enemy_angle, hand_phase,is_slowed=False,is_frozen=False,is_burn=False,is_boss=False):
    glPushMatrix()
    glTranslatef(x, y, 25)
    if is_boss:
        glScalef(0.9, 0.9, 0.9)
    else:
        glScalef(0.4,0.4,0.4)
    glRotatef(enemy_angle, 0, 0, 1)
    
    
    glPushMatrix()
    if is_frozen:
        glColor3f(0.5, 0.5, 1)
    elif is_slowed:
        glColor3f(0.5, 0.5, 0.7)
    elif is_boss:
        glColor3f(0,0,0)
    elif is_burn:
        glColor3f(1, 0.2, 0.1)
    else:
        glColor3f(10/255, 101/255, 34/255)
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

def enemy_robot(x, z, enemy_angle, hand_phase,is_slowed=False,is_frozen=False,is_burn=False,is_boss=False):
    glPushMatrix()
    glTranslatef(x, z, 20)
    if is_boss:
        glScalef(0.7, 0.7, 0.7)
    else:
        glScalef(0.4,0.4,0.4)
    glRotatef(enemy_angle, 0, 0, 1)


    ### MAIN BODY (Bright Red)
    if is_frozen:
        glColor3f(0.5, 0.5, 1)
    elif is_slowed:
        glColor3f(0.5, 0.5, 0.7)
    elif is_boss:
        glColor3f(0,0,0)
    elif is_burn:
        glColor3f(1, 0.2, 0.1)
    else:
        glColor3f(0.8, 0.0, 0.0) # Bright red
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


def enemy_dog(x, y, enemy_angle, hand_phase,is_slowed=False,is_frozen=False,is_burn=False,is_boss=False):    
    glPushMatrix()
    glTranslatef(x, y, 0)
    if is_boss:
        glScalef(0.7, 0.7, 0.7)
    else:
        glScalef(0.4,0.4,0.4)
    glRotatef(enemy_angle, 0, 0, 1)
        
    # body
    glPushMatrix()
    if is_frozen:
        glColor3f(0.5, 0.5, 1)
    elif is_slowed:
        glColor3f(0.5, 0.5, 0.7)
    elif is_boss:
        glColor3f(0,0,0)
    elif is_burn:
        glColor3f(1, 0.2, 0.1)
    else:
         glColor3f(0.45, 0, 0.45)   
    glTranslatef(0,0,32)
    glScalef(0.6, 1.2, 0.7)
    glutSolidCube(40)
    glColor3f(0.65, 0, 0.65)
    glTranslatef(0,25,18)
    glutSolidSphere(8, 20, 20)
    glPopMatrix()
    
    # head
    glPushMatrix()
    glColor3f(0.65, 0, 0.65)
    glTranslatef(0,-32,50)
    glutSolidSphere(15, 20, 20)
    glPopMatrix()
    # legs
    right_angle = 120 + 60 * math.sin(hand_phase * 2 * math.pi)
    glPushMatrix()
    glColor3f(0.65, 0, 0.65)
    glTranslatef(+14,-15,37)
    glRotatef(right_angle, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 4, 1, 37, 10, 10)
    glutSolidSphere(4, 20, 20)
    glPopMatrix()
    glPushMatrix()
    glColor3f(0.65, 0, 0.65)
    glTranslatef(-14,-15,37)
    glRotatef(right_angle, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 4, 1, 37, 10, 10)
    glutSolidSphere(4, 20, 20)
    glPopMatrix()
    glPushMatrix()
    glColor3f(0.65, 0, 0.65)
    glTranslatef(+14,+15,37)
    glRotatef(right_angle, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 4, 1, 37, 10, 10)
    glutSolidSphere(4, 20, 20)
    glPopMatrix()
    glPushMatrix()
    glColor3f(0.65, 0, 0.65)
    glTranslatef(-14,+15,37)
    glRotatef(right_angle, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 4, 1, 37, 10, 10)
    glutSolidSphere(4, 20, 20)
    glPopMatrix()
    # eyes
    glPushMatrix()
    glColor3f(0, 0, 0)
    glTranslatef(+5,-45,58)
    glutSolidSphere(2, 10, 10)
    glPopMatrix()
    glPushMatrix()
    glColor3f(0, 0, 0)
    glTranslatef(-5,-45,58)
    glutSolidSphere(2, 10, 10)
    glPopMatrix()
    # ears
    glPushMatrix()
    glColor3f(0.65, 0, 0.65)
    glTranslatef(+6,-32,60)
    glutSolidCone(5, 8, 10, 10)
    glPopMatrix()
    glPushMatrix()
    glColor3f(0.65, 0, 0.65)
    glTranslatef(-6,-32,60)
    glutSolidCone(5, 8, 10, 10)
    glPopMatrix()
    
    glPopMatrix()


def init_game():
    game_state['road_paths'] = [path1, path2, path3]
    game_state['stage'] = 1  # Ensure stage starts at 1




# Energy_Tower
def Energy_tower(x, y):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glScalef(1.4,1.4,1.4)
    glColor3f(0.4, 0.4, 0.4)
    gluCylinder(gluNewQuadric(), 30, 15, 20, 32, 32)  # Match base
    glTranslatef(0, 0, 20)
    glColor3f(0.4, 0.4, 0.4)
    gluCylinder(gluNewQuadric(), 15, 15, 50, 32, 32)
    glColor3f(1, 1, 0.3)
    gluCylinder(gluNewQuadric(), 17, 17, 8, 30, 30)
    glTranslatef(0, 0, 50)
    glPushMatrix()
    glColor3f(1, 1, 0.3)
    for i in range(8):
        glPushMatrix()
        glRotatef(i * 45, 0, 0, 1)
        glTranslatef(18, 0, 0)
        glutSolidCube(7)
        glPopMatrix()
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0, 0, -8)
    glColor3f(0.3, 0.3, 0.3)
    for i in range(8):
        glPushMatrix()
        glRotatef(i * 45, 0, 0, 1)
        glTranslatef(18, 0, 8)
        glRotatef(90, 0, 1, 0)
        gluCylinder(gluNewQuadric(), 2,2, 12, 30, 30)
        glPopMatrix()
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0, 0, 5)
    glColor3f(1, 1, 0.3)
    glutSolidSphere(8, 20, 20)  
    glPopMatrix()
    glPopMatrix()
# slowtower
def Slow_tower(x, y):
    glPushMatrix()
    glColor3f(95/255, 124/255, 132/255)
    glTranslatef(x, y, 0)
    glScalef(0.8,0.8,0.8)
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
def Cannon_tower(x,y):
    
     # body
    glPushMatrix()
    glColor3f(113/255, 113/255, 113/255)
    glTranslatef(x, y, 0)
    gluCylinder(gluNewQuadric(), 30, 25, 80, 30, 30)
    glPopMatrix()
    
    # cannon sphere
    glPushMatrix()
    glColor3f(35/255, 30/255, 28/255)
    glTranslatef(x, y, 110)
    glutSolidSphere(20, 20, 20)
    glPopMatrix()
    
    # cannon barrel
    glPushMatrix()
    glColor3f(35/255, 30/255, 28/255) 
    glTranslatef(x, y, 110)
    glRotatef(90, 0, 1, 0)  # Rotate to make it horizontal
    gluCylinder(gluNewQuadric(), 8, 12, 50, 20, 20)  # Cannon barrel
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(203/255, 112/255, 29/255)  # golden cannon  ring big
    glTranslatef(x-10, y, 110)
    glRotatef(90, 0, 1, 0)
    gluCylinder(gluNewQuadric(), 20, 21, 14, 30, 30)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(203/255, 112/255, 29/255)  # golden cannon  ring small
    glTranslatef(x+18, y, 110)
    glRotatef(90, 0, 1, 0)
    gluCylinder(gluNewQuadric(),10,10,8,30, 30)
    glPopMatrix()
    
    # Top rings (black and golden)
    glPushMatrix()
    glColor3f(0,0,0)
    glTranslatef(x, y, 80)
    gluCylinder(gluNewQuadric(), 25, 33, 15, 30, 30)
    glPopMatrix()
    glPushMatrix()
    glColor3f(173/255, 178/255, 188/255)
    glTranslatef(x, y, 80)
    gluCylinder(gluNewQuadric(), 33, 33, 15, 30, 30)
    glPopMatrix()
    
    
    # lower base surrounding cylinder
    glPushMatrix()
    glColor3f(99/255, 102/255, 98/255)
    glTranslatef(x, y, 0)
    gluCylinder(gluNewQuadric(), 45, 25, 30, 30, 30)
    glPopMatrix()
    


    # Mid ring (dark band)
    glPushMatrix()
    glColor3f(0, 0, 0)  # Black ring
    glTranslatef(x, y, 23)
    gluCylinder(gluNewQuadric(), 30, 30, 8, 30, 30)
    glPopMatrix()

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

    # side blocks cannon
    glPushMatrix()
    glColor3f(121/255, 71/255, 39/255)
    glTranslatef(x-2, y-22, 103)
    glScalef(1, 0.8, 2)
    glutSolidCube(14)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(121/255, 71/255, 39/255)
    glTranslatef(x-2, y + 22, 103)
    glScalef(1, 0.5, 2)
    glutSolidCube(14)
    glPopMatrix()
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
# Fire Tower
def Fire_tower(x,y):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glColor3f(0.4, 0.4, 0.4)
    gluCylinder(gluNewQuadric(), 30, 14, 100, 30, 30)
    glColor3f(1, 0.2, 0.1)
    a = 35
    for i in range(7):
        glPushMatrix()
        glTranslatef(0, 0, i * 16)
        glRotatef(20, 0, 1, 0)
        glRotatef(90, 0, 0, 1)
        gluCylinder(gluNewQuadric(), a, a, 5, 20, 20)
        glPopMatrix()
        a -= 3
    glPopMatrix()
    glPushMatrix()
    glTranslatef(x, y, 105)
    glColor3f(0.3, 0.3, 0.3)
    for i in range(8):
        glPushMatrix()
        glRotatef(i * 45, 0, 0, 1)
        glTranslatef(10, 0, 0) 
        glutSolidCube(8)
        glPopMatrix()
    glColor3f(0.4, 0.4, 0.4)
    gluCylinder(gluNewQuadric(), 8, 2, 15, 30, 30)
    glTranslatef(0, 0, 18)
    glColor3f(1, 0.2, 0.1)
    glutSolidSphere(9, 20, 20)
    for i in range(8):
        glPushMatrix()
        glRotatef(i * 90, 0, 0, 1)
        glTranslatef(6, 0, 0)
        glRotatef(90, 0, 1, 0)
        glColor3f(0.4, 0.4, 0.4)
        gluCylinder(gluNewQuadric(), 4, 1, 30, 10, 10)
        glPopMatrix()
    glPopMatrix()
# Ice Tower
def Ice_tower(x,y):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glPushMatrix()
    glColor3f(0.6, 0.6, 0.6)
    glScalef(1.3, 1.3, 4.7)
    glutSolidCube(40)
    glPopMatrix()
    pillar_positions = [(22, 22),(-22, 22),(-22, -22),(22, -22)]
    for (px, py) in pillar_positions:
        glPushMatrix()
        glTranslatef(px, py, 0)
        glScalef(0.5, 0.5, 9)
        glColor3f(0.5, 0.8, 1.0)
        glutSolidCube(25)
        glPopMatrix()
    pillar_positions = [(24, 0),(-24, 0),(0, 24),(0, -24)]
    for (px, py) in pillar_positions:
        glPushMatrix()
        glTranslatef(px, py, 0)
        glScalef(0.5, 0.5, 8.5)
        glColor3f(0.7, 0.9, 1.0)
        glutSolidCube(25)
        glPopMatrix()
    for i in range(8):
        glPushMatrix()
        glRotatef(i * 45, 0, 0, 1)
        glTranslatef(26, 0, 120)
        glRotatef(90, 0, 1, 0)
        glColor3f(0.7, 0.95, 1.0)
        glutSolidCone(7, 20, 20, 20)
        glPopMatrix()
    glTranslatef(0, 0, 120)
    glColor3f(0.5, 0.8, 1)
    glutSolidSphere(13, 20, 20)
    glPopMatrix()

    
    

def draw_bullet(x, y, bullet_type,height=10,target_x=None,target_y=None,time=0,dx=None,dz=None):
    if bullet_type == 2:#Energy_beam
        return
    glPushMatrix()  
    if bullet_type == 0: #cannon
        glColor3f(1, 1, 0)
        glTranslatef(x, y, height)
        glutSolidSphere(5, 10, 10)
   
        # # glColor4f(1, 1, 0.3, 0.7)
        # glTranslatef(x, y, height)
        # if dx != 0 or dz != 0:
        #     angle = math.degrees(math.atan2(dx, dz))
        #     glRotatef(angle, 0, 1, 0)
        # glScalef(1, 0.1, 1)
        # gluCylinder(gluNewQuadric(), 5, 5, 400, 10, 10)
    elif bullet_type == 3:  # Fire
        glColor3f(1, 0.2, 0.1)
        glTranslatef(x, y, height)
        glutSolidSphere(7, 10, 10)
    elif bullet_type == 4:  # Ice
        glColor3f(0.5, 0.8, 1.0)
        glTranslatef(x, y, height)
        glutSolidSphere(6, 10, 10)
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
    global camera_angle_x, camera_angle_y, camera_distance,set_tower,selecting_tower
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
        game_state['enemies_per_stage'] = 5
        game_state['active_roads'] = 1
        game_state['selected_tower'] = None
        game_state['stage'] = 1  # Explicitly reset to stage 1
        game_state['available_towers'] = [0]
        game_state['stage_timer'] = 0
        init_game()
        return
    
    if game_state['game_over']:
        return
    
    if key == b'1':
        game_state['selected_tower_type'] = 0
    elif key == b'2':
        game_state['selected_tower_type'] = 1
    elif key == b'3':
        game_state['selected_tower_type'] = 2
    elif key == b'4':
        game_state['selected_tower_type'] = 3
    elif key == b'5':
        game_state['selected_tower_type'] = 4
    elif key == b'z':
        camera_distance -= 50
    elif key == b'x':
        camera_distance += 50
    elif key == b'p':
        global is_paused
        is_paused = not is_paused
    elif key == b'b':
        selecting_tower = True
        camera_angle_x, camera_angle_y = 45, 0
        camera_distance = 500
        set_tower = not set_tower
   

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
    if selecting_tower:
        return  
    if key == GLUT_KEY_UP:
        camera_angle_x = min(camera_angle_x + 5, 90)
    elif key == GLUT_KEY_DOWN:
        camera_angle_x = max(camera_angle_x - 5, 10)
    elif key == GLUT_KEY_LEFT:
        camera_angle_y = (camera_angle_y + 5) % 360
    elif key == GLUT_KEY_RIGHT:
        camera_angle_y = (camera_angle_y - 5) % 360

def mouseListener(button, state, x, y):
    global set_tower,selecting_tower
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
                selecting_tower = False
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
        
        
         # update enemies
        for enemy in game_state['enemies']:
            if not enemy.is_slowed:
                enemy.update_speed(1)  # Revert to base speed if not slowed
            enemy.update(current_time)
            
        game_state['enemies'] = [enemy for enemy in game_state['enemies'] if enemy.alive]
        
        
        # update tower

            
        for tower in game_state['towers']:
            tower.update(current_time, game_state['enemies'])
        
        
        # Stage-specific enemy spawning
        if game_state['enemies_spawned'] < game_state['enemies_per_stage']:
            if current_time - game_state['spawn_timer'] > 1.0:
                game_state['spawn_timer'] = current_time
                print(f"Stage {game_state['stage']}: Attempting to spawn enemy {game_state['enemies_spawned'] + 1}/{game_state['enemies_per_stage']}")
                if game_state['stage'] == 1:
                    enemy_type = random.choice([0, 1])  # Monster, Dog
                    game_state['enemies'].append(Enemy(enemy_type))
                elif game_state['stage'] == 2:                   
                    if game_state['enemies_spawned'] < 6:
                        enemy_type = random.choice([0, 1])
                        print(f"  Spawning normal enemy {game_state['enemies_spawned'] + 1}, type {enemy_type}")
                        game_state['enemies'].append(Enemy(enemy_type))
                    else:
                        enemy_type = random.choice([0, 1])
                        print(f"  Spawning boss enemy {game_state['enemies_spawned'] + 1}, type {enemy_type}")
                        game_state['enemies'].append(Enemy(enemy_type, is_boss=True))
                elif game_state['stage'] == 3:
                    enemy_type = random.choice([2, 1])  # Robot, Dog
                    game_state['enemies'].append(Enemy(enemy_type))
                elif game_state['stage'] == 4:
                    # 8 normal (robot) + 2 boss
                    if game_state['enemies_spawned'] < 10:
                        enemy_type = 2
                        game_state['enemies'].append(Enemy(enemy_type))
                    else:
                        enemy_type = 2
                        game_state['enemies'].append(Enemy(enemy_type, is_boss=True))
                elif game_state['stage'] == 5:
                    enemy_type = random.choice([0, 1, 2])
                    is_boss = random.choice([True, False])
                    game_state['enemies'].append(Enemy(enemy_type, is_boss))
                game_state['enemies_spawned'] += 1
                
        
        
        
       

       

        new_bullets = []
        for bullet in game_state['bullets']:
            if bullet['type'] == 0:  # Cannon
                bullet['x'] += bullet['dx'] * bullet['speed']
                bullet['z'] += bullet['dz'] * bullet['speed']
                bullet['distance'] += bullet['speed']
                hit = False
                for enemy in game_state['enemies']:
                    dist = math.sqrt((bullet['x'] - enemy.x)**2 + (bullet['z'] - enemy.z)**2)
                    if dist < enemy.size:
                        enemy.health -= bullet['damage']
                        hit = True
                        break
                if not hit and bullet['distance'] < 500:
                    new_bullets.append(bullet)
            elif bullet['type'] == 2:  # Energy beam
                if current_time - bullet['time'] < 0.2:  # Beam lasts 0.9s
                    hits = []
                    for enemy in game_state['enemies']:
                        px = enemy.x - bullet['x']
                        py = enemy.z - bullet['z']
                        proj = px * bullet['dx'] + py * bullet['dz']
                        if proj > 0:
                            perp_dist = abs(px * bullet['dz'] - py * bullet['dx'])
                            if perp_dist < enemy.size and bullet['hits_left'] > 0:
                                enemy.health -= bullet['damage']
                                bullet['hits_left'] -= 1
                                hits.append(enemy)
                    if bullet['hits_left'] > 0:
                        new_bullets.append(bullet)
                else:
                    bullet['distance'] = 400
            elif bullet['type'] == 3:  # Fire
                bullet['x'] += bullet['dx'] * bullet['speed']
                bullet['z'] += bullet['dz'] * bullet['speed']
                bullet['distance'] += bullet['speed']
                hit = False
                for enemy in game_state['enemies']:
                    dist = math.sqrt((bullet['x'] - enemy.x)**2 + (bullet['z'] - enemy.z)**2)
                    if dist < enemy.size:
                        enemy.health -= bullet['damage']
                        enemy.is_burn=True
                        enemy.burn_damage = 12
                        enemy.burn_end_time = current_time + 3.0
                        hit = True
                        break
                if not hit and bullet['distance'] < 500:
                    new_bullets.append(bullet)
            elif bullet['type'] == 4:  # Ice
                bullet['x'] += bullet['dx'] * bullet['speed']
                bullet['z'] += bullet['dz'] * bullet['speed']
                bullet['distance'] += bullet['speed']
                hit = False
                for enemy in game_state['enemies']:
                    dist = math.sqrt((bullet['x'] - enemy.x)**2 + (bullet['z'] - enemy.z)**2)
                    if dist < enemy.size:
                        enemy.health -= bullet['damage']
                        enemy.is_frozen = True
                        enemy.freeze_end_time = current_time + 1.5
                        hit = True
                        break
                if not hit and bullet['distance'] < 500:
                    new_bullets.append(bullet)
        
        game_state['bullets'] = new_bullets
        # Reward coins for killed enemies
        for enemy in game_state['enemies'][:]:
            if enemy.health <= 0:
                game_state['enemies'].remove(enemy)
                # game_state['coins'] += 20 if game_state['stage'] <= 2 else (30 if game_state['stage'] == 3 else 40 if game_state['stage'] == 4 else 50)

        # Stage progression  
        if game_state['enemies_spawned'] >= game_state['enemies_per_stage'] and len(game_state['enemies']) == 0:
            if game_state['stage_timer'] == 0:
                game_state['stage_timer'] = current_time
                print(f"Stage {game_state['stage']}: All enemies spawned, starting 10s timer")
            elif current_time - game_state['stage_timer'] > 10.0:
                print(f"Stage {game_state['stage']}: Advancing to stage {game_state['stage'] + 1}")
                # current_time - game_state['stage_timer'] > 10.0:  # 10-second delay between stages
                game_state['stage'] += 1
                print(f"Stage {game_state['stage']}: All enemies spawned, starting 10s timer")
                game_state['enemies_spawned'] = 0
                game_state['stage_timer'] = current_time
                if game_state['stage'] == 2:
                    game_state['enemies_per_stage'] = 8
                    game_state['available_towers'] = [0, 1, 4]
                    game_state['coins'] += 150
                elif game_state['stage'] == 3:
                    game_state['enemies_per_stage'] = 10
                    game_state['available_towers'] = [0, 1, 4]
                    game_state['coins'] += 210
                elif game_state['stage'] == 4:
                    game_state['enemies_per_stage'] = 15
                    game_state['available_towers'] = [0, 1, 2, 4]
                    game_state['coins'] += 240
                elif game_state['stage'] == 5:
                    game_state['enemies_per_stage'] = 20
                    game_state['available_towers'] = [0, 1, 2, 3, 4]
                    game_state['coins'] += 300
                elif game_state['stage'] > 5:
                    game_state['game_over'] = True  # Game ends after stage 5

        if game_state['health'] <= 0:
            game_state['game_over'] = True



    

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



def draw_mountain(x, y, z):
    glPushMatrix()
    glTranslatef(x, y, z)  # Base position of the mountain
    
    # Define the relative offsets for each cube pair

    offsets = [
        (0, 0, 0),    # First pair
        (5, 5, 23),   # Second pair
        (-20, -10, 0),# Third pair
        (20, 20, 0),  # Fourth pair
        (50, 10, 0),  # Fifth pair
        (0, 40, -10),  # Sixth pair
        (-25,15,0),
        (-30,30,0),
        (40,-20,0),
        
    ]
    
    for (dx, dy, dz) in offsets:
        # First cube
        glPushMatrix()
        glTranslatef(dx, dy, dz)
        glColor3f(125/255, 109/255, 79/255)
        glutSolidCube(40)
        glPopMatrix()
        
        # Second cube (offset by +8 in z)
        glPushMatrix()
        glTranslatef(dx, dy, dz + 8)
        glColor3f(67/255, 94/255, 54/255)
        glutSolidCube(40)
        glPopMatrix()
    
    glPopMatrix()

def draw_range(x, z, range,tower_type,valid=True,angle=0):
    glPushMatrix()
    if tower_type == 2:  # Energy tower (line range)
        # glColor4f(0.2, 0.8, 0.2, 0.3) if valid else glColor4f(0.8, 0.2, 0.2, 0.3)
        glTranslatef(-x, -z, 0)
        glRotatef(angle, 0, 0, 1)
        glScalef(1, 0.1, 1)
        gluCylinder(gluNewQuadric(), 10, 10, range, 30, 30)
    else:  # Circular range for other towers
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
    draw_trees(-650, 300)
    draw_trees(-580, 600)
    draw_trees(-500, -500)
    draw_trees(450, 250)
    draw_trees(-100, 200)
    draw_trees(500, -200)
    draw_trees(550, 150)
    draw_trees(-200, 450)
    draw_trees(-450, 250)
    draw_trees(650, 450)
    draw_trees(450, -600)
    draw_trees(500, -300)
    draw_trees(-650, 200)
    draw_trees(-400, -350)
    draw_trees(-600, 150)
    draw_trees(-500, -200)
    draw_trees(-100, -500)
    draw_trees(-100, -200)
    
    draw_rocks(200, -100)
    draw_rocks(-500, -100)
    draw_rocks(250, 100)
    draw_rocks(200, 600)
    
    draw_rocks(300, -300)
       
    # draw_mountain(100, 100, 0)
    
   
    draw_mountain(-500, -600, 0)
    draw_mountain(-520, -520, 0)
    draw_mountain(-540,-560, 0)
    draw_mountain(-550, -480, 0)
    draw_mountain(-530, -610, 0)
    draw_mountain(-570, -580, 0)
    draw_mountain(-575, -520, 0)
    
    
    
    draw_mountain(300, -300, 0)        # Main center mountain
    draw_mountain(330, -280, 0)        # Slightly northeast
    draw_mountain(270, -320, 0)        # Slightly southwest  
    draw_mountain(340, -330, 0)        # Southeast
    draw_mountain(280, -270, 0)        # Northwest
    draw_mountain(400, -300, 0)        # East
    draw_mountain(250, -300, 0)        # West
    
    
    
    
    

    
    glBegin(GL_QUADS)
    glColor3f(121/255, 166/255, 110/255)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glEnd()
    
    draw_paths()
    draw_center_tower(350,300)  
    
    for enemy in game_state['enemies']:
        if enemy.type == 0:
            enemy_monster(enemy.x, enemy.z, enemy.rotation, enemy.hand_phase,enemy.is_slowed,enemy.is_frozen,enemy.is_burn,enemy.is_boss)
        elif enemy.type == 1:
            enemy_dog(enemy.x, enemy.z, enemy.rotation, enemy.hand_phase,enemy.is_slowed,enemy.is_frozen,enemy.is_burn,enemy.is_boss)
        elif enemy.type == 2:
            enemy_robot(enemy.x, enemy.z, enemy.rotation, enemy.hand_phase,enemy.is_slowed,enemy.is_frozen,enemy.is_burn,enemy.is_boss)
        
    
    for tower in game_state['towers']:
        if tower.type == 0:
            Cannon_tower(tower.x,tower.z)
        elif tower.type == 1:
            Slow_tower(tower.x, tower.z)
        elif tower.type == 2:
            Energy_tower(tower.x, tower.z)
        elif tower.type == 3:
            Fire_tower(tower.x, tower.z)
        elif tower.type == 4:
            Ice_tower(tower.x, tower.z)
    for bullet in game_state['bullets']:
        draw_bullet(
            bullet['x'], bullet['z'], bullet['type'],
            height=10,
            dx=bullet.get('dx'),
            dz=bullet.get('dz'),
            time=bullet.get('time', 0)
        )
    
    if game_state['selected_tower']:
        draw_range(
            game_state['selected_tower'].x, game_state['selected_tower'].z,
            game_state['selected_tower'].range, game_state['selected_tower'].type,
            angle=game_state['selected_tower'].angle
        )
    if set_tower:
        world_x = (last_mouse_x - 500) * 1.2
        world_z = (400 - last_mouse_y) * 1.2
        range = [200, 200, 400, 200, 200][game_state['selected_tower_type']]
        angle=0
        valid = is_position_valid(-world_x,-world_z)
        
        if game_state['selected_tower_type'] == 2:
            closest_enemy = None
            min_dist = float('inf')
            for enemy in game_state['enemies']:
                dist = math.sqrt((world_x - enemy.x)**2 + (world_z - enemy.z)**2)
                if dist < range and dist < min_dist:
                    min_dist = dist
                    closest_enemy = enemy
            if closest_enemy:
                dx = closest_enemy.x - world_x
                dz = closest_enemy.z - world_z
                dist = math.sqrt(dx*dx + dz*dz)
                if dist > 0:
                    angle = math.degrees(math.atan2(dx, dz))
        
        draw_range(world_x, world_z, range, valid)
        glColor4f(1, 1, 1, 0.5)
        if game_state['selected_tower_type'] == 0:
            Cannon_tower(-world_x, -world_z)
        elif game_state['selected_tower_type'] == 1:
            Slow_tower(-world_x,-world_z)
        elif game_state['selected_tower_type'] == 2:
            Energy_tower(-world_x, -world_z)
        elif game_state['selected_tower_type'] == 3:
            Fire_tower(-world_x, -world_z)
        elif game_state['selected_tower_type'] == 4:
            Ice_tower(-world_x, -world_z)
 
    
    draw_text(10, 770, f"Coins: {game_state['coins']}")
    draw_text(10, 740, f"Wave: {game_state['stage']}")
    draw_text(10, 710, f"Health: {game_state['health']}")
    draw_text(10, 680, f"Selected: {'Cannon' if game_state['selected_tower_type'] == 0 else 'Slow' if game_state['selected_tower_type'] == 1 else 'Energy' if game_state['selected_tower_type'] == 2 else 'Fire' if game_state['selected_tower_type'] == 3 else 'Ice'} (1-5)")
    draw_text(10, 650, f"Place Tower: B")
    draw_text(10, 620, f"Pause: P")
    
    
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
