import json
import pickle


def jsonLoad(scores_json):
    with open(scores_json) as json_file:
        return json.load(json_file)


def pickleStore( savethings , filename ):
    dbfile = open( filename , 'wb' )
    pickle.dump( savethings , dbfile )
    dbfile.close()
    return


def pikleOpen( filename ):
    file_to_read = open( filename , "rb" )
    p = pickle.load( file_to_read )
    return p


def opentext( file, col_start ):
    s = set()
    with open(file, "r") as f:
        for l in f.readlines():
            for w in l.split()[col_start:]:
                s.add(w)
    return list(s)


def getbyFilter( data, filter ):
    rtn = [i for i in data if filter in i]
    return list(set(rtn))


## START
file = "/share/nas167/a2y3a1N0n2Yann/tlt-school-chanllenge/kaldi/egs/tlt-school/is2021_data-prep-all_baseline/data/lang_1char/text_all_cleaned"
data = opentext( file, 1 )

## Validation of our data
# a = getbyFilter( data, '<unk>' )
# print(a)
# b = getbyFilter( data, '<unk-' )
# print(b)
# c = getbyFilter( data, '@' )
# print(c)
d = getbyFilter( data, '-' )
d = [ i for i in d if len(list(filter(None, i.split("-")))) >= 2 ]
print(d)
# e = getbyFilter( data, '#' )
# print(e)
# f = getbyFilter( data, '(' )
# print(f)
# g = getbyFilter( data, ')' )
# print(g)