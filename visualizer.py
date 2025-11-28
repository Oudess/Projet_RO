# visualizer.py 
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure
import numpy as np

class VisualizationWidget(Canvas):
    def __init__(self):
        self.fig = Figure(figsize=(10, 6), dpi=100)
        super().__init__(self.fig)

    def clear(self):
        self.fig.clear()
        self.draw()

    # 1. Charges par agent (histogramme)
   
    def show_agent_load(self, sol):
        self.clear()
        ax = self.fig.add_subplot(111)
        E = len(sol)
        loads = [sum(sum(day) for day in agent) for agent in sol]

        bars = ax.bar(range(1, E+1), loads, color='#3498db', edgecolor='black', alpha=0.85)
        ax.set_title("Charge de travail par agent", fontsize=18, fontweight='bold', pad=20, color='#2c3e50')
        ax.set_xlabel("Agent", fontsize=13)
        ax.set_ylabel("Nombre de quarts", fontsize=13)
        ax.set_xticks(range(1, E+1, max(1, E//20)))  

        for bar in bars:
            h = int(bar.get_height())
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.1, f'{h}', ha='center', va='bottom', fontweight='bold')

        self.fig.tight_layout()
        self.draw()


    # 2. Heatmap 

    def show_heatmap(self, sol):
        self.clear()
        ax = self.fig.add_subplot(111)

        E = len(sol)
        D = len(sol[0])
        heat = np.zeros((E, D))
        for e in range(E):
            for d in range(D):
                heat[e, d] = sum(sol[e][d])

        jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        im = ax.imshow(heat, cmap="YlOrRd", aspect='auto', vmin=0, vmax=1)

        ax.set_yticks(np.arange(E))
        ax.set_yticklabels([f"Agent {e+1}" for e in range(E)], fontsize=9)
        ax.set_xticks(np.arange(D))
        ax.set_xticklabels(jours, fontsize=12, fontweight='bold', color='#2c3e50')

        ax.set_title("Planning Hebdomadaire – Qui travaille quand ?", 
                     fontsize=18, fontweight='bold', pad=30, color='#2c3e50')

        # Grille
        ax.set_xticks(np.arange(-.5, D, 1), minor=True)
        ax.set_yticks(np.arange(-.5, E, 1), minor=True)
        ax.grid(which='minor', color='gray', linestyle='-', linewidth=1.5)
        ax.tick_params(which='both', length=0)

        # Légende
        from matplotlib.patches import Patch
        legend = [Patch(facecolor='#ffffb3', label='Repos'),
                  Patch(facecolor='#fb6a4a', label='Travaille')]
        ax.legend(handles=legend, loc='upper right', bbox_to_anchor=(1.15, 1),
                  title="Légende", fontsize=11, title_fontsize=12)

        self.fig.tight_layout()
        self.draw()
