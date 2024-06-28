from concurrent.futures import ProcessPoolExecutor
import os, re, sys, time, argparse
from itertools import combinations
from z3 import *

from utils import path_sequence, read_instance, write_json_solution


# Naive pairwise encoding
def at_least_one_np(bool_vars, name = ""):
    return Or(bool_vars)


def at_most_one_np(bool_vars, name = ""):
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

def get_couriers_tours(model, x, NODES):
        path = []
        for i in range(NODES):
            for j in range(NODES):
                if model[x[i][j]]:
                    path.append((i, j))
        idx = 0
        couriers_tours = {}
        for i,j in path:
            if i == 0:
                couriers_tours[idx] = [j]
                idx += 1
            else:
                couriers_tours[idx-1].append(j)
        return couriers_tours


def main(args):
    if args.verbose:
        print(f"Running instance {args.instance}")
    instance = read_instance(args.instance, depot=0, padded_size=False)

    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    symm = instance['D_symmetric']
    lower_bnd = instance['lower_bound']
    upper_bnd = instance['upper_bound']

    effective_search_time = int(args.timeout - instance['preprocess_time'])*1000

    solver = Solver()
    solver.set("timeout", effective_search_time, "seed", args.seed)

    x = [[Bool(f'x_{i}_{j}') for j in range(NODES)] for i in range(NODES)]
    z = [[Bool(f'z_{k}_{j}') for j in range(ITEMS)] for k in range(COURIERS)]

    # Remove self loops
    for i in range(NODES):
        solver.add(Not(x[i][i]))

    # 1. Exactly k couriers leave the depot
    solver.add(Sum([If(x[0][j], 1, 0) for j in range(1, NODES)]) == COURIERS)

    # 2. Indegree constraint: sum of indegree is exactly 1 for each x_ij
    for j in range(1, NODES):
        solver.add(exactly_one_bw([x[i][j] for i in range(NODES) if i != j], f'ind_{j}'))

    # 3. Outdegree constraint: sum of outdegree is at most 1 for each x_ij
    for i in range(1, NODES):
        solver.add(exactly_one_bw([x[i][j] for j in range(1, NODES) if i != j], f'out_{i}'))

    # 4. Subtour elimination
    y = [Int(f'y_{i}') for i in range(ITEMS)]
    Q = max(MAX_LOAD)

    for i in range(ITEMS):
        solver.add(y[i] <= Q)
        solver.add(y[i] >= SIZE[i])

    for i in range(ITEMS):
        for j in range(ITEMS):
            if i != j:
                solver.add(y[j] - y[i] >= SIZE[j] + If(x[i+1][j+1], 0, -Q))

    # Add the load constraints for each courier
    for k in range(COURIERS):
        solver.add(Sum([If(z[k][j], SIZE[j], 0) for j in range(ITEMS)]) <= MAX_LOAD[k])
    
    # Add the assignment constraints for each item
    for j in range(ITEMS):
        solver.add(exactly_one_bw([z[k][j] for k in range(COURIERS)], f'assign_{j}'))

    # Channeling constraints
    #for k in range(COURIERS):
    #    for j in range(ITEMS):
    #        solver.add(Implies(z[k][j], Or([And(x[k][i], x[i][j]) for i in range(NODES)])))

    # Objective function

    obj = Int('max_distance')
    total_route_distance = Sum([Sum([If(x[i][j], int(D[i][j]), 0) for j in range(NODES)  if i != j]) for i in range(NODES)])
    
    solver.add(obj == total_route_distance)

    solver.add(obj >= lower_bnd)
    solver.add(obj <= upper_bnd)

    start = time.time()
    #print(s.dimacs()) 
    # Check if the problem is satisfiable
    print(solver)
    outcome = solver.check()
    # If the problem is satisfiable, enter the loop
    while outcome == sat and int(time.time() - start)*1000 < effective_search_time:
        # Get the model
        model = solver.model()

        # Retrieve the value of the objective function of the model
        print(f'Best minimum found so far: {model[obj]}')

        # Impose that the objective function is strictly less than the value of the objective function of the model
        solver.add(obj < model[obj])
        
        # Check if the problem is satisfiable
        outcome = solver.check()
    
    if solver.check() != sat:
        optimality = True
    else: # time has run out
        optimality = False

    print(model)
    print(MAX_LOAD, SIZE)
    print(f'Objective value: {model[obj]}')
    print(f'Preprocess time: {instance["preprocess_time"]}')
    print(f'Time needed: {int(time.time() - start)} seconds')
    print(f'Solution: {get_couriers_tours(model, x, NODES)}')
    print(f'Y: {[model[y[i]] for i in range(ITEMS)]}')
            

    #if cost > max_cost:
    #    max_cost = cost

    #path = [x[1] for x in path[:-1]]
    #print(f'Courier: {k}\tPath sequence: {path}\t cost: {cost}')
    #print('\n')
    #all_paths.append(path)

    #time_needed = int(time.time() - start)

    #write_json_solution(args.instance,  'SMT', 'z3', time_needed, optimality, model[obj].as_long(), all_paths)

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
            for instance in instances[:10]:
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

