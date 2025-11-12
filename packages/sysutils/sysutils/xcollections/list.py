def list_sliding(arr, window_size, step=1):
    '''each chunk will have window_size elements.
    Each chunk will be step elements away from the previous one. '''
    return [arr[i:i + window_size] for i in range(0, len(arr), step)]
