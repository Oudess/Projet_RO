from PyQt5 import QtWidgets, QtCore, QtGui
from visualizer import VisualizationWidget
import os


class SchedulerView(QtWidgets.QWidget):
    solve_requested = QtCore.pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Planificateur Centre d'Appels - Gurobi Turbo")
        self.resize(1280, 780)
        self._last_solution = None
        self._last_demand = None

        # Fond clair pro
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(248, 250, 252))
        self.setPalette(palette)

        self._build_ui()
        self._load_sample_demand()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QtWidgets.QLabel("PLANIFICATEUR CENTRE D'APPELS")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 26px; font-weight: bold; color: white;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #3498db, stop:1 #2980b9);
                padding: 18px; border-radius: 12px;
            }
        """)
        layout.addWidget(title)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0; background: white; border-radius: 10px; }
            QTabBar::tab {
                background: #ecf0f1; color: #2c3e50; padding: 12px 30px; margin: 2px;
                border-top-left-radius: 8px; border-top-right-radius: 8px;
            }
            QTabBar::tab:selected { background: #3498db; color: white; font-weight: bold; }
        """)
        layout.addWidget(self.tabs)

        # ONGLET PARAMÈTRES
        self.tab_params = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_params, "Paramètres")
        grid = QtWidgets.QGridLayout(self.tab_params)
        grid.setSpacing(12)

        labels = ["Nombre d'agents", "Jours", "Quarts / jour", "Max quarts / agent"]
        defaults = [16, 7, 3, 12]
        ranges = [(5, 100), (1, 31), (2, 8), (1, 50)]
        self.spins = []
        for i, (txt, val, (minv, maxv)) in enumerate(zip(labels, defaults, ranges)):
            lbl = QtWidgets.QLabel(f"<b>{txt} :</b>")
            lbl.setStyleSheet("font-size: 14px; color: #2c3e50;")
            spin = QtWidgets.QSpinBox()
            spin.setRange(minv, maxv)
            spin.setValue(val)
            spin.setStyleSheet("""
                QSpinBox { padding: 10px; font-size: 16px; border: 2px solid #bdc3c7; border-radius: 8px; }
                QSpinBox:focus { border-color: #3498db; }
            """)
            spin.valueChanged.connect(self._update_demand_label)
            if txt == "Quarts / jour":
                spin.valueChanged.connect(self._update_cost_table)
            grid.addWidget(lbl, i, 0)
            grid.addWidget(spin, i, 1)
            self.spins.append(spin)

        # CADRE COÛTS PAR QUART 
        self.cost_group = QtWidgets.QGroupBox("Coûts par quart de travail")
        self.cost_group.setStyleSheet("""
            QGroupBox { font-weight: bold; color: #2c3e50; font-size: 15px; margin-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px; background: white; }
        """)
        self.cost_layout = QtWidgets.QFormLayout(self.cost_group)
        self.cost_spins = []
        grid.addWidget(self.cost_group, 4, 0, 1, 2)

        # Boutons
        btns = QtWidgets.QHBoxLayout()
        btns.addStretch()
        style_btn = lambda color: f"""
            QPushButton {{ background: {color}; color: white; font-weight: bold; font-size: 15px;
                          padding: 12px 24px; border-radius: 10px; border: none; }}
            QPushButton:hover {{ background: {QtGui.QColor(color).darker(115).name()}; }}
        """
        self.btnBuild = QtWidgets.QPushButton("Reconstruire")
        self.btnBuild.setStyleSheet(style_btn("#9b59b6"))
        self.btnBuild.clicked.connect(self._on_build)

        self.btnLoad = QtWidgets.QPushButton("Charger sample")
        self.btnLoad.setStyleSheet(style_btn("#e67e22"))
        self.btnLoad.clicked.connect(self._load_sample_demand)

        self.btnSafe = QtWidgets.QPushButton("Config 100% sûre")
        self.btnSafe.setStyleSheet(style_btn("#2ecc71"))
        self.btnSafe.clicked.connect(lambda: (self.spins[0].setValue(16), self.spins[3].setValue(12)))

        for b in (self.btnBuild, self.btnLoad, self.btnSafe):
            btns.addWidget(b)
        grid.addLayout(btns, 5, 0, 1, 2)

        # Tableau demande
        self.tableDemand = QtWidgets.QTableWidget()
        self.tableDemand.setStyleSheet("""
            QTableWidget { gridline-color: #95a5a6; background: white; font-size: 14px;
                          border: 2px solid #dcdcdc; border-radius: 10px; }
            QHeaderView::section { background: #34495e; color: white; padding: 8px; }
        """)
        self.tableDemand.itemChanged.connect(self._update_demand_label)
        grid.addWidget(self.tableDemand, 6, 0, 1, 2)

        # BANDEAU MAGIQUE
        self.demand_label = QtWidgets.QLabel("Calcul en cours...")
        self.demand_label.setAlignment(QtCore.Qt.AlignCenter)
        self.demand_label.setStyleSheet("""
            QLabel { font-size: 20px; font-weight: bold; padding: 15px; border-radius: 12px;
                     background: #fef9e7; border: 3px dashed #f39c12; }
        """)
        grid.addWidget(self.demand_label, 7, 0, 1, 2)

        # Bouton Résoudre
        solve_layout = QtWidgets.QHBoxLayout()
        self.btnSolve = QtWidgets.QPushButton("RÉSOUDRE AVEC GUROBI")
        self.btnSolve.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #2ecc71, stop:1 #27ae60);
                color: white; font-weight: bold; font-size: 22px;
                padding: 20px; border-radius: 15px; border: 4px solid #27ae60;
            }
            QPushButton:hover { transform: scale(1.05); }
        """)
        self.btnSolve.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btnSolve.clicked.connect(self._on_solve_clicked)

        self.statusLabel = QtWidgets.QLabel("Prêt")
        self.statusLabel.setStyleSheet("font-size: 16px; color: #27ae60; font-weight: bold;")
        solve_layout.addWidget(self.btnSolve)
        solve_layout.addWidget(self.statusLabel)
        grid.addLayout(solve_layout, 8, 0, 1, 2)

        # Onglets Résultats + Visualisation
        self.tab_results = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_results, "Résultats")
        res_layout = QtWidgets.QVBoxLayout(self.tab_results)
        self.resultBox = QtWidgets.QTextEdit()
        self.resultBox.setFont(QtGui.QFont("Consolas", 12))
        self.resultBox.setStyleSheet("background: #2c3e50; color: #1abc9c; padding: 15px; border-radius: 10px;")
        res_layout.addWidget(self.resultBox)

        self.tab_visu = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_visu, "Visualisation")
        visu_layout = QtWidgets.QVBoxLayout(self.tab_visu)
        self.canvas = VisualizationWidget()
        visu_layout.addWidget(self.canvas, stretch=1)

        visu_btns = QtWidgets.QHBoxLayout()
        visu_btns.addStretch()
        btn_load = QtWidgets.QPushButton("Charges par agent")
        btn_load.setStyleSheet("background: #3498db; color: white; font-weight: bold; padding: 16px 32px; border-radius: 12px; font-size: 16px; min-width: 220px;")
        btn_load.clicked.connect(self._visu_load)
        visu_btns.addWidget(btn_load)

        btn_heatmap = QtWidgets.QPushButton("Planning Hebdomadaire")
        btn_heatmap.setStyleSheet("background: #e67e22; color: white; font-weight: bold; padding: 16px 32px; border-radius: 12px; font-size: 16px; min-width: 220px;")
        btn_heatmap.clicked.connect(self._visu_heat)
        visu_btns.addWidget(btn_heatmap)
        visu_btns.addStretch()
        visu_layout.addLayout(visu_btns)

        self._on_build()
        self._update_cost_table()  # initialise les coûts au démarrage


    def _update_cost_table(self):
        S = self.spins[2].value()
        # Vide l’ancien
        for i in reversed(range(self.cost_layout.count())):
            child = self.cost_layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()
        self.cost_spins.clear()

        # Recrée les champs
        for s in range(S):
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(0.1, 20.0)
            spin.setSingleStep(0.1)
            spin.setDecimals(2)
            spin.setValue(1.8 if s == S - 1 else 1.0)
            spin.setStyleSheet("padding: 8px; font-size: 15px;")
            self.cost_spins.append(spin)

            label = f"Coût quart {s+1}" + (" (nuit)" if s == S - 1 else "") + " :"
            self.cost_layout.addRow(label, spin)

 
    def _on_build(self):
        D = self.spins[1].value()
        S = self.spins[2].value()
        self.tableDemand.blockSignals(True)
        self.tableDemand.setRowCount(D)
        self.tableDemand.setColumnCount(S)
        for s in range(S):
            self.tableDemand.setHorizontalHeaderItem(s, QtWidgets.QTableWidgetItem(f"Quart {s+1}"))
        for d in range(D):
            self.tableDemand.setVerticalHeaderItem(d, QtWidgets.QTableWidgetItem(f"Jour {d+1}"))
            for s in range(S):
                item = QtWidgets.QTableWidgetItem("2")
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.tableDemand.setItem(d, s, item)
        self.tableDemand.blockSignals(False)
        self._update_demand_label()
        self._update_cost_table()

    def _load_sample_demand(self):
        path = "sample_demand.csv"
        if os.path.exists(path):
            with open(path) as f:
                lines = [l.strip().split(',') for l in f if l.strip()]
            if lines:
                D, S = len(lines), len(lines[0])
                self.spins[1].setValue(D)
                self.spins[2].setValue(S)
                self._on_build()
                for d, row in enumerate(lines):
                    for s, val in enumerate(row):
                        if d < self.tableDemand.rowCount() and s < self.tableDemand.columnCount():
                            self.tableDemand.item(d, s).setText(val.strip())
        self._update_demand_label()

    def _update_demand_label(self):
        D = self.tableDemand.rowCount()
        S = self.tableDemand.columnCount()
        total = 0
        for d in range(D):
            for s in range(S):
                item = self.tableDemand.item(d, s)
                if item and item.text().isdigit():
                    total += int(item.text())
        agents = self.spins[0].value()
        max_shifts = self.spins[3].value()
        capacity = agents * max_shifts
        color = "#27ae60" if capacity >= total else "#e74c3c"
        status = "Faisable" if capacity >= total else "RISQUE D'INFAISABILITÉ"
        self.demand_label.setText(
            f"DEMANDE TOTALE = <b>{total}</b> quarts → "
            f"CAPACITÉ MAX = <b>{capacity}</b> ({agents} × {max_shifts}) → <b style='color:{color};'>{status}</b>"
        )


    def _collect_params(self):
        E, D, S = [sp.value() for sp in self.spins[:3]]
        demand = [[int(self.tableDemand.item(d, s).text() or 0) for s in range(S)] for d in range(D)]
        max_shifts = self.spins[3].value()

        user_costs = [spin.value() for spin in self.cost_spins]

       
        cost = []
        for e in range(E):
            agent_cost = []
            for d in range(D):
                day_cost = []
                for s in range(S):
                    day_cost.append(user_costs[s])   
                agent_cost.append(day_cost)
            cost.append(agent_cost)

        self._last_demand = demand
        return {"E": E, "D": D, "S": S, "demand": demand,
                "max_shifts": max_shifts, "cost": cost}

    def _on_solve_clicked(self):
        params = self._collect_params()
        self.solve_requested.emit(params)
        self.set_status("Gurobi en action...")

    def show_result(self, text: str, sol=None):
        self.resultBox.setPlainText(text)
        if sol is not None:
            self._last_solution = sol
            self.tabs.setCurrentIndex(1)

    def set_status(self, text: str):
        self.statusLabel.setText(text)
        if "optimal" in text.lower():
            self.statusLabel.setStyleSheet("color: #2ecc71; font-size: 18px; font-weight: bold;")
        elif "infaisable" in text.lower():
            self.statusLabel.setStyleSheet("color: #e74c3c; font-size: 18px; font-weight: bold;")
        else:
            self.statusLabel.setStyleSheet("color: #3498db; font-size: 16px;")

    def _visu_load(self):
        if self._last_solution:
            self.canvas.show_agent_load(self._last_solution)
            self.tabs.setCurrentIndex(2)

    def _visu_heat(self):
        if self._last_solution:
            self.canvas.show_heatmap(self._last_solution)
            self.tabs.setCurrentIndex(2)
