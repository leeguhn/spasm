import pygame, random, sys
from muscle_network import Tissue
from scatterplot import Scatterplot

class MuscleGUI:
    def __init__(self):
        pygame.init()
        pygame.key.set_repeat(0, 1000)
        self.width, self.height = 1200, 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption('Muscle ↔ Scatterplot')
        self.clock = pygame.time.Clock()
        self.running = True

        # Core engine
        self.muscle_mapping = {k: i for i, k in enumerate("qwertyuiopasdfghjklzxcvbnm")}
        self.network = Tissue(num_muscles=len(self.muscle_mapping), coupling_strength=0.05)
        self.positions = self.calculate_positions()

        # Scatterplot overlay
        self.scatter = Scatterplot(self.width, self.height, num_dots=500, muscle_positions=self.positions)
        self.show_scatter = True
        self.btn_rect = pygame.Rect(10, 10, 140, 30)
        self.btn_font = pygame.font.SysFont(None, 24)

        # Input tracking
        self.held_keys = set()
        self.time_elapsed = 0.0  # for optional breathing

    # 1) Startup screen
    def wait_for_start(self):
        font = pygame.font.SysFont(None, 48)
        waiting = True
        while waiting:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN:
                    waiting = False
            self.screen.fill((0,0,0))
            txt = font.render("Press any key to start", True, (255,255,255))
            rect = txt.get_rect(center=(self.width//2, self.height//2))
            self.screen.blit(txt, rect)
            pygame.display.flip()
            self.clock.tick(30)

    # 2) Layout calculation
    def calculate_positions(self):
        spacing_x = self.width // 10
        spacing_y = self.height // 4
        rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
        positions, idx = {}, 0
        for r, row in enumerate(rows):
            for c, _ in enumerate(row):
                x = spacing_x//2 + c*spacing_x
                y = 100 + r*spacing_y
                positions[idx] = (x, y)
                idx += 1
        return positions
    
    # 3) Draw toggle‐button
    def draw_toggle_btn(self):
        pygame.draw.rect(self.screen, (50,50,50), self.btn_rect)
        txt = self.btn_font.render("Toggle View", True, (255,255,255))
        self.screen.blit(txt, (self.btn_rect.x+10, self.btn_rect.y+5))

    # 4) Draw network (tendons + muscles)
    def draw_tendons(self):
        neighbor_map = {
            'q': ['w', 'a', 's'],
            'w': ['q', 'e', 'a', 's', 'd'],
            'e': ['w', 'r', 's', 'd', 'f'],
            'r': ['e', 't', 'd', 'f', 'g'],
            't': ['r', 'y', 'f', 'g', 'h'],
            'y': ['t', 'u', 'g', 'h', 'j'],
            'u': ['y', 'i', 'h', 'j', 'k'],
            'i': ['u', 'o', 'j', 'k', 'l'],
            'o': ['i', 'p', 'k', 'l'],
            'p': ['o', 'l'],
            'a': ['q', 'w', 's', 'z'],
            's': ['q', 'w', 'e', 'a', 'd', 'z', 'x'],
            'd': ['w', 'e', 'r', 's', 'f', 'x', 'c'],
            'f': ['e', 'r', 't', 'd', 'g', 'c', 'v'],
            'g': ['r', 't', 'y', 'f', 'h', 'v', 'b'],
            'h': ['t', 'y', 'u', 'g', 'j', 'b', 'n'],
            'j': ['y', 'u', 'i', 'h', 'k', 'n', 'm'],
            'k': ['u', 'i', 'o', 'j', 'l', 'm'],
            'l': ['i', 'o', 'p', 'k'],
            'z': ['a', 's', 'x'],
            'x': ['s', 'd', 'z', 'c'],
            'c': ['d', 'f', 'x', 'v'],
            'v': ['f', 'g', 'c', 'b'],
            'b': ['g', 'h', 'v', 'n'],
            'n': ['h', 'j', 'b', 'm'],
            'm': ['j', 'k', 'n']
        }
        drawn = set()
        for letter, idx in self.muscle_mapping.items():
            pos1 = self.positions[idx]
            for neighbor_letter in neighbor_map.get(letter, []):
                if neighbor_letter in self.muscle_mapping:
                    n_idx = self.muscle_mapping[neighbor_letter]
                    if (idx, n_idx) in drawn or (n_idx, idx) in drawn:
                        continue
                    pos2 = self.positions[n_idx]
                    force_diff = abs(self.network.muscles[idx].force - self.network.muscles[n_idx].force)
                    line_width = max(1, int(force_diff * 10))
                    pygame.draw.line(self.screen, (100,100,100), pos1, pos2, line_width)
                    drawn.add((idx, n_idx))
        pass

    def draw_muscles(self):
        self.screen.fill((20, 20, 20))  # Background
        
        self.draw_tendons()
        for idx, (x, y) in self.positions.items():
            muscle = self.network.muscles[idx]
            radius = int(20 + 40 * muscle.force)  # Size based on force
            # If the muscle is not alive, draw it using a dull color
            color = (80, 80, 80) if not muscle.alive else (
                min(255, int(muscle.atp_available * 255)),
                min(255, int(muscle.calcium_concentration * 255)),
                150
            )
            pygame.draw.circle(self.screen, color, (x, y), radius)
            
            # Draw letter mapping
            letter = list(self.muscle_mapping.keys())[idx]
            font = pygame.font.SysFont(None, 24)
            img = font.render(letter.upper(), True, (255, 255, 255))
            rect = img.get_rect(center=(x, y))
            self.screen.blit(img, rect)
        pass

    # 5) Draw scatterplot
    def draw_scatterplot(self):
        self.scatter.draw(self.screen)

    # 6) Pump a single muscle by key
    def pump_muscle(self, key):
        key_lower = key.lower()
        if key_lower in self.muscle_mapping:
            idx = self.muscle_mapping[key_lower]
            base_force = 1.0  # Full force for the pressed node
            # Pump the pressed muscle at full power.
            self.network.muscles[idx].pump_energy(base_force)
            # Propagate force to neighbors with a hard cap using neighbor mapping.
            cap_percentage = 1.0
            self.propagate_force_by_neighbors(idx, base_force, cap_percentage)
        pass

    # 7) Force propagation
    def propagate_force_by_neighbors(self, source_idx, base_force, cap_percentage, force_threshold=0.1):
        """
        Propagates force from the source muscle to all neighbors using a BFS.
        Direct neighbors (level 1) get at most base_force * cap_percentage,
        level 2 get at most base_force * (cap_percentage)^2, and so on.
        force_threshold is used to cut off propagation when the pumped force becomes negligible.
        """
        # Define the neighbor mapping (same as in draw_tendons)
        neighbor_map = {
            'q': ['w', 'a', 's'],
            'w': ['q', 'e', 'a', 's', 'd'],
            'e': ['w', 'r', 's', 'd', 'f'],
            'r': ['e', 't', 'd', 'f', 'g'],
            't': ['r', 'y', 'f', 'g', 'h'],
            'y': ['t', 'u', 'g', 'h', 'j'],
            'u': ['y', 'i', 'h', 'j', 'k'],
            'i': ['u', 'o', 'j', 'k', 'l'],
            'o': ['i', 'p', 'k', 'l'],
            'p': ['o', 'l'],
            'a': ['q', 'w', 's', 'z'],
            's': ['q', 'w', 'e', 'a', 'd', 'z', 'x'],
            'd': ['w', 'e', 'r', 's', 'f', 'x', 'c'],
            'f': ['e', 'r', 't', 'd', 'g', 'c', 'v'],
            'g': ['r', 't', 'y', 'f', 'h', 'v', 'b'],
            'h': ['t', 'y', 'u', 'g', 'j', 'b', 'n'],
            'j': ['y', 'u', 'i', 'h', 'k', 'n', 'm'],
            'k': ['u', 'i', 'o', 'j', 'l', 'm'],
            'l': ['i', 'o', 'p', 'k'],
            'z': ['a', 's', 'x'],
            'x': ['s', 'd', 'z', 'c'],
            'c': ['d', 'f', 'x', 'v'],
            'v': ['f', 'g', 'c', 'b'],
            'b': ['g', 'h', 'v', 'n'],
            'n': ['h', 'j', 'b', 'm'],
            'm': ['j', 'k', 'n']
        }
        # Build inverse mapping: index → letter.
        inv_mapping = {v: k for k, v in self.muscle_mapping.items()}
        
        visited = set()
        queue = [(source_idx, 0)]  # Each tuple: (muscle index, level)
        visited.add(source_idx)
        
        while queue:
            current, level = queue.pop(0)
            current_letter = inv_mapping[current]
            # Determine the force multiplier for the next level.
            next_level_multiplier = cap_percentage ** (level + 1)
            propagated_force = base_force * next_level_multiplier
            if propagated_force < force_threshold:
                continue  # Stop propagation if force is negligible.
            # Get neighbors from neighbor_map (if any).
            for neighbor_letter in neighbor_map.get(current_letter, []):
                if neighbor_letter in self.muscle_mapping:
                    neighbor_idx = self.muscle_mapping[neighbor_letter]
                    if neighbor_idx not in visited:
                        # Pump the neighbor with the capped propagated force.
                        self.network.muscles[neighbor_idx].pump_energy(propagated_force)
                        visited.add(neighbor_idx)
                        queue.append((neighbor_idx, level + 1))

    def propagate_force_by_neighbors_realtime(self, source_idx, center_force, cap_percentage):
        """
        For the center node with current force "center_force", ensure that every neighboring
        node is at least at the capped level relative to center_force.
        Direct neighbors should be at most center_force * cap_percentage,
        level 2 at most center_force * (cap_percentage)^2, etc.
        """
        neighbor_map = {
            'q': ['w', 'a', 's'],
            'w': ['q', 'e', 'a', 's', 'd'],
            'e': ['w', 'r', 's', 'd', 'f'],
            'r': ['e', 't', 'd', 'f', 'g'],
            't': ['r', 'y', 'f', 'g', 'h'],
            'y': ['t', 'u', 'g', 'h', 'j'],
            'u': ['y', 'i', 'h', 'j', 'k'],
            'i': ['u', 'o', 'j', 'k', 'l'],
            'o': ['i', 'p', 'k', 'l'],
            'p': ['o', 'l'],
            'a': ['q', 'w', 's', 'z'],
            's': ['q', 'w', 'e', 'a', 'd', 'z', 'x'],
            'd': ['w', 'e', 'r', 's', 'f', 'x', 'c'],
            'f': ['e', 'r', 't', 'd', 'g', 'c', 'v'],
            'g': ['r', 't', 'y', 'f', 'h', 'v', 'b'],
            'h': ['t', 'y', 'u', 'g', 'j', 'b', 'n'],
            'j': ['y', 'u', 'i', 'h', 'k', 'n', 'm'],
            'k': ['u', 'i', 'o', 'j', 'l', 'm'],
            'l': ['i', 'o', 'p', 'k'],
            'z': ['a', 's', 'x'],
            'x': ['s', 'd', 'z', 'c'],
            'c': ['d', 'f', 'x', 'v'],
            'v': ['f', 'g', 'c', 'b'],
            'b': ['g', 'h', 'v', 'n'],
            'n': ['h', 'j', 'b', 'm'],
            'm': ['j', 'k', 'n']
        }
        # Build inverse mapping: index -> letter.
        inv_mapping = {v: k for k, v in self.muscle_mapping.items()}
        
        visited = set()
        queue = [(source_idx, 0)]  # Each tuple: (neighbor muscle index, level)
        visited.add(source_idx)
        
        while queue:
            current, level = queue.pop(0)
            # The target maximum force for a neighbor at this level:
            target_force = center_force * (cap_percentage ** (level + 1))
            
            current_letter = inv_mapping[current]
            for neighbor_letter in neighbor_map.get(current_letter, []):
                if neighbor_letter in self.muscle_mapping:
                    neighbor_idx = self.muscle_mapping[neighbor_letter]
                    if neighbor_idx not in visited:
                        visited.add(neighbor_idx)
                        neighbor_muscle = self.network.muscles[neighbor_idx]
                        # Only pump if the neighbor's force is below the cap.
                        if neighbor_muscle.force < target_force:
                            pump_amount = target_force - neighbor_muscle.force
                            neighbor_muscle.pump_energy(pump_amount)
                        queue.append((neighbor_idx, level + 1))

    # 8) Main Loop 
    def run(self):
        self.wait_for_start()
        while self.running:
            # — Event handling —
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type == pygame.KEYDOWN:
                    k = ev.unicode.lower()
                    if k in self.muscle_mapping:
                        self.held_keys.add(k)
                elif ev.type == pygame.KEYUP:
                    k = ev.unicode.lower()
                    self.held_keys.discard(k)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self.btn_rect.collidepoint(ev.pos):
                        self.show_scatter = not self.show_scatter

            # — Input processing —
            for k in self.held_keys:
                idx = self.muscle_mapping[k]
                self.network.muscles[idx].pump_energy(1.0)
                # double‐pump if desired...
                cap = 0.66
                self.propagate_force_by_neighbors_realtime(idx,
                    self.network.muscles[idx].force, cap)

            # — Core update —
            # optional breathing:
            # self.time_elapsed += 0.02
            # self.network.set_activation(0.5 + 0.5*math.sin(self.time_elapsed))
            self.network.stimulate(intensity=1.0)
            self.network.update_network()
            # scatterplot update must come after network forces are fresh
            self.scatter.update_dots({i:m.force for i,m in enumerate(self.network.muscles)})

            # — Rendering —
            self.screen.fill((20,20,20))
            self.draw_toggle_btn()
            if self.show_scatter:
                self.draw_scatterplot()
            else:
                self.draw_tendons()
                self.draw_muscles()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    MuscleGUI().run()















class MuscleGUI:
    def __init__(self):
        pygame.init()
        pygame.key.set_repeat(0, 1000)  # Enable continuous keydown events: delay 200ms, repeat every 50ms
        
        self.width = 1200
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption('Muscle Network')

        self.clock = pygame.time.Clock()
        self.running = True
        
        self.muscle_mapping = {k: i for i, k in enumerate("qwertyuiopasdfghjklzxcvbnm")}
        self.network = Tissue(num_muscles=len(self.muscle_mapping), coupling_strength=0.05)

        # Layout muscles into grid positions
        self.positions = self.calculate_positions()

        # Initialize time for breathing simulation
        self.time_elapsed = 0.0

        # New: Track keys being held down.
        self.held_keys = set()

    def wait_for_start(self):
        waiting = True
        font = pygame.font.SysFont(None, 48)
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if event.type == pygame.KEYDOWN:
                    waiting = False
            self.screen.fill((0, 0, 0))
            text = font.render("Press any key to start simulation", True, (255, 255, 255))
            rect = text.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(text, rect)
            pygame.display.flip()
            self.clock.tick(30)

    def calculate_positions(self):
        spacing_x = self.width // 10
        spacing_y = self.height // 4
        positions = {}
        rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
        y_start = 100
        
        idx = 0
        for r, row in enumerate(rows):
            for c, char in enumerate(row):
                x = spacing_x // 2 + c * spacing_x
                y = y_start + r * spacing_y
                positions[idx] = (x, y)
                idx += 1
        return positions

    def draw_tendons(self):
        # Define neighbors by QWERTY layout
        neighbor_map = {
            'q': ['w', 'a', 's'],
            'w': ['q', 'e', 'a', 's', 'd'],
            'e': ['w', 'r', 's', 'd', 'f'],
            'r': ['e', 't', 'd', 'f', 'g'],
            't': ['r', 'y', 'f', 'g', 'h'],
            'y': ['t', 'u', 'g', 'h', 'j'],
            'u': ['y', 'i', 'h', 'j', 'k'],
            'i': ['u', 'o', 'j', 'k', 'l'],
            'o': ['i', 'p', 'k', 'l'],
            'p': ['o', 'l'],
            'a': ['q', 'w', 's', 'z'],
            's': ['q', 'w', 'e', 'a', 'd', 'z', 'x'],
            'd': ['w', 'e', 'r', 's', 'f', 'x', 'c'],
            'f': ['e', 'r', 't', 'd', 'g', 'c', 'v'],
            'g': ['r', 't', 'y', 'f', 'h', 'v', 'b'],
            'h': ['t', 'y', 'u', 'g', 'j', 'b', 'n'],
            'j': ['y', 'u', 'i', 'h', 'k', 'n', 'm'],
            'k': ['u', 'i', 'o', 'j', 'l', 'm'],
            'l': ['i', 'o', 'p', 'k'],
            'z': ['a', 's', 'x'],
            'x': ['s', 'd', 'z', 'c'],
            'c': ['d', 'f', 'x', 'v'],
            'v': ['f', 'g', 'c', 'b'],
            'b': ['g', 'h', 'v', 'n'],
            'n': ['h', 'j', 'b', 'm'],
            'm': ['j', 'k', 'n']
        }
        drawn = set()
        for letter, idx in self.muscle_mapping.items():
            pos1 = self.positions[idx]
            for neighbor_letter in neighbor_map.get(letter, []):
                if neighbor_letter in self.muscle_mapping:
                    n_idx = self.muscle_mapping[neighbor_letter]
                    # Avoid drawing duplicate lines.
                    if (idx, n_idx) in drawn or (n_idx, idx) in drawn:
                        continue
                    pos2 = self.positions[n_idx]
                    # Vary the tendon width based on the force difference.
                    force_diff = abs(self.network.muscles[idx].force - self.network.muscles[n_idx].force)
                    line_width = max(1, int(force_diff * 10))
                    pygame.draw.line(self.screen, (100, 100, 100), pos1, pos2, line_width)
                    drawn.add((idx, n_idx))


    def draw_muscles(self):
        self.screen.fill((20, 20, 20))  # Background
        
        self.draw_tendons()
        for idx, (x, y) in self.positions.items():
            muscle = self.network.muscles[idx]
            radius = int(20 + 40 * muscle.force)  # Size based on force
            # If the muscle is not alive, draw it using a dull color
            color = (80, 80, 80) if not muscle.alive else (
                min(255, int(muscle.atp_available * 255)),
                min(255, int(muscle.calcium_concentration * 255)),
                150
            )
            pygame.draw.circle(self.screen, color, (x, y), radius)
            
            # Draw letter mapping
            letter = list(self.muscle_mapping.keys())[idx]
            font = pygame.font.SysFont(None, 24)
            img = font.render(letter.upper(), True, (255, 255, 255))
            rect = img.get_rect(center=(x, y))
            self.screen.blit(img, rect)
            
    def pump_muscle(self, key):
        key_lower = key.lower()
        if key_lower in self.muscle_mapping:
            idx = self.muscle_mapping[key_lower]
            base_force = 1.0  # Full force for the pressed node
            # Pump the pressed muscle at full power.
            self.network.muscles[idx].pump_energy(base_force)
            # Propagate force to neighbors with a hard cap using neighbor mapping.
            cap_percentage = 1.0
            self.propagate_force_by_neighbors(idx, base_force, cap_percentage)

    def propagate_force_by_neighbors(self, source_idx, base_force, cap_percentage, force_threshold=0.1):
        """
        Propagates force from the source muscle to all neighbors using a BFS.
        Direct neighbors (level 1) get at most base_force * cap_percentage,
        level 2 get at most base_force * (cap_percentage)^2, and so on.
        force_threshold is used to cut off propagation when the pumped force becomes negligible.
        """
        # Define the neighbor mapping (same as in draw_tendons)
        neighbor_map = {
            'q': ['w', 'a', 's'],
            'w': ['q', 'e', 'a', 's', 'd'],
            'e': ['w', 'r', 's', 'd', 'f'],
            'r': ['e', 't', 'd', 'f', 'g'],
            't': ['r', 'y', 'f', 'g', 'h'],
            'y': ['t', 'u', 'g', 'h', 'j'],
            'u': ['y', 'i', 'h', 'j', 'k'],
            'i': ['u', 'o', 'j', 'k', 'l'],
            'o': ['i', 'p', 'k', 'l'],
            'p': ['o', 'l'],
            'a': ['q', 'w', 's', 'z'],
            's': ['q', 'w', 'e', 'a', 'd', 'z', 'x'],
            'd': ['w', 'e', 'r', 's', 'f', 'x', 'c'],
            'f': ['e', 'r', 't', 'd', 'g', 'c', 'v'],
            'g': ['r', 't', 'y', 'f', 'h', 'v', 'b'],
            'h': ['t', 'y', 'u', 'g', 'j', 'b', 'n'],
            'j': ['y', 'u', 'i', 'h', 'k', 'n', 'm'],
            'k': ['u', 'i', 'o', 'j', 'l', 'm'],
            'l': ['i', 'o', 'p', 'k'],
            'z': ['a', 's', 'x'],
            'x': ['s', 'd', 'z', 'c'],
            'c': ['d', 'f', 'x', 'v'],
            'v': ['f', 'g', 'c', 'b'],
            'b': ['g', 'h', 'v', 'n'],
            'n': ['h', 'j', 'b', 'm'],
            'm': ['j', 'k', 'n']
        }
        # Build inverse mapping: index → letter.
        inv_mapping = {v: k for k, v in self.muscle_mapping.items()}
        
        visited = set()
        queue = [(source_idx, 0)]  # Each tuple: (muscle index, level)
        visited.add(source_idx)
        
        while queue:
            current, level = queue.pop(0)
            current_letter = inv_mapping[current]
            # Determine the force multiplier for the next level.
            next_level_multiplier = cap_percentage ** (level + 1)
            propagated_force = base_force * next_level_multiplier
            if propagated_force < force_threshold:
                continue  # Stop propagation if force is negligible.
            # Get neighbors from neighbor_map (if any).
            for neighbor_letter in neighbor_map.get(current_letter, []):
                if neighbor_letter in self.muscle_mapping:
                    neighbor_idx = self.muscle_mapping[neighbor_letter]
                    if neighbor_idx not in visited:
                        # Pump the neighbor with the capped propagated force.
                        self.network.muscles[neighbor_idx].pump_energy(propagated_force)
                        visited.add(neighbor_idx)
                        queue.append((neighbor_idx, level + 1))

    def propagate_force_by_neighbors_realtime(self, source_idx, center_force, cap_percentage):
        """
        For the center node with current force "center_force", ensure that every neighboring
        node is at least at the capped level relative to center_force.
        Direct neighbors should be at most center_force * cap_percentage,
        level 2 at most center_force * (cap_percentage)^2, etc.
        """
        neighbor_map = {
            'q': ['w', 'a', 's'],
            'w': ['q', 'e', 'a', 's', 'd'],
            'e': ['w', 'r', 's', 'd', 'f'],
            'r': ['e', 't', 'd', 'f', 'g'],
            't': ['r', 'y', 'f', 'g', 'h'],
            'y': ['t', 'u', 'g', 'h', 'j'],
            'u': ['y', 'i', 'h', 'j', 'k'],
            'i': ['u', 'o', 'j', 'k', 'l'],
            'o': ['i', 'p', 'k', 'l'],
            'p': ['o', 'l'],
            'a': ['q', 'w', 's', 'z'],
            's': ['q', 'w', 'e', 'a', 'd', 'z', 'x'],
            'd': ['w', 'e', 'r', 's', 'f', 'x', 'c'],
            'f': ['e', 'r', 't', 'd', 'g', 'c', 'v'],
            'g': ['r', 't', 'y', 'f', 'h', 'v', 'b'],
            'h': ['t', 'y', 'u', 'g', 'j', 'b', 'n'],
            'j': ['y', 'u', 'i', 'h', 'k', 'n', 'm'],
            'k': ['u', 'i', 'o', 'j', 'l', 'm'],
            'l': ['i', 'o', 'p', 'k'],
            'z': ['a', 's', 'x'],
            'x': ['s', 'd', 'z', 'c'],
            'c': ['d', 'f', 'x', 'v'],
            'v': ['f', 'g', 'c', 'b'],
            'b': ['g', 'h', 'v', 'n'],
            'n': ['h', 'j', 'b', 'm'],
            'm': ['j', 'k', 'n']
        }
        # Build inverse mapping: index -> letter.
        inv_mapping = {v: k for k, v in self.muscle_mapping.items()}
        
        visited = set()
        queue = [(source_idx, 0)]  # Each tuple: (neighbor muscle index, level)
        visited.add(source_idx)
        
        while queue:
            current, level = queue.pop(0)
            # The target maximum force for a neighbor at this level:
            target_force = center_force * (cap_percentage ** (level + 1))
            
            current_letter = inv_mapping[current]
            for neighbor_letter in neighbor_map.get(current_letter, []):
                if neighbor_letter in self.muscle_mapping:
                    neighbor_idx = self.muscle_mapping[neighbor_letter]
                    if neighbor_idx not in visited:
                        visited.add(neighbor_idx)
                        neighbor_muscle = self.network.muscles[neighbor_idx]
                        # Only pump if the neighbor's force is below the cap.
                        if neighbor_muscle.force < target_force:
                            pump_amount = target_force - neighbor_muscle.force
                            neighbor_muscle.pump_energy(pump_amount)
                        queue.append((neighbor_idx, level + 1))

    def run(self):
        import math
        self.wait_for_start()  # Wait until user presses a key

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame.KEYDOWN:
                    key_lower = event.unicode.lower()
                    if key_lower in self.muscle_mapping:
                        self.held_keys.add(key_lower)
                if event.type == pygame.KEYUP:
                    key_lower = event.unicode.lower()
                    if key_lower in self.held_keys:
                        self.held_keys.remove(key_lower)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.btn_rect.collidepoint(event.pos):
                        self.show_scatter = not self.show_scatter

            # For every key that's being held, pump its corresponding muscle.
            for key in self.held_keys:
                idx = self.muscle_mapping[key]
                self.network.muscles[idx].pump_energy(1.0)
                cap_percentage = 0.66
                center_force = self.network.muscles[idx].force
                self.propagate_force_by_neighbors_realtime(idx, center_force, cap_percentage)

            # --- NEW: Tell scatterplot which nodes are active ---
            active_indices = [self.muscle_mapping[k] for k in self.held_keys]
            self.scatter.set_active_nodes(active_indices)
            # Update scatterplot dots with current muscle forces
            self.scatter.update_dots({i: m.force for i, m in enumerate(self.network.muscles)})

            # Stimulate and update network
            self.network.stimulate(intensity=1.0)
            self.network.update_network()

            # Draw updated state
            self.screen.fill((20, 20, 20))
            self.draw_toggle_btn()
            if self.show_scatter:
                self.draw_scatterplot()
            else:
                self.draw_tendons()
                self.draw_muscles()
            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS

        pygame.quit()

# --- RUN THE GUI ---
if __name__ == "__main__":
    MuscleGUI().run()