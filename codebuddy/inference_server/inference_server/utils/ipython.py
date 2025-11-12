import builtins


def is_in_ipython():
    return hasattr(builtins, '__IPYTHON__')


def enable_auto_reload():
    '''python function for ipython magic
    %load_ext autoreload
    %autoreload 2
    the magic will fail lint tool, so let's use real python
    '''
    if not is_in_ipython():
        print("not in ipython, won't enable auto reload")
        return

    try:
        # 在IPython环境中，get_ipython()函数是可用的
        ipy = get_ipython()  # noqa: F821
        ipy.run_line_magic('load_ext', 'autoreload')
        ipy.run_line_magic('autoreload', '2')
        print('autoreload enabled')
    except Exception as e:
        print(f'failed to get ipython instance, got error {e}')
        return


enable_auto_reload()
