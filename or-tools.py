import os
import re
import argparse
from ortools.sat.python import cp_model

from utils import path_sequence, read_instance, write_json_solution

def main(args):
    instance = read_instance(args.instance, depot=0, padded_size=True)

    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    symm = instance['D_symmetric']
    lower_bnd, _ = instance['lower_bound']
    upper_bnd = instance['upper_bound']

    model = cp_model.CpModel()

    # Decision variables
    TENSOR = []
    for i in range(NODES):
        TENSOR.append([])
        for j in range(NODES):
            TENSOR[i].append([])
            for k in range(COURIERS):
                TENSOR[i][j].append(model.NewBoolVar(f'x_{i}_{j}_{k}'))
                    
    # Constraints
    # 1) Vehicle leaves node it enters
    for j in range(NODES):
        for k in range(COURIERS):
            model.Add(sum(TENSOR[i][j][k] for i in range(NODES)) == sum(TENSOR[j][i][k] for i in range(NODES)))

    # 2) Each node is entered just once by any vehicle
    for j in range(1, NODES):
        model.AddExactlyOne([TENSOR[i][j][k] for i in range(NODES) for k in range(COURIERS)])
        model.AddExactlyOne([TENSOR[j][i][k] for i in range(NODES) for k in range(COURIERS)])

    # 3) Every vehicle starts from the depot and ends at the depot
    for k in range(COURIERS):
        model.AddExactlyOne([TENSOR[0][j][k] for j in range(1, NODES)])

    # 4) Capacity constraints
    for k in range(COURIERS):
        model.Add(sum(SIZE[j] * TENSOR[i][j][k] for j in range(1, NODES) for i in range(NODES)) <= MAX_LOAD[k])

    # 5) Remove self-loops
    for i in range(NODES):
        for k in range(COURIERS):
            model.Add(TENSOR[i][i][k] == 0)

    # 6) Miller-Tucker-Zemlin formulation (MTZ)
    u = []
    Q = max(MAX_LOAD)
    for i in range(NODES):
        u.append(model.NewIntVar(SIZE[i], Q, f'u_{i}'))

    for k in range(COURIERS):
        for i in range(1, NODES):
            for j in range(1, NODES):
                if i != j:
                    model.Add(u[j] - u[i] >= SIZE[j] - Q*(1 - TENSOR[i][j][k]))

    # 6) All the items must be collected
    for i in range(1, NODES):
        model.add(sum(TENSOR[i][j][k] for j in range(NODES) for k in range(COURIERS)) == 1)

    # 7) size symmetry breaking:
    for k1 in range(COURIERS):
        for k2 in range(k1 + 1, COURIERS):
            if abs(MAX_LOAD[k1] - MAX_LOAD[k2]) < min(SIZE):
                for i in range(NODES):
                    for j in range(i + 1, NODES):
                        model.AddAtMostOne(TENSOR[0][j][k1], TENSOR[0][i][k2])

    # 8) Path symmetry breaking for symmetric matrix only
    if symm:
        for k in range(COURIERS):
            for i in range(NODES):
                for j in range(i + 1, NODES):
                    model.AddAtMostOne(TENSOR[0][j][k], TENSOR[i][0][k])

    # Objective function: minimize the maximum distance traveled by any vehicle
    arr_dist = []
    for k in range(COURIERS):
        arr_dist.append(sum(D[i][j] * TENSOR[i][j][k] for i in range(NODES) for j in range(NODES)))

    obj = model.NewIntVar(lower_bnd, upper_bnd, 'max_distance')
            
    model.AddMaxEquality(obj, arr_dist)

    # Minimize the objective function
    model.Minimize(obj)
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.timeout
    if args.verbose:
        solver.parameters.log_search_progress = True
    solver.parameters.num_search_workers = 12
    if symm:
        solver.parameters.symmetry_level = 3
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(solver.ResponseStats())

        all_paths = []
        for k in range(COURIERS):
            path = []
            for i in range(NODES):
                for j in range(NODES):
                    if solver.Value(TENSOR[i][j][k]) == 1:
                        path.append((i,j))
            cost = path_sequence(path, D)
            path = [x[1] for x in path[:-1]]
            print(f'Courier: {k}\tPath sequence: {path}\t cost: {cost}')
            print('\n')
            all_paths.append(path)

        write_json_solution(args.instance, 'SAT', 'ortools', solver.WallTime(), solver.StatusName() == 'OPTIMAL', int(solver.ObjectiveValue()), all_paths)

    else:
        print('No solution found')
        return

if __name__ == '__main__':
    parser  = argparse.ArgumentParser(
        prog='SAT Solver with Google OR-Tools for Multiple Couriers Problem',
        description='SAT Solver with Google OR-Tools for Multiple Couriers Problem',
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
