_inf_num = 1234567890


# inf/-inf is not standard json, some languages like golang do not
# support it, we need to convert it
def xfloat(f):
    if f == float('inf'):
        return _inf_num
    elif f == float('-inf'):
        return -_inf_num
    elif f == float('nan'):
        return 'NaN'
    return f
