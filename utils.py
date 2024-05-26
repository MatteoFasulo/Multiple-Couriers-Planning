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
    # Convert the distance matrix to a numpy array if it is not
    if not isinstance(D, np.ndarray):
        D = np.array(D)

    return np.allclose(D, D.T)

def preprocess(D):
    """
    Preprocess the distance matrix
    """
    # load it as a numpy array
    D = np.array(D)
    D = np.insert(D, 0, D[-1], axis=0)
    D = np.delete(D, -1, axis=0)
    D = np.insert(D, 0, D[:, -1], axis=1)
    D = np.delete(D, -1, axis=1)
    return D

def read_instance(filename: str) -> dict:
    with open(filename, 'r') as file:
        data = file.read().splitlines()
    
    return {
        'm': int(data[0]), # Number of couriers
        'n': int(data[1]), # Number of items
        'l': [int(x) for x in data[2].split()], # maximum load size
        's': [int(x) for x in data[3].split()], # size of items
        'D': [[int(x) for x in line.split()] for line in data[4:]] # distance matrix
    }

def path_sequence(path, D=None): # TODO: fix this function using OrderedDict with move_to_end
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
        file.write(f'MAX_LOAD = {instance["l"]};\n')
        file.write(f'SIZE = {[0] + instance["s"]};\n') # Prepend 0 to the list of sizes to match the indexing
        D = preprocess(instance['D']) # Preprocess the distance matrix
        file.write('D = [|')
        for row in D:
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