# Multiple-Couriers-Planning (MCP)

This repository contains the code and report for the project of the course "Combinatorial Decision Making and Optimization" at Alma Mater Studiorum Università di Bologna. The project consists in solving the Multiple Couriers Planning problem using different techniques: Constraint Programming (CP), SMT, and Mixed Integer Programming (MIP).

## Authors

- [Antonio Gravina](https://github.com/GravAnt)
- [Maksim Omelchenko](https://github.com/omemaxim)
- [Matteo Fasulo](https://github.com/MatteoFasulo)

## Report

The pdf report is available [here](https://matteofasulo.github.io/Multiple-Couriers-Planning/report.pdf).

## Run with Docker

In order to run the project with Docker, you need first to have the repository cloned on your machine. Then, you need to pull the Docker image from the GitHub Container Registry (GHCR) by running the following command:

```bash
docker pull ghcr.io/matteofasulo/multiple-couriers-planning:main
```

After that, you need to map the `res` folder to the Docker container in order to save the results. You can do this by running the following command:

```bash
docker run -it -v $(pwd)/res:/src/res ghcr.io/matteofasulo/multiple-couriers-planning:main
```

where `$(pwd)/res` is the path to the `res` folder of the repository.

The Docker container will run the project and save the results in the `res` folder.

## Run locally (docker compose)

In order to run the project locally, you need to have Docker and Docker Compose installed on your machine. After cloning the repository, run the following command from the root of the repository:

```bash
docker-compose up
```

which will build the Docker image and run the project. The results will be saved in the `res` folder without the need to map it to the Docker container.
> Note: docker compose might not show the output while solving the instances. To see the output, you can run the project with Docker as explained in the previous section.

## Single instances

### Run CP (with MiniZinc Python binding)

Timeout can be specified in seconds with the `--t` option and it is by default set to 300 seconds.

Solver can be specified with the `--solver` option. The default solver is `gecode`. Supported options are `gecode` and `chuffed`.

All the solutions run with the same seed (42), so the results are comparable.

The two different models can be run with the `--model` option. Supported options are `default`, `SB` (symmetry breaking).

All the instances can be run with the `--runall` option which uses all the available cores on the machine to run the instances in parallel (one instance per core so that they don't interfere with each other).

### CP CLI Examples

Run only instance 1 with the default model and Gecode solver with verbose output:

```python
python cp.py --i Instances/inst01.dat --solver gecode --model default --verbose
```

Run all the instances with the SB model and Chuffed solver with verbose output:

```python
python cp.py --runall --solver chuffed --model SB --verbose
```

### Run SMT

Same Command Line Arguments of CP but only z3 solver is available.

### SMT CLI Examples

Run only instance 1 with the SB model with verbose output:

```python
python smt.py --i Instances/inst01.dat --model SB --verbose
```

Run all the instances with SB model with verbose output:

```python
python smt.py --runall --model SB --verbose
```

### Run MIP

Same Command Line Arguments of CP and SMT with `CBC` and `GLPK` solvers available.

### MIP CLI Examples

Run only instance 1 with the SB model and CBC solver with verbose output:

```python
python mip.py --i Instances/inst01.dat --solver CBC --model SB --verbose
```

Run all the instances with default model, GLPK solver but no verbosity:

```python
python mip.py --runall --solver GLPK
```

## Check Solution

The `check_solution` python script can be used to verify that the produced solutions are correct. It is sufficient to run the following command to check all of them:

```python
python check_solution.py Instances res/
```

### Generate .dzn files

The `utils.py` script can be used to generate the `.dzn` files for the CP model. Since we used the MiniZinc python binding, the `.dzn` files are generated from their `.dat` counterparts.

It also supports the `--runall` option to generate all the `.dzn` files at once by also allowing to specify the depot node value with the `--depot` option. The default depot value is `-1` which means that the depot node is the last row/column of the distance matrix.

For the CP model, the depot node is the last row/column of the distance matrix while for the SMT and MIP models the depot node is the first row/column of the distance matrix for all the instances.

> Note: The time to generate the `.dzn` files is negligible compared to the time to solve the instances thus it was not included in the preprocessing time.

### Utils CLI Examples

Generate the `.dzn` file for instance 1 with the depot node set to -1:

```python
python utils.py --i Instances/inst01.dat --depot -1
```

Generate all the `.dzn` files with the depot node set to 0:

```python
python utils.py --runall --depot 0
```
