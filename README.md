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


## Using alongside Gooey
It can be useful to decorate methods with both `@Tooey` and `@Gooey` so that scripts can be run flexibly depending on context.
To avoid conflicts, if both decorators are present for a single method, Tooey makes sure that only one of them is active.
Which one is chosen depends on the order in which you add their decorators, with the decorator closest to the function taking priority:

```python
@Gooey
@Tooey
def main_tooey():
    # Here Tooey is activated and Gooey is ignored
    # To force Gooey to be used instead, pass the `--ignore-tooey` command line option
    [...]

@Tooey
@Gooey
def main_gooey():
    # Here Gooey is activated and Tooey is ignored
    # To force Tooey to be used instead, pass the `--ignore-gooey` command line option
    [...]
```

Regardless of decorator order, you can always use the command line parameters `--ignore-tooey` and `--ignore-gooey` to switch behaviour, as outlined in the example above.
If Gooey is present (and not ignored) it will take precedence over the the `--force-tooey` parameter.
Please note that due to the nature of Gooey's interaction with command line arguments, complex scripts with multiple Gooey decorators or unusual configurations may not be fully compatibile with this approach, and it is advisable to test your script when using both Tooey and Gooey simultaneously.


## Testing
To run the Tooey tests and generate a coverage report, first clone this repository and open the `tests` directory in a terminal, then:

```console
python -m pip install gooey
python -m coverage run -m unittest
python -m coverage html --include '*/tooey/*' --omit '*test*'
```


## Inspirations and alternatives
- [Gooey](https://github.com/chriskiehl/Gooey) adds a GUI interface to (almost) any script
- [GooeyWrapper](https://github.com/skeenp/gooeywrapper) extends Gooey to make switching between the command line and Gooey a little more seamless
- [Click](https://click.palletsprojects.com/en/8.1.x/options/#prompting) supports command line options that auto-prompt when missing


## License
[Apache 2.0](https://github.com/simonrob/tooey/blob/main/LICENSE)
