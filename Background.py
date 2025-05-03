from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import uuid

# Game constants
GRID_LENGTH = 700
TOWER_COST = [100, 300, 200,250,280]  # Costs for cannon, slow, energy,fire,ice towers
UPGRADE_COST = [50, 100, 200,150,180]
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
    'selected_tower_type': 0,  # 0=cannon, 1=slow, 2=Energy,3=Fire,4=Ice
    'select_enemy_type':0,
    'game_over': False,
    'is_slowed': False,
    'spawn_timer': 0,
    'enemies_spawned': 0,
    'enemies_per_wave': 5,
    'active_roads': 1,
    'selected_tower': None
}
selecting_tower = False
# Camera settings
camera_pos = [0, 500, 500]
camera_angle_x = 45
camera_angle_y = 0
camera_distance = 500
fovY = 120
path1 = [(700, -50), (150, -50),(150,-350),(-200,-350),(-200, 0),(-200,300),(200, 300)]
path2= [(-200, -700), (-200, 0),(-200,300),(200, 300)]
path3=[(-700,-50),(-200, -50),(-200,300),(200,300)]
all_paths = [path1, path2, path3]
game_state['road_paths'] = [path1, path2, path3]

class Tower:
    def __init__(self, x, z, tower_type):
        self.x = x
        self.z = z
        self.type = tower_type
        self.level = 1
        self.health = 100 + tower_type * 50
        self.range= [200,200,400,200,200][tower_type]
        self.damage = [20, 0, 30,20,10][tower_type]  # Cannon: 20, Slow: 0, Energy: 30,Fire: 20,Ice:10
        self.fire_rate = [0.5, 2.0, 4.2, 1.8, 3.0][tower_type]  # Cannon: fast, Slow/Mortar: 2s
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
                    else:
                        enemy.is_slowed=False
                        enemy.update_speed(1.0)                        
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
    def __init__(self):
        self.path =random.choice(all_paths[:game_state['active_roads']])  # Use path1 for all enemies
        self.current_waypoint = 0 
        self.type= 0  #0 for normal enemy 1 for boss enemey
        self.x, self.z = self.path[0]  # Start at first waypoint
        self.base_speed = [0.4, 0.1][self.type]
        self.speed =self.base_speed 
        # self.scale = [0.5, 0.4, 0.7][self.type]
        # self.color = [(10/255, 101/255, 34/255), (0, 1, 0), (0, 0, 1)][self.type]
        self.rotation = 0  # Y-axis rotation in degrees
        self.health = [100,250][self.type]
        self.hand_phase = 0.0  # Controls hand animation
        self.alive = True
        self.size = 20  # For collision detection
        self.max_health = self.health
        self.is_boss=False
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
        if self.is_slowed:
            self.speed=self.base_speed * slow_factor
        else:
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
            return False
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

def init_game():
    game_state['road_paths'] = [path1, path2, path3]

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
    global camera_angle_x, camera_angle_y, camera_distance,set_tower, selecting_tower
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
    elif key == b'4':
        game_state['selected_tower_type'] = 3
    elif key == b'5':
        game_state['selected_tower_type'] = 4
    elif key == b'z':
        if not selecting_tower and camera_distance>50:
            camera_distance -= 50
    elif key == b'x':
        if not selecting_tower and camera_distance<950:
            camera_distance += 50
    elif key == b'b':
        selecting_tower = True
        camera_angle_x, camera_angle_y = 45, 0
        camera_distance = 500
        set_tower = not set_tower
    elif key == b'u' and game_state['selected_tower']:
        tower = game_state['selected_tower']
        cost = UPGRADE_COST[tower.type]
        if game_state['coins'] >= cost:
            game_state['coins'] -= cost
            tower.level += 1
            tower.damage += 5 + tower.type * 5
            if tower.level % MAJOR_UPGRADE_LEVEL == 0:
                tower.fire_rate *= 0.8
    glutPostRedisplay()

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
    global set_tower, selecting_tower
    if button != GLUT_LEFT_BUTTON or state != GLUT_DOWN or game_state['game_over']:
        return

    world_x = -(x - 500) * 1.2
    world_z = -(400 - y) * 1.2

    # if set_tower:
    #     cost = TOWER_COST[game_state['selected_tower_type']]
    #     if game_state['coins'] >= cost:
    #         if is_position_valid(world_x, world_z):
    #             game_state['coins'] -= cost
    #             game_state['towers'].append(Tower(world_x, world_z, game_state['selected_tower_type']))
    #             set_tower = False
    # else:
    #     game_state['selected_tower'] = None
    #     for tower in game_state['towers']:
    #         dist = math.sqrt((world_x - tower.x)**2 + (world_z - tower.z)**2)
    #         if dist < 50:
    #             game_state['selected_tower'] = tower
    #             break
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
        enemy.update(current_time)
    for tower in game_state['towers']:
        tower.update(current_time, game_state['enemies'])
    
    game_state['enemies'] = [enemy for enemy in game_state['enemies'] if enemy.alive]
    
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
            if current_time - bullet['time'] < 0.8:  # Beam lasts 0.9s
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
                    enemy.burn_damage = 50
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
                    enemy.freeze_end_time = current_time + 1.2
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
def draw_range(x, z, range,tower_type,valid=True,angle=0):
    glPushMatrix()
    if tower_type == 2:  # Energy tower (line range)
        glColor4f(0.2, 0.8, 0.2, 0.3) if valid else glColor4f(0.8, 0.2, 0.2, 0.3)
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
    draw_trees(550, 50)
    draw_trees(-200, 450)
    draw_trees(-450, 250)
    draw_trees(650, 450)
    draw_trees(450, -600)
    draw_trees(500, -300)
    draw_trees(-650, 200)
    draw_trees(-400, -350)
    draw_trees(-600, 50)
    draw_trees(-500, -200)
    draw_trees(-100, -500)
    draw_trees(-100, -200)
    
    draw_rocks(600, -200)
    draw_rocks(-550, -450)
    draw_rocks(-100, 400)
    draw_rocks(200, -500)
       
    mountain(100, 100, 0)
    mountain(-100, -100, 0)
    mountain(105, 105, 23)
    mountain(80, 90, 0)
    mountain(120, 120, 0)
    mountain(150, 110, 0)
    mountain(100, 140, -10)
    mountain(-500, -600, 0)
    mountain(-350, -450, 0)
    mountain(650, 610, 0)
    mountain(500, 540, -10)
    mountain(0, 0, 0)
    mountain(50, -450, 0)
    mountain(650, -500, 0)
    mountain(-300, 300, 0)
    mountain(-550, 250, 0)
    mountain(450, 300, 0)
    
    glBegin(GL_QUADS)
    glColor3f(121/255, 166/255, 110/255)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glEnd()
    
    draw_paths()
    draw_center_tower(200, 300)

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