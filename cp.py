import os, re, sys, datetime
from minizinc import Instance, Model, Solver, Status
import numpy as np

from utils import *

def main(args):
    # Define the solver to use
    solver = Solver.lookup("gecode")

    # Get the args from CLI
    if args.instance is None:
        print('Error: missing instance')
        sys.exit(1)

    # Retrieve the instance .dzn file
    instance_file = args.instance.replace('dat', 'dzn')

    # Retrieve the instance .dat file for checking properties
    problem = read_instance(args.instance)

    # Instantiate the model using the MiniZinc .mzn file
    model = Model("mcp.mzn")

    # Add one more constraint if the distance matrix is symmetric
    # 
    if problem["D_symmetric"]:
        model.add_string(
        r"""
        constraint forall(k in 1..COURIERS, i in 1..NODES, j in i+1..NODES) (
            not(TENSOR[1,j,k] /\ TENSOR[i,1,k])
        );
        """
        )

    if solver == Solver.lookup("gecode"):
        model.add_string(
            r"""
            solve :: int_search([TENSOR[i,j,k] | i in 1..NODES, j in 1..NODES, k in 1..COURIERS], first_fail, indomain_min)
            minimize(obj);
            """
        )
    else:
        model.add_string(
            r"""
            solve minimize obj;
            """
        )

    instance = Instance(solver, model)

    # Add the .dzn file to the instance input
    instance.add_file(instance_file)

    # Define useful constant to iterate over
    COURIERS = problem["m"]
    NODES = problem["n"] + 1

    # Solve the instance with a timeout
    result = instance.solve(timeout=datetime.timedelta(seconds=args.timeout))

    # Check if a solution has been found
    if result.status is Status.UNKNOWN or result.status is Status.UNSATISFIABLE:
        print('No solution found')
        return

    print(result.solution)

    # Retrieve the solution
    TENSOR = result["TENSOR"]
    TENSOR = np.array(TENSOR).reshape(NODES, NODES, COURIERS)

    # Print the tensor
    all_paths = []
    for k in range(COURIERS):
        path = []
        for i in range(NODES):
            for j in range(NODES):
                if TENSOR[i][j][k] == 1:
                    path.append((i,j))
        path_sequence(path)
        path = [x[1] for x in path[:-1]]
        print(f'Courier: {k}\tPath sequence: {path}')
        print('\n')
        all_paths.append(path)

    write_json_solution(args.instance, 'CP', solver.name.lower(), result.statistics['solveTime'].total_seconds(), result.status is Status.OPTIMAL_SOLUTION, result.solution.objective, all_paths)

if __name__ == '__main__':
    args = parser_obj()
    if args.runall:
        for instance in sorted(os.listdir('Instances'), key=lambda x: int(re.search(r'\d+', x).group())):
            print(instance)
            if instance.endswith('.dat'):
                args.instance = f'Instances{os.sep}{instance}'
                main(args)
    else:
        main(args)