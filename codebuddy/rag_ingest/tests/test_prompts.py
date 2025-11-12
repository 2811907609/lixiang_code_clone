from rag_ingest.prompts import render


def test_render():
    content = render('code_summary.jinja2',
                     lang='go',
                     path='./test.go',
                     code='// this is go test code')
    print(f'render ==========\n||{content}||')
