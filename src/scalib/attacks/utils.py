
def _indices_dict(lis):
    d = dict()
    for i,(a,b) in enumerate(lis):
        d.setdefault(a, list()).append(i)
        d.setdefault(b, list()).append(i)
    return d

def _disjoint_indices(lis):
    d = _indices_dict(lis)
    sets = []
    while len(d):
        que = set(d.popitem()[1])
        ind = set()
        while len(que):
            ind |= que
            que = set([y for i in que
                         for x in lis[i]
                         for y in d.pop(x, [])]) - ind
        sets += [ind]
    return sets

def disjoint_sets(lis):
    """Let lis be a list of pairs that represent equivelence relations, this
    returns a list of sets whose elements are equivalent.

    From https://stackoverflow.com/a/20167281
    """
    return [set([x for i in s for x in lis[i]]) for s in _disjoint_indices(lis)]
