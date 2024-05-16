import argparse

# Read an instance in .dat format and parse the content to a suitable data structure.

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

def parser_obj():
    parser  = argparse.ArgumentParser(
        prog='CP OR',
        description='CP OR solver',
        epilog='Developed by: Antonello Gravina, Maksim Omelchenko & Matteo Fasulo'
    )

    parser.add_argument('--instance', type=str, metavar='--i', help='Input instance', required=False)
    parser.add_argument('--runall', help='Run all instances', default=False, required=False, action='store_true')
    parser.add_argument('--verbose', help='Verbose mode', default=False, required=False, action='store_true')
    
    return parser.parse_args()

if __name__ == '__main__':
    print(read_instance('Instances/inst03.dat'))