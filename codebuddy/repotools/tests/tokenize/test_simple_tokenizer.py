from repotools.tokenize import simple_tokenize


def test_simple_tokenize():
    s1 = '''HelloWorld, this is an Example of CamelCase and SOME_CONSTANT
 and snake_case_and_number_1234567890_and_symbols##..
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)].
pub struct SomeStruct { field: i32 };
'''
    testcases = [
        (s1, {
            'constant',
            'number',
            'this',
            'hash',
            'hello',
            'debug',
            'some',
            'world',
            'camel',
            'of',
            'field',
            'an',
            'derive',
            'and',
            'partial',
            'snake',
            'symbols',
            'example',
            'case',
            'clone',
            'eq',
            'copy',
            'pub',
            'i32',
            'is',
            'struct',
        }),
    ]
    for tc in testcases:
        assert set(simple_tokenize(tc[0])) == tc[1]
