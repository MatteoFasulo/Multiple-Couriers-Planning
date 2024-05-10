import time
from ortools.sat.python import cp_model

from utils import read_instance, parser_obj

def main() -> None:
    args = parser_obj()
    instance = read_instance(args.instance)
    print(instance)

    # Variables
    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD_SIZE = instance['l']
    SIZE = instance['s']
    D = instance['D']

    # Model
    model = cp_model.CpModel()

    # Decision variables
    ...

    # Constraints
    ...

    # Objective
    ...

    # Minimize ...
    ...

    # Solve model
    solver = cp_model.CpSolver()

    # Status
    status = solver.solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        ...
    else:
        print("No solution found.")

    # Statistics
    if args.verbose:
        print("\nStatistics")
        print(f"  status   : {solver.status_name(status)}")
        print(f"  conflicts: {solver.num_conflicts}")
        print(f"  branches : {solver.num_branches}")
        print(f"  wall time: {solver.wall_time} s")

if __name__ == '__main__':
    main()