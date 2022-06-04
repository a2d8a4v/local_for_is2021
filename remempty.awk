# remove files with transcription of "@sil" i.e. empty files
{
    if (NF == 2) {
	if ($2 != "@sil") {
            # only keep files with a single word transcription if not the empty symbol
	    print $0;
	}
    } else {
        # file had standard transcription, keep
	print $0;
    }
}
