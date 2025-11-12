'''
pytest -vv  -s pkg/codebuddy/postprocess -k 'test_drop_duplicate_suffix'
'''

from typing import Callable

from inference_server.types import CompletionItem

from .fix_duplicate import (
    drop_duplicate_suffix,
    fix_fim_multiline_duplicate,
    remove_duplicated_block_closing_line,
)
from .test_utils import new_completion_item, not_changed_symbol, run_testcases


def assure_result(fn: Callable, item: CompletionItem, completion: str,
                  expected: str):
    item.set_output(completion)
    fn(item)
    assert item.output_text() == expected


def test_fix_fim_multiline_duplicate():
    # should trim multiline completions, when the suffix have non-auto-closed chars in the current line.
    item = new_completion_item('''
        let error = new Error("Something went wrong");
        console.log(║message);
    ''')
    completion = '''message);
        throw error;'''
    assure_result(fix_fim_multiline_duplicate, item, completion, '')

    # should trim multiline completions, when the suffix have non-auto-closed chars in the current line
    item = new_completion_item('''
        let error = new Error("Something went wrong");
        console.log(║message);
    ''')
    completion = '''error, message);
        throw error;'''
    assure_result(fix_fim_multiline_duplicate, item, completion, 'error, ')

    # should allow singleline completions, when the suffix have non-auto-closed chars in the current line
    item = new_completion_item('''
        let error = new Error("Something went wrong");
        console.log(║message);
    ''')
    completion = '''error, '''
    assure_result(fix_fim_multiline_duplicate, item, completion, completion)

    # should allow multiline completions, when the suffix only have auto-closed chars that will be replaced in the current line, such as `)]}`
    item = new_completion_item('''
            function findMax(arr) {║}
    ''')
    completion = '''\
              let max = arr[0];
          for (let i = 1; i < arr.length; i++) {
            if (arr[i] > max) {
              max = arr[i];
            }
          }
          return max;
        }'''
    assure_result(fix_fim_multiline_duplicate, item, completion, completion)


def test_drop_duplicate_suffix():
    testcases = [
        ('should drop completion duplicated with suffix', '''
    let sum = (a, b) => {
        ║return a + b;
    };
''', 'return a + b;', ''),
        ('should drop completion similar to suffix', '''
    let sum = (a, b) => {
        return a + b;
        ║
    };
''', '}', ''),
        # 这里如果保留会更好，但是跟上面的case冲突了，这里按理更合适的应该是补全{\n}这样的
        ('case: single open char', '''
	return nil
}
func (w *Worker) Run() {
	for {
		select ║
	}
	err := w.pullTasks()
	if err != nil {
		log.Error().Msgf("pull tasks error: %v", err)
		return
	}
''', '{', '')
    ]
    run_testcases(testcases, drop_duplicate_suffix)


def test_remove_duplicated_block_closing_line():
    testcases = [
        ('should remove duplicated block closing line.', '''
        function hello() {
          ║
        }
''', '''console.log("hello");
        }''', 'console.log("hello");'),
        ('should remove duplicated block closing line.', '''
        function check(condition) {
          if (!condition) {
            ║
          } else {
            return;
          }
        }''', '''throw new Error("check not passed");
          }''', 'throw new Error("check not passed");'),
        ('should remove duplicated block closing line.', '''
        function check(condition) {
          if (!condition) {
            ║
        }
''', '''throw new Error("check not passed");
          }''', not_changed_symbol),
    ]
    run_testcases(testcases, remove_duplicated_block_closing_line)
