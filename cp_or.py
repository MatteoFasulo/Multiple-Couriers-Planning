import os, re, json, sys
from ortools.sat.python import cp_model
import numpy as np

from utils import read_instance, parser_obj

def path_sequence_cost(path, D):
    """
    Calculate the cost of a path sequence
    """
    for idx, (i,j) in enumerate(path[:-1]):
        if j == path[idx+1][0]:
            continue
        for pos in range(idx+1, len(path)):
            if j == path[pos][0]:
                path[idx+1], path[pos] = path[pos], path[idx+1]
                break
    cost = 0
    for i,j in path:
        cost += D[i][j]
    return cost

def check_symmetric(D):
    """
    Check if the distance matrix is symmetric
    """
    return np.allclose(D, D.T)

def preprocess(D):
    """
    Preprocess the distance matrix
    """
    # load it as a numpy array
    D = np.array(D)
    D = np.insert(D, 0, D[-1], axis=0)
    D = np.delete(D, -1, axis=0)
    D = np.insert(D, 0, D[:, -1], axis=1)
    D = np.delete(D, -1, axis=1)
    return D

def apply_constraints(model, TENSOR, NODES, COURIERS, SIZE, MAX_LOAD):
    # 1) Vehicle leaves node it enters
    for j in range(NODES):
        for k in range(COURIERS):
            model.Add(sum(TENSOR[i][j][k] for i in range(NODES)) == sum(TENSOR[j][i][k] for i in range(NODES)))

    # 2) Each node is entered just once by any vehicle
    for j in range(1, NODES):
        model.AddExactlyOne([TENSOR[i][j][k] for i in range(NODES) for k in range(COURIERS)]) # TODO: at least one here if the courier can go the two tours (???)

    # 3) Every vehicle starts from the depot and ends at the depot
    for k in range(COURIERS):
        model.AddExactlyOne([TENSOR[0][j][k] for j in range(1, NODES)]) # assumption of courier doing one routing path

    # 4) Capacity constraints
    for k in range(COURIERS):
        model.AddElement
        model.Add(sum(SIZE[j] * TENSOR[i][j][k] for j in range(1, NODES) for i in range(NODES)) <= MAX_LOAD[k])

    # 5) Remove self-loops
    for i in range(NODES):
        for k in range(COURIERS):
            model.Add(TENSOR[i][i][k] == 0)

    # 6) All the items must be collected
    for i in range(1, NODES):
        model.add(sum(TENSOR[i][j][k] for j in range(NODES) for k in range(COURIERS)) == 1)

    # 7) Explicit Dantzig-Fulkerson-Johnson (subtour elimination)
    # Generate all possible subsets (except the empty set and sets with depot)
    #for i in range(1, (2**(NODES-1))):
    #    #print(bin(i))
    #    subset = []
    #    notsubset = [0]
    #    t = 1
    #    while t < NODES:
    #        if i % 2 == 1:
    #            subset.append(t)
    #        else:
    #            notsubset.append(t)
    #        i //= 2
    #        t += 1
    #    if len(subset)<2:
    #        continue
#
    #    #print(subset, notsubset)
    #    
    #    S = 0
    #    for node1 in subset:
    #        for node2 in notsubset:
    #            for k in range(COURIERS):
    #                S += TENSOR[node1][node2][k] + TENSOR[node2][node1][k]
#
    #    model.Add(S >= 2)

    # 8) Miller-Tucker-Zemlin formulation # TODO: check this constraint
    u = []
    for k in range(COURIERS):
        u.append([])
        for i in range(NODES):
            u[k].append(model.NewIntVar(0, NODES, f'u_{k}_{i}'))

    for k in range(COURIERS):
        for i in range(1, NODES):
            for j in range(1, NODES):
                if i != j:
                    model.Add(u[k][i] - u[k][j] + 1 <= (NODES - 1)*(1 - TENSOR[i][j][k]))

def main(args):
    if args.instance is None:
        print('Error: missing instance')
        sys.exit(1)
    instance = read_instance(args.instance)

    print("Instance: ", args.instance)

    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = [0] + instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    # Preprocess the distance matrix
    D = preprocess(D)
    symm = check_symmetric(D)

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
    apply_constraints(model, TENSOR, NODES, COURIERS, SIZE, MAX_LOAD)

    # Objective function: minimize the maximum distance traveled by any vehicle
    arr_dist = []
    if symm:
        # We're only considering the upper triangular part of the matrix
        for k in range(COURIERS):
            arr_dist.append(sum(D[i][j] * TENSOR[i][j][k] for i in range(NODES) for j in range(i+1, NODES))) 

        obj = model.NewIntVar(0, sum(sum(row[i:]) for i, row in enumerate(D)), 'max_distance')
    else:
        for k in range(COURIERS):
            arr_dist.append(sum(D[i][j] * TENSOR[i][j][k] for i in range(NODES) for j in range(NODES)))
        
        obj = model.NewIntVar(0, sum(sum(row) for row in D), 'max_distance')
    model.AddMaxEquality(obj, arr_dist)

    # Minimize the objective function
    model.Minimize(obj)
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 300
    solver.parameters.log_search_progress = True
    #solver.parameters.num_search_workers = 1
    solver.parameters.linearization_level = 2
    solver.parameters.symmetry_level = 1
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
            cost = path_sequence_cost(path, D)
            path = [x[1] for x in path[:-1]]
            print(f'Courier: {k}\tPath sequence: {path}\t cost: {cost}')
            print('\n')
            all_paths.append(path)

        # Extract digit from string
        num = int(re.search('\d+', args.instance).group())
        # Write the results to a json file and if the same key is present, it will be overwritten
        with open(f'{os.getcwd()}{os.sep}res{os.sep}SAT{os.sep}{num}.json', 'w') as file:
            json.dump({
                'gecode':{ #TODO: change this, just to check the solution
                    'time': int(solver.WallTime()),
                    'optimal': status == cp_model.OPTIMAL,
                    'obj': int(solver.ObjectiveValue()),
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
