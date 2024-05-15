import os, re, json
from ortools.sat.python import cp_model
import numpy as np

from utils import read_instance, parser_obj

# https://how-to.aimms.com/Articles/332/332-Formulation-CVRP.html

def path_sequence_cost(path, D, as_solution:bool=False):
    """
    Calculate the cost of a path sequence
    """
    cost = 0
    for i,j in path:
        cost += D[i][j]
    return cost

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

def main():
    args = parser_obj()
    instance = read_instance(args.instance)

    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = [0] + instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    # Preprocess the distance matrix
    D = preprocess(D)

    print(D)

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
        model.Add(sum(TENSOR[i][j][k] for i in range(NODES) for k in range(COURIERS)) == 1)

    # 3) Every vehicle starts from the depot and ends at the depot
    for k in range(COURIERS):
        model.Add(sum(TENSOR[0][j][k] for j in range(1, NODES)) == 1)
        #model.Add(sum(TENSOR[j][0][k] for j in range(1, NODES)) == 1)

    # 4) Capacity constraints
    for k in range(COURIERS):
        model.Add(sum(SIZE[j] * TENSOR[i][j][k] for j in range(1, NODES) for i in range(NODES)) <= MAX_LOAD[k])

    # 5) Remove self-loops
    for i in range(NODES):
        for k in range(COURIERS):
            model.Add(TENSOR[i][i][k] == 0)

    # 6) Do not go come back to previous node
    for k in range(COURIERS):
        for i in range(1, NODES):
            for j in range(1, NODES):
                model.Add(TENSOR[i][j][k] + TENSOR[j][i][k] <= 1)

    # Objective function: minimize the maximum distance traveled by any vehicle
    arr_dist = []
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
    #solver.parameters.linearization_level = 2
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f'Objective value: {solver.ObjectiveValue()}')

        print(solver.ResponseStats())

        for k in range(COURIERS):
            path = []
            for i in range(NODES):
                for j in range(NODES):
                    if solver.Value(TENSOR[i][j][k]) == 1:
                        path.append((i,j))
                        print(f'Courier {k} travels from node {i} to node {j}')
            print(f'Path sequence: {path}, cost: {path_sequence_cost(path, D)}')
            print('\n')

        # Extract digit from string
        num = int(re.search('\d+', args.instance).group())
        with open(f'{os.getcwd()}{os.sep}res{os.sep}SAT{os.sep}{num}.json', 'w') as file:
            json.dump({
                'gecode':{ #TODO: change this, just to check the solution
                    'time': solver.WallTime(),
                    'optimal': status == cp_model.OPTIMAL,
                    'obj': int(solver.ObjectiveValue()),
                    # list of lists of paths
                    'sol': [[j for i in range(NODES-1) for j in range(1, NODES) if solver.Value(TENSOR[i][j][k]) == 1] for k in range(COURIERS)]
                }
            }, file, indent=4)

    else:
        print('No solution found')

if __name__ == '__main__':
    main()
