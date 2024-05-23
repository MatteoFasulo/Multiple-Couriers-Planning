import argparse
import numpy as np

# Read an instance in .dat format and parse the content to a suitable data structure.

def check_symmetric(D):
    """
    Check if the distance matrix is symmetric
    """
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
    d = dict()
    for i,j in path:
        d[i] = (i,j)
    sorted_path = []
    sorted_path.append(d[0])
    tail = d[0][1]
    while tail != 0:
        sorted_path.append(d[tail])
        tail = d[tail][1]
    path = sorted_path

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
    if args.instance is not None:
        convert_dat_to_dzn(args.instance)
    else:
        print('Error: missing instance')
        exit(1)