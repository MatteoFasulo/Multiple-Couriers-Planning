include "globals.mzn";
include "alldifferent.mzn";

% Input data
int: couriers;
int: items;
int: n_edges;
int: LOWER_BOUND;
int: UPPER_BOUND;
array[ITEMS] of int: DEMAND;
array[COURIERS] of int: CAPACITY;
%array[NODES, NODES] of int: D;
array[GRAPH_EDGES] of NODES: starting_nd;
array[GRAPH_EDGES] of NODES: ending_nd;
array[GRAPH_EDGES] of int: weights;

int: nodes = items+1;
int: Q = max(CAPACITY);

% Sequences
set of int: COURIERS = 1..couriers;
set of int: ITEMS = 1..items;
set of int: NODES = 1..items+2;
set of int: GRAPH_EDGES = 1..n_edges;

% Variables
array[COURIERS] of var 0..Q: couriers_loads;
array[ITEMS] of var COURIERS: loads;
array[COURIERS, NODES] of var bool :ns;
array[COURIERS, GRAPH_EDGES] of var bool :es;
array[COURIERS] of var LOWER_BOUND..UPPER_BOUND: path_dist;

% Decision variables
var LOWER_BOUND..UPPER_BOUND: obj;

% force the pair ns es to be a sub graph of the original one for each courier, it also
% computes the total cost of the path (cycle) obtained (see  https://www.minizinc.org/doc-2.5.5/en/lib-globals.html#index-125)
constraint forall(k in COURIERS)(
    bounded_dpath(
            items+2, n_edges, 
            starting_nd, ending_nd, weights, 
            1, items+2, [ns[k,i] | i in NODES], [es[k,i] | i in GRAPH_EDGES], path_dist[k])
);

% Ensure that each item is taken care of by a single courier
constraint forall(i in 2..items+1)(
       count([ns[k,i] | k in COURIERS], true, 1)
);

% channelling the loads with the assignments
constraint forall (k in COURIERS) 
      (forall(i in 2..items+1)(
      if ns[k, i] then loads[i-1] = k endif
));

% Ensure that the weight of all the items assigned to a courier is under the limit
% ensure that each courier does not exceed the max capacity
constraint bin_packing_capa(
                           CAPACITY,
                           loads,
                           DEMAND);

% Symmetry breaking
constraint forall(k in COURIERS)(
    couriers_loads[k] = sum(
            [DEMAND[i] | i in ITEMS where loads[i]=k]
    )
);

%solve ::  int_search(loads, first_fail, indomain_min)
%                    minimize(obj);

% Obj setting
constraint obj = max(path_dist);