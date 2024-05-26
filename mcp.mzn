include "globals.mzn";

% Parameters
int: ITEMS;
int: NODES = ITEMS+1;
int: COURIERS;
int: LOWER_BOUND;
int: UPPER_BOUND;
array[1..NODES] of int: SIZE;
array[1..NODES, 1..NODES] of int: D;
array[1..COURIERS] of int: MAX_LOAD;

% Decision variables
array[1..NODES, 1..NODES, 1..COURIERS] of var bool: TENSOR;

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
    count([TENSOR[1,j,k] | j in 2..NODES], true) = 1
);

% 4) Capacity constraints
constraint forall(k in 1..COURIERS) (
    sum([SIZE[j]*TENSOR[i,j,k] | j in 2..NODES, i in 1..NODES]) <= MAX_LOAD[k]
);

% 5) Remove self-loops
constraint forall(i in 1..NODES, k in 1..COURIERS) (
    % the diagonal of the TENSOR must be zero
    TENSOR[i,i,k] = 0
);

% 6) Miller-Tucker-Zemlin formulation # TODO: check this constraint
var int: Q = max(MAX_LOAD);
array[1..NODES] of var int: u;
% Assigning the domain to each decision variable in the array
constraint forall(i in 1..NODES) (
    u[i] in SIZE[i]..Q
);

constraint forall(k in 1..COURIERS, i in 2..NODES, j in 2..NODES where i != j) (
    u[j] - u[i] >= SIZE[j] - Q *(1 - TENSOR[i,j,k])
);

% 7) Size symmetry breaking
constraint forall(k1 in 1..COURIERS, k2 in k1+1..COURIERS) (
    if SIZE[k1] == SIZE[k2] then
        forall(i in 1..NODES, j in i+1..NODES) (
            not(TENSOR[1,j,k1] /\ TENSOR[1,i,k2])
        )
    endif
);

% Calculate the total distance traveled by each courier
array[1..COURIERS] of var int: arr_dist = [sum(i in 1..NODES, j in 1..NODES)(D[i,j] * TENSOR[i,j,k]) | k in 1..COURIERS];

% Objective function: minimize the maximum distance traveled by any vehicle
var LOWER_BOUND..UPPER_BOUND : obj;

constraint (
    obj == max(arr_dist)
);

%solve minimize obj;

output [
    "Distance array: "++show(arr_dist)++"\n"++"Objective function: "++show(obj)
];