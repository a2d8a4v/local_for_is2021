

def opentext( file, col_start ):
    s = {}
    with open(file, "r") as f:
        for l in f.readlines():
            for w in l.split()[col_start:]:
                s.add(w)
    return list(s)