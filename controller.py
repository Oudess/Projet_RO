# controller.py 
from PyQt5 import QtCore
from model import SchedulingModel
import traceback

class SolverWorker(QtCore.QThread):
    finished = QtCore.pyqtSignal(dict)

    def __init__(self, params, time_limit=60):
        super().__init__()
        self.params = params
        self.time_limit = time_limit

    def run(self):
        try:
            model = SchedulingModel(**self.params)
            res = model.solve(time_limit=self.time_limit)
            self.finished.emit(res)
        except Exception as e:
            self.finished.emit({'status': 'error', 'message': traceback.format_exc()})


class SchedulerController:
    def __init__(self, view):
        self.view = view
        self.view.solve_requested.connect(self.on_solve_requested)
        self._worker = None

    def on_solve_requested(self, params):
        self.view.set_status("Résolution en cours avec Gurobi...")
        self.view.show_result("Gurobi optimise le planning...", sol=None)
        self._worker = SolverWorker(params)
        self._worker.finished.connect(self.on_finished)
        self._worker.start()

    def on_finished(self, result):
        status = result.get('status')

        if status == 'optimal':
            obj = result['obj']
            runtime = result.get('runtime', 0.0)   # ← temps de résolution en secondes
            sol = result['solution']

            # Formatage du texte avec le temps
            txt = self._format_solution(sol, obj, runtime)
            self.view.show_result(txt, sol)

            # Statut en vert avec le temps
            self.view.set_status(f"Solution optimale trouvée en {runtime:.3f} s")

        elif status == 'infeasible':
            msg = result.get('message', 'Modèle infaisable sans explication.')
            self.view.show_result("INFASIBLE\n\n" + msg)
            self.view.set_status("Infaisable – Ajustez les paramètres")

        else:
            msg = result.get('message', 'Erreur inconnue')
            self.view.show_result("ERREUR :\n" + msg)
            self.view.set_status("Erreur lors de la résolution")

    def _format_solution(self, sol, obj, runtime):
        E, D, S = len(sol), len(sol[0]), len(sol[0][0])
        lines = [
            f"Coût total = {obj:.2f} €",
            f"Solution optimale trouvée en {runtime:.3f} seconde(s)",
            "=" * 65,
            ""
        ]
        for e in range(E):
            shifts = sum(sum(day) for day in sol[e])
            if shifts > 0:
                lines.append(f"Agent {e+1} → {shifts} quarts")
                for d in range(D):
                    assigned = [s+1 for s in range(S) if sol[e][d][s]]
                    if assigned:
                        lines.append(f"   Jour {d+1} : quart(s) {', '.join(map(str, assigned))}")
                lines.append("")
        return "\n".join(lines)
