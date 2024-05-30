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

def subtour_presence(MAX_LOAD, SIZE) -> bool:
    """
    Check if there is a subtour presence
    """
    return min(MAX_LOAD) >= max(SIZE)

def compute_lower_bound(D, depot: int = -1):
    """
    Compute the lower bound of the problem
    """
    # Select the first row and column if depot is 0, else select the last row and column
    row = D[0, :] if depot == 0 else D[-1, :]
    column = D[:, 0] if depot == 0 else D[:, -1]

    # Calculate the maximum indices for the row and column
    max_idx_row = np.argmax(row)
    max_idx_column = np.argmax(column)

    # The lower bound is the maximum of these two values
    lb = max(column[max_idx_row] + np.max(row), row[max_idx_column] + np.max(column))

    # Get the non-zero elements of the row and column
    nonzero_row = row[np.nonzero(row)]
    nonzero_column = column[np.nonzero(column)]

    # Calculate the minimum indices for the row and column
    min_idx_row = np.argmin(nonzero_row)
    min_idx_column = np.argmin(nonzero_column)

    # The lower bound for courier distances is the minimum of these two values
    dist_lb = min(column[min_idx_row] + np.min(nonzero_row), row[min_idx_column] + np.min(nonzero_column))

    # Return the lower bounds
    return lb, dist_lb


def compute_upper_bound(D, MAX_LOAD):
    """
    Compute the upper bound of the problem
    """
    COURIERS = len(MAX_LOAD)
    # Calculate the maximum value per row
    max_per_row = np.max(D, axis=1)
    # Sort the maximum values
    sorted_arr = np.sort(max_per_row)
    # Get the first n-couriers+1 values where n is the number of nodes and couriers is the number of couriers
    # This accounts for the case where one courier makes almost all the deliveries and the rest make only one
    sliced_arr = sorted_arr[COURIERS-1:]
    # Sum the sliced values
    val = np.sum(sliced_arr)

    return val

def sort_couriers(MAX_LOAD):
    """
    Sort the couriers based on their capacity and return the dictionary
    """
    max_load_dict = {idx: val for idx, val in enumerate(MAX_LOAD)}
    max_load_dict = dict(sorted(max_load_dict.items(), key=lambda item: item[1], reverse=True))
    return max_load_dict
    

def read_instance(filename: str, depot: int = -1) -> dict:
    with open(filename, 'r') as file:
        data = file.read().splitlines()

    couriers = int(data[0])
    items = int(data[1])
    max_load = [int(x) for x in data[2].split()]
    sizes = [int(x) for x in data[3].split()]
    D = [[int(x) for x in line.split()] for line in data[4:]]

    # Preprocess the distance matrix
    D = preprocess(D, depot=depot)

    # Sort the max load in descending order and save old order
    #max_load = sort_couriers(max_load)
    #idxs, values = zip(*max_load.items())

    # Sort the items in ascending order
    #sizes.sort()

    # Insert 0 demand for the depot
    #sizes.insert(0, 0)
    
    return {
        'm': couriers,
        'n': items,
        'l': max_load,
        's': sizes,
        'D': D,
        'D_symmetric': check_symmetric(D),
        'lower_bound': compute_lower_bound(D, depot=depot),
        'upper_bound': compute_upper_bound(D, max_load),
        #'old_order': list(idxs)
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
        file.write(f'couriers = {instance["m"]};\n')
        file.write(f'items = {instance["n"]};\n')
        file.write(f'LOWER_BOUND = {instance["lower_bound"][0]};\n')
        file.write(f'DIST_LOWER_BOUND = {instance["lower_bound"][1]};\n')
        file.write(f'UPPER_BOUND = {instance["upper_bound"]};\n')
        file.write(f'CAPACITY = {instance["l"]};\n')
        file.write(f'DEMAND = {instance["s"]};\n')
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

if __name__ == '__main__':
    parser  = argparse.ArgumentParser(
        prog='Utility for Solvers of Multiple Couriers Problem',
        description='Utility for Solvers of Multiple Couriers Problem',
        epilog='Developed by: Antonio Gravina, Maksim Omelchenko & Matteo Fasulo'
    )

    parser.add_argument('--instance', type=str, metavar='--i', help='Input instance', required=False)
    parser.add_argument('--runall', help='Run all instances', default=False, required=False, action='store_true')
    args = parser.parse_args()

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