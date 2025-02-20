import pygame
import sys
import json
import random
import noise
from typing import List, Dict, Tuple

pygame.init()

WINDOW_SIZE = (800, 600)
TILE_SIZE = 32
PLAYER_SIZE = (32, 48)
GRAVITY = 0.5
JUMP_FORCE = -10
MOVE_SPEED = 5
CHUNK_SIZE = 16
RENDER_DISTANCE = 2

BLACK = (0, 0, 0)
SKY_BLUE = (135, 206, 235)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
WHITE = (255, 255, 255)
GREEN = (34, 139, 34)
BLUE = (0, 0, 255)
DARK_BROWN = (101, 67, 33)
LIGHT_BLUE = (173, 216, 230)
SAND_COLOR = (194, 178, 128)

class Player:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.vel_y = 0
        self.jumping = False
        self.rect = pygame.Rect(x, y, PLAYER_SIZE[0], PLAYER_SIZE[1])
        
    def move(self, dx: int, blocks: List[pygame.Rect]):
        self.x += dx
        self.rect.x = self.x
        for block in blocks:
            if self.rect.colliderect(block):
                if dx > 0:
                    self.rect.right = block.left
                    self.x = self.rect.x
                elif dx < 0:
                    self.rect.left = block.right
                    self.x = self.rect.x

    def apply_gravity(self, blocks: List[pygame.Rect]):
        self.vel_y += GRAVITY
        self.y += self.vel_y
        self.rect.y = self.y
        
        for block in blocks:
            if self.rect.colliderect(block):
                if self.vel_y > 0:
                    self.rect.bottom = block.top
                    self.y = self.rect.y
                    self.vel_y = 0
                    self.jumping = False
                elif self.vel_y < 0:
                    self.rect.top = block.bottom
                    self.y = self.rect.y
                    self.vel_y = 0

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("2D Building Game")
        self.clock = pygame.time.Clock()
        self.player = Player(WINDOW_SIZE[0]//2, 100)
        self.blocks = {}
        self.camera_x = 0
        self.generated_chunks = set()  # Keep track of generated chunks
        self.block_types = {
            0: BROWN,
            1: GRAY,
            2: GREEN,
            3: DARK_BROWN,
            4: GREEN,
            5: LIGHT_BLUE,
            6: SAND_COLOR
        }
        self.block_names = {
            0: "Dirt",
            1: "Stone",
            2: "Grass",
            3: "Wood",
            4: "Leaves",
            5: "Water",
            6: "Sand"
        }
        self.selected_block = 0
        self.font = pygame.font.Font(None, 36)
        
        # Generate initial chunks
        self.generate_initial_chunks()

    def get_chunk_key(self, x):
        return int(x // (CHUNK_SIZE * TILE_SIZE))

    def generate_initial_chunks(self):
        player_chunk = self.get_chunk_key(self.player.x)
        for chunk_x in range(player_chunk - RENDER_DISTANCE, player_chunk + RENDER_DISTANCE + 1):
            self.generate_chunk(chunk_x)

    def generate_chunk(self, chunk_x):
        if chunk_x in self.generated_chunks:
            return

        self.generated_chunks.add(chunk_x)
        start_x = chunk_x * CHUNK_SIZE * TILE_SIZE
        scale = 50.0
        octaves = 6
        persistence = 0.5
        lacunarity = 2.0

        for x in range(start_x, start_x + CHUNK_SIZE * TILE_SIZE, TILE_SIZE):
            nx = x / 1000.0
            height = noise.pnoise1(nx * scale, octaves=octaves, persistence=persistence, lacunarity=lacunarity)
            height = (height + 1) / 2
            height = int(height * (WINDOW_SIZE[1] / 2)) + WINDOW_SIZE[1] // 3

            for y in range(height, WINDOW_SIZE[1], TILE_SIZE):
                block_type = 0
                if y == height:
                    block_type = 2
                elif y < height + 3 * TILE_SIZE:
                    block_type = 0
                else:
                    block_type = 1

                block = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                self.blocks[(x, y)] = (block, block_type)

                if random.random() < 0.1 and height < WINDOW_SIZE[1] - 5 * TILE_SIZE:
                    structure = random.choice(['tree', 'house'])
                    if structure == 'tree':
                        self.generate_tree(x, height)
                    else:
                        self.generate_house(x, height)

    def generate_house(self, x, ground_height):
        width = 5 * TILE_SIZE
        height = 4 * TILE_SIZE
        
        for wall_x in range(x, x + width, TILE_SIZE):
            for wall_y in range(ground_height - height, ground_height, TILE_SIZE):
                block = pygame.Rect(wall_x, wall_y, TILE_SIZE, TILE_SIZE)
                self.blocks[(wall_x, wall_y)] = (block, 1)
        
        door_x = x + (width // 2)
        door_y = ground_height - 2 * TILE_SIZE
        for dy in range(2):
            block = pygame.Rect(door_x, door_y + dy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            self.blocks[(door_x, door_y + dy * TILE_SIZE)] = (block, 3)
        
        window_y = ground_height - 3 * TILE_SIZE
        for window_x in [x + TILE_SIZE, x + width - 2 * TILE_SIZE]:
            block = pygame.Rect(window_x, window_y, TILE_SIZE, TILE_SIZE)
            self.blocks[(window_x, window_y)] = (block, 5)

    def generate_tree(self, x, ground_height):
        trunk_height = random.randint(3, 5)
        for y in range(ground_height - trunk_height * TILE_SIZE, ground_height, TILE_SIZE):
            block = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            self.blocks[(x, y)] = (block, 3)

        for i in range(-2, 3):
            for j in range(-2, 1):
                leaf_x = x + i * TILE_SIZE
                leaf_y = ground_height - (trunk_height + abs(j)) * TILE_SIZE
                if leaf_y > 0:
                    block = pygame.Rect(leaf_x, leaf_y, TILE_SIZE, TILE_SIZE)
                    self.blocks[(leaf_x, leaf_y)] = (block, 4)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.player.move(-MOVE_SPEED, [b[0] for b in self.blocks.values()])
            self.camera_x = self.player.x - WINDOW_SIZE[0]//2
        if keys[pygame.K_d]:
            self.player.move(MOVE_SPEED, [b[0] for b in self.blocks.values()])
            self.camera_x = self.player.x - WINDOW_SIZE[0]//2
        if (keys[pygame.K_w] or keys[pygame.K_SPACE]) and not self.player.jumping:
            self.player.vel_y = JUMP_FORCE
            self.player.jumping = True

        # Generate new chunks as needed
        player_chunk = self.get_chunk_key(self.player.x)
        for chunk_x in range(player_chunk - RENDER_DISTANCE, player_chunk + RENDER_DISTANCE + 1):
            self.generate_chunk(chunk_x)

        # Handle mouse scroll for block rotation
        for event in pygame.event.get(pygame.MOUSEWHEEL):
            self.selected_block = (self.selected_block + event.y) % len(self.block_types)
            
        # Handle mouse input for building/mining
        if pygame.mouse.get_pressed()[0]:  # Left click to place blocks
            pos = pygame.mouse.get_pos()
            block_x = ((pos[0] + self.camera_x) // TILE_SIZE) * TILE_SIZE
            block_y = (pos[1] // TILE_SIZE) * TILE_SIZE
            new_block = pygame.Rect(block_x, block_y, TILE_SIZE, TILE_SIZE)
            if not any(b[0].colliderect(new_block) for b in self.blocks.values()):
                self.blocks[(block_x, block_y)] = (new_block, self.selected_block)
                
        if pygame.mouse.get_pressed()[2]:  # Right click to remove blocks
            pos = pygame.mouse.get_pos()
            screen_x = pos[0] + self.camera_x
            screen_y = pos[1]
            for (x, y), (block, block_type) in list(self.blocks.items()):
                if block.collidepoint(screen_x, screen_y):
                    del self.blocks[(x, y)]

    def draw(self):
        self.screen.fill(SKY_BLUE)
        
        for (x, y), (block, block_type) in self.blocks.items():
            screen_x = x - self.camera_x
            if -TILE_SIZE <= screen_x <= WINDOW_SIZE[0]:
                screen_rect = pygame.Rect(screen_x, block.y, TILE_SIZE, TILE_SIZE)
                color = self.block_types[block_type]
                pygame.draw.rect(self.screen, color, screen_rect)
                
                if block_type == 2:
                    pygame.draw.line(self.screen, GREEN, (screen_x, block.y), 
                                   (screen_x + TILE_SIZE, block.y), 3)
                elif block_type == 3:
                    pygame.draw.line(self.screen, BLACK, (screen_x + TILE_SIZE//2, block.y), 
                                   (screen_x + TILE_SIZE//2, block.y + TILE_SIZE), 1)
                elif block_type == 4:
                    pygame.draw.circle(self.screen, DARK_BROWN, 
                                     (screen_x + TILE_SIZE//2, block.y + TILE_SIZE//2), 2)
                
                pygame.draw.rect(self.screen, BLACK, screen_rect, 1)
        
        player_screen_x = self.player.x - self.camera_x
        player_screen_rect = pygame.Rect(player_screen_x, self.player.rect.y,
                                        self.player.rect.width, self.player.rect.height)
        pygame.draw.rect(self.screen, (255, 0, 0), player_screen_rect)
        
        toolbar_text = f"Selected Block: {self.block_names[self.selected_block]}"
        text_surface = self.font.render(toolbar_text, True, BLACK)
        self.screen.blit(text_surface, (10, 10))
        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7]:
                        self.selected_block = event.key - pygame.K_1  # Convert key to block index

            self.handle_input()
            self.player.apply_gravity([b[0] for b in self.blocks.values()])
            self.draw()
            self.clock.tick(60)

if __name__ == "__main__":
    game = Game()
    game.run()
GRAY = (128, 128, 128)
WHITE = (255, 255, 255)
GREEN = (34, 139, 34)
BLUE = (0, 0, 255)
DARK_BROWN = (101, 67, 33)
LIGHT_BLUE = (173, 216, 230)
SAND_COLOR = (194, 178, 128)

class Player:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.vel_y = 0
        self.jumping = False
        self.rect = pygame.Rect(x, y, PLAYER_SIZE[0], PLAYER_SIZE[1])
        
    def move(self, dx: int, blocks: List[pygame.Rect]):
        self.x += dx
        self.rect.x = self.x
        for block in blocks:
            if self.rect.colliderect(block):
                if dx > 0:
                    self.rect.right = block.left
                    self.x = self.rect.x
                elif dx < 0:
                    self.rect.left = block.right
                    self.x = self.rect.x

    def apply_gravity(self, blocks: List[pygame.Rect]):
        self.vel_y += GRAVITY
        self.y += self.vel_y
        self.rect.y = self.y
        
        for block in blocks:
            if self.rect.colliderect(block):
                if self.vel_y > 0:
                    self.rect.bottom = block.top
                    self.y = self.rect.y
                    self.vel_y = 0
                    self.jumping = False
                elif self.vel_y < 0:
                    self.rect.top = block.bottom
                    self.y = self.rect.y
                    self.vel_y = 0

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("2D Building Game")
        self.clock = pygame.time.Clock()
        self.player = Player(WINDOW_SIZE[0]//2, 100)
        self.blocks = {}
        self.camera_x = 0
        self.generated_chunks = set()  # Keep track of generated chunks
        self.block_types = {
            0: BROWN,
            1: GRAY,
            2: GREEN,
            3: DARK_BROWN,
            4: GREEN,
            5: LIGHT_BLUE,
            6: SAND_COLOR
        }
        self.block_names = {
            0: "Dirt",
            1: "Stone",
            2: "Grass",
            3: "Wood",
            4: "Leaves",
            5: "Water",
            6: "Sand"
        }
        self.selected_block = 0
        self.font = pygame.font.Font(None, 36)
        
        # Generate terrain
        self.generate_terrain()

    def generate_terrain(self):
        # Generate terrain using Perlin noise
        scale = 50.0
        octaves = 6
        persistence = 0.5
        lacunarity = 2.0

        for x in range(0, WINDOW_SIZE[0], TILE_SIZE):
            # Generate height using Perlin noise
            nx = x/WINDOW_SIZE[0]
            height = noise.pnoise1(nx * scale, octaves=octaves, persistence=persistence, lacunarity=lacunarity)
            height = (height + 1) / 2  # Normalize to 0-1
            height = int(height * (WINDOW_SIZE[1] / 2)) + WINDOW_SIZE[1] // 3

            # Create terrain column
            for y in range(height, WINDOW_SIZE[1], TILE_SIZE):
                block_type = 0  # Dirt by default
                if y == height:
                    block_type = 2  # Grass on top
                elif y < height + 3 * TILE_SIZE:
                    block_type = 0  # Dirt near surface
                else:
                    block_type = 1  # Stone deeper down

                block = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                self.blocks.append((block, block_type))

            # Generate trees randomly
            if random.random() < 0.1 and height < WINDOW_SIZE[1] - 5 * TILE_SIZE:  # 10% chance for a tree
                self.generate_tree(x, height)

    def generate_tree(self, x, ground_height):
        # Tree trunk
        trunk_height = random.randint(3, 5)
        for y in range(ground_height - trunk_height * TILE_SIZE, ground_height, TILE_SIZE):
            block = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            self.blocks.append((block, 3))  # Wood

        # Tree leaves
        for i in range(-2, 3):
            for j in range(-2, 1):
                leaf_x = x + i * TILE_SIZE
                leaf_y = ground_height - (trunk_height + abs(j)) * TILE_SIZE
                if 0 <= leaf_x < WINDOW_SIZE[0] and leaf_y > 0:
                    block = pygame.Rect(leaf_x, leaf_y, TILE_SIZE, TILE_SIZE)
                    self.blocks.append((block, 4))  # Leaves

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.player.move(-MOVE_SPEED, [b[0] for b in self.blocks.values()])
            self.camera_x = self.player.x - WINDOW_SIZE[0]//2
        if keys[pygame.K_d]:
            self.player.move(MOVE_SPEED, [b[0] for b in self.blocks.values()])
            self.camera_x = self.player.x - WINDOW_SIZE[0]//2
        if (keys[pygame.K_w] or keys[pygame.K_SPACE]) and not self.player.jumping:
            self.player.vel_y = JUMP_FORCE
            self.player.jumping = True

        # Generate new chunks as needed
        player_chunk = self.get_chunk_key(self.player.x)
        for chunk_x in range(player_chunk - RENDER_DISTANCE, player_chunk + RENDER_DISTANCE + 1):
            self.generate_chunk(chunk_x)

        # Handle mouse scroll for block rotation
        for event in pygame.event.get(pygame.MOUSEWHEEL):
            self.selected_block = (self.selected_block + event.y) % len(self.block_types)
            
        # Handle mouse input for building/mining
        if pygame.mouse.get_pressed()[0]:  # Left click to place blocks
            pos = pygame.mouse.get_pos()
            block_x = ((pos[0] + self.camera_x) // TILE_SIZE) * TILE_SIZE
            block_y = (pos[1] // TILE_SIZE) * TILE_SIZE
            new_block = pygame.Rect(block_x, block_y, TILE_SIZE, TILE_SIZE)
            if not any(b[0].colliderect(new_block) for b in self.blocks.values()):
                self.blocks[(block_x, block_y)] = (new_block, self.selected_block)
                
        if pygame.mouse.get_pressed()[2]:  # Right click to remove blocks
            pos = pygame.mouse.get_pos()
            screen_x = pos[0] + self.camera_x
            screen_y = pos[1]
            for (x, y), (block, block_type) in list(self.blocks.items()):
                if block.collidepoint(screen_x, screen_y):
                    del self.blocks[(x, y)]

    def draw(self):
        self.screen.fill(SKY_BLUE)
        
        # Draw blocks
        for block, block_type in self.blocks:
            color = self.block_types[block_type]
            pygame.draw.rect(self.screen, color, block)
            
            # Add texture details based on block type
            if block_type == 2:  # Grass
                pygame.draw.line(self.screen, GREEN, (block.x, block.y), (block.x + TILE_SIZE, block.y), 3)
            elif block_type == 3:  # Wood
                pygame.draw.line(self.screen, BLACK, (block.x + TILE_SIZE//2, block.y), 
                               (block.x + TILE_SIZE//2, block.y + TILE_SIZE), 1)
            elif block_type == 4:  # Leaves
                pygame.draw.circle(self.screen, DARK_BROWN, 
                                 (block.x + TILE_SIZE//2, block.y + TILE_SIZE//2), 2)
            
            pygame.draw.rect(self.screen, BLACK, block, 1)
        
        # Draw player
        pygame.draw.rect(self.screen, (255, 0, 0), self.player.rect)
        
        # Draw toolbar
        toolbar_text = f"Selected Block: {self.block_names[self.selected_block]}"
        text_surface = self.font.render(toolbar_text, True, BLACK)
        self.screen.blit(text_surface, (10, 10))

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7]:
                        self.selected_block = event.key - pygame.K_1  # Convert key to block index

            self.handle_input()
            self.player.apply_gravity([b[0] for b in self.blocks])
            self.draw()
            self.clock.tick(60)
            pygame.display.flip()  # Add this line to update the display

if __name__ == "__main__":
    game = Game()
    game.run()

class Player:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.vel_y = 0
        self.jumping = False
        self.rect = pygame.Rect(x, y, PLAYER_SIZE[0], PLAYER_SIZE[1])
        
    def move(self, dx: int, blocks: List[pygame.Rect]):
        self.x += dx
        self.rect.x = self.x
        for block in blocks:
            if self.rect.colliderect(block):
                if dx > 0:
                    self.rect.right = block.left
                    self.x = self.rect.x
                elif dx < 0:
                    self.rect.left = block.right
                    self.x = self.rect.x

    def apply_gravity(self, blocks: List[pygame.Rect]):
        self.vel_y += GRAVITY
        self.y += self.vel_y
        self.rect.y = self.y
        
        for block in blocks:
            if self.rect.colliderect(block):
                if self.vel_y > 0:
                    self.rect.bottom = block.top
                    self.y = self.rect.y
                    self.vel_y = 0
                    self.jumping = False
                elif self.vel_y < 0:
                    self.rect.top = block.bottom
                    self.y = self.rect.y
                    self.vel_y = 0

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("2D Building Game")
        self.clock = pygame.time.Clock()
        self.player = Player(100, 100)
        self.blocks: List[pygame.Rect] = []
        self.block_types = {
            0: BROWN,
            1: GRAY,
            2: GREEN,
            3: DARK_BROWN,
            4: GREEN,
            5: LIGHT_BLUE,
            6: SAND_COLOR
        }
        self.block_names = {
            0: "Dirt",
            1: "Stone",
            2: "Grass",
            3: "Wood",
            4: "Leaves",
            5: "Water",
            6: "Sand"
        }
        self.selected_block = 0
        self.font = pygame.font.Font(None, 36)
        
        # Generate terrain
        self.generate_terrain()

    def generate_terrain(self):
        # Generate terrain using Perlin noise
        scale = 50.0
        octaves = 6
        persistence = 0.5
        lacunarity = 2.0

        for x in range(0, WINDOW_SIZE[0], TILE_SIZE):
            # Generate height using Perlin noise
            nx = x/WINDOW_SIZE[0]
            height = noise.pnoise1(nx * scale, octaves=octaves, persistence=persistence, lacunarity=lacunarity)
            height = (height + 1) / 2  # Normalize to 0-1
            height = int(height * (WINDOW_SIZE[1] / 2)) + WINDOW_SIZE[1] // 3

            # Create terrain column
            for y in range(height, WINDOW_SIZE[1], TILE_SIZE):
                block_type = 0  # Dirt by default
                if y == height:
                    block_type = 2  # Grass on top
                elif y < height + 3 * TILE_SIZE:
                    block_type = 0  # Dirt near surface
                else:
                    block_type = 1  # Stone deeper down

                block = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                self.blocks.append((block, block_type))

            # Generate trees randomly
            if random.random() < 0.1 and height < WINDOW_SIZE[1] - 5 * TILE_SIZE:  # 10% chance for a tree
                self.generate_tree(x, height)

    def generate_tree(self, x, ground_height):
        # Tree trunk
        trunk_height = random.randint(3, 5)
        for y in range(ground_height - trunk_height * TILE_SIZE, ground_height, TILE_SIZE):
            block = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            self.blocks.append((block, 3))  # Wood

        # Tree leaves
        for i in range(-2, 3):
            for j in range(-2, 1):
                leaf_x = x + i * TILE_SIZE
                leaf_y = ground_height - (trunk_height + abs(j)) * TILE_SIZE
                if 0 <= leaf_x < WINDOW_SIZE[0] and leaf_y > 0:
                    block = pygame.Rect(leaf_x, leaf_y, TILE_SIZE, TILE_SIZE)
                    self.blocks.append((block, 4))  # Leaves

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.player.move(-MOVE_SPEED, [b[0] for b in self.blocks])
        if keys[pygame.K_d]:
            self.player.move(MOVE_SPEED, [b[0] for b in self.blocks])
        if (keys[pygame.K_w] or keys[pygame.K_SPACE]) and not self.player.jumping:
            self.player.vel_y = JUMP_FORCE
            self.player.jumping = True

        # Handle mouse scroll for block rotation
        for event in pygame.event.get(pygame.MOUSEWHEEL):
            self.selected_block = (self.selected_block + event.y) % len(self.block_types)
            
        # Handle mouse input for building/mining
        if pygame.mouse.get_pressed()[0]:  # Left click to place blocks
            pos = pygame.mouse.get_pos()
            block_x = (pos[0] // TILE_SIZE) * TILE_SIZE
            block_y = (pos[1] // TILE_SIZE) * TILE_SIZE
            new_block = pygame.Rect(block_x, block_y, TILE_SIZE, TILE_SIZE)
            if not any(block.colliderect(new_block) for block in self.blocks):
                self.blocks.append(new_block)
                
        if pygame.mouse.get_pressed()[2]:  # Right click to remove blocks
            pos = pygame.mouse.get_pos()
            for block in self.blocks[:]:
                if block.collidepoint(pos):
                    self.blocks.remove(block)

    def draw(self):
        self.screen.fill(SKY_BLUE)
        
        # Draw blocks
        for block, block_type in self.blocks:
            color = self.block_types[block_type]
            pygame.draw.rect(self.screen, color, block)
            
            # Add texture details based on block type
            if block_type == 2:  # Grass
                pygame.draw.line(self.screen, GREEN, (block.x, block.y), (block.x + TILE_SIZE, block.y), 3)
            elif block_type == 3:  # Wood
                pygame.draw.line(self.screen, BLACK, (block.x + TILE_SIZE//2, block.y), 
                               (block.x + TILE_SIZE//2, block.y + TILE_SIZE), 1)
            elif block_type == 4:  # Leaves
                pygame.draw.circle(self.screen, DARK_BROWN, 
                                 (block.x + TILE_SIZE//2, block.y + TILE_SIZE//2), 2)
            
            pygame.draw.rect(self.screen, BLACK, block, 1)
        
        # Draw player
        pygame.draw.rect(self.screen, (255, 0, 0), self.player.rect)
        
        # Draw toolbar
        toolbar_text = f"Selected Block: {self.block_names[self.selected_block]}"
        text_surface = self.font.render(toolbar_text, True, BLACK)
        self.screen.blit(text_surface, (10, 10))
        
        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7]:
                        self.selected_block = event.key - pygame.K_1  # Convert key to block index

            self.handle_input()
            self.player.apply_gravity([b[0] for b in self.blocks])
            self.draw()
            self.clock.tick(60)

if __name__ == "__main__":
    game = Game()
    game.run()
