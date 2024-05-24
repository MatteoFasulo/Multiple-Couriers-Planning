import sys, datetime
from minizinc import Instance, Model, Solver
import numpy as np

from utils import read_instance, parser_obj, path_sequence, check_symmetric, write_json_solution

def main():
    # Define the solver to use
    solver = Solver.lookup("chuffed")

    # Get the args from CLI
    args = parser_obj()
    if args.instance is None:
        print('Error: missing instance')
        sys.exit(1)

    # Retrieve the instance .dzn file
    instance_file = args.instance.replace('dat', 'dzn')

    # Retrieve the instance .dat file for checking properties
    problem = read_instance(args.instance)

    # Check if the distance matrix D is symmetric
    D_symmetric = check_symmetric(problem["D"])

    # Instantiate the model using the MiniZinc .mzn file
    model = Model("mcp.mzn")

    # Add one more constraint if the distance matrix is symmetric
    # 
    if D_symmetric:
        model.add_string(
            """
            constraint forall(i in 1..NODES, j in 1..NODES, k in 1..COURIERS) (
                (TENSOR[1,i,k] /\ TENSOR[j,1,k]) -> i <= j
            );
            """
        )

    if solver == Solver.lookup("gecode"):
        model.add_string(
            """
            % Solve the problem using LNS
            solve :: bool_search([TENSOR[i,j,k] | i in 1..NODES, j in 1..NODES, k in 1..COURIERS], dom_w_deg, indomain_min)
            :: relax_and_reconstruct([TENSOR[i,j,k] | i in 1..NODES, j in 1..NODES, k in 1..COURIERS], 85)
                  minimize obj;
            """
        )
    else:
        model.add_string(
            """
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
    result = instance.solve(timeout=datetime.timedelta(seconds=300))

    # Check if a solution has been found
    if not result:
        print('No solution found')
        sys.exit(1)

    # Convert the result to a numpy array and reshape it
    TENSOR = np.array(result.solution.TENSOR).reshape(NODES, NODES, COURIERS)

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
    
    write_json_solution(args.instance, 'SAT', solver.name.lower(), result.statistics['time'].total_seconds(), str(result.status) == 'OPTIMAL_SOLUTION', result.solution.objective, all_paths)

if __name__ == '__main__':
    main()