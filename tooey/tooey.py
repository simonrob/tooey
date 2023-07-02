"""
Tooey: Gooey, but for TUIs
Decorate your argparse function with `@Tooey` to be prompted interactively in the terminal to enter each argument
"""
import argparse
import os
import sys

# noinspection PyUnresolvedReferences,PyProtectedMember
from argparse import (
    ArgumentParser,

    _HelpAction,
    _VersionAction,

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


class Tooey(object):
    def __init__(self, f):
        self.f = f

    def __call__(self, *args, **kwargs):
        ArgumentParser.original_parse_args = ArgumentParser.parse_args
        ArgumentParser.original_error = ArgumentParser.error
        ArgumentParser.original_error_message = None

        ArgumentParser.parse_args = parse_args
        ArgumentParser.error = error

        result = self.f(*args, **kwargs)

        ArgumentParser.parse_args = ArgumentParser.original_parse_args
        ArgumentParser.error = ArgumentParser.original_error

        del ArgumentParser.original_parse_args
        del ArgumentParser.original_error
        del ArgumentParser.original_error_message

        return result


def parse_args(self, args=None, namespace=None):
    self.add_argument('--ignore-tooey', action='store_true', help=argparse.SUPPRESS)
    self.add_argument('--force-tooey', action='store_true', help=argparse.SUPPRESS)
    parsed_args = self.original_parse_args(args, namespace)

    ignore_tooey = parsed_args.ignore_tooey or os.environ.get('IGNORE_TOOEY')
    force_tooey = parsed_args.force_tooey or os.environ.get('FORCE_TOOEY')
    if ignore_tooey and force_tooey:
        force_tooey = False
    del parsed_args.__dict__['ignore_tooey']
    del parsed_args.__dict__['force_tooey']
    self._actions = [a for a in self._actions if a.dest not in ('ignore_tooey', 'force_tooey')]

    if (not sys.stdout.isatty() or ignore_tooey) and not force_tooey:
        if self.original_error_message:
            self.original_error(self.original_error_message)
        return parsed_args

    print(_SEPARATOR)
    print('Tooey interactive mode starting - presenting script options')

    try:
        # we have to use the parser's internal _actions object because there is no other way to get an action's details
        for action in self._actions:
            if type(action) in (_HelpAction, _VersionAction):
                continue  # these actions do not request user input

            option_string = ', '.join(action.option_strings) if action.option_strings else action.dest
            current_value = parsed_args.__dict__[action.dest]

            print()
            print('Argument:', option_string, '(required)' if action.required else '')
            print('Help text:', action.help)

            if current_value not in (action.default, []) and type(action) is not _AppendConstAction:
                # note: currently all `append_const` actions are shown even if some are provided at runtime
                # we don't exclude these because the intent may be to provide them multiple times
                print('Skipping interactive mode for argument provided at runtime (value: %s)' % current_value)
                continue

            new_value = _parse_action(action, current_value)

            if isinstance(parsed_args.__dict__[action.dest], list):  # lists should be extended rather than replaced
                if new_value:
                    parsed_args.__dict__[action.dest] = list(set(current_value + new_value))
            else:
                parsed_args.__dict__[action.dest] = new_value

            print('Outcome:', action.dest, 'is `%s`' % parsed_args.__dict__[action.dest])

        print('\nTooey interactive mode completed - continuing script')
        print(_SEPARATOR)

        return parsed_args

    except KeyboardInterrupt:
        print('\n\nTooey interactive mode interrupted - continuing script')
        print(_SEPARATOR)
        if self.original_error_message:
            self.original_error(self.original_error_message)


def _parse_action(action, current_value):
    action_type = type(action)

    if action_type in (_StoreConstAction, _StoreTrueAction, _StoreFalseAction):
        # these action types provide a constant value - either user-defined, or True/False
        yes_response = action.const if action_type is _StoreConstAction else not action.default
        if action.required:
            print('Skipping interactive mode for required action - the only possible value is `%s`' % yes_response)
            return yes_response
        print('Enter %s to set to `%s`, or anything else to accept the default value (`%s`): ' % (
            _YES_CHOICES_STRING, yes_response, action.default))
        response = input().strip()
        return yes_response if response in _YES_CHOICES else action.default

    elif action_type is _AppendConstAction:
        # this action type appends a constant value each time it is provided
        new_value = current_value if current_value else []
        while True:
            print('Enter %s to append `%s` to the current value of `%s`, or anything else to skip: ' % (
                _YES_CHOICES_STRING, action.const, new_value))
            response = input().strip()
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
            print('Enter the number of times you would like to provide this argument, or leave blank to accept the '
                  'default value (`%s`): ' % action.default)
            count_response = input().strip()
            if count_response.isdigit():
                return int(count_response)
            elif not count_response:
                return action.default

    elif action_type is _StoreAction:
        # the default action type is able to handle one or more arguments flexibly
        return _parse_store_action(action)

    else:
        print('Tooey warning: action type', action_type, 'is not currently handled - skipping')

    return action.default


def _parse_store_action(action, append=False):
    new_value = []
    arg_num = 0
    type_string = ' of type `%s`' % action.type.__name__ if action.type else ''
    choice_list_string = (' from `%s`' % ', '.join([str(c) for c in action.choices])) if action.choices else ''
    argument_required_string = 'This argument is required but has not been provided - please enter a value'
    while True:
        while True:
            print('Enter %s%s%s for this argument, or leave blank to skip: ' % (
                'an additional value' if append else 'a value',
                choice_list_string if choice_list_string else type_string if type_string else '',
                (' to append to the current value `%s`' % new_value) if len(new_value) > 0 else ''))
            response = input()
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
                    print('This argument has a constant value (`%s`) - enter %s to choose this, or leave blank to '
                          'accept the default (`%s`): ' % (action.const, _YES_CHOICES_STRING, action.default))
                    if input().strip() in _YES_CHOICES:
                        return action.const
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
    force_parser = argparse.ArgumentParser(add_help=False)
    force_parser.add_argument('--force-tooey', action='store_true')
    force_tooey = force_parser.parse_known_args()[0].force_tooey or os.environ.get('FORCE_TOOEY')
    if sys.stdout.isatty() or force_tooey:
        self.original_error_message = message  # to be used on failure/cancellation
        return
    self.original_error(message)
