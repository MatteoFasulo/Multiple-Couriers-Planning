import json
import os
import re
import argparse
import numpy as np

# Read an instance in .dat format and parse the content to a suitable data structure.

def check_symmetric(D):
    """
    Check if the distance matrix is symmetric
    """
    return np.allclose(D, D.T)

def preprocess(D, depot: int = -1):
    """
    Preprocess the distance matrix
    """
    # load it as a numpy array
    D = np.array(D)
    if depot == 0: # take last row and col and put them in the first row and col shifting the rest
        D = np.insert(D, 0, D[-1], axis=0)
        D = np.delete(D, -1, axis=0)
        D = np.insert(D, 0, D[:, -1], axis=1)
        D = np.delete(D, -1, axis=1)
    return D

def get_nodes_and_weights(D):
    starting_nodes = []
    ending_nodes = []
    weights = []
    for i in range(1, len(D[0])+1):
        for j in range(1, len(D[0])+1):
            if i != j and i < len(D[0]):
                starting_nodes.append(i+1)
                ending_nodes.append(j+1)
                weights.append(D[i-1][j-1])
            elif i != j:
                starting_nodes.append(1)
                ending_nodes.append(j+1)
                weights.append(D[i-1][j-1])
            elif i == j and i == len(D[0]):
                starting_nodes.append(1)
                ending_nodes.append(len(D[0])+1)
                weights.append(0)

    return starting_nodes, ending_nodes, weights

def compute_lower_bound(D, MAX_LOAD, SIZE):
    """
    Compute the lower bound of the problem
    """
    # Get the last row and column from the distances matrix
    first_row = D[0]
    first_column = [D[i][0] for i in range(len(D[0]))]
    smallest_courier_capaciy = min(MAX_LOAD)
    largest_item_size = max(SIZE)

    # Calculate the maximum values for the last row and column
    max_value1 = first_column[np.argmax(first_row)] + np.max(first_row)
    max_value2 = first_row[np.argmax(first_column)] + np.max(first_column)

    # The lower bound is the maximum of these two values
    lb = np.max([max_value1, max_value2])

    # If all_travel is False, set the lower bound for courier distances to 0
    if not smallest_courier_capaciy >= largest_item_size:
        dist_lb = 0
    else:
        # Otherwise, calculate the minimum values for the last row and column
        min_value1 = first_column[np.argmin(first_row)] + np.min(first_row)
        min_value2 = first_row[np.argmin(first_column)] + np.min(first_column)

        # The lower bound for courier distances is the minimum of these two values
        dist_lb = np.min([min_value1, min_value2]) 

    # Return the lower bounds
    return lb, dist_lb

def compute_upper_bound(D, ITEMS):
    """
    Compute the upper bound of the problem
    """
    return sum([max(D[i]) for i in range(ITEMS)])
    

def read_instance(filename: str) -> dict:
    with open(filename, 'r') as file:
        data = file.read().splitlines()

    couriers = int(data[0])
    items = int(data[1])
    max_load = [int(x) for x in data[2].split()]
    sizes = [int(x) for x in data[3].split()]
    D = [[int(x) for x in line.split()] for line in data[4:]]

    # Preprocess the distance matrix
    D = preprocess(D, depot=0)

    # Sort the max load in descending order
    #max_load.sort(reverse=True)

    # Sort the items in ascending order
    #sizes.sort()

    # Insert 0 demand for the depot
    sizes.insert(0, 0)

    # Get starting nodes, ending nodes and weights
    starting_nodes, ending_nodes, weights = get_nodes_and_weights(D)
    
    return {
        'm': couriers,
        'n': items,
        'l': max_load,
        's': sizes,
        'D': D,
        'D_symmetric': check_symmetric(D),
        'lower_bound': compute_lower_bound(D, max_load, sizes),
        'upper_bound': compute_upper_bound(D, items),
        'starting_nodes': starting_nodes,
        'ending_nodes': ending_nodes,
        'weights': weights,
        'num_edges': len(starting_nodes)
    }

def path_sequence(path, D=None):
    """
    Calculate the cost of a path sequence
    """
    for idx in range(len(path) - 1):
        i, j = path[idx]
        if j == path[idx+1][0]:
            continue
        for pos in range(idx+1, len(path)):
            if j == path[pos][0]:
                path[idx+1], path[pos] = path[pos], path[idx+1]
                break

    if D is None:
        return
        
    cost = 0
    for i,j in path:
        cost += D[i][j]
    return cost

def convert_dat_to_dzn(filename: str):
    instance = read_instance(filename)
    with open(filename.replace('.dat', '.dzn'), 'w') as file:
        file.write(f'COURIERS = {instance["m"]};\n')
        file.write(f'ITEMS = {instance["n"]};\n')
        #file.write(f'n_edges = {instance["num_edges"]};\n')
        file.write(f'LOWER_BOUND = {instance["lower_bound"][0]};\n')
        file.write(f'UPPER_BOUND = {instance["upper_bound"]};\n')
        file.write(f'MAX_LOAD = {instance["l"]};\n')
        file.write(f'SIZE = {instance["s"]};\n')
        #file.write(f'starting_nd = {instance["starting_nodes"]};\n')
        #file.write(f'ending_nd = {instance["ending_nodes"]};\n')
        #file.write(f'weights = {instance["weights"]};\n')
        file.write('D = [|')
        for row in instance['D']:
            for elem in row:
                file.write(f'{elem}, ')
            file.write(f'\n|')
        file.write('];\n')

def write_json_solution(instance: str, folder: str, solver: str, time: int, optimal: bool, obj: int, sol: list):
    # Extract digit from string
    num = int(re.search(r'\d+', instance).group())

    # read the json file as a dictionary 
    if os.path.exists(f'{os.getcwd()}{os.sep}res{os.sep}{folder}{os.sep}{num}.json'):
        with open(f'{os.getcwd()}{os.sep}res{os.sep}{folder}{os.sep}{num}.json', 'r') as file:
            data = json.load(file)
        
        # Check if the same solver is present in the json file
        if solver in data:
            with open(f'{os.getcwd()}{os.sep}res{os.sep}{folder}{os.sep}{num}.json', 'w') as file:
                json.dump({
                    solver:{ 
                        'time': time,
                        'optimal': optimal,
                        'obj': obj,
                        'sol': sol
                    }
                }, file, indent=3)
            return False
        else:
            data[solver] = {
                'time': time,
                'optimal': optimal,
                'obj': obj,
                'sol': sol
            }
            with open(f'{os.getcwd()}{os.sep}res{os.sep}{folder}{os.sep}{num}.json', 'w') as file:
                json.dump(data, file, indent=3)

    # Create a new json file, first entry for that instance
    else:
        with open(f'{os.getcwd()}{os.sep}res{os.sep}{folder}{os.sep}{num}.json', 'w') as file:
            json.dump({
                solver: {
                    'time': time,
                    'optimal': optimal,
                    'obj': obj,
                    'sol': sol
                }
            }, file, indent=3)

    return True

def parser_obj():
    parser  = argparse.ArgumentParser(
        prog='CP OR',
        description='CP OR solver',
        epilog='Developed by: Antonio Gravina, Maksim Omelchenko & Matteo Fasulo'
    )

    parser.add_argument('--instance', type=str, metavar='--i', help='Input instance', required=False)
    parser.add_argument('--runall', help='Run all instances', default=False, required=False, action='store_true')
    parser.add_argument('--verbose', help='Verbose mode', default=False, required=False, action='store_true')
    parser.add_argument('--timeout', type=int, metavar='--t', help='Timeout for the solver', default=300, required=False)
    
    return parser.parse_args()

if __name__ == '__main__':
    args = parser_obj()
    if args.runall:
        for instance in sorted(os.listdir('Instances'), key=lambda x: int(re.search(r'\d+', x).group())):
            if instance.endswith('.dat'):
                args.instance = f'Instances{os.sep}{instance}'
                convert_dat_to_dzn(args.instance)
    elif args.instance:
        convert_dat_to_dzn(args.instance)
    else:
        print('Error: missing instance')
        exit(1)