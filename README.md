# Tooey
Turn any python console script into an interactive TUI application.
Tooey is similar to (and inspired by) [Gooey](https://github.com/chriskiehl/Gooey/), but keeps you in the terminal.

<p align="center"><b>Without Tooey 😕</b></p>

![Running a command line script without the Tooey decorator](https://github.com/simonrob/tooey/assets/934006/938791ce-c0f5-4684-a779-48fdacb336b9)

<p align="center"><b>With Tooey 🎉</b></p>

![Running a command line script with the Tooey decorator (sample)](https://github.com/simonrob/tooey/assets/934006/c8c53abd-e4b3-4803-a42c-f3bffa409455)


## Installation
Install Tooey from [PyPi](https://pypi.org/project/tooey/) via `pip`:

```console
python -m pip install tooey
```


## Getting started
Decorate your script's [argparse](https://docs.python.org/3/library/argparse.html) function with `@Tooey`, then run the script with or without any of its arguments.
You'll be prompted interactively in the terminal to enter each argument.
After this the script will continue as normal.


## Example
The following python script requests and then prints three arguments.
The method that handles command line arguments is decorated with `@Tooey`.

```python
import argparse
from tooey import Tooey

@Tooey
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('positional', nargs=1, help='A positional argument requiring one value')
    parser.add_argument('--named-choices', nargs=2, type=int, choices=range(1, 5), help='A named argument requiring two integers from a given list of choices')
    parser.add_argument('--store-true', action='store_true', help='A store_true argument')
    print(parser.parse_args())

main()
```

Tooey automatically turns this into an interactive prompt for each argument.
![Running a command line script with the Tooey decorator (full)](https://github.com/simonrob/tooey/assets/934006/a48d6499-04d2-42d1-91e3-f8d6db219266)


## Configuration
Tooey will automatically inject itself into any decorated functions whenever `sys.isatty()` is `True`.

If you would like to override this behaviour and disable Tooey when running a script, add the additional parameter `--ignore-tooey` when running, or set an environment variable `IGNORE_TOOEY`.
For example, Tooey will ignore any decorated methods in this script:

```console
$ python tooey_example.py val1 --named-choices 1 3 --ignore-tooey
```

Conversely, if you would like to force Tooey to inject itself into decorated functions even when it does not detect a terminal-like environment, add the additional parameter `--force-tooey` when running, or set an environment variable `FORCE_TOOEY`.
For example, Tooey will still run in the following script:

```console
$ FORCE_TOOEY=1 python tooey_example.py val1 --named-choices 1 3 | sort
```


## License
[Apache 2.0](https://github.com/simonrob/tooey/blob/main/LICENSE)
