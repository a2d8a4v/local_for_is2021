import random

class CutMix(object):
    def __init__(self, index_i, index_j, length=3200, k=6):
        super().__init__()
        self.index_i = index_i
        self.index_j = index_j
        self.length = length
        self.k = k

    def __call__(self, x1, x2):
        return self.augment(x1, x2)

    def augment(self, x1, x2):
        index_i = self.index_i
        index_j = self.index_j
        length = self.length
        k = self.k

        if length < ((len(x1)//k)-length)-(index_i+index_j)//2:
            si = random.sample(range(length, ((len(x1)//k)-length)-(index_i+index_j)//2) , k)
        else:
            si = random.sample(range(length, length*2), k)
        for i in range(1, k, 1):
            # x1[index_i+sum(si[:i-1]):index_i+sum(si[:i])] = x2[index_j+sum(si[:i-1]):index_j+sum(si[:i])]
            if max(index_i, index_j)+sum(si[:i])+length < min(len(x1),len(x2)):
                x1[index_i+sum(si[:i]):index_i+sum(si[:i])+length] = x2[index_j+sum(si[:i]):index_j+sum(si[:i])+length]
            else:
                break
        return x1
