from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
import os, re, time, argparse
from z3 import *

from utils import read_instance, write_json_solution, path_sequence


# Naive pairwise encoding
def at_least_one_np(bool_vars):
    return Or(bool_vars)

def at_most_one_np(bool_vars):
    return And([Not(And(pair[0], pair[1])) for pair in combinations(bool_vars, 2)])

# Heule encoding
def at_least_one_he(bool_vars):
    return at_least_one_np(bool_vars)


def at_most_one_he(bool_vars, name):
    if len(bool_vars) <= 4:
        return And([Not(And(pair[0], pair[1])) for pair in combinations(bool_vars, 2)])
    y = Bool(f"y_{name}")
    return And(And(at_most_one_np(bool_vars[:3] + [y])), And(at_most_one_he(bool_vars[3:] + [Not(y)], name+"_")))


def exactly_one_he(bool_vars, name):
    return And(at_most_one_he(bool_vars, name), at_least_one_he(bool_vars))

# Binary encoding
def toBinary(num, length = None):
    num_bin = bin(num).split("b")[-1]
    if length:
        return "0"*(length - len(num_bin)) + num_bin
    return num_bin
    
def at_least_one_bw(bool_vars):
    return at_least_one_np(bool_vars)

def at_most_one_bw(bool_vars, name):
    constraints = []
    n = len(bool_vars)
    m = math.ceil(math.log2(n))
    r = [Bool(f"r_{name}_{i}") for i in range(m)]
    binaries = [toBinary(i, m) for i in range(n)]
    for i in range(n):
        for j in range(m):
            phi = Not(r[j])
            if binaries[i][j] == "1":
                phi = r[j]
            constraints.append(Or(Not(bool_vars[i]), phi))        
    return And(constraints)

def exactly_one_bw(bool_vars, name):
    return And(at_least_one_bw(bool_vars), at_most_one_bw(bool_vars, name)) 


def max_z3(vars):
    max_value = vars[0]
    for arg in vars[1:]:
        max_value = If(arg > max_value, arg, max_value)
    return max_value


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

    # Create the solver
    s = Solver()
    s.set("timeout", args.timeout*1000, "seed", args.seed) # smtlib2_log="test.smt2"

    # Decision variables
    TENSOR = [[[Bool(f'x_{i}_{j}_{k}') for k in range(COURIERS)] for j in range(NODES)] for i in range(NODES)]
    obj = Int('max_distance')

    # 1) Vehicle leaves node it enters
    for i in range(NODES):
        for j in range(NODES):
            for k in range(COURIERS):
                s.add(Implies(TENSOR[i][j][k], Or([TENSOR[j][h][k] for h in range(NODES)])))

    # 2) Each node is entered and leaved just once by any vehicle
    for j in range(1, NODES):
        s.add(exactly_one_bw([TENSOR[i][j][k] for i in range(NODES) for k in range(COURIERS)], f'valid_n_{j}'))
        s.add(exactly_one_bw([TENSOR[j][i][k] for i in range(NODES) for k in range(COURIERS)], f'valid_node_{j}'))

    # 3) Every courier goes through the depot once
    for k in range(COURIERS):
        s.add(exactly_one_bw([TENSOR[0][j][k] for j in range(1, NODES)], f'depot_in_{k}'))

    # 4) Remove self-loops
    for i in range(NODES):
        for k in range(COURIERS):
            s.add(Not(TENSOR[i][i][k]))

    # 5) Capacity constraints
    for k in range(COURIERS):
        s.add(Sum([If(TENSOR[i][j][k], SIZE[j], 0) for j in range(1, NODES) for i in range(NODES)]) <= MAX_LOAD[k])

    # 6) subtour elimination Miller-Tucker-Zemlin formulation
    u = [Int(f'u_{i}') for i in range(NODES)]
    Q = max(MAX_LOAD)

    for i in range(NODES):
        s.add(u[i] <= Q)
        s.add(u[i] >= SIZE[i])

    for k in range(COURIERS):
        for i in range(1, NODES):
            for j in range(1, NODES):
                if i != j:
                    s.add(u[j] - u[i] >= SIZE[j] + If(TENSOR[i][j][k], 0, -Q))

    if args.model == 'SB':
        # 7) Symmetry breaking: impose ordering on first item delivered by couriers (2)
        for k1 in range(COURIERS):
            for k2 in range(k+1, COURIERS-1):
                if MAX_LOAD[k] == MAX_LOAD[k2]:
                    for i in range(NODES):
                        for j in range(i + 1, NODES):
                            s.add(Not(And(TENSOR[0][j][k1], TENSOR[0][i][k2])))
        
        # Only if Graph is undirected since {1,3,5,9} = {9,5,3,1}
        #if symm:
        #    # 8) Symmetry breaking constraint: remove inverse path solutions
        #    for k in range(COURIERS):
        #        for i in range(NODES):
        #            for j in range(i + 1, NODES):
        #                s.add(Not(And(TENSOR[0][j][k], TENSOR[i][0][k])))

    # Define the objective function
    s.add(obj == max_z3([Sum([If(TENSOR[i][j][k], int(D[i][j]), 0) for i in range(NODES) for j in range(NODES)]) for k in range(COURIERS)]))

    # Add the bounds
    s.add(obj >= lower_bnd)
    s.add(obj <= upper_bnd)

    # Start the timer
    start = time.time()
    
    # Check if the problem is satisfiable
    if s.check() != sat: # The problem is unsatisfiable
        print('Unsatisfiable problem')
        return args.instance, None, None

    # Binary search for the optimal solution. The search is performed by decreasing the upper bound and increasing the lower bound
    # If the problem is SAT, the upper bound is decreased, otherwise the lower bound is increased until the bounds are adjacent

    # Initially set the optimality to False
    optimality = False
    previous = True
    # Set the satisfiable flag to True
    satisfiable = True
    # While the problem is satisfiable keep searching for the optimal solution
    while satisfiable:
        elapsed_time = time.time() - start
        if elapsed_time >= args.timeout:
            if args.verbose:
                print('Timeout reached')
            break
        # Verbose
        if args.verbose:
            print('Time:', elapsed_time)
            print(f'Upper: {upper_bnd}\tLower: {lower_bnd}\tTime: {int(time.time() - start)}s')
        # Compute new bounds
        bound_dist = (upper_bnd - lower_bnd) / 2
        # If the bounds are adjacent, set the midpoint to the lower bound
        if upper_bnd - lower_bnd < 1:
            break
        # Otherwise, set the midpoint to the upper bound minus the bound distance and search for the optimal solution
        else:
            midpoint = upper_bnd - bound_dist

        # Update the maximum
        if args.verbose:
            print(f'New midpoint: {midpoint}')
        # Add the new constraints
        s.add(obj <= midpoint)
        s.add(obj >= lower_bnd)

        # If the previous solution was found, push the solver
        if previous:
            s.push() # Create a backtracking point
            previous = False

        # Check the status of the solver
        status = s.check()

        elapsed_time = time.time() - start
        if elapsed_time >= args.timeout:
            if args.verbose:
                print('Timeout reached')
            break
        if args.verbose:
            print('Time:', elapsed_time)

        # If the status is unsatisfiable, set the lower bound to the midpoint and pop the solver to the previous state
        if status == unsat:
            lower_bnd = midpoint
            previous = True
            s.pop() # jump back to the last backtrack point

        # If the status is satisfiable, set the upper bound to the objective value
        elif status == sat:
            model = s.model()
            upper_bnd = model[obj].as_long()
            previous = False
            last_satisfiable_model = model  # Save the last satisfiable model
            optimality = True  # Set optimality to True

    # If the loop exited because a solution was found, set optimality to True
    optimality = True
    if not model and last_satisfiable_model:
        model = last_satisfiable_model

    time_needed = elapsed_time.__floor__()
    if time_needed > args.timeout:
        time_needed = args.timeout
        optimality = False

    all_paths = []
    max_cost = 0
    for k in range(COURIERS):
        path = []
        for i in range(NODES):
            for j in range(NODES):
                if model[TENSOR[i][j][k]]:
                    path.append((i, j))
        cost = path_sequence(path, D)

        if cost > max_cost:
            max_cost = cost

        path = [x[1] for x in path[:-1]]
        print(f'Courier: {k}\tPath sequence: {path}\t cost: {cost}')
        all_paths.append(path)

    write_json_solution(args.instance,  'SMT', f'z3 {args.model}', time_needed, optimality, model[obj].as_long(), all_paths)

    return args.instance, time_needed, model[obj].as_long()


if __name__ == '__main__':
    parser  = argparse.ArgumentParser(
        prog='SMT Solver with Z3 for Multiple Couriers Problem',
        description='SMT Solver with Z3 for Multiple Couriers Problem',
        epilog='Developed by: Antonio Gravina, Maksim Omelchenko & Matteo Fasulo'
    )
    parser.add_argument('--instance', type=str, metavar='--i', help='Input instance', required=False)
    parser.add_argument('--runall', help='Run all instances', default=False, required=False, action='store_true')
    parser.add_argument('--timeout', type=int, metavar='--t', help='Timeout for the solver', default=300, required=False)
    parser.add_argument('--solver', type=str, metavar='--s', help='Solver to use', choices=['z3'], default='z3')
    parser.add_argument('--seed', type=int, help='Set seed for solving', default=42, required=False)
    parser.add_argument('--model', type=str, metavar='--m', help='Model to use', choices=['default', 'SB'], default='default')
    parser.add_argument('--verbose', help='Verbose mode', default=False, required=False, action='store_true')
    args = parser.parse_args()

    if args.runall:
        with ProcessPoolExecutor(max_workers=os.cpu_count()//2) as executor:
            futures = []
            instances = sorted(os.listdir('Instances'), key=lambda x: int(re.search(r'\d+', x).group()))
            instances = [inst for inst in instances if inst.endswith('.dat')]
            # Run only the first 10 instances as the others are not even compiling due to the model size and constraints
            for instance in instances[:10]: 
                instance_args = copy.deepcopy(args)
                instance_args.instance = f'Instances{os.sep}{instance}'
                futures.append(executor.submit(main, instance_args))
            # Collect the results
            results = [future.result() for future in futures]

            if args.verbose:
                print(results)

    elif args.instance:
        main(args)
    else:
        print('Error: missing instance')
        exit(1)

