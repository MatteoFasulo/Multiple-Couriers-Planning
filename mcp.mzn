include "globals.mzn";

% Parameters
int: ITEMS;
int: NODES = ITEMS+1;
int: COURIERS;
array[1..NODES] of int: SIZE;
array[1..NODES, 1..NODES] of int: D;
array[1..COURIERS] of int: MAX_LOAD;
var int: Q = max(MAX_LOAD);
array[1..NODES] of var int: u;

% Decision variables
array[1..NODES, 1..NODES, 1..COURIERS] of var 0..1: TENSOR;

% Constraints
% 1) Vehicle leaves node it enters
constraint forall(j in 1..NODES, k in 1..COURIERS) (
    sum([TENSOR[i,j,k] | i in 1..NODES]) = sum([TENSOR[j,i,k] | i in 1..NODES])
);

% 2) Each node is entered just once by any vehicle
constraint forall(j in 2..NODES) (
    sum([TENSOR[i,j,k] | i in 1..NODES, k in 1..COURIERS]) = 1
);

% 3) Every vehicle starts from the depot and ends at the depot
% Use count(i in x)(i=v) >= n instead.
constraint forall(k in 1..COURIERS) (
    sum([TENSOR[1,j,k] | j in 2..NODES]) = 1
);

% 4) Capacity constraints
constraint forall(k in 1..COURIERS) (
    sum([SIZE[j]*TENSOR[i,j,k] | i in 1..NODES, j in 2..NODES]) <= MAX_LOAD[k]
);

% 5) Remove self-loops
constraint forall(i in 1..NODES, k in 1..COURIERS) (
    % the diagonal of the TENSOR must be zero
    TENSOR[i,i,k] = 0
);

% 6) All the items must be collected
constraint forall(i in 2..NODES) (
    sum([TENSOR[i,j,k] | j in 1..NODES, k in 1..COURIERS]) = 1
);

% 7) Miller-Tucker-Zemlin formulation # TODO: check this constraint
constraint forall(k in 1..COURIERS, i in 2..NODES, j in 2..NODES where i != j) (
    u[j] - u[i] >= SIZE[j] - Q * (1 - TENSOR[i, j, k])
);

% Objective function
var int: arr_dist = min([sum([D[i,j]*TENSOR[i,j,k] | i in 1..NODES, j in 1..NODES]) | k in 1..COURIERS]);

solve minimize arr_dist;


output [
    "arr_dist: \(arr_dist)\n",
    "TENSOR: \(TENSOR)\n"
];