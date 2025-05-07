import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QKeyEvent

class Muscle:
    """Represents a muscle with detailed contraction dynamics based on the Sliding Filament Theory."""
    
    def __init__(self, resting_force=0.2, max_force=1.0, fatigue_rate=0.1,
                 regeneration_rate=0.002, actin_length=100, myosin_heads=100):
        self.resting_force = resting_force
        self.max_force = max_force
        self.fatigue_rate = fatigue_rate  # Controls ATP depletion rate
        self.regeneration_rate = regeneration_rate  # Rate of ATP regeneration when relaxing
        self.activation = 0.0  # Current activation level (0-1)
        self.force = self.resting_force  # Current force output
        self.fatigue_level = 1.0  # Fatigue level, affects max force
        self.calcium_concentration = 0.0  # Calcium concentration (0-1)
        
        self.actin_length = actin_length
        self.myosin_heads = myosin_heads
        self.actin = np.zeros(actin_length)  # Actin filament positions
        self.myosin = np.zeros(myosin_heads)  # Myosin heads ready for binding
        
        self.atp_available = 1.0  # ATP concentration (1 means full availability)
        
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
            self.atp_available -= atp_consumed
            self.atp_available = max(0.0, self.atp_available)
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
            self.calcium_concentration -= reduction
            self.calcium_concentration = max(0.1, self.calcium_concentration)
    
    def regenerate_atp(self):
        if self.force == self.resting_force and self.atp_available < 1.0:
            self.atp_available += min(0.03, (1.0 - self.atp_available) * self.regeneration_rate)
        
    def update(self):
        self.fatigue_update()
        if self.atp_available > 0.01:
            self.activate_muscle()
        else:
            self.force = self.resting_force
            self.calcium_concentration = max(0.0, self.calcium_concentration - 0.02)
        self.regenerate_atp()
        return f"Force: {self.force:.2f}, ATP: {self.atp_available:.3f}, Calcium: {self.calcium_concentration:.3f}"
    
    def pump_energy(self):
        """Simulates a user pumping energy into the muscle."""
        self.atp_available = min(1.0, self.atp_available + 0.2)  # Boost ATP
        self.calcium_concentration = min(1.0, self.calcium_concentration + 0.1)  # Boost calcium


class MuscleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.muscle = Muscle()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_muscle)
        self.timer.start(100)  # Update every 100ms
        self.simulation_paused = False  # Track whether the simulation is paused

    def initUI(self):
        self.setWindowTitle("Muscle Simulation")
        self.setGeometry(100, 100, 600, 400)
        
        self.text_console = QTextEdit(self)
        self.text_console.setReadOnly(True)
        
        layout = QVBoxLayout()
        layout.addWidget(self.text_console)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def update_muscle(self):
        if not self.simulation_paused:  # Only update if the simulation is not paused
            state = self.muscle.update()
            self.text_console.append(state)
            if self.muscle.atp_available <= 0.0:
                self.text_console.append("System flatlined! Press any key to pump energy.")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == 16777216:  # Esc key
            self.simulation_paused = not self.simulation_paused  # Toggle pause state
            if self.simulation_paused:
                self.text_console.append("Simulation paused.")
            else:
                self.text_console.append("Simulation resumed.")
        else:
            self.muscle.pump_energy()
            self.text_console.append("Energy pumped into the muscle!")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MuscleApp()
    window.show()
    sys.exit(app.exec_())