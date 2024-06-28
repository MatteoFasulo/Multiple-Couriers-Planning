from concurrent.futures import ProcessPoolExecutor
import os, re, sys, time, argparse
from itertools import combinations
from z3 import *

from utils import path_sequence, read_instance, write_json_solution


# Naive pairwise encoding
def at_least_one_np(bool_vars):
    return Or(bool_vars)


def at_most_one_np(bool_vars):
    return And([Not(And(pair[0], pair[1])) for pair in combinations(bool_vars, 2)])


def exactly_one_np(bool_vars, name = ""):
    return And(at_least_one_np(bool_vars), at_most_one_np(bool_vars))

# Sequence encoding
def at_least_one_seq(bool_vars):
    return at_least_one_np(bool_vars)

def at_most_one_seq(bool_vars, name):
    constraints = []
    n = len(bool_vars)
    s = [Bool(f"s_{name}_{i}") for i in range(n - 1)]
    constraints.append(Or(Not(bool_vars[0]), s[0]))
    constraints.append(Or(Not(bool_vars[n-1]), Not(s[n-2])))
    for i in range(1, n - 1):
        constraints.append(Or(Not(bool_vars[i]), s[i]))
        constraints.append(Or(Not(bool_vars[i]), Not(s[i-1])))
        constraints.append(Or(Not(s[i-1]), s[i]))
    return And(constraints)

def exactly_one_seq(bool_vars, name):
    return And(at_least_one_seq(bool_vars), at_most_one_seq(bool_vars, name))

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

    effective_search_time = int(args.timeout - instance['preprocess_time'])

    s = Solver()
    s.set("timeout", effective_search_time*1000, "seed", args.seed, smtlib2_log="test.smt2")

    TENSOR = [[[Bool(f'x{i}_{j}_{k}') for k in range(COURIERS)] for j in range(NODES)] for i in range(NODES)]

    # 1) Vehicle leaves node it enters
    for i in range(NODES):
        for j in range(NODES):
            for k in range(COURIERS):
                if i != j:
                    s.add(Implies(TENSOR[i][j][k], Or([TENSOR[j][h][k] for h in range(NODES)])))

    # 2) Each node is entered and leaved just once by any vehicle
    for j in range(1, NODES):
        s.add(exactly_one_bw([TENSOR[i][j][k] for i in range(NODES) for k in range(COURIERS) if i != j], f'valid_n_{j}'))
        s.add(exactly_one_bw([TENSOR[j][i][k] for i in range(NODES) for k in range(COURIERS) if i != j], f'valid_node_{j}'))

    # 3) Every goes through the depot once
    for k in range(COURIERS):
        s.add(exactly_one_bw([TENSOR[0][j][k] for j in range(1, NODES)], f'depot_in_{k}'))

    # 4) Remove self-loops
    for i in range(NODES):
        for k in range(COURIERS):
            s.add(Not(TENSOR[i][i][k]))

    # 5) Capacity constraints
    for k in range(COURIERS):
        s.add(Sum([SIZE[j] * If(TENSOR[i][j][k], 1, 0) for j in range(1, NODES) for i in range(NODES) if i != j]) <= MAX_LOAD[k])

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

    # 7) size symmetry breaking: TODO: Out of date
    #for k1 in range(COURIERS):
    #    for k2 in range(k1 + 1, COURIERS):
    #        if MAX_LOAD[k1] == MAX_LOAD[k2]:
    #            for i in range(NODES):
    #                for j in range(i + 1, NODES):
    #                    s.add(Not(And(TENSOR[0][j][k1], TENSOR[0][i][k2])))

    # 7.2) Ordering symmetry breaking: first item delivered by each courier has a lesser value, with the last courier being an exception
    #for k in range(COURIERS-2):
    #    for i in range(NODES):
    #        for j in range(i + 1, NODES):
    #            s.add(Implies(TENSOR[0][j][k], Not(TENSOR[0][i][k+1])))

    # 8) Path symmetry breaking for symmetric matrix only
    if symm:
        for k in range(COURIERS):
            for i in range(NODES):
                for j in range(i + 1, NODES):
                    s.add(Not(And(TENSOR[0][j][k], TENSOR[i][0][k])))

    arr_dist = []
    for k in range(COURIERS):
        arr_dist.append(Sum([If(TENSOR[i][j][k], int(D[i][j]), 0) for i in range(NODES) for j in range(NODES) if i != j]))

    obj = Int('max_distance')

    s.add(obj == max_z3(arr_dist))
    s.add(obj >= lower_bnd)
    s.add(obj <= upper_bnd)

    # Start the timer
    start = time.time()
    #print(s.dimacs()) 
    
    # Check if the problem is satisfiable
    if s.check() != sat:
        print(s)
        raise Exception('Unsatisfiable problem') # The problem is unsatisfiable

    # Initially set the optimality to False
    optimality = False
    previous = True
    # Set the satisfiable flag to True
    satisfiable = True
    # While the problem is satisfiable keep searching for the optimal solution
    while satisfiable:
        # Verbose
        print(f'Upper: {upper_bnd}\tLower: {lower_bnd}\tTime: {int(time.time() - start)}s')
        # Compute new bounds
        bound_dist = (upper_bnd - lower_bnd) // 2
        # If the bounds are adjacent, set the midpoint to the lower bound
        if upper_bnd - lower_bnd <= 1:
            midpoint = lower_bnd
            break
        # Otherwise, set the midpoint to the upper bound minus the bound distance and search for the optimal solution
        else:
            midpoint = upper_bnd - bound_dist

        # Update the maximum
        print(f'New midpoint: {midpoint}')
        s.add(obj <= midpoint)
        s.add(obj >= lower_bnd)

        # If the previous solution was found, push the solver
        if previous:
            s.push()
            previous = False

        # Check the status of the solver
        status = s.check()

        # Update the wall clock time
        current_time = int(time.time() - start)

        # If the status is unsatisfiable, set the lower bound to the midpoint and pop the solver to the previous state
        if status == unsat:
            lower_bnd = midpoint
            previous = True
            s.pop()

        # If the status is satisfiable, set the upper bound to the objective value
        elif status == sat:
            model = s.model()
            upper_bnd = model[obj].as_long()
            previous = False
            last_satisfiable_model = model  # Save the last satisfiable model
            optimality = True  # Set optimality to True


        # If the current time is greater than the effective search time, break the loop (timeout)
        if current_time > effective_search_time:
            time_needed = effective_search_time
            break

    # If the loop exited because a solution was found, set optimality to True
    if s.check() == sat:
        optimality = True
    if not model and last_satisfiable_model:
        model = last_satisfiable_model
    time_needed = current_time

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
        print(f'Courier: {k}\tPath sequence: {path}\t cost: {cost}\t load: {sum([SIZE[node-1] for node in path])}')
        print('\n')
        all_paths.append(path)

    write_json_solution(args.instance,  'SMT', 'z3', time_needed, optimality, model[obj].as_long(), all_paths)

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
    parser.add_argument('--seed', type=int, help='Set seed for solving', default=42, required=False)
    parser.add_argument('--model', type=str, metavar='--m', help='Model to use', choices=['default', 'SB'], default='default')
    parser.add_argument('--verbose', help='Verbose mode', default=False, required=False, action='store_true')
    args = parser.parse_args()

    if args.runall:
        with ProcessPoolExecutor(max_workers=1) as executor:
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

