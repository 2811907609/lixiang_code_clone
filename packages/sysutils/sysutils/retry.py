import time


def retry(n: int, delay: int):

    def decorator(func):

        def wrapper(*args, **kwargs):
            for i in range(n):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == n - 1:
                        raise e
                time.sleep(delay)

        return wrapper

    return decorator
