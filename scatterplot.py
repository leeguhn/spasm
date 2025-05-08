import random
import pygame

class Scatterplot:
    def __init__(self, width, height, num_dots, muscle_positions):
        self.width = width
        self.height = height
        self.num_dots = num_dots
        self.muscle_positions = muscle_positions
        self.dots = self.initialize_dots()
        self.active_nodes = set()

    def initialize_dots(self):
        dots = []
        # Calculate grid size (try to make it as square as possible)
        cols = int(self.num_dots ** 0.5)
        rows = (self.num_dots + cols - 1) // cols
        spacing_x = self.width / (cols + 1)
        spacing_y = self.height / (rows + 1)
        count = 0
        for row in range(rows):
            for col in range(cols):
                if count >= self.num_dots:
                    break
                x = int((col + 1) * spacing_x)
                y = int((row + 1) * spacing_y)
                closest = self.find_closest_muscle(x, y)
                dots.append({
                    'x': x, 'y': y,
                    'vx': 0.0, 'vy': 0.0,
                    'rest_x': x, 'rest_y': y,
                    'closest': closest
                })
                count += 1
        return dots

    def find_closest_muscle(self, x, y):
        closest, md = None, float('inf')
        for idx, (mx, my) in self.muscle_positions.items():
            d = ((x - mx)**2 + (y - my)**2)**0.5
            if d < md:
                md, closest = d, idx
        return closest

    def set_active_nodes(self, active_node_indices):
        self.active_nodes = set(active_node_indices)

    def update_dots(self, muscle_forces):
        k_spring = 0.01  # spring constant for rest position
        damping = 0.92   # velocity damping for resistance
        pull_strength = 0.04  # how strong the node pull is

        for dot in self.dots:
            idx = dot['closest']
            # Always: spring back to rest position
            fx = -k_spring * (dot['x'] - dot['rest_x'])
            fy = -k_spring * (dot['y'] - dot['rest_y'])

            # If node is active, add elastic pull toward node
            if idx in self.active_nodes:
                mx, my = self.muscle_positions[idx]
                force = muscle_forces.get(idx, 0)
                fx += pull_strength * force * (mx - dot['x']) / max(1, abs(mx - dot['x']) + abs(my - dot['y']))
                fy += pull_strength * force * (my - dot['y']) / max(1, abs(mx - dot['x']) + abs(my - dot['y']))

            # Update velocity and position
            dot['vx'] = (dot['vx'] + fx) * damping
            dot['vy'] = (dot['vy'] + fy) * damping
            dot['x'] += dot['vx']
            dot['y'] += dot['vy']

            # Keep dots within bounds
            dot['x'] = max(0, min(self.width, dot['x']))
            dot['y'] = max(0, min(self.height, dot['y']))

    def draw(self, screen):
        for dot in self.dots:
            pygame.draw.circle(screen, (255,255,255), (int(dot['x']), int(dot['y'])), 2)