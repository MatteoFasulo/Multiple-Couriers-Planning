import os, re, json, sys, time
from itertools import combinations
from z3 import *
from utils import read_instance, parser_obj, check_symmetric, preprocess, path_sequence, write_json_solution

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


def main(args):
    if args.instance is None:
        print('Error: missing instance')
        sys.exit(1)
    instance = read_instance(args.instance)

    #print("Instance: ", instance)

    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = [0] + instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    D = preprocess(D)

    s = Optimize()
    s.set("timeout", 300_000)

    TENSOR = [[[Bool(f'TENSOR_{i}_{j}_{k}') for k in range(COURIERS)] for j in range(NODES)] for i in range(NODES)]

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

    # 7) size symmetry breaking:
    for k1 in range(COURIERS):
        for k2 in range(k1 + 1, COURIERS):
            if SIZE[k1] == SIZE[k2]:
                for i in range(NODES):
                    for j in range(i + 1, NODES):
                        s.add(Not(And(TENSOR[0][j][k1], TENSOR[0][i][k2])))

    # 8) Path symmetry breaking for symmetric matrix only
    if check_symmetric(D):
        for k in range(COURIERS):
            for i in range(NODES):
                for j in range(i + 1, NODES):
                    s.add(Not(And(TENSOR[0][j][k], TENSOR[i][0][k])))

    arr_dist = []
    for k in range(COURIERS):
        arr_dist.append(Sum([If(TENSOR[i][j][k], int(D[i][j]), 0) for i in range(NODES) for j in range(NODES)]))

    obj = max_z3(arr_dist)
    min_obj_val = s.minimize(obj)

    outcome = s.check()
    if outcome != sat:
        print('No solution found')
        return

    else:
        model = s.model()

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

        write_json_solution(args.instance, 'SAT', 'z3', s.statistics().get_key_value('time'), str(outcome) == 'sat', min_obj_val.value().as_long(), all_paths)


if __name__ == '__main__':
    args = parser_obj()
    if args.runall:
        for instance in sorted(os.listdir('Instances'), key=lambda x: int(re.search('\d+', x).group())):
            if instance.endswith('.dat'):
                args.instance = f'Instances{os.sep}{instance}'
                main(args)
    else:
        main(args)

