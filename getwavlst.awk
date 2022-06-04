# only keep wav files that are found in text source
{
    if (a == 0) {
	flist[$1] = 1;
    } else {
        n = split($1,b,"/");
	m = split(b[n],c,".wav");
	if (flist[c[1]] == 1) {
            # wav is in input list
   	    print $0;
	}
    }
}
