# model.py on fait 1 quart max/jour + pas de nuit → matin
from typing import List, Optional, Dict, Any
try:
    from gurobipy import Model as GurobiModel, GRB, quicksum
except Exception:
    GurobiModel = None
    GRB = None

class SchedulingModel:
    def __init__(self, E: int, D: int, S: int,
                 demand: List[List[int]],
                 max_shifts: int,
                 cost: Optional[List[List[List[float]]]] = None):
        self.E = E; self.D = D; self.S = S
        self.demand = demand
        self.max_shifts = max_shifts
        self.cost = cost if cost is not None else self._default_cost()

    def _default_cost(self):
        cost = [[[1.0 for _ in range(self.S)] for _ in range(self.D)] for _ in range(self.E)]
        if self.S >= 3:
            for e in range(self.E):
                for d in range(self.D):
                    cost[e][d][2] = 1.8  # Quart de nuit plus cher
        return cost

    def solve(self, time_limit: Optional[int] = None) -> Dict[str, Any]:
        if GurobiModel is None:
            return {'status': 'error', 'message': 'gurobipy non installé ou licence manquante'}

        try:
            m = GurobiModel("CallCenter")
            m.setParam('OutputFlag', 0)
            if time_limit:
                m.setParam('TimeLimit', time_limit)

            # Variables binaires : x[e,d,s] = 1 si agent e travaille quart s le jour d
            x = m.addVars(self.E, self.D, self.S, vtype=GRB.BINARY, name="x")

            #  1. CONTRAINTE : Au plus 1 quart par jour par agent 
            for e in range(self.E):
                for d in range(self.D):
                    m.addConstr(quicksum(x[e, d, s] for s in range(self.S)) <= 1,
                                name=f"un_quart_par_jour_{e}_{d}")

            # 2. CONTRAINTE : Pas de nuit (dernier quart) suivi du matin (premier quart) 
            if self.S >= 2:  # seulement si au moins 2 quarts
                for e in range(self.E):
                    for d in range(self.D - 1):  # tous les jours sauf le dernier
                        nuit_aujourdhui = x[e, d, self.S-1]      # dernier quart du jour d
                        matin_demain    = x[e, d+1, 0]           # premier quart du jour d+1
                        m.addConstr(nuit_aujourdhui + matin_demain <= 1,
                                    name=f"pas_nuit_matin_{e}_{d}")

            # Contraintes de couverture (demande minimale)
            for d in range(self.D):
                for s in range(self.S):
                    m.addConstr(quicksum(x[e, d, s] for e in range(self.E)) >= self.demand[d][s],
                                name=f"couverture_{d}_{s}")

            #  Max quarts par agent sur l'horizon 
            for e in range(self.E):
                m.addConstr(quicksum(x[e, d, s] for d in range(self.D) for s in range(self.S)) <= self.max_shifts,
                            name=f"max_quarts_{e}")

            #  Objectif : minimiser le coût total 
            obj = quicksum(self.cost[e][d][s] * x[e, d, s]
                           for e in range(self.E) for d in range(self.D) for s in range(self.S))
            m.setObjective(obj, GRB.MINIMIZE)

            m.optimize()

            if m.Status == GRB.OPTIMAL:
                sol = [[[int(x[e,d,s].X > 0.5) for s in range(self.S)]
                        for d in range(self.D)] for e in range(self.E)]
                return {
                    'status': 'optimal',
                    'obj': m.ObjVal,
                    'solution': sol,
                    'runtime': m.Runtime         
                }

            elif m.Status == GRB.INFEASIBLE:
                m.computeIIS()
                return {'status': 'infeasible',
                        'message': 'Modèle infaisable !\n'
                                   '→ Essayez : plus d\'agents, ou augmentez "Max quarts/agent"\n'
                                   '   ou réduisez la demande sur certains créneaux.'}
            else:
                return {'status': 'error', 'message': f'Gurobi status: {m.Status}'}

        except Exception as ex:
            return {'status': 'error', 'message': str(ex)}
