from inference_server.modules.specedit.lib.patch import patch_spec_edit


def test_patch_ngram():
    from vllm.spec_decode.ngram_worker import NGramWorker
    assert NGramWorker.__name__ == 'NGramWorker'

    patch_spec_edit()
    from vllm.spec_decode.ngram_worker import NGramWorker
    assert NGramWorker.__name__ == 'SpecEditWorker'


def test_patch_method():

    class A:

        def __init__(self, a):
            self.x = a

        def sample(self, n):
            print('sample is ', self.x + n)

    class B:

        def __init__(self, a):
            self.x = a

        def sample_a(self, n):
            A.sample(self, n)

    b = B(10)
    b.sample_a(20)
