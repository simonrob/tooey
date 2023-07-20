import argparse
import io
import os
import sys
import unittest.mock

from tooey import Tooey


class Argument(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class TestTooey(unittest.TestCase):
    @Tooey
    def create_parser(self, test_parameters, mocked_input):
        os.environ['FORCE_TOOEY'] = '1'

        parser = argparse.ArgumentParser()
        input_values = []
        for parameter in test_parameters:
            arg, inputs, outcome = parameter
            parser.add_argument(*arg.args, **arg.kwargs)
            if inputs is not None:
                input_values.extend(inputs)

        mocked_input.side_effect = input_values
        result = parser.parse_args()

        del os.environ['FORCE_TOOEY']
        return result

    def check_result(self, test_parameters, result):
        for parameter in test_parameters:
            arg, inputs, outcome = parameter
            dest = arg.kwargs['dest'] if 'dest' in arg.kwargs else arg.args[0].lstrip('--').replace('-', '_')
            self.assertEqual(outcome, result.__dict__[dest])

    # ------------------------------------------------------------------------------------------------------------------

    def test_no_tooey_error(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--required', required=True)
        with self.assertRaises(SystemExit):
            parser.parse_args()

    def test_no_tooey_no_error(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--optional')
        result = parser.parse_args()
        self.assertIsNone(result.optional)

    @Tooey
    def test_ignored_tooey_error(self):
        os.environ['FORCE_TOOEY'] = '1'
        os.environ['IGNORE_TOOEY'] = '1'

        parser = argparse.ArgumentParser()
        parser.add_argument('--required', required=True)
        with self.assertRaises(SystemExit):
            parser.parse_args()

        del os.environ['FORCE_TOOEY']
        del os.environ['IGNORE_TOOEY']

    @Tooey
    def test_ignored_tooey_no_error(self):
        os.environ['FORCE_TOOEY'] = '1'
        os.environ['IGNORE_TOOEY'] = '1'

        parser = argparse.ArgumentParser()
        parser.add_argument('--optional')
        result = parser.parse_args()

        del os.environ['FORCE_TOOEY']
        del os.environ['IGNORE_TOOEY']

        self.assertIsNone(result.optional)

    @Tooey
    def test_arguments_provided(self):
        os.environ['FORCE_TOOEY'] = '1'

        parser = argparse.ArgumentParser()
        parser.add_argument('--provided')
        args = parser.parse_args(['--provided', 'abc'])

        del os.environ['FORCE_TOOEY']

        self.assertIs(args.provided, 'abc')

    @Tooey
    def test_unsupported_action(self):
        os.environ['FORCE_TOOEY'] = '1'

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        a_parser = subparsers.add_parser('a')
        a_parser.add_argument('a_arg')
        args = parser.parse_args()

        del os.environ['FORCE_TOOEY']

        self.assertEqual(args, argparse.Namespace())

    @Tooey
    @unittest.mock.patch('builtins.input')
    def test_interrupted_entry(self, mocked_input):
        os.environ['FORCE_TOOEY'] = '1'

        mocked_input.side_effect = [KeyboardInterrupt]
        parser = argparse.ArgumentParser()
        parser.add_argument('--required', required=True)
        with self.assertRaises(SystemExit):
            parser.parse_args()

        del os.environ['FORCE_TOOEY']

    def test_with_gooey(self):
        # TODO: test the Gooey integration more extensively/effectively
        from gooey import Gooey

        @Gooey
        @Tooey
        @unittest.mock.patch('builtins.input')
        def tooey_with_gooey(mocked_input):
            os.environ['FORCE_TOOEY'] = '1'

            mocked_input.side_effect = ['y']
            parser = argparse.ArgumentParser()
            parser.add_argument('--no-gooey')
            args = parser.parse_args()

            del os.environ['FORCE_TOOEY']

            self.assertIs(args.no_gooey, 'y')

        tooey_with_gooey()

        with unittest.mock.patch('sys.argv', ['fake_gooey_with_tooey.py', '--ignore-gooey']):
            @Tooey
            @Gooey
            @unittest.mock.patch('builtins.input')
            def gooey_with_tooey(mocked_input):
                os.environ['FORCE_TOOEY'] = '1'

                mocked_input.side_effect = ['y']
                parser = argparse.ArgumentParser()
                parser.add_argument('--skipped-gooey')
                args = parser.parse_args()

                del os.environ['FORCE_TOOEY']

                self.assertIs(args.skipped_gooey, 'y')

            gooey_with_tooey()

        sys.modules.pop('gooey')
        del Gooey

    def test_nothing_of_value_just_to_get_full_coverage(self):
        from tooey.tooey import safe_get_namespace_boolean  # just returns false when a key is not found...
        self.assertFalse(safe_get_namespace_boolean([argparse.Namespace()], 'fake_key'))

    # ------------------------------------------------------------------------------------------------------------------

    @unittest.mock.patch('builtins.input')
    def test_store_true(self, mocked_input):
        test_parameters = [
            (Argument('--positive', action='store_true', help='A positive _StoreTrueAction'),  # args for add_argument
             ['y'],  # the value(s) to pass as input; '' to provide no input; None if no input is expected
             True),  # the expected outcome

            (Argument('--negative', action='store_true', help='_StoreTrueAction'),
             ['n'],
             False),

            (Argument('--skipped', action='store_true', help='_StoreTrueAction'),
             [''],
             False),

            (Argument('--req', action='store_true', required=True, help='_StoreTrueAction'),
             None,
             True)
        ]

        self.check_result(test_parameters, self.create_parser(test_parameters, mocked_input))

    @unittest.mock.patch('builtins.input')
    def test_store_false(self, mocked_input):
        test_parameters = [
            (Argument('--positive', action='store_false', help='_StoreFalseAction'),
             ['y'],
             False),

            (Argument('--negative', action='store_false', help='_StoreFalseAction'),
             ['n'],
             True),

            (Argument('--skipped', action='store_false', help='_StoreFalseAction'),
             [''],
             True),

            (Argument('--required', action='store_false', required=True, help='_StoreFalseAction'),
             None,
             False)
        ]

        self.check_result(test_parameters, self.create_parser(test_parameters, mocked_input))

    @unittest.mock.patch('builtins.input')
    def test_store_const(self, mocked_input):
        test_parameters = [
            (Argument('--positive', action='store_const', const=42, default=5, help='_StoreConstAction'),
             ['y'],
             42),

            (Argument('--negative', action='store_const', const=42, default=5, help='_StoreConstAction'),
             ['n'],
             5),

            (Argument('--skipped', action='store_const', const=42, default=5, help='_StoreConstAction'),
             [''],
             5),

            (Argument('--required', action='store_const', const=42, default=5, required=True, help='_StoreConstAction'),
             None,
             42)
        ]

        self.check_result(test_parameters, self.create_parser(test_parameters, mocked_input))

    @unittest.mock.patch('builtins.input')
    def test_append_const(self, mocked_input):
        outcome = [42, 42, 5, 10]  # we are testing the final outcome, which includes all args with the same dest value
        test_parameters = [
            (Argument('--const-1', action='append_const', dest='append_const', const=42, help='_AppendConstAction'),
             ['y', 'y', ''],
             outcome),

            (Argument('--const-2', action='append_const', dest='append_const', const=5, help='_AppendConstAction'),
             ['y', ''],
             outcome),

            (Argument('--const-3', action='append_const', dest='append_const', const=10, required=True,
                      help='_AppendConstAction'),
             [''],
             outcome)
        ]

        self.check_result(test_parameters, self.create_parser(test_parameters, mocked_input))

    @unittest.mock.patch('builtins.input')
    def test_count(self, mocked_input):
        test_parameters = [
            (Argument('--count-1', action='count', help='_CountAction', default=1),
             ['y', 'n', ''],
             1),

            (Argument('--count-2', action='count', help='_CountAction', default=1),
             ['5'],
             5)
        ]

        self.check_result(test_parameters, self.create_parser(test_parameters, mocked_input))

    @unittest.mock.patch('builtins.input')
    def test_append(self, mocked_input):
        outcome = ['abc', 'def', 'ghi', 'jkl']  # as above, the outcome includes all args with the same dest value
        test_parameters = [
            (Argument('--append-1', action='append', dest='append', help='_AppendAction'),
             ['abc', 'def', ''],
             outcome),

            (Argument('--append-2', action='append', dest='append', help='_AppendAction'),
             ['ghi', ''],
             outcome),

            (Argument('--append-3', action='append', dest='append', required=True, help='_AppendAction'),
             ['', 'jkl', ''],
             outcome)
        ]

        self.check_result(test_parameters, self.create_parser(test_parameters, mocked_input))

    @unittest.mock.patch('builtins.input')
    def test_positional(self, mocked_input):
        test_parameters = [
            (Argument('positional', help='Positional _StoreAction; no `nargs`'),
             ['', 'abc'],
             'abc'),

            (Argument('positional_1', nargs=1, help='Positional _StoreAction; `nargs=1`'),
             ['', 'abc'],
             ['abc']),

            (Argument('positional_2', nargs=2, help='Positional _StoreAction; `nargs=2`'),
             ['', 'abc', '', 'def'],
             ['abc', 'def']),

            (Argument('positional_q_1', nargs='?', help='Positional _StoreAction; `nargs=?`; no const'),
             [''],
             None),

            (Argument('positional_q_2', nargs='?', help='Positional _StoreAction; `nargs=?`; no const'),
             ['abc'],
             'abc'),

            (Argument('positional_q_c_y', nargs='?', const='const', help='Positional _StoreAction; `nargs=?`; const'),
             ['', 'y'],
             'const'),

            (Argument('positional_q_c_n', nargs='?', const='const', help='Positional _StoreAction; `nargs=?`; const'),
             ['', 'n', '', ''],
             None),

            (Argument('positional_a', nargs='*', help='Positional _StoreAction; `nargs=*`'),
             ['abc', 'def', 'ghi', ''],
             ['abc', 'def', 'ghi']),

            (Argument('positional_p', nargs='+', help='Positional _StoreAction; `nargs=+`'),
             ['', 'abc', 'def', 'ghi', ''],
             ['abc', 'def', 'ghi'])
        ]

        self.check_result(test_parameters, self.create_parser(test_parameters, mocked_input))

    @unittest.mock.patch('builtins.input')
    def test_named(self, mocked_input):
        test_parameters = [
            (Argument('--named-0a', help='Named _StoreAction; no `nargs`'),
             [''],
             None),

            (Argument('--named-0b', help='Named _StoreAction; no `nargs`'),
             ['abc'],
             'abc'),

            (Argument('--named-1', nargs=1, help='Named _StoreAction; `nargs=1`'),
             ['abc'],
             ['abc']),

            (Argument('--named-2a', nargs=2, help='Named _StoreAction; `nargs=2`'),
             ['abc', ''],
             None),

            (Argument('--named-2b', nargs=2, help='Named _StoreAction; `nargs=2`'),
             ['abc', 'def'],
             ['abc', 'def']),

            (Argument('--named-q-1', nargs='?', help='Named _StoreAction; `nargs=?`; no const'),
             [''],
             None),

            (Argument('--named-q-2', nargs='?', help='Named _StoreAction; `nargs=?`; no const'),
             ['abc'],
             'abc'),

            (Argument('--named-q-3', nargs='?', required=True, help='Named _StoreAction; `nargs=?`; no const'),
             ['', 'abc'],
             'abc'),

            (Argument('--named-qc-y', nargs='?', const='const', help='Named _StoreAction; `nargs=?`; const'),
             ['', 'y'],
             'const'),

            (Argument('--named-qc-n', nargs='?', const='const', help='Named _StoreAction; `nargs=?`; const'),
             ['', 'n', '', ''],
             None),

            (Argument('--named-a', nargs='*', help='Named _StoreAction; `nargs=*`'),
             ['abc', 'def', 'ghi', ''],
             ['abc', 'def', 'ghi']),

            (Argument('--named-p', nargs='+', help='named _StoreAction; `nargs=+`'),
             ['abc', 'def', 'ghi', ''],
             ['abc', 'def', 'ghi'])
        ]

        self.check_result(test_parameters, self.create_parser(test_parameters, mocked_input))

    @unittest.mock.patch('builtins.input')
    def test_types(self, mocked_input):
        test_parameters = [
            (Argument('--type-int-1', type=int, help='_StoreAction; `int` type'),
             [''],
             None),

            (Argument('--type-int-2', type=int, help='_StoreAction; `int` type'),
             ['abc', ''],
             None),

            (Argument('--type-int-3', type=int, help='_StoreAction; `int` type'),
             ['abc', 1],
             1),

            (Argument('--type-float-1', type=float, help='_StoreAction; `int` type'),
             [''],
             None),

            (Argument('--type-float-2', type=float, help='_StoreAction; `int` type'),
             ['1'],
             1.0),

            (Argument('--type-float-3', type=float, help='_StoreAction; `int` type'),
             ['3.14'],
             3.14)
        ]

        self.check_result(test_parameters, self.create_parser(test_parameters, mocked_input))

    @Tooey
    @unittest.mock.patch('builtins.input')
    def test_file_type(self, mocked_input):
        os.environ['FORCE_TOOEY'] = '1'

        parser = argparse.ArgumentParser()
        parser.add_argument('--type-file', type=argparse.FileType('rb'), help='_StoreAction; `int` type')

        mocked_input.side_effect = ['/dev/random']
        args = parser.parse_args()

        self.assertIs(type(args.type_file), io.BufferedReader)
        self.assertIs(args.type_file.name, '/dev/random')
        args.type_file.close()

        del os.environ['FORCE_TOOEY']

    @unittest.mock.patch('builtins.input')
    def test_choices(self, mocked_input):
        test_parameters = [
            (Argument('--choice-0a', type=int, choices=range(1, 6), help='_StoreAction; choices 1-5'),
             [''],
             None),

            (Argument('--choice-0b', type=int, choices=range(1, 6), help='_StoreAction; choices 1-5'),
             ['abc', '6', '1'],
             1),

            (Argument('--choice-1', nargs=1, type=int, choices=range(1, 6),
                      help='_StoreAction; `nargs=1`; choices 1-5'),
             ['1'],
             [1]),

            (Argument('--choice-2a', nargs=2, type=int, choices=range(1, 6),
                      help='_StoreAction; `nargs=2`; choices 1-5'),
             ['1', ''],
             None),

            (Argument('--choice-2b', nargs=2, type=int, choices=range(1, 6),
                      help='_StoreAction; `nargs=2`; choices 1-5'),
             ['1', '2'],
             [1, 2]),

            (Argument('--choice-q-1', nargs='?', type=int, choices=range(1, 6),
                      help='_StoreAction; `nargs=?`; no const; choices 1-5'),
             [''],
             None),

            (Argument('--choice-q-2', nargs='?', type=int, choices=range(1, 6),
                      help='_StoreAction; `nargs=?`; no const; choices 1-5'),
             ['1'],
             1),

            (Argument('--choice-q-3', nargs='?', type=int, choices=range(1, 6), required=True,
                      help='_StoreAction; `nargs=?`; no const; choices 1-5'),
             ['', '1'],
             1),

            (Argument('--choice-qc-y', nargs='?', type=int, choices=range(1, 6), const='const',
                      help='_StoreAction; `nargs=?`; const; choices 1-5'),
             ['', 'y'],
             'const'),

            (Argument('--choice-qc-n', nargs='?', type=int, choices=range(1, 6), const='const',
                      help='_StoreAction; `nargs=?`; const; choices 1-5'),
             ['', 'n', '', ''],
             None),

            (Argument('--choice-a', nargs='*', type=int, choices=range(1, 6),
                      help='_StoreAction; `nargs=*`; choices 1-5'),
             ['1', '2', '3', ''],
             [1, 2, 3]),

            (Argument('--choice-p', nargs='+', type=int, choices=range(1, 6),
                      help='_StoreAction; `nargs=+`; choices 1-5'),
             ['3', '2', '1', ''],
             [3, 2, 1])
        ]

        self.check_result(test_parameters, self.create_parser(test_parameters, mocked_input))


if __name__ == '__main__':
    unittest.main()
