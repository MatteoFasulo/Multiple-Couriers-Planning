import argparse
import os, re, sys, datetime
from minizinc import Instance, Model, Solver, Status
import numpy as np

from utils import read_instance, write_json_solution

def main(args):
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
    model = Model("model.mzn")

    if solver == Solver.lookup("gecode"):
        model.add_string(
            r"""
            solve :: seq_search([
                    int_search(couriers_nodes, dom_w_deg, indomain_random),
                    int_search(loads, dom_w_deg, indomain_random)])
                minimize(obj);
            """
        )
    elif solver == Solver.lookup("chuffed"):
        model.add_string(
            r"""
            include "chuffed.mzn";
            solve :: seq_search([
                int_search(couriers_nodes, random_order, indomain_min),
                int_search(loads, random_order, indomain_min)
                ])
                minimize(obj);
            """
        )

    instance = Instance(solver, model)

    # Add the .dzn file to the instance input
    instance.add_file(instance_file)

    # Solve the instance with a timeout
    result = instance.solve(timeout=datetime.timedelta(seconds=args.timeout))

    # Check if a solution has been found
    if result.status is Status.UNKNOWN or result.status is Status.UNSATISFIABLE:
        print('No solution found')
        return

    # Retrieve the solution
    couriers_nodes = result.solution.couriers_nodes
    time_needed = result.statistics['solveTime'].total_seconds().__floor__()
    obj = max(result.solution.obj_dist)
    ITEMS = len(couriers_nodes[0])

    print(np.array(couriers_nodes).reshape(len(couriers_nodes), ITEMS))

    # Reorder the rows of couriers_nodes according to the order saved before sorting capacities in preprocessing
    #couriers_nodes = [couriers_nodes[i] for i in problem['old_order']]

    res = []
    for k in range(len(couriers_nodes)):
        asg = []
        start = ITEMS-1
        second = couriers_nodes[k][start]
        while second != ITEMS:
            asg.append(second)
            start = second - 1
            second = couriers_nodes[k][start]
        res.append(asg)

    print(f'Objective value: {obj}')
    print(f'Time needed: {time_needed} seconds')
    print(f'Solution: {res}')
    print(f'Status: {result.status}')

    write_json_solution(args.instance, 'CP', solver.name.lower(), time_needed, str(result.status) == 'OPTIMAL_SOLUTION' or 'ALL_SOLUTIONS', obj, res)

if __name__ == '__main__':
    parser  = argparse.ArgumentParser(
        prog='CP Solver for Multiple Couriers Problem',
        description='CP Solver for Multiple Couriers Problem',
        epilog='Developed by: Antonio Gravina, Maksim Omelchenko & Matteo Fasulo'
    )

    parser.add_argument('--instance', type=str, metavar='--i', help='Input instance', required=False)
    parser.add_argument('--runall', help='Run all instances', default=False, required=False, action='store_true')
    parser.add_argument('--timeout', type=int, metavar='--t', help='Timeout for the solver', default=300, required=False)
    parser.add_argument('--solver', type=str, metavar='--s', help='Solver to use', choices=['gecode', 'chuffed', 'com.google.ortools.sat'])
    parser.add_argument('--verbose', help='Verbose mode', default=False, required=False, action='store_true')
    args = parser.parse_args()
    
    if args.runall:
        for instance in sorted(os.listdir('Instances'), key=lambda x: int(re.search(r'\d+', x).group())):
            if instance.endswith('.dat'):
                print(instance)
                args.instance = f'Instances{os.sep}{instance}'
                main(args)
    elif args.instance:
        main(args)
    else:
        print('Error: missing instance')
        exit(1)