import random
import numpy as np

class SamplePairing(object):
    def __init__(self, index_i, index_j, length=3200, k=6):
        super().__init__()
        self.index_i = index_i
        self.index_j = index_j
        self.length = length
        self.k = k

    def __call__(self, x1, x2):
        [x1, x2] = self.padding([x1,x2])
        return self.augment(x1, x2)

    def padding(self, item_list):
        new_list=[]
        len_list=[ len(x) for x in item_list ]
        for x in item_list:
            if len(x) < max(len_list):
                pad_n = ( max(len_list) - len(x) ) / 2
                new_list.append( np.pad(x, (int(np.floor(pad_n)), int(np.ceil(pad_n))), 'wrap') )
            else:
                new_list.append( x )
        return new_list

    def augment(self, x1, x2):
        lmda = random.uniform(0,0.2)
        nx1 = (1-lmda)*x1+lmda*x2
        return nx1
