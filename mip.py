from concurrent.futures import ProcessPoolExecutor
import copy
import re
import os
import argparse
import pulp as plp


from utils import read_instance, write_json_solution, get_solutions, plot_solution

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
    TENSOR = plp.LpVariable.dicts("x", (range(NODES), range(NODES), range(COURIERS)), cat=plp.LpBinary)
    max_var = plp.LpVariable("max_var", lowBound=lower_bnd, upBound=upper_bnd, cat=plp.LpInteger)

    # Model
    cvrp_model = plp.LpProblem("CVRP", plp.LpMinimize) 

    cvrp_model += max_var, "Objective"

    # Constraints
    # 1) Each node is entered just once
    for j in range(1, NODES):
        cvrp_model += plp.LpConstraint(plp.lpSum([TENSOR[i][j][k] for i in range(NODES) for k in range(COURIERS)]), sense=plp.LpConstraintEQ, rhs=1, name=f"Node_{j}_once")
    
    # 2) Every vehicle leaves the depot once
    for k in range(COURIERS):
        cvrp_model += plp.LpConstraint(plp.lpSum([TENSOR[0][j][k] for j in range(NODES)]), sense=plp.LpConstraintEQ, rhs=1, name=f"Leaves_depot_{k}_once")
    
    # 3) Vehicle leaves node it enters
    for i in range(NODES):
        for k in range(COURIERS):
            cvrp_model += plp.LpConstraint(plp.lpSum([TENSOR[i][j][k] for j in range(NODES)]) - plp.lpSum([TENSOR[j][i][k] for j in range(NODES)]), sense=plp.LpConstraintEQ, rhs=0, name=f"Node_{i}_Courier_{k}_balance")

    # 4) Remove self-loops
    for i in range(NODES):
        for k in range(COURIERS):
            cvrp_model += TENSOR[i][i][k] == 0, f"Self_loop_{i}_{k}"

    # 5) Capacity constraints
    for k in range(COURIERS):
        cvrp_model += plp.LpConstraint(plp.lpSum([SIZE[j] * TENSOR[i][j][k] for j in range(1, NODES) for i in range(NODES)]), sense=plp.LpConstraintLE, rhs=MAX_LOAD[k], name=f"Capacity_{k}")

    # 6) Subtour elimination Miller-Tucker-Zemlin formulation
    Q = max(MAX_LOAD)
    u = [plp.LpVariable(f"u_{i}", lowBound=SIZE[i], upBound=max(MAX_LOAD), cat=plp.LpInteger) for i in range(NODES)]
    
    for k in range(COURIERS):
        for i in range(1, NODES):
            for j in range(1, NODES):
                cvrp_model += u[i] + SIZE[j] * TENSOR[i][j][k] - Q * (1 - TENSOR[i][j][k]) <= u[j], f"Subtour_{k}_{i}_{j}"

    if args.model == 'SB':
        for k in range(COURIERS-2):
            cvrp_model += plp.lpSum([i * TENSOR[0][j][k] for i in range(1, NODES-1) for j in range(i + 1, NODES)]) <= plp.lpSum([i * TENSOR[0][j][k+1] for i in range(1, NODES-1) for j in range(i + 1, NODES)]), f"Order_{k}"
        
        # 8) Symmetry breaking constraint: remove inverse path solutions
        if symm:
            for k in range(COURIERS):
                for i in range(NODES):
                    for j in range(i + 1, NODES):
                        cvrp_model += plp.LpConstraint(TENSOR[i][j][k] + TENSOR[j][i][k], sense=plp.LpConstraintLE, rhs=1, name=f"Symmetry_breaking_inverse_{k}_{i}_{j}")

    # Objective function: minimize the maximum distance
    for k in range(COURIERS):
        cvrp_model += plp.lpSum([TENSOR[i][j][k] * D[i][j] for i in range(NODES) for j in range(NODES)]) <= max_var, f"Objective_{k}"

    # Solve the model3
    if args.solver == 'CBC':
        solver = plp.PULP_CBC_CMD(msg=args.verbose, timeLimit=effective_search_time, timeMode='cpu', options=[f"RandomS {args.seed}"])
    elif args.solver == 'GLPK':
        solver = plp.GLPK_CMD(msg=args.verbose, timeLimit=effective_search_time)

    # Solve the model
    cvrp_model.solve(solver)

    time_needed = cvrp_model.solutionTime.__floor__()
    status = cvrp_model.status
    if status == plp.LpStatusNotSolved or status == plp.LpStatusUndefined or status == plp.LpStatusInfeasible:
        return args.instance, None, None, None
    obj_val = int(plp.value(cvrp_model.objective))
    optimality = status == plp.LpStatusOptimal
    if time_needed >= effective_search_time:
        optimality = False

    # Print the results
    if args.verbose:
        print(f"Status: {plp.LpStatus[status]}")
        print(f"Objective: {obj_val}")
        print(f"Time needed: {time_needed}")

    all_paths = get_solutions(NODES, COURIERS, D, TENSOR, obj_val, args.verbose)
    if all_paths is None:
        return args.instance, None, None, None

    write_json_solution(args.instance, 'MIP', f'{args.solver} {args.model}', time_needed, optimality, obj_val, all_paths)

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
    parser.add_argument('--solver', type=str, metavar='--s', help='Solver to use', choices=['CBC', 'GLPK'], default='GLPK')
    parser.add_argument('--seed', type=int, help='Set seed for solving', default=42, required=False)
    parser.add_argument('--model', type=str, metavar='--m', help='Model to use', choices=['default', 'SB'], default='default')
    parser.add_argument('--verbose', help='Verbose mode', default=False, required=False, action='store_true')
    args = parser.parse_args()

    if args.runall:
        with ProcessPoolExecutor(max_workers=os.cpu_count()//2) as executor:
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

