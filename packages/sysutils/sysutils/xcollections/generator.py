def yield_agg(g, batch_size: int = 20):
    '''this convert generator to batch generator'''
    batch = []
    for item in g:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
