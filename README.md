# Multiple-Couriers-Planning

Multiple Couriers Planning (MCP)

## Run CP (with MiniZinc Python binding)

Time can be specified in seconds with the `--t` option.
Solver can be specified with the `--solver` option. The default solver is `gecode`. Supported options are `gecode`, `chuffed`, `com.google.ortools.sat`.
All the solutions run with the same seed (42), so the results are comparable. The seed can be changed with the `--seed` option. The two different models can be run with the `--model` option. Supported options are `default`, `SB` (symmetry breaking). All the instances can be run with the `--runall` option which uses all the available cores on the machine to run the instances in parallel (one instance per core so that they don't interfere with each other).

```python
python cp.py --i Instances/inst01.dat --solver gecode --model default --verbose
python cp.py --runall --solver chuffed --model SB --verbose
```

## Run SAT

```python
```

## Run SMT

```python
python smt.py --i Instances/inst01.dat --model SB --verbose
```

## Run MIP

```python
python mip.py --i Instances/inst01.dat
```

## Check Solution

```python
python check_solution.py Instances res/
```

### Generate .dzn files

```python
python utils.py --runall
```
