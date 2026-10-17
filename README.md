# ACEest Fitness & Performance

ACEest is a Python desktop application built with Tkinter. It provides client and membership management, workout planning, and PDF report generation. Client and workout data are stored in a local SQLite database named `aceest_fitness.db`.

## Local setup and execution

### Requirements

- Python 3
- Tkinter
- Matplotlib
- `fpdf2`

Tkinter is included with most Windows Python installations. On Debian/Ubuntu, install it and Matplotlib with:

```bash
sudo apt-get update
sudo apt-get install python3 python3-tk python3-matplotlib
```

Install the Python PDF dependency:

```bash
python -m pip install fpdf2
```

On Windows, use `py -3 -m pip install fpdf2` if `python` does not select the desired Python installation. Matplotlib can be installed with `python -m pip install matplotlib` if it is not already available.

### Start the app

From the `devops-assignment-1` directory:

```bash
python Aceestver.py
```

On Windows, `py -3 Aceestver.py` is also supported. The app creates or initializes `aceest_fitness.db` in its current working directory when started. The starter database has a demo `admin` / `admin` account; change this before using the app with real or sensitive data.

## Run tests manually

The test suite uses Python's built-in `unittest` framework and can also be run with pytest. From the project directory, run either:

```bash
python -m unittest discover -s . -p "test_*.py" -v
```

or:

```bash
python -m pytest -q
```

On Windows, replace `python` with `py -3` if needed. The tests use a temporary SQLite database and mock GUI and external-library components; they do not open a real application window.

## CI/CD integrations

### Jenkins

The [Jenkinsfile](./Jenkinsfile) defines a two-stage declarative pipeline:

1. Runs the unit tests with `unittest`.
2. Builds the Docker image only if tests pass. The image is tagged with both the Jenkins build number and `latest`.

The Jenkins agent needs Python 3 and Docker installed and available to the account running the agent. Configure the Jenkins job to load this repository's `Jenkinsfile` from the project root.

### GitHub Actions

The [CI workflow](./.github/workflows/ci.yml) runs on every push. It checks out the repository, installs Tkinter on the Ubuntu runner, runs the unit tests, and builds the Docker image if tests pass. It tags the image with the commit SHA and `latest`. It does not push the image to a registry.

### Docker and GUI display

The [Dockerfile](./Dockerfile) installs Python, Tkinter, Matplotlib, and `fpdf2`, then starts `Aceestver.py`. Since the app is a Tkinter GUI, running the container also requires a display server and GUI display forwarding; building the image alone does not display the window.
