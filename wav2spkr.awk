# get speaker names from the wav.scp file, processed by source type
{
    if ($2 ~ "ETLT2021_ETS_EN") {
	n = split($1,b,"-");
	spkr = b[1];
    } else if ($2 ~ "TLT2017") {
	n = split($1,b,"_");
	spkr = b[1];
    } else if ($2 ~ "TLT1618") {
	n = split($1,b,"-");
	spkr = b[1];
    }
    print spkr;
}
