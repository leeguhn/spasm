import numpy as np
import pygame

class Muscle:
    """A node representing a muscle fiber with dynamic contraction and fatigue mechanisms."""
    
    def __init__(self, 
                 resting_force=0.2, 
                 max_force=1.0, 
                 fatigue_rate=0.1,
                 regeneration_rate=0.002, 
                 actin_length=100, 
                 myosin_heads=100):
        
        # Muscle Parameters
        self.resting_force = resting_force
        self.max_force = max_force
        self.fatigue_rate = fatigue_rate
        self.regeneration_rate = regeneration_rate
        
        # Contraction States
        self.activation = 0.0
        self.force = resting_force
        self.fatigue_level = 1.0
        self.calcium_concentration = 0.0
        
        # Sliding Filament Components
        self.actin_length = actin_length
        self.myosin_heads = myosin_heads
        self.actin = np.zeros(actin_length)
        self.myosin = np.zeros(myosin_heads)
        
        # Energy System
        self.atp_available = 1.0

        # New Damage/Healing Attributes
        self.alive = True
        self.damage_level = 0.0

    def check_damage(self):
        # Increase damage when force is excessive or ATP is very low, otherwise heal slowly.
        # Reduce damage slowly when conditions are normal.
        if (self.force > self.max_force * 1.2 and self.activation > 0.8) or self.atp_available < 0.05:
            self.damage_level += 0.001  # reduced increment
        else:
            self.damage_level = max(0.0, self.damage_level - 0.0005)
        # Instead of marking the muscle as dead, cap the damage level.
        self.damage_level = min(self.damage_level, 1.0)
        
    def release_calcium(self, intensity):
        if self.atp_available > 0.01 and self.activation > 0:
            sinusoidal_component = np.sin(intensity * np.pi) / 2 + 0.5
            self.calcium_concentration = np.clip(
                self.resting_force + (intensity * sinusoidal_component),
                0.0, 
                1.0
            )
        else:
            if self.calcium_concentration > 0.02:
                self.calcium_concentration -= min(0.04, self.calcium_concentration * 0.05)
            else:
                self.calcium_concentration = max(0.0, self.calcium_concentration - 0.02)
    
    def activate_muscle(self):
        if self.atp_available > 0.01:
            myosin_bindable = int(min(
                self.myosin_heads,
                (self.calcium_concentration + self.activation) * self.myosin_heads / 2
            ))
            force_factor = self.atp_available * myosin_bindable
            self.force = self.resting_force + (force_factor * 0.01)
            
            atp_consumed = min(0.002, 0.4 * self.fatigue_rate) * myosin_bindable
            self.atp_available = max(0.0, self.atp_available - atp_consumed)
            
            # Simulate actin sliding
            self.actin = np.roll(self.actin, int(-myosin_bindable * 0.2))
        else:
            self.force = self.resting_force
            self.calcium_concentration = max(0.0, self.calcium_concentration - 0.02)
    
    def fatigue_update(self):
        if self.atp_available < 1.0:
            self.atp_available -= min(0.005, (1.0 - self.atp_available) * 0.01)
            self.atp_available = max(0.0, self.atp_available)
            
        if self.atp_available <= 0.2 and self.calcium_concentration > 0.0:
            reduction = max(0.01, min(0.05, (self.fatigue_level - 1) * 0.01))
            self.calcium_concentration = max(0.1, self.calcium_concentration - reduction)
    
    def regenerate_atp(self):
        if self.force == self.resting_force and self.atp_available < 1.0:
            self.atp_available += min(0.03, (1.0 - self.atp_available) * self.regeneration_rate)
            self.atp_available = min(1.0, self.atp_available)
    
    def pump_energy(self, amount=0.2):
        """Externally pump energy into the muscle (simulates voluntary boost)."""
        self.atp_available = min(1.0, self.atp_available + amount)
        self.calcium_concentration = min(1.0, self.calcium_concentration + amount * 0.5)
    
    def update(self, external_activation=0.0):
        """Update muscle state given an external activation signal."""
        self.activation = np.clip(external_activation, 0.0, 1.0)

        # Always attempt to release calcium and update fatigue
        self.release_calcium(self.activation)
        self.fatigue_update()
        
        if self.atp_available > 0.01:
            self.activate_muscle()
        else:
            # Instead of zeroing out, simply retain the baseline force.
            self.force = self.resting_force
            self.calcium_concentration = max(self.resting_force, self.calcium_concentration - 0.02)
        
        self.regenerate_atp()
        self.check_damage()
        
        # Guarantee a moderate baseline force (simulate inherent muscle tone)
        self.force = max(self.force, self.resting_force)
        return {
            'force': self.force,
            'atp': self.atp_available,
            'calcium': self.calcium_concentration
        }   
    
    def __str__(self):
        return f"[Muscle] Force: {self.force:.2f}, ATP: {self.atp_available:.3f}, Calcium: {self.calcium_concentration:.3f}"

class Tissue:
    """Manages an interconnected network of muscles with local influence dynamics."""
    
    def __init__(self, num_muscles=5, coupling_strength=0.1):
        self.muscles = [Muscle() for _ in range(num_muscles)]
        self.global_activation = 0.0  # Overall network drive
        self.coupling_strength = coupling_strength  # How much neighboring muscles affect each other
    
    def set_activation(self, activation_level):
        """Sets a global drive across the network."""
        self.global_activation = np.clip(activation_level, 0.0, 1.0)
        for muscle in self.muscles:
            muscle.activation = self.global_activation * 0.8  # slight loss to individuality
    
    def stimulate(self, intensity=1.0):
        """Releases calcium in all muscles proportionally."""
        for muscle in self.muscles:
            muscle.release_calcium(intensity * self.global_activation)
    
    def local_coupling(self):
        """Applies local influence between neighboring muscles."""
        forces = np.array([muscle.force for muscle in self.muscles])
        new_activations = []
        
        for i, muscle in enumerate(self.muscles):
            left_force = forces[i - 1] if i > 0 else 0.0
            right_force = forces[i + 1] if i < len(self.muscles) - 1 else 0.0
            neighbor_influence = (left_force + right_force) * 0.5
            adjustment = (neighbor_influence - muscle.force) * self.coupling_strength
            new_activation = np.clip(muscle.activation + adjustment, 0.0, 1.0)
            new_activations.append(new_activation)
        
        for i, muscle in enumerate(self.muscles):
            muscle.activation = new_activations[i]
    
    def update_network(self):
        """Update all muscles and apply local coupling effects."""
        self.local_coupling()
        
        forces = []
        for muscle in self.muscles:
            status = muscle.update()
            forces.append(muscle.force)
        
        return {
            'average_force': np.mean(forces),
            'total_force': np.sum(forces),
            'forces': forces
        }
    
    def pump_energy_to_all(self):
        """Energize all muscles simultaneously."""
        for muscle in self.muscles:
            muscle.pump_energy()
    
    def network_status(self):
        """Returns a full readable status."""
        statuses = [f"Muscle {i}: {muscle.update()}" for i, muscle in enumerate(self.muscles)]
        return "\n".join(statuses)

# Map each alphabet letter to a muscle
KEYS = "qwertyuiopasdfghjklzxcvbnm"

class MuscleGUI:
    def __init__(self):
        pygame.init()
        pygame.key.set_repeat(200, 50)  # Enable continuous keydown events: delay 200ms, repeat every 50ms
        
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

    def draw_skin(self):
        # Create a semi-transparent skin layer that bulges based on underlying muscle force
        skin = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        points = []
        for idx in sorted(self.positions.keys()):
            x, y = self.positions[idx]
            bulge = int(self.network.muscles[idx].force * 10)
            points.append((x, y - bulge))
        if len(points) > 2:
            pygame.draw.polygon(skin, (150, 50, 50, 80), points)
        self.screen.blit(skin, (0, 0))

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
            # Pump the selected muscle at full power (0.3)
            self.network.muscles[idx].pump_energy(0.3)
            
            # Define neighbor mapping (same as used in draw_tendons)
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
            # If there are neighbors for this key, pump them with half power (0.15)
            if key_lower in neighbor_map:
                for nb in neighbor_map[key_lower]:
                    if nb in self.muscle_mapping:
                        nb_idx = self.muscle_mapping[nb]
                        self.network.muscles[nb_idx].pump_energy(0.15)

    def run(self):
        import math
        self.wait_for_start()  # Wait until user presses a key
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.unicode.lower() in self.muscle_mapping:
                        self.pump_muscle(event.unicode)
            
            # Breathing Pattern: autonomous sine wave activation across the network
            self.time_elapsed += 0.02
            breath_activation = 0.5 + 0.5 * math.sin(self.time_elapsed)
            self.network.set_activation(breath_activation)
            
            # Stimulate and update network
            self.network.stimulate(intensity=1.0)
            self.network.update_network()

            # Draw updated state
            self.draw_muscles()
            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS
        
        pygame.quit()

# --- RUN THE GUI ---
if __name__ == "__main__":
    gui = MuscleGUI()
    gui.run()