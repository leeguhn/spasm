import numpy as np

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
        self.atp_available = resting_force

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

        # If there's no activation, apply an extra decay for any residual energy
        if self.activation == 0.0:
            decay_amount = 0.05   # adjust as needed for faster decay
            if self.atp_available > self.resting_force:
                self.atp_available = max(self.resting_force, self.atp_available - decay_amount)
            if self.calcium_concentration > 0.0:
                self.calcium_concentration = max(0.0, self.calcium_concentration - (decay_amount * 0.5))
        
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
    
    def propagate_force(self, source_idx, base_force, positions, damping_factor=0.5):
        """
        Propagates energy from a source muscle through the network.
        The additional force each muscle receives is a function of its 
        distance from the source:
        
            added_force = (base_force / (1 + distance)) * damping_factor
        
        positions: a dict mapping muscle index to (x,y) coordinates.
        """
        source_pos = positions[source_idx]
        for idx, pos in positions.items():
            if idx == source_idx:
                continue
            dx = pos[0] - source_pos[0]
            dy = pos[1] - source_pos[1]
            distance = (dx**2 + dy**2)**0.5
            added_force = (base_force / (1 + distance)) * damping_factor
            self.muscles[idx].pump_energy(added_force)