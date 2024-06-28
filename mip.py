from concurrent.futures import ProcessPoolExecutor
import copy
import time
import re
import os
import argparse
import pulp as plp


from utils import read_instance, write_json_solution, path_sequence

def main(args):
    if args.verbose:
        print(f"Running instance {args.instance}")
    instance = read_instance(args.instance, depot=0, padded_size=True)

    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    symm = instance['D_symmetric']
    lower_bnd = instance['lower_bound']
    upper_bnd = instance['upper_bound']

    effective_search_time = int(args.timeout - instance['preprocess_time'])

    # Decision variables
    TENSOR = plp.LpVariable.dicts("x", (range(NODES), range(NODES), range(COURIERS)), 0, 1, plp.LpBinary)
    max_var = plp.LpVariable("max_var", lowBound=lower_bnd, upBound=upper_bnd, cat=plp.LpInteger)
    u = [plp.LpVariable(f"u_{i}", lowBound=SIZE[i], upBound=max(MAX_LOAD), cat=plp.LpInteger) for i in range(NODES)]

    # Model
    cvrp_model = plp.LpProblem("CVRP", plp.LpMinimize) 

    # Constraints
    # 1) Each node is entered just once
    for j in range(1, NODES):
        cvrp_model += plp.lpSum([TENSOR[i][j][k] for i in range(NODES) for k in range(COURIERS) if i != j]) == 1, f"Node_{j}_once"
    
    # 2) Every behicle leaves the depot once
    for k in range(COURIERS):
        cvrp_model += plp.lpSum([TENSOR[0][j][k] for j in range(NODES)]) == 1, f"Depot_{k}_once"
    
    # 3) Vehicle leaves node it enters
    for i in range(NODES):
        for k in range(COURIERS):
            cvrp_model += plp.lpSum([TENSOR[i][j][k] for j in range(NODES) if i != j]) == plp.lpSum([TENSOR[j][i][k] for j in range(NODES) if i != j]), f"Node_{i}_Courier_{k}_balance"

    # 4) Remove self-loops
    for i in range(NODES):
        for k in range(COURIERS):
            cvrp_model += TENSOR[i][i][k] == 0, f"Self_loop_{i}_{k}"

    # 5) Capacity constraints
    for k in range(COURIERS):
        cvrp_model += plp.lpSum([SIZE[j] * TENSOR[i][j][k] for j in range(NODES) for i in range(NODES) if i != j]) <= MAX_LOAD[k], f"Capacity_{k}"

    # 6) Subtour elimination Miller-Tucker-Zemlin formulation
    Q = max(MAX_LOAD)
    for k in range(COURIERS):
        for i in range(1, NODES):
            for j in range(1, NODES):
                if i != j:
                    cvrp_model += u[j] - u[i] + Q * (1 - TENSOR[i][j][k]) >= SIZE[j], f"Subtour_{i}_{j}_{k}"

    # 7) Maximum distance constraint
    for k in range(COURIERS):
        cvrp_model += plp.lpSum([TENSOR[i][j][k] * D[i][j] for i in range(NODES) for j in range(NODES) if i != j]) <= max_var, f"Courier_{k}_max_distance"

    if args.model == 'SB':
        # 8) Symmetry breaking constraint: impose order on first node to visit
        for k in range(COURIERS-2):
            for i in range(NODES):
                for j in range(i + 1, NODES):
                    if i != j:
                        cvrp_model += TENSOR[0][j][k] + TENSOR[0][i][k+1] <= 1, f"Symmetry_breaking_{k}_{i}_{j}"
        
        # 9) Symmetry breaking constraint: remove inverse path solutions
        if symm:
            for k in range(COURIERS):
                for i in range(NODES):
                    for j in range(i + 1, NODES):
                        if i != j:
                            cvrp_model += TENSOR[i][j][k] + TENSOR[j][i][k] <= 1, f"Symmetry_breaking_inverse_{k}_{i}_{j}"

    # Objective function: minimize the maximum distance
    cvrp_model += max_var

    # Solve the model3
    if args.solver == 'CBC':
        solver = plp.PULP_CBC_CMD(msg=args.verbose, timeLimit=effective_search_time)
    elif args.solver == 'GLPK':
        solver = plp.GLPK_CMD(msg=args.verbose, timeLimit=effective_search_time)
    elif args.solver == 'COIN-OR':
        solver = plp.COIN_CMD(msg=args.verbose, timeLimit=effective_search_time)

    # Solve the model
    cvrp_model.solve(solver)

    time_needed = cvrp_model.solutionTime.__floor__()
    status = cvrp_model.status
    obj_val = int(plp.value(cvrp_model.objective))
    # Print the results
    if args.verbose:
        print(f"Status: {status}")
        print(f"Objective: {obj_val}")
        print(f"Time needed: {time_needed}")

    all_paths = []
    for k in range(COURIERS):
        path = []
        for i in range(NODES):
            for j in range(NODES):
                if TENSOR[i][j][k]:
                    path.append((i, j))
        cost = path_sequence(path, D)
        path = [x[1] for x in path[:-1]]
        if args.verbose:
            print(f'Courier: {k}\tPath sequence: {path}\t cost: {cost}')
        all_paths.append(path)

    write_json_solution(args.instance, 'MIP', f'{args.solver} {args.model}', time_needed, status == plp.LpStatusOptimal, obj_val, all_paths)

    return args.instance, obj_val, time_needed, obj_val


if __name__ == '__main__':
    parser  = argparse.ArgumentParser(
        prog='MIP Solver with PuLP for Multiple Couriers Problem',
        description='MIP Solver with PuLP for Multiple Couriers Problem',
        epilog='Developed by: Antonio Gravina, Maksim Omelchenko & Matteo Fasulo'
    )
    parser.add_argument('--instance', type=str, metavar='--i', help='Input instance', required=False)
    parser.add_argument('--runall', help='Run all instances', default=False, required=False, action='store_true')
    parser.add_argument('--timeout', type=int, metavar='--t', help='Timeout for the solver', default=300, required=False)
    parser.add_argument('--solver', type=str, metavar='--s', help='Solver to use', choices=['CBC', 'GLPK', 'COIN-OR'], default='CBC')
    parser.add_argument('--seed', type=int, help='Set seed for solving', default=42, required=False)
    parser.add_argument('--model', type=str, metavar='--m', help='Model to use', choices=['default', 'SB'], default='default')
    parser.add_argument('--verbose', help='Verbose mode', default=False, required=False, action='store_true')
    args = parser.parse_args()

    if args.runall:
        with ProcessPoolExecutor(max_workers=os.cpu_count()/2) as executor:
            futures = []
            instances = sorted(os.listdir('Instances'), key=lambda x: int(re.search(r'\d+', x).group()))
            instances = [inst for inst in instances if inst.endswith('.dat')]
            for instance in instances:
                instance_args = copy.deepcopy(args)
                instance_args.instance = f'Instances{os.sep}{instance}'
                futures.append(executor.submit(main, instance_args))
            # Collect the results
            results = [future.result() for future in futures]

            print(results)

    elif args.instance:
        main(args)
    else:
        print('Error: missing instance')
        exit(1)

