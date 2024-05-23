import sys, datetime
from dataclasses import dataclass
from minizinc import Instance, Model, Solver
import numpy as np

from utils import read_instance, parser_obj, path_sequence

@dataclass
class MCPOutput:
    objective: int
    u: np.ndarray
    TENSOR: np.ndarray

def main():
    solver = Solver.lookup("chuffed")

    model = Model("mcp.mzn")
    #model.output_type = MCPOutput

    instance = Instance(solver, model)

    args = parser_obj()
    if args.instance is None:
        print('Error: missing instance')
        sys.exit(1)

    instance.add_file(args.instance.replace('dat', 'dzn'))
    problem = read_instance(args.instance)

    # Find and print all possible solutions
    COURIERS = problem["m"]
    NODES = problem["n"] + 1

    result = instance.solve(timeout=datetime.timedelta(seconds=10))
    if not result:
        print('No solution found')
        sys.exit(1)
    
    result = result.solution

    TENSOR = np.array(result.TENSOR).reshape(NODES, NODES, COURIERS)

    all_paths = []
    for k in range(COURIERS):
        path = []
        for i in range(NODES):
            for j in range(NODES):
                if TENSOR[i][j][k] == 1:
                    path.append((i,j))
        print(path)
        path_sequence(path)
        print(path)
        path = [x[1] for x in path[:-1]]
        print(path)
        print(f'Courier: {k}\tPath sequence: {path}')
        print('\n')
        all_paths.append(path)
    print(all_paths)

if __name__ == '__main__':
    main()