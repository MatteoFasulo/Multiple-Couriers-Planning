import os, re, sys, time, argparse
from itertools import combinations
from z3 import *

from utils import check_symmetric, compute_lower_bound, compute_upper_bound, path_sequence, preprocess, read_instance, write_json_solution


# Naive encoding
def at_least_one_np(bool_vars):
    return Or(bool_vars)


def at_most_one_np(bool_vars):
    return And([Not(And(pair[0], pair[1])) for pair in combinations(bool_vars, 2)])


def exactly_one_np(bool_vars, name = ""):
    return And(at_least_one_np(bool_vars), at_most_one_np(bool_vars))


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
    instance = read_instance(args.instance, depot=0)

    #print("Instance: ", instance)

    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = [0] + instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    start = time.time()
    symm = instance['D_symmetric']
    lower_bnd, _ = instance['lower_bound']
    upper_bnd = instance['upper_bound']

    s = Solver()
    s.set("timeout", 300_000)

    TENSOR = [[[Bool(f'x{i}_{j}_{k}') for k in range(COURIERS)] for j in range(NODES)] for i in range(NODES)]

    # 1) Vehicle leaves node it enters
    for i in range(NODES):
        for j in range(NODES):
            for k in range(COURIERS):
                s.add(Implies(TENSOR[i][j][k], Or([TENSOR[j][h][k] for h in range(NODES)])))

    # 2) Each node is entered and leaved just once by any vehicle
    for j in range(1, NODES):
        s.add(exactly_one_he([TENSOR[i][j][k] for i in range(NODES) for k in range(COURIERS)], f'valid_n_{j}'))
        s.add(exactly_one_he([TENSOR[j][i][k] for i in range(NODES) for k in range(COURIERS)], f'valid_node_{j}'))

    # 3) Every goes through the depot once
    for k in range(COURIERS):
        s.add(exactly_one_he([TENSOR[0][j][k] for j in range(1, NODES)], f'depot_in_{k}'))

    # 4) Remove self-loops
    for i in range(NODES):
        for k in range(COURIERS):
            s.add(Not(TENSOR[i][i][k]))

    # 5) Capacity constraints
    for k in range(COURIERS):
        s.add(Sum([SIZE[j] * If(TENSOR[i][j][k], 1, 0) for j in range(1, NODES) for i in range(NODES)]) <= MAX_LOAD[k])

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

    # 7) size symmetry breaking:
    for k1 in range(COURIERS):
        for k2 in range(k1 + 1, COURIERS):
            if MAX_LOAD[k1] == MAX_LOAD[k2]:
                for i in range(NODES):
                    for j in range(i + 1, NODES):
                        s.add(Not(And(TENSOR[0][j][k1], TENSOR[0][i][k2])))

    # 8) Path symmetry breaking for symmetric matrix only
    if symm:
        for k in range(COURIERS):
            for i in range(NODES):
                for j in range(i + 1, NODES):
                    s.add(Not(And(TENSOR[0][j][k], TENSOR[i][0][k])))

    arr_dist = []
    for k in range(COURIERS):
        arr_dist.append(Sum([If(TENSOR[i][j][k], int(D[i][j]), 0) for i in range(NODES) for j in range(NODES)]))

    obj = Int('max_distance')

    s.add(obj == max_z3(arr_dist))
    s.add(obj >= lower_bnd)
    s.add(obj <= upper_bnd)

    outcome = s.check()
    if outcome != sat:
        print('No solution found')
        return

    else:
        solved = False
        while True:
            s.set("timeout", 300_000 - int(time.time() - start)*1000)

            model = s.model()

            print(f'Best minimum found so far: {model[obj]}')
            s.add(obj < model[obj])

            outcome = s.check()
            if outcome != sat:
                if outcome == unsat:  # can also be unknown
                    solved = True
                break

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
            print('\n')
            all_paths.append(path)

        write_json_solution(args.instance,  'SAT', 'z3', int(time.time() - start), solved, model[obj].as_long(), all_paths)


if __name__ == '__main__':
    parser  = argparse.ArgumentParser(
        prog='SAT Solver with Z3 for Multiple Couriers Problem',
        description='SAT Solver with Z3 for Multiple Couriers Problem',
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

