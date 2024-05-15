from ortools.sat.python import cp_model
import matplotlib.pyplot as plt
import numpy as np

from utils import read_instance, parser_obj


def main():
    args = parser_obj()
    instance = read_instance(args.instance)

    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = [0] + instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    model = cp_model.CpModel()

    # Decision Variables
    DISTANCE_MATRIX = []
    for k in range(COURIERS):
        DISTANCE_MATRIX.append([])
        for i in range(NODES):
            DISTANCE_MATRIX[k].append([])
            for j in range(NODES):
                DISTANCE_MATRIX[k][i].append(model.NewBoolVar(name=f"c_{k}_{i}_{j}"))
    
    # Convert it to a numpy array
    DISTANCE_MATRIX = np.array(DISTANCE_MATRIX)
    D = np.array(D)

    # Constraints
    # Each item is delivered by exactly one courier - aka each row/column has exactly one 1 in the 3D matrix
    for i in range(ITEMS):
        model.AddExactlyOne([DISTANCE_MATRIX[k][i][j] for k in range(COURIERS) for j in range(NODES) if j != i])
        model.AddExactlyOne([DISTANCE_MATRIX[k][j][i] for k in range(COURIERS) for j in range(NODES) if j != i])

    # All the couriers leave the depot
    for k in range(COURIERS):
        model.Add(DISTANCE_MATRIX[k][ITEMS][ITEMS] == 0)
        #model.Add(DISTANCE_MATRIX[k][NODES-1][0] == 1)

    # Weight constraint for each courier
    #for k in range(COURIERS):
    #    model.Add(sum([SIZE[i] * DISTANCE_MATRIX[k][i][j] for i in range(NODES) for j in range(NODES)]) <= MAX_LOAD[k])
    
    # Circuit constraint for each courier
    # Create the circuit constraint.
    arcs = []
    for k in range(COURIERS):
        for i in range(NODES):
            for j in range(NODES):
                if i != j:
                    arcs.append([i, j, DISTANCE_MATRIX[k][i][j]])

    model.AddCircuit(arcs)

    # OBJECTIVE FUNCTION - minimize the maximum distance travelled by any courier
    #obj = cp_model.LinearExpr.Sum([DISTANCE_MATRIX[k][i][j]*D[i, j] for k in range(COURIERS) for i in range(NODES) for j in range(NODES)])

    # MINIMIZATION OF THE OBJ FUNCTION
    #model.Minimize(obj)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 300.0 # Time Limit of 5 minutes
    #solver.parameters.log_search_progress = True
    #solver.parameters.linearization_level = 2
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:

        # Print the stats
        print(solver.ResponseStats())

        # Print the true variables for each courier
        print(np.array([[[solver.Value(DISTANCE_MATRIX[k][i][j]) for i in range(NODES)] for j in range(NODES)] for k in range(COURIERS)]))

    else:
        print("No solution found")

if __name__ == '__main__':
    main()