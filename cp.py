import argparse
import copy
import os, re, sys, datetime
from minizinc import Instance, Model, Solver, Status
import numpy as np
from concurrent.futures import ProcessPoolExecutor

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
    if args.model == 'default':
        model = Model('model.mzn')
    elif args.model == 'SB':
        model = Model('model_SB.mzn')

        # Add symmetry breaking constraint if the distance matrix is symmetric (1)
        #if problem["D_symmetric"]:
        #    model.add_string(
        #        r"""
        #        % Symmetry breaking for symmetric matrices
        #        % Order of traversing the tour
        #        constraint forall(k in COURIERS) (
        #            forall(i in ITEMS) (
        #                if couriers_nodes[k, i] = items+1 then
        #                    i <= couriers_nodes[k, items+1]
        #                endif
        #            )
        #        );
        #        """
        #    )

    if solver == Solver.lookup("gecode") or solver == Solver.lookup("com.google.ortools.sat"):
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
                %:: restart_luby(100)
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
    
    else:
        model.add_string(
            r"""
            solve minimize(obj);
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

    if solver == Solver.lookup("gecode"):
        try:
            time_needed = result.statistics['time'].total_seconds().__floor__()
        except KeyError:
            time_needed = 300
            optimal_sol = False
    elif solver == Solver.lookup("chuffed"):
        try:
            time_needed = result.statistics['time'].total_seconds().__floor__()
        except KeyError:
            time_needed = 300
            optimal_sol = False

    obj = max(result.solution.obj_dist)
    ITEMS = len(couriers_nodes[0])
    
    print(np.array(couriers_nodes).reshape(len(couriers_nodes), ITEMS))

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
    parser.add_argument('--solver', type=str, metavar='--s', help='Solver to use', choices=['gecode', 'chuffed', 'com.google.ortools.sat'])
    parser.add_argument('--seed', type=int, help='Set seed for solving', default=42, required=False)
    parser.add_argument('--model', type=str, metavar='--m', help='Model to use', choices=['default', 'SB'], default='default')
    parser.add_argument('--verbose', help='Verbose mode', default=False, required=False, action='store_true')

    args = parser.parse_args()
    
    if args.runall:
        with ProcessPoolExecutor(max_workers=os.cpu_count()//2) as executor:
            futures = []
            instances = sorted(os.listdir('Instances'), key=lambda x: int(re.search(r'\d+', x).group()))
            instances = [inst for inst in instances if inst.endswith('.dat')]
            for instance in instances:
                instance_args = copy.deepcopy(args)
                instance_args.instance = f'Instances{os.sep}{instance}'
                print(f"Running instance {instance_args.instance} with model {instance_args.model}")
                futures.append(executor.submit(main, instance_args))
            # Collect the results
            results = [future.result() for future in futures]

            print(results)

    elif args.instance:
        main(args)
    else:
        print('Error: missing instance')
        exit(1)