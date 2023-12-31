"""
Tooey: Gooey, but for TUIs
Decorate your argparse function with `@Tooey` to be prompted interactively in the terminal to enter each argument
"""
import argparse
import contextlib
import copy
import functools
import os
import sys

# noinspection PyUnresolvedReferences,PyProtectedMember
from argparse import (
    ArgumentParser,

    # we ignore these action types currently
    _HelpAction,
    _VersionAction,
    _SubParsersAction,

    # we support these action types
    _StoreConstAction,
    _StoreTrueAction,
    _StoreFalseAction,
    _AppendConstAction,
    _AppendAction,
    _CountAction,
    _StoreAction
)

_SEPARATOR = '-' * 80
_YES_CHOICES = ('y', 'yes')
_YES_CHOICES_STRING = ' / '.join(_YES_CHOICES)

_GOOEY_IGNORE_COMMAND = '--ignore-gooey'


# noinspection PyPep8Naming
def Tooey(f=None):
    global_config = None
    if 'gooey' in sys.modules:
        # when Gooey is present we need to be able to parse arguments earlier in order to disable it if necessary, and
        # with no ability to detect parent decorators, must assume importing Gooey means using it for *this* function
        # note: the need to handle this in the root Tooey definition means that it will be run at launch, before the
        # wrapped function is actually called (and multiple times if there are multiple `@Tooey` decorators used)
        config_parser = argparse.ArgumentParser(add_help=False)
        config_parser.add_argument('--ignore-tooey', action='store_true')
        config_parser.add_argument('--force-tooey', action='store_true')
        global_config, remaining_argv = config_parser.parse_known_args()
        global_config.ignore_tooey, global_config.force_tooey = check_environment(global_config.ignore_tooey,
                                                                                  global_config.force_tooey)

        # TODO: improvable without breaking Gooey integration? E.g., via a new decorator that applies Tooey *and* Gooey?
        sys.argv = [sys.argv[0]] + remaining_argv

        if not global_config.ignore_tooey:
            with contextlib.suppress(IndexError):
                if _GOOEY_IGNORE_COMMAND not in sys.argv:
                    sys.argv.append(_GOOEY_IGNORE_COMMAND)

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        ArgumentParser.tooey_original_parse_args = ArgumentParser.parse_args
        ArgumentParser.tooey_original_error = ArgumentParser.error
        ArgumentParser.tooey_global_config = global_config

        ArgumentParser.parse_args = parse_args
        ArgumentParser.error = error

        if 'gooey' in sys.modules and not global_config.ignore_tooey:  # undo our Gooey modification
            with contextlib.suppress(IndexError):
                if sys.argv[-1] == _GOOEY_IGNORE_COMMAND:
                    sys.argv.pop()

        result = f(*args, **kwargs)

        ArgumentParser.parse_args = ArgumentParser.tooey_original_parse_args
        ArgumentParser.error = ArgumentParser.tooey_original_error

        return result

    return wrapper


def check_environment(ignore_tooey, force_tooey):
    ignore_tooey = os.environ.get('IGNORE_TOOEY') or ignore_tooey
    force_tooey = os.environ.get('FORCE_TOOEY') or force_tooey
    if ignore_tooey and force_tooey:
        force_tooey = False
    return ignore_tooey, force_tooey


def safe_get_namespace_boolean(namespaces, key):
    for namespace in namespaces:  # for when we don't know if a store_true argument is actually present
        if key in namespace.__dict__:
            return namespace.__dict__[key]
    return False


def parse_args(self, args=None, namespace=None):
    self.tooey_original_error_message = None
    if hasattr(self, 'tooey_global_config') and self.tooey_global_config:
        self.tooey_config = copy.deepcopy(self.tooey_global_config)
    else:
        self.tooey_config = argparse.Namespace()

    if 'gooey' not in sys.modules or args is not None:
        # called on a specified list rather than sys.argv - note: if Gooey supported this (which it currently doesn't),
        # calling in this way would show up in the Gooey UI - perhaps not fixable until Gooey is patched?
        with contextlib.suppress(argparse.ArgumentError):
            self.add_argument('--ignore-tooey', action='store_true', help=argparse.SUPPRESS)
            self.add_argument('--force-tooey', action='store_true', help=argparse.SUPPRESS)

    parsed_args = self.tooey_original_parse_args(args, namespace)

    # re-check environment variables - they could be set inside the patched function itself (e.g. in our own tests...)
    self.tooey_config.ignore_tooey, self.tooey_config.force_tooey = check_environment(
        safe_get_namespace_boolean([self.tooey_config, parsed_args], 'ignore_tooey'),
        safe_get_namespace_boolean([self.tooey_config, parsed_args], 'force_tooey'))

    if 'gooey' not in sys.modules or args is not None:
        internal_args = ('ignore_tooey', 'force_tooey')
        for arg in internal_args:
            if arg in parsed_args.__dict__:
                del parsed_args.__dict__[arg]  # TODO: if these weren't defined by us, they'll now be missing...
        self._actions = [a for a in self._actions if a.dest not in internal_args]

    if (not sys.stdout.isatty() or self.tooey_config.ignore_tooey) and not self.tooey_config.force_tooey:
        if self.tooey_original_error_message:
            self.tooey_original_error(self.tooey_original_error_message)
        return parsed_args

    print(_SEPARATOR)
    print('Tooey interactive mode starting - presenting script options')

    try:
        # we have to use the parser's internal _actions object because there is no other way to get an action's details
        # first, save the initial values to check what _was_ provided at runtime, skipping help and version actions
        # because they don't require input, and doing this step separately to option parsing itself because multiple
        # options can share the same `dest`, so the original value could have been updated before we get to it
        initial_values = {}
        ignored_actions = (_HelpAction, _VersionAction, _SubParsersAction)
        for action in self._actions:
            action_type = type(action)
            if action_type not in ignored_actions:
                initial_values[action.dest] = parsed_args.__dict__[action.dest]
            elif action_type not in (_HelpAction, _VersionAction):
                # TODO: we print an error, but don't handle these args at all, so any real argparse errors will be
                #  suppressed - best to drop back to standard argparse if any of these arguments are found?
                print('\nTooey warning: action type', action_type.__name__, 'is not currently handled - skipping')

        # then, iterate over the available options, gathering any additions via user input
        for action in filter(lambda a: type(a) not in ignored_actions, self._actions):

            option_string = ', '.join(action.option_strings) if action.option_strings else action.dest
            current_value = parsed_args.__dict__[action.dest]

            print()
            print('Argument:', option_string, '(required)' if action.required else '')
            print('Help text:', action.help)

            if initial_values[action.dest] not in (action.default, []) and type(action) is not _AppendConstAction:
                # note: currently all `append_const` actions are shown even if some are provided at runtime
                # we don't exclude these because the intent may be to provide them multiple times
                print('Skipping interactive mode for argument provided at runtime (value: %s)' % current_value)
                continue

            parsed_args.__dict__[action.dest] = _parse_action(action, current_value)
            print('Outcome:', action.dest, 'is `%s`' % parsed_args.__dict__[action.dest])

        print('\nTooey interactive mode completed - continuing script')
        print(_SEPARATOR)

        return parsed_args

    except KeyboardInterrupt:
        print('\n\nTooey interactive mode interrupted - continuing script')
        print(_SEPARATOR)
        if self.tooey_original_error_message:
            # TODO: continue script execution instead if inputs so far have addressed the original error?
            self.tooey_original_error(self.tooey_original_error_message)


def get_input(prompt='', strip=False):
    print(prompt, end=' ')
    response = input()
    if not response:  # testing can produce an actual `None` where real input would only lead to an empty string
        response = ''
    if strip:
        response = response.strip()
    if 'unittest' in sys.modules:
        print(response)  # it is useful to be able to see the actual input when testing
    return response


def _parse_action(action, current_value):
    action_type = type(action)

    if action_type in (_StoreConstAction, _StoreTrueAction, _StoreFalseAction):
        # these action types provide a constant value - either user-defined, or True/False
        yes_response = action.const if action_type is _StoreConstAction else not action.default
        if action.required:
            print('Skipping interactive mode for required action - the only possible value is `%s`' % yes_response)
            return yes_response
        response = get_input(prompt='Enter %s to set to `%s`, or anything else to accept the default value (`%s`):' % (
            _YES_CHOICES_STRING, yes_response, action.default), strip=True)
        return yes_response if response in _YES_CHOICES else action.default

    elif action_type is _AppendConstAction:
        # this action type appends a constant value each time it is provided
        new_value = current_value if current_value else []
        while True:
            response = get_input(prompt='Enter %s to append `%s` to the current value of `%s`, or anything else to '
                                        'skip:' % (_YES_CHOICES_STRING, action.const, new_value), strip=True)
            if response in _YES_CHOICES:
                new_value.extend([action.const])
            else:
                if action.required and action.const not in new_value:
                    print('This argument is required but has not been provided - adding `%s`' % action.const)
                    new_value.extend([action.const])
                return new_value

    elif action_type is _AppendAction:
        # this action is like the default, but can be called repeatedly, adding to a single list
        new_value = _parse_store_action(action)
        action_required = action.required
        while new_value:
            if current_value is None:
                current_value = [new_value]
            else:
                current_value.append(new_value)
            print('Current outcome:', action.dest, 'is `%s`' % current_value)
            action.required = False  # once we have one result, additional ones are always optional
            new_value = _parse_store_action(action, append=True)
        action.required = action_required
        return current_value if current_value else action.default

    elif action_type is _CountAction:
        # this action provides the number of times the same argument occurs
        while True:
            count_response = get_input(prompt='Enter the number of times you would like to provide this argument, or '
                                              'leave blank to accept the default value (`%s`):' % action.default,
                                       strip=True)
            if count_response.isdigit():
                return int(count_response)
            elif not count_response:
                return action.default

    elif action_type is _StoreAction:
        # the default action type is able to handle one or more arguments flexibly
        return _parse_store_action(action)


def _parse_store_action(action, append=False):
    new_value = []
    arg_num = 0
    type_string = ' of type `%s`' % (
        action.type.__name__ if hasattr(action.type, '__name__') else action.type) if action.type else ''
    choice_list_string = (' from `%s`' % ', '.join([str(c) for c in action.choices])) if action.choices else ''
    argument_required_string = 'This argument is required but has not been provided - please enter a value'
    while True:
        while True:
            response = get_input(prompt='Enter %s%s%s for this argument, or leave blank to skip:' % (
                'an additional value' if append else 'a value',
                choice_list_string if choice_list_string else type_string if type_string else '',
                (' to append to the current value `%s`' % new_value) if len(new_value) > 0 else ''), strip=False)
            if response:
                if action.type:
                    try:
                        response = action.type(response)
                    except ValueError:
                        print('The response entered (`%s`) is not of the required type - please enter a value of type '
                              '`%s`' % (response, action.type.__name__))
                        continue
                if action.choices and response not in action.choices:
                    print('The response entered (`%s`) is not in the list of choices - please enter a value%s' % (
                        response, choice_list_string))
                    continue
                new_value.append(response)
                arg_num += 1
            break

        if action.nargs is None:
            # the default - a single argument
            if response:
                return new_value[0]
            if action.required:
                print(argument_required_string)
                continue
            return action.default

        if type(action.nargs) is int:
            # a specified number of arguments
            if len(new_value) < action.nargs:
                if not action.required and not response:
                    return action.default
                print('This argument requires', action.nargs, 'values;', len(new_value), 'have been provided so far',
                      '- please enter another value')
                continue
            else:
                return new_value

        if action.nargs == '?':
            # an optional single argument value, or its constant
            if not response:
                if action.required:
                    print(argument_required_string)
                    continue
                if action.const:
                    response = get_input(prompt='This argument has a constant value (`%s`) - enter %s to choose this, '
                                                'leave blank to accept the default (`%s`), or enter anything else to '
                                                'return to the previous prompt:' % (
                                                    action.const, _YES_CHOICES_STRING, action.default), strip=True)
                    if response in _YES_CHOICES:
                        return action.const
                    elif response:
                        continue
                return action.default
            return response

        if action.nargs == '*':
            # a list of arguments (no minimum)
            if response:
                continue
            return new_value if new_value else action.default

        if action.nargs == '+':
            # a list of arguments (minimum of one if provided as a positional argument)
            if response:
                continue
            if not action.option_strings and len(new_value) < 1:
                print(argument_required_string)
                continue
            return new_value if new_value else action.default


# ArgumentParser's exit_on_error argument was added in Python 3.9; we support below this so override rather than catch
def error(self, message):
    self.tooey_original_error_message = message  # to be used on failure/cancellation
