include "globals.mzn";

% Input variables
int: couriers;
int: items;
int: UPPER_BOUND;
int: LOWER_BOUND;

% useful sets
set of int: COURIERS = 1..couriers;
set of int: ITEMS = 1..items;
set of int: NODES = 1..items + 1;

array[COURIERS] of int: CAPACITY;
array[ITEMS] of int: DEMAND;
array[NODES, NODES] of int: D; 

% Model variables
array[COURIERS] of var 0..UPPER_BOUND: obj_dist;
array[COURIERS, NODES] of var NODES: couriers_nodes;

% objective function
var LOWER_BOUND..UPPER_BOUND: obj; 

int: max_load = max(CAPACITY) + 1;

array[ITEMS] of var COURIERS: loads;

array[COURIERS] of var min(DEMAND)..max_load: couriers_loads;


% Each courier must leave the depot (we use all the couriers)
constraint forall(k in COURIERS) (
    couriers_nodes[k, items+1] != items+1
);

% Each item must be assigned to one courier
constraint forall(i in ITEMS)(
      count([couriers_nodes[k, i]| k in COURIERS], i, couriers-1)
);

% Initialize the loads array
constraint forall(k in COURIERS) (
    forall(i in ITEMS) (
        if couriers_nodes[k, i] != i then
            loads[i] = k endif
    )
);

% Ensure that each courier does not exceed the max capacity
constraint bin_packing_capa(CAPACITY, loads, DEMAND);

% Subcircuit
constraint forall(k in COURIERS) (
      subcircuit([couriers_nodes[k, i] | i in NODES]) 
);

% Total path cost per courier
constraint forall(k in COURIERS) (
      obj_dist[k] = sum([D[i, couriers_nodes[k, i]]| i in NODES])
);

% Total load per courier
constraint forall(k in COURIERS)(
    couriers_loads[k] = sum(
            [DEMAND[i] | i in ITEMS where loads[i]=k]
    )
);

% Symmetry breaking: impose ordering on first item delivered by couriers (2)
constraint forall(k1 in 1..couriers-1)(
    forall (k2 in k1+1..couriers) (
        if CAPACITY[k1] = CAPACITY[k2] then
            couriers_nodes[k1, items+1] <= couriers_nodes[k2, items+1]
        endif
    )  
);

constraint obj = max(obj_dist);