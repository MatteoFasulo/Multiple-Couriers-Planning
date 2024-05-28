include "alldifferent.mzn";
include "globals.mzn";

% Input variables
int: couriers;
int: items;
int: UPPER_BOUND;
int :LOWER_BOUND;
int: DIST_LOWER_BOUND;

% useful sets
set of int: COURIERS = 1..couriers;
set of int: ITEMS = 1..items;
set of int: NODES = 1..items + 1;

array[COURIERS] of int: CAPACITY;
array[ITEMS] of int: DEMAND;
array[NODES, NODES] of int: D; 

% Model variables
array[COURIERS] of var DIST_LOWER_BOUND..UPPER_BOUND: obj_dist;
array[COURIERS, NODES] of var NODES: couriers_nodes;

% objective function
var LOWER_BOUND..UPPER_BOUND: obj; 

int: max_load = max(CAPACITY) + 1;

array[ITEMS] of var 1..couriers: loads;

array[COURIERS] of var min(DEMAND)..max_load: couriers_loads;


% ensure that each courier starts and ends in origin point
constraint forall(k in COURIERS) (
      count([couriers_nodes[k, i] | i in ITEMS], items+1, 1)  /\ couriers_nodes[k, items+1] != items+1
);

% each item must be assigned only to one courier
constraint forall(i in ITEMS)(
      count([couriers_nodes[k, i]| k in COURIERS], i, couriers-1)
);

% setting the loads to verify the load_size for each courier
constraint forall(k in COURIERS) (
    forall(i in ITEMS) (
        if couriers_nodes[k, i] != i then
            loads[i] = k endif
    )
);

% Remove possible swaps of couriers having same capacity
constraint forall(k in COURIERS)(
    forall (k2 in k+1..couriers-1) (
        if CAPACITY[k] = CAPACITY[k2] then
            couriers_nodes[k, items+1] < couriers_nodes[k2, items+1]
        endif
    )  
);

% ensure that each courier does not exceed the max capacity
constraint bin_packing_capa(CAPACITY, loads, DEMAND);

% Circuit
constraint forall(k in COURIERS) (
      subcircuit([couriers_nodes[k, i] | i in NODES]) 
);

% distance computation
constraint forall(k in COURIERS) (
      obj_dist[k] = sum([D[i, couriers_nodes[k, i]]| i in NODES where couriers_nodes[k, i] != i])
);


% Symmetry breaking constraint
constraint forall(k in COURIERS)(
    couriers_loads[k] = sum(
            [DEMAND[i] | i in ITEMS where loads[i]=k]
    )
);

% sub tour elimination, if the last courier can carry all the packages
% then all courier must start
/*
constraint forall(k in COURIERS) (
    if CAPACITY[couriers] >= max(DEMAND) then 
        couriers_nodes[k, items+1] != items+1   
    endif
);
*/

constraint obj = max(obj_dist);