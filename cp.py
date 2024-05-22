import sys
from dataclasses import dataclass
from minizinc import Instance, Model, Solver
import numpy as np

from utils import read_instance, parser_obj, check_symmetric, preprocess

@dataclass
class MCPOutput:
    objective: int
    u: np.ndarray
    TENSOR: np.ndarray

def main():
    gecode = Solver.lookup("gecode")

    model = Model("mcp.mzn")
    model.output_type = MCPOutput

    instance = Instance(gecode, model)

    args = parser_obj()
    if args.instance is None:
        print('Error: missing instance')
        sys.exit(1)

    problem = read_instance(args.instance)

    instance["COURIERS"] = problem['m']
    instance["ITEMS"] = problem['n']
    instance["MAX_LOAD"] = problem['l']
    instance["SIZE"] = [0] + problem['s']
    instance["D"] = problem['D']

    # Find and print all possible solutions
    result = instance.solve().solution
    print(result)

if __name__ == '__main__':
    main()