import os, re, json, sys
import time
from itertools import combinations

from ortools.sat.python import cp_model
from z3 import *
import numpy as np

from utils import read_instance, parser_obj, check_symmetric, preprocess


def at_least_one(bool_vars):
    return Or(bool_vars)


def at_most_one(bool_vars):
    return [Not(And(pair[0], pair[1])) for pair in combinations(bool_vars, 2)]


def exactly_one(bool_vars):
    return at_most_one(bool_vars) + [at_least_one(bool_vars)]


def max_z3(vars):
    max_value = vars[0]
    for arg in vars[1:]:
        max_value = If(arg > max_value, arg, max_value)

    return max_value


def path_sequence_cost(path, D):
    """
    Calculate the cost of a path sequence
    """
    for idx in range(len(path) - 1):
        i, j = path[idx]
        if j == path[idx+1][0]:
            continue
        for pos in range(idx+1, len(path)):
            if j == path[pos][0]:
                path[idx+1], path[pos] = path[pos], path[idx+1]
                break
    cost = 0
    for i, j in path:
        cost += D[i][j]
    return cost


def main(args):
    if args.instance is None:
        print('Error: missing instance')
        sys.exit(1)
    instance = read_instance(args.instance)

    print("Instance: ", instance)

    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = [0] + instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    start = time.time()

    D = preprocess(D)

    s = Optimize()

    TENSOR = [[[Bool(f'TENSOR_{i}_{j}_{k}') for k in range(COURIERS)] for j in range(NODES)] for i in range(NODES)]

    # SMT_D = [[Int(f"D_{i}_{j}") for j in range(NODES)] for i in range(NODES)]
    #
    # for i in range(NODES):
    #     for j in range(NODES):
    #         s.add(SMT_D[i][j] == D[i][j])

    # 1) Vehicle leaves node it enters
    for j in range(NODES):
        for k in range(COURIERS):
            s.add(Sum([If(TENSOR[i][j][k], 1, 0) for i in range(NODES)]) == Sum([If(TENSOR[j][i][k], 1, 0) for i in range(NODES)]))

    # 2) Each node is entered just once by any vehicle
    for j in range(1, NODES):
        s.add(exactly_one([TENSOR[i][j][k] for i in range(NODES) for k in range(COURIERS)]))

    # 3) Depot is entered and leaved once by every courier
    for k in range(COURIERS):
        s.add(exactly_one([TENSOR[0][i][k] for i in range(NODES)]))

    # 4) Capacity constraints
    for k in range(COURIERS):
        s.add(Sum([SIZE[j] * If(TENSOR[i][j][k], 1, 0) for j in range(1, NODES) for i in range(NODES)]) <= MAX_LOAD[k])

    # 5) Remove self-loops
    for i in range(NODES):
        for k in range(COURIERS):
            s.add(Not(TENSOR[i][i][k]))


    # 6) Miller-Tucker-Zemlin formulation
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
                    # s.add(u[j] - u[i] >= SIZE[j] - Q * (1 - TENSOR[i][j][k]))

    arr_dist = []
    for k in range(COURIERS):
        arr_dist.append(Sum([If(TENSOR[i][j][k], int(D[i][j]), 0) for i in range(NODES) for j in range(NODES)]))

    obj = max_z3(arr_dist)
    s.minimize(obj)

    if s.check() == sat:
        model = s.model()
        all_paths = []
        max_cost = 0
        for k in range(COURIERS):
            path = []
            for i in range(NODES):
                for j in range(NODES):
                    if model[TENSOR[i][j][k]]:
                        path.append((i, j))
            cost = path_sequence_cost(path, D)

            if cost > max_cost:
                max_cost = cost

            path = [x[1] for x in path[:-1]]
            print(f'Courier: {k}\tPath sequence: {path}\t cost: {cost}')
            print('\n')
            all_paths.append(path)

            # Extract digit from string
            num = int(re.search('\d+', args.instance).group())
            # Write the results to a json file and if the same key is present, it will be overwritten
            with open(f'{os.getcwd()}{os.sep}res{os.sep}SAT{os.sep}{num}.json', 'w') as file:
                json.dump({
                    'gecode': {  # TODO: change this, just to check the solution
                        'time': int(time.time() - start),
                        'optimal': True,
                        'obj': int(max_cost),
                        'sol': all_paths
                    }
                }, file, indent=4)

    else:
        print('No solution found')


if __name__ == '__main__':
    args = parser_obj()
    if args.runall:
        for instance in sorted(os.listdir('Instances'), key=lambda x: int(re.search('\d+', x).group())):
            args.instance = f'Instances{os.sep}{instance}'
            main(args)
    else:
        main(args)

