include "globals.mzn";
include "alldifferent.mzn";

int: items;
set of int: ITEMS = 1..items;

int: nodes = items + 1;
set of int: NODES = 1..nodes; % set of vertex

int: couriers;
set of int: COURIERS = 1..couriers;

array[NODES] of int: DEMAND;
array[COURIERS] of int: CAPACITY;

int: LOWER_BOUND;
int: UPPER_BOUND;

array[NODES, NODES] of int: D;

% Decision variables
var LOWER_BOUND..UPPER_BOUND: obj;

array[ITEMS] of var ITEMS: routeOf;
array[ITEMS] of var ITEMS: succ;
array[ITEMS] of var 0..1: isAssigned;

constraint alldifferent(succ)::domain;
constraint circuit (succ)::domain;

% Ensure all items are assigned
constraint forall(i in ITEMS) (
    isAssigned[i] = 1
);

% Ensure all COURIERS are used
constraint forall(j in COURIERS) (
    exists(i in ITEMS) (routeOf[i] = j)
);

% The objective is now to minimize the maximum route length
constraint forall(j in COURIERS) (
    sum(i in ITEMS where j = routeOf[i]) (D[i, succ[i]]) <= obj
);

% Capacity constraint
constraint forall(j in COURIERS) (
    sum(i in ITEMS where j = routeOf[i]) (DEMAND[i]) < CAPACITY[j]
);

solve minimize(obj);