# Multiple-Couriers-Planning

Multiple Couriers Planning (MCP)

## Run CP (with MiniZinc Python binding)

Time can be specified in seconds with the `--t` option.
Solver can be specified with the `--solver` option. The default solver is `gecode`. Supported options are `gecode`, `chuffed`, `com.google.ortools.sat`.
All the solutions run with the same seed (42), so the results are comparable.

```python
python cp.py --i Instances/inst01.dat --t 60 --solver gecode 
```

## Run SAT

```python
python sat.py --i Instances/inst01.dat
```

## Run SMT

```python
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
