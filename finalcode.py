import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import gurobipy as gp
from gurobipy import GRB


class AtelierNOVA(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Atelier NOVA – Planning Journalier Optimal")
        self.resize(1700, 980)
        self.setStyleSheet("background:#0d1117; color:#c9d1d9; font-family: Segoe UI;")

        self.config = {
            "max_projects": 12,
            "max_tasks_per_project": 8,
            "nb_teams": 6,
            "hours_per_day": 24.0,
            "max_task_hours": 5
        }
        self.teams = [f"Équipe {i+1}" for i in range(self.config["nb_teams"])]
        self.projects = {}

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === TITRE + DESCRIPTION ===
        header = QLabel(f"""
        <div style='text-align:center; padding:40px; background:linear-gradient(135deg,#238636,#58a6ff); border-radius:22px; color:white;'>
            <h1 style='margin:0; font-size:40px;'>Atelier NOVA</h1>
            <h2 style='margin:12px 0; font-size:28px;'>Planning Journalier Intelligent – Sujet 18</h2>
        </div>
        <div style='background:#161b22; padding:32px; border-radius:18px; margin-top:20px; line-height:2.3; font-size:18px;'>
            <h3 style='color:#79c0ff; margin:0 0 20px 0;'>Fonctionnement de l'Atelier NOVA</h3>
            <ul style='margin:15px 0; padding-left:50px; font-size:17px;'>
                <li>Atelier Nova délivres un nombre déterminé de projets (jalons) par jour</li>
                <li>l'atelier dispose d'un nombre d'equipe variable chaque jour (ressources renouvelables)</li>
                <li>chaque projet est constitué de certain nombre de taches,chacune a une durée différente</li>
                <li>Chaque équipe ne traite qu'une seule tâche à la fois</li>
                <li>Chaque équipe ne traite qu'une seule tâche d'un projets déterminé</li>
                <li>Les tâches d'un même projet sont séquentielles (précédences respectées dans l'ordre)</li>
                <li>Objectif : terminer tous les projets le plus tôt possible (makespan minimal)</li>
                <li>Gurobi optimise automatiquement l'affectation pour une parallélisation maximale</li>
            </ul>
            <p style='color:#58a6ff; font-weight:bold; font-size:20px; margin-top:25px;'>
                Résultats complets (récapitulatif + Gantt détaillé) affichés à droite
            </p>
        </div>
        """)
        header.setWordWrap(True)

        # === COLONNE GAUCHE ===
        left = QVBoxLayout()
        left.addWidget(header)

        # Configuration
        config = QGroupBox("Configuration Journalière")
        config.setStyleSheet("font-weight:bold; border:3px solid #30363d; border-radius:16px; padding:20px;")
        grid = QGridLayout()
        labels = ["Projets max", "Tâches max/projet", "Nb Équipes(<=10) ", "Heures de travail/jour", "Durée max tâche(<=5h) "]
        self.spins = [
            QSpinBox(value=12, minimum=1, maximum=24),
            QSpinBox(value=8, minimum=1, maximum=24),
            QSpinBox(value=6, minimum=1, maximum=10),
            QDoubleSpinBox(value=24.0, minimum=1.0, maximum=24.0, decimals=1, singleStep=0.5),
            QSpinBox(value=5, minimum=1, maximum=5)
        ]
        for spin in self.spins:
            spin.setStyleSheet("font-size:16px; padding:10px;")
        for i, (txt, spin) in enumerate(zip(labels, self.spins)):
            grid.addWidget(QLabel(f"<b>{txt} :</b>"), i, 0)
            grid.addWidget(spin, i, 1)
        btn_apply = QPushButton("Appliquer")
        btn_apply.setStyleSheet("background:#238636; color:white; padding:12px 30px; border-radius:12px; font-size:16px;")
        btn_apply.clicked.connect(self.apply_config)
        grid.addWidget(btn_apply, 5, 1, Qt.AlignRight)
        config.setLayout(grid)
        left.addWidget(config)

        # Boutons
        btns = QHBoxLayout()
        for txt, col, func in [("Ajouter Projet", "#238636", self.add_project),
                               ("Lancer NOVA", "#8957e5", self.solve),
                               ("Nouvelle Journée", "#da3633", self.clear_all)]:
            b = QPushButton(txt)
            b.setStyleSheet(f"background:{col}; color:white; padding:18px 45px; border-radius:14px; font-weight:bold; font-size:17px;")
            b.clicked.connect(func)
            btns.addWidget(b)
        left.addLayout(btns)
        left.addStretch()

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMaximumWidth(int(self.width() * 0.38))

        # === COLONNE DROITE : Résultats avec scroll ===
        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setStyleSheet("background:#161b22; border-radius:18px; padding:30px; font-family: Consolas; font-size:16px; line-height:2; border: 3px solid #30363d;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.result)

        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(scroll, 2)
        self.setLayout(main_layout)

        self.log("Atelier NOVA prêt – interface adaptée à votre écran")

    def apply_config(self):
        self.config.update({
            "max_projects": self.spins[0].value(),
            "max_tasks_per_project": self.spins[1].value(),
            "nb_teams": self.spins[2].value(),
            "hours_per_day": self.spins[3].value(),
            "max_task_hours": self.spins[4].value()
        })
        self.teams = [f"Équipe {i+1}" for i in range(self.config["nb_teams"])]
        cap = self.config["hours_per_day"] * self.config["nb_teams"]
        self.log(f"<span style='color:#79c0ff; font-size:20px;'><b>Capacité : {cap}h ({self.config['nb_teams']} équipes × {self.config['hours_per_day']}h)</b></span>")

    def log(self, msg):
        self.result.append(f"<div style='margin:8px 0; color:#8b949e; font-size:16px;'>{msg}</div>")

    def clear_all(self):
        self.projects.clear()
        self.result.clear()
        self.log("Nouvelle journée démarrée.")

    def add_project(self):
        if len(self.projects) >= self.config["max_projects"]:
            QMessageBox.warning(self, "NOVA", "Maximum de projets atteint")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Nouveau Projet")
        dialog.resize(560, 520)
        layout = QVBoxLayout()

        layout.addWidget(QLabel("<h2 style='color:#58a6ff;'>Ajouter un Projet</h2>"))
        layout.addWidget(QLabel("<b>Nom du projet :</b>"))
        name_input = QLineEdit("Client Alpha")
        name_input.setStyleSheet("font-size:18px; padding:12px;")
        layout.addWidget(name_input)

        layout.addWidget(QLabel("<b>Nombre de tâches :</b>"))
        tasks_spin = QSpinBox(value=4, minimum=2, maximum=self.config["max_tasks_per_project"])
        tasks_spin.setStyleSheet("font-size:18px; padding:10px;")
        layout.addWidget(tasks_spin)

        durations = []
        def update():
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if isinstance(w, QSpinBox) and w != tasks_spin:
                    w.deleteLater()
            durations.clear()
            for i in range(1, tasks_spin.value() + 1):
                layout.addWidget(QLabel(f"<b>Tâche {i} – Durée (h) :</b>"))
                spin = QSpinBox(value=3, minimum=1, maximum=self.config["max_task_hours"])
                spin.setStyleSheet("font-size:18px; padding:10px;")
                durations.append(spin)
                layout.addWidget(spin)
        tasks_spin.valueChanged.connect(update)
        update()

        btn_ok = QPushButton("Valider")
        btn_ok.setStyleSheet("background:#238636; color:white; padding:16px; font-size:18px; font-weight:bold;")
        btn_ok.clicked.connect(dialog.accept)
        layout.addWidget(btn_ok)
        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            name = name_input.text().strip() or f"Projet {len(self.projects)+1}"
            dur_list = [float(s.value()) for s in durations]
            self.projects[name] = dur_list
            self.log(f"<br><b style='color:#79c0ff; font-size:20px;'>Projet : {name}</b>")
            for i, d in enumerate(dur_list, 1):
                self.log(f"   Tâche {i} → {d}h")
            self.log(f"<span style='color:#7ee787; font-size:18px;'>Projet ajouté avec succès</span>")

    def solve(self):
        if not self.projects:
            QMessageBox.warning(self, "NOVA", "Aucun projet")
            return

        total_hours = sum(sum(t) for t in self.projects.values())
        capacity = self.config["hours_per_day"] * self.config["nb_teams"]

        if total_hours > capacity:
            self.result.setHtml(f"""
            <h1 style='color:#ff4444;'>DÉPASSEMENT DE CAPACITÉ</h1>
            <p style='font-size:24px; color:#ffaaaa; line-height:2.2;'>
            Charge totale : <b>{total_hours}h</b> > Capacité : <b>{capacity}h</b><br><br>
            Impossible de tout terminer dans la journée.<br><br>
            <span style='color:#ffff66; font-size:26px;'>Augmenter les équipes ou reporter des tâches</span>
            </p>
            """)
            return

        self.log("<h2 style='color:#00ff88;'>Optimisation en cours...</h2>")
        try:
            m = gp.Model("NOVA")
            m.Params.OutputFlag = 0

            S, X = {}, {}
            for proj, tasks in self.projects.items():
                for t in range(len(tasks)):
                    S[(proj, t)] = m.addVar(lb=0)
                    for team in range(self.config["nb_teams"]):
                        X[(proj, t, team)] = m.addVar(vtype=GRB.BINARY)

            Cmax = m.addVar()
            bigM = 1e6
            first_proj = next(iter(self.projects))
            S[(first_proj, 0)].LB = S[(first_proj, 0)].UB = 0

            for proj, tasks in self.projects.items():
                for t in range(len(tasks)):
                    m.addConstr(gp.quicksum(X[(proj, t, team)] for team in range(self.config["nb_teams"])) == 1)
                for t in range(1, len(tasks)):
                    m.addConstr(S[(proj, t)] >= S[(proj, t-1)] + tasks[t-1])
                m.addConstr(Cmax >= S[(proj, len(tasks)-1)] + tasks[-1])

            for team in range(self.config["nb_teams"]):
                ops = [(p, t) for p, ts in self.projects.items() for t in range(len(ts))]
                for i in range(len(ops)):
                    for j in range(i+1, len(ops)):
                        a, b = ops[i], ops[j]
                        y = m.addVar(vtype=GRB.BINARY)
                        da = self.projects[a[0]][a[1]]
                        db = self.projects[b[0]][b[1]]
                        m.addConstr(S[b] >= S[a] + da - bigM * (3 - X[(a[0],a[1],team)] - X[(b[0],b[1],team)] - (1-y)))
                        m.addConstr(S[a] >= S[b] + db - bigM * (3 - X[(a[0],a[1],team)] - X[(b[0],b[1],team)] - y))

            m.setObjective(Cmax, GRB.MINIMIZE)
            m.optimize()

            if m.status == GRB.OPTIMAL:
                self.display_final_result(S, X, Cmax.X)
            else:
                self.log("<h2 style='color:#ff4444;'>Pas de solution optimale trouvée</h2>")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def display_final_result(self, S, X, makespan):
        colors = ["#f7768e","#ff9e64","#e0af68","#9ece6a","#73daca","#7aa2f7","#bb9af7","#c0caf5"]

        recap = "<h2 style='color:#58a6ff; font-size:30px;'>Récapitulatif des Tâches</h2>"
        recap += "<table style='width:100%; border-collapse:collapse; font-size:18px; background:#161b22;'><tr style='background:#21262d; height:60px;'><th>Projet</th><th>Tâche</th><th>Équipe</th><th>Début</th><th>Fin</th><th>Durée</th></tr>"
        for (proj, t), v in S.items():
            start = v.X
            dur = self.projects[proj][t]
            end = start + dur
            team_idx = next(i for i in range(self.config["nb_teams"]) if X.get((proj, t, i), None) and X[(proj, t, i)].X > 0.5)
            team = self.teams[team_idx]
            color = colors[hash(proj) % len(colors)]
            recap += f"<tr style='background:{color}22; height:55px;'><td style='padding:12px;'><b>{proj}</b></td><td style='padding:12px;'>Tâche {t+1}</td><td style='padding:12px; color:#79c0ff; font-weight:bold;'>{team}</td><td style='padding:12px;'>{start:.1f}h</td><td style='padding:12px;'>{end:.1f}h</td><td style='padding:12px;'>{dur}h</td></tr>"
        recap += "</table>"

        max_h = int(makespan) + 10
        hours = list(range(0, max_h + 1))
        grid = {team: ["-" for _ in hours] for team in self.teams}
        for (proj, t), v in S.items():
            start = int(v.X)
            dur = int(self.projects[proj][t])
            team_idx = next(i for i in range(self.config["nb_teams"]) if X.get((proj, t, i), None) and X[(proj, t, i)].X > 0.5)
            team = self.teams[team_idx]
            color = colors[hash(proj) % len(colors)]
            label = f"{proj[:9]}<br><b>T{t+1}</b>"
            for h in range(start, start + dur):
                if h < len(grid[team]):
                    grid[team][h] = f"<div style='background:{color}; color:black; padding:6px; border-radius:8px; font-size:11px; text-align:center; font-weight:bold;'>{label}</div>"

        gantt = "<h2 style='color:#58a6ff; margin-top:50px; font-size:30px;'>Gantt – Parallélisation</h2>"
        gantt += "<table style='border-collapse:collapse; width:100%; font-size:12px;'><tr style='background:#21262d;'><th style='padding:12px; min-width:120px;'>Équipe</th>"
        for h in hours: gantt += f"<th style='padding:8px; min-width:50px;'>{h}h</th>"
        gantt += "</tr>"
        for team in self.teams:
            gantt += f"<tr><td style='background:#1f6feb; color:white; padding:12px; font-weight:bold;'>{team}</td>"
            for cell in grid[team]:
                gantt += f"<td style='border:1px solid #30363d; text-align:center; height:70px; vertical-align:middle;'>{cell}</td>"
            gantt += "</tr>"
        gantt += "</table>"

        final = f"<h1 style='color:#00ff88; margin:60px 0; font-size:46px;'>TERMINÉ À {makespan:.1f}h</h1>"

        self.result.setHtml(f"<div style='line-height:2.2;'>{final}{recap}{gantt}</div>")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AtelierNOVA()
    window.show()
    sys.exit(app.exec_())