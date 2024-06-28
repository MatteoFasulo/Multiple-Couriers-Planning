import gurobipy as gp
from gurobipy import GRB

import os, re, time, argparse

from utils import read_instance, write_json_solution, path_sequence

def main(args):
    instance = read_instance(args.instance, depot=0, padded_size=True)

    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    start = time.time()
    symm = instance['D_symmetric']
    lower_bnd = instance['lower_bound']
    upper_bnd = instance['upper_bound']

    m = gp.Model()

    TENSOR = [[[m.addVar(vtype=GRB.BINARY, name=f'x{i}_{j}_{k}') for k in range(COURIERS)]
               for j in range(NODES)] for i in range(NODES)]

    # 1) Each node is entered just once by any vehicle
    for j in range(1, NODES):
        m.addConstr(gp.quicksum([TENSOR[i][j][k] for i in range(NODES) for k in range(COURIERS)]) == 1)

    # 2) Every goes through the depot once
    for k in range(COURIERS):
        m.addConstr(gp.quicksum([TENSOR[0][j][k] for j in range(NODES)]) == 1)

    # 3) Vehicle leaves node it enters same amount of times (0 or 1)
    for i in range(NODES):
        for k in range(COURIERS):
            m.addConstr(gp.quicksum([TENSOR[i][j][k] for j in range(NODES)]) ==
                        gp.quicksum([TENSOR[j][i][k] for j in range(NODES)]))

    # 4) Remove self-loops
    for i in range(NODES):
        for k in range(COURIERS):
            m.addConstr(TENSOR[i][i][k] == 0)

    # 5) Capacity constraints
    for k in range(COURIERS):
        m.addConstr(gp.quicksum([SIZE[j] * TENSOR[i][j][k] for j in range(1, NODES) for i in range(NODES)]) <= MAX_LOAD[k])

    # 6) subtour elimination Miller-Tucker-Zemlin formulation
    Q = max(MAX_LOAD)
    u = [m.addVar(vtype=GRB.INTEGER, name=f'u_{i}', lb=SIZE[i], ub=Q) for i in range(NODES)]

    for k in range(COURIERS):
        for i in range(1, NODES):
            for j in range(1, NODES):
                if i != j:
                    m.addConstr(u[j] - u[i] + Q*(1 - TENSOR[i][j][k]) >= SIZE[j])

    # 7) size symmetry breaking:
    # for k1 in range(COURIERS):
    #     for k2 in range(k1 + 1, COURIERS):
    #         if MAX_LOAD[k1] == MAX_LOAD[k2]:
    #             for i in range(NODES):
    #                 for j in range(i + 1, NODES):
    #                     m.addConstr(TENSOR[0][j][k1] + TENSOR[0][i][k2] <= 1)

    # # 8) Path symmetry breaking for symmetric matrix only
    if symm:
        for k in range(COURIERS):
            for i in range(NODES):
                for j in range(i + 1, NODES):
                    m.addConstr(TENSOR[0][j][k] + TENSOR[i][0][k] <= 1)

    max_var = m.addVar(name="max", vtype=GRB.INTEGER, lb=lower_bnd, ub=upper_bnd)
    for k in range(COURIERS):
        m.addConstr(gp.quicksum(TENSOR[i][j][k] * D[i][j] for i in range(NODES) for j in range(NODES)) <= max_var)

    m.setObjective(max_var, GRB.MINIMIZE)

    m.optimize()

    print(f"Obj: {m.ObjVal:g}")
    all_paths = []
    max_cost = 0
    for k in range(COURIERS):
        path = []
        for i in range(NODES):
            for j in range(NODES):
                if TENSOR[i][j][k].X:
                    path.append((i, j))
        cost = path_sequence(path, D)

        if cost > max_cost:
            max_cost = cost

        path = [x[1] for x in path[:-1]]
        print(f'Courier: {k}\tPath sequence: {path}\t cost: {cost}')
        print('\n')
        all_paths.append(path)

    write_json_solution(args.instance, 'MIP', 'gurobi', int(time.time() - start), True, int(m.ObjVal), all_paths)


if __name__ == '__main__':
    parser  = argparse.ArgumentParser(
        prog='MIP',
        description='MIP',
        epilog='Developed by: Antonio Gravina, Maksim Omelchenko & Matteo Fasulo'
    )
    parser.add_argument('--instance', type=str, metavar='--i', help='Input instance', required=False)
    parser.add_argument('--runall', help='Run all instances', default=False, required=False, action='store_true')
    parser.add_argument('--timeout', type=int, metavar='--t', help='Timeout for the solver', default=300, required=False)
    parser.add_argument('--verbose', help='Verbose mode', default=False, required=False, action='store_true')
    args = parser.parse_args()

    if args.runall:
        for instance in sorted(os.listdir('Instances'), key=lambda x: int(re.search(r'\d+', x).group())):
            if instance.endswith('.dat'):
                args.instance = f'Instances{os.sep}{instance}'
                main(args)
    elif args.instance:
        main(args)
    else:
        print('Error: missing instance')
        exit(1)

