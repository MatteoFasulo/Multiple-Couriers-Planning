import argparse
import copy
import os, re, sys, datetime
from minizinc import Instance, Model, Solver, Status

from utils import read_instance, write_json_solution

def main(args):
    if args.verbose:
        print(f"Running instance {args.instance} with {args.solver} solver and {args.model} model")

    # Define the solver to use
    solver = Solver.lookup(args.solver)

    # Get the args from CLI
    if args.instance is None:
        print('Error: missing instance')
        sys.exit(1)

    # Retrieve the instance .dzn file
    instance_file = args.instance.replace('dat', 'dzn')

    # Retrieve the instance .dat file for checking properties
    problem = read_instance(args.instance)

    # Instantiate the model using the MiniZinc .mzn file
    if args.model == 'default':
        model = Model('model.mzn')
    elif args.model == 'SB':
        model = Model('model_SB.mzn')

    if solver == Solver.lookup("gecode"):
        if problem["D_symmetric"]:
            model.add_string(
                r"""
                solve :: seq_search([
                    int_search(couriers_nodes, first_fail, indomain_random),
                    int_search(loads, first_fail, indomain_min)])
                :: restart_luby(100)
                :: relax_and_reconstruct(loads, 70)
                    minimize(obj);
                """
            )

        else:
            model.add_string(
                r"""
                solve :: seq_search([
                    int_search(couriers_nodes, first_fail, indomain_min),
                    int_search(loads, first_fail, indomain_min)])
                    minimize(obj);
                """
            )

    elif solver == Solver.lookup("chuffed"):
        if problem["D_symmetric"]:
            model.add_string(
            r"""
            include "chuffed.mzn";
            solve :: seq_search([
                int_search(couriers_nodes, first_fail, indomain_min),
                int_search(loads, first_fail, indomain_min)])
            minimize(obj);
            """
        )
        
        else:
            model.add_string(
                r"""
                include "chuffed.mzn";
                solve :: seq_search([
                    int_search(couriers_nodes, first_fail, indomain_min),
                    int_search(loads, first_fail, indomain_min)])
                    minimize(obj);
                """
            )

    instance = Instance(solver, model)

    # Add the .dzn file to the instance input
    instance.add_file(instance_file)

    # Solve the instance with a timeout
    free_search_strategy = True
    if solver == Solver.lookup("gecode"):
        free_search_strategy = False

    result = instance.solve(timeout=datetime.timedelta(seconds=args.timeout), random_seed=args.seed, free_search=free_search_strategy)

    # Check if a solution has been found
    if result.status is Status.UNKNOWN or result.status is Status.UNSATISFIABLE:
        print('No solution found')
        return

    # Retrieve the solution
    couriers_nodes = result.solution.couriers_nodes
    optimal_sol = str(result.status) == 'OPTIMAL_SOLUTION'

    time_needed = result.statistics['time'].total_seconds().__floor__()
    if time_needed > args.timeout:
        time_needed = args.timeout
        optimal_sol = False

    obj = max(result.solution.obj_dist)
    ITEMS = len(couriers_nodes[0])

    res = []
    for k in range(len(couriers_nodes)):
        path = []
        start = ITEMS-1
        second = couriers_nodes[k][start]
        while second != ITEMS:
            path.append(second)
            start = second - 1
            second = couriers_nodes[k][start]
        res.append(path)

    if args.verbose:
        print(f'Status: {result.status}')
        print(f'Objective value: {obj}')
        print(f'Time needed: {time_needed} seconds')
        print(f'Solution: {res}')

    write_json_solution(args.instance, 'CP', f"{solver.name.lower()} {args.model}", time_needed, optimal_sol, obj, res)

    return args.instance, time_needed, obj

if __name__ == '__main__':
    parser  = argparse.ArgumentParser(
        prog='CP Solver for Multiple Couriers Problem',
        description='CP Solver for Multiple Couriers Problem',
        epilog='Developed by: Antonio Gravina, Maksim Omelchenko & Matteo Fasulo'
    )

    parser.add_argument('--instance', type=str, metavar='--i', help='Input instance', required=False)
    parser.add_argument('--runall', help='Run all instances', default=False, required=False, action='store_true')
    parser.add_argument('--timeout', type=int, metavar='--t', help='Timeout for the solver', default=300, required=False)
    parser.add_argument('--solver', type=str, metavar='--s', help='Solver to use', choices=['gecode', 'chuffed'])
    parser.add_argument('--seed', type=int, help='Set seed for solving', default=42, required=False)
    parser.add_argument('--model', type=str, metavar='--m', help='Model to use', choices=['default', 'SB'], default='default')
    parser.add_argument('--verbose', help='Verbose mode', default=False, required=False, action='store_true')

    args = parser.parse_args()
    
    if args.runall:
        instances = sorted(os.listdir('Instances'), key=lambda x: int(re.search(r'\d+', x).group()))
        instances = [inst for inst in instances if inst.endswith('.dat')]
        for instance in instances:
            instance_args = copy.deepcopy(args)
            instance_args.instance = f'Instances{os.sep}{instance}'
            main(instance_args)

    elif args.instance:
        main(args)
    else:
        print('Error: missing instance')
        exit(1)