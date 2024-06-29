import json
import time
import os
import re
import argparse
import numpy as np
import matplotlib.pyplot as plt

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
    start = time.time()
    # load it as a numpy array
    D = np.array(D)
    if depot == 0: # take last row and col and put them in the first row and col shifting the rest
        D = np.insert(D, 0, D[-1], axis=0)
        D = np.delete(D, -1, axis=0)
        D = np.insert(D, 0, D[:, -1], axis=1)
        D = np.delete(D, -1, axis=1)

    return D, time.time() - start

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

    # Return the lower bound
    return int(lb)


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

    return int(val)

def read_instance(filename: str, depot: int = -1, padded_size: bool = False) -> dict:
    with open(filename, 'r') as file:
        data = file.read().splitlines()

    couriers = int(data[0])
    items = int(data[1])
    max_load = [int(x) for x in data[2].split()]
    sizes = [int(x) for x in data[3].split()]
    D = [[int(x) for x in line.split()] for line in data[4:]]

    # Preprocess the distance matrix
    D, preprocess_time = preprocess(D, depot=depot)

    if padded_size:
        # Insert 0 demand for the depot
        sizes.insert(0, 0)
    
    return {
        'm': couriers,
        'n': items,
        'l': max_load,
        's': sizes,
        'D': D,
        'D_symmetric': check_symmetric(D),
        'lower_bound': compute_lower_bound(D, depot=depot),
        'upper_bound': compute_upper_bound(D, max_load),
        'preprocess_time': preprocess_time,
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

def get_solutions(nodes, couriers, distance_matrix, decision_var, verbose: bool = False):
    all_paths = []
    for k in range(couriers):
        path = []
        for i in range(nodes):
            for j in range(nodes):
                if decision_var[i][j][k]:
                    path.append((i, j))
        cost = path_sequence(path, distance_matrix)
        path = [x[1] for x in path[:-1]]
        if verbose:
            print(f'Courier: {k}\tPath sequence: {path}\t cost: {cost}')
        all_paths.append(path)
    return all_paths

def plot_solution(instance, solution):
    COURIERS = instance['m']
    ITEMS = instance['n']
    MAX_LOAD = instance['l']
    SIZE = instance['s']
    D = instance['D']
    NODES = ITEMS + 1

    num_locs = NODES

    # Define the center of the plot (i.e., the depot)
    x_coords = [0]
    y_coords = [0]

    # Define the radius of the circle where the other nodes will be placed
    radius = 0.5

    # Calculate the angle between each node
    angle = 2 * np.pi / (num_locs - 1)

    # Generate the coordinates for the other nodes
    for i in range(1, num_locs):
        x_coords.append(0 + radius * np.cos(i * angle))
        y_coords.append(0 + radius * np.sin(i * angle))

    # Plot the depot
    plt.scatter(x_coords[0], y_coords[0], c='r', s=100, label='Depot')

    for idx, route in enumerate(solution):
        x = [x_coords[i] for i in route]
        y = [y_coords[i] for i in route]

        # Plot items
        plt.scatter(x, y, label=f"Route {idx}", zorder=3, s=75)
        plt.plot(x, y)

        plt.annotate(
            "",
            xy=(x[0], y[0]),
            xytext=(x_coords[0], y_coords[0]),
            arrowprops=dict(arrowstyle="-|>"),
            zorder=1,
        )

    plt.grid(color="grey", linestyle="solid", linewidth=0.2)

    plt.title("Solution")
    plt.legend(frameon=False, ncol=2)
    plt.show()


def convert_dat_to_dzn(filename: str, depot: int):
    instance = read_instance(filename, depot=depot)
    with open(filename.replace('.dat', '.dzn'), 'w') as file:
        file.write(f'couriers = {instance["m"]};\n')
        file.write(f'items = {instance["n"]};\n')
        file.write(f'LOWER_BOUND = {instance["lower_bound"]};\n')
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
    json_file = f'{os.getcwd()}{os.sep}res{os.sep}{folder}{os.sep}{num}.json'
    if os.path.exists(json_file):
        with open(json_file, 'r') as file:
            data = json.load(file)

        data[solver] = {
            'time': time,
            'optimal': optimal,
            'obj': obj,
            'sol': sol
        }
        with open(json_file, 'w') as file:
            json.dump(data, file, indent=3)

    # Create a new json file, first entry for that instance
    else:
        with open(json_file, 'w') as file:
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
    parser.add_argument('--depot', type=int, metavar='--d', help='Depot index', default=-1, required=False)
    args = parser.parse_args()

    if args.runall:
        for instance in sorted(os.listdir('Instances'), key=lambda x: int(re.search(r'\d+', x).group())):
            if instance.endswith('.dat'):
                args.instance = f'Instances{os.sep}{instance}'
                convert_dat_to_dzn(args.instance, depot=args.depot)
    elif args.instance:
        convert_dat_to_dzn(args.instance, depot=args.depot)
    else:
        print('Error: missing instance')
        exit(1)