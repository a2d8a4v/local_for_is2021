#!/bin/bash

# Copyright (c) 2021 Cambridge University
# License: Apache 2.0

if [ $# -ne 3 ]; then
    echo "Usage: $0 taskdir lmid data_aug_on"
    echo "  e.g.    LOCAL_ABSPATH_CHALLENGE_DATA/ETLT2021 ETLT-2021 true:true:true:true:true"
fi

TASKDIR=$1
LMID=$2
DATAAUG=$3
if [ ! -d $TASKDIR ]; then
    echo "ERROR: source data directory not found: $TASKDIR"
    exit 100
fi

missingdir=0
for src in ETLT2021_ETS_EN ETLT2021_FBK_EN; do
    if [ ! -d ${TASKDIR}/${src} ]; then
         echo "ERROR: individual source data directory not found: ${TASKDIR}/${src}"
         missingdir=1
    fi
done
if [[ $missingdir == 1 ]]; then
    exit 100
fi

sup_sfx=sup

. ./utils/parse_options.sh 

# loop over all data sources

# prepare training data
echo "A. Prepare training data"
d=train
if [ -d data/${d} ]; then
    \rm -r data/${d}
fi
mkdir -pv data/${d} > /dev/null 2>&1

# prepare ETS data
src="ETLT2021_ETS_EN"
echo "ETS data"
prefix=""
tfix="ETS2021"

echo "${TASKDIR}/${src}/audio/${prefix}${d}"
if [ ! -d ${TASKDIR}/${src}/audio/${prefix}${d} ] ; then
    echo "ERROR: data source directory not found: ${TASKDIR}/${src}/audio/${prefix}${d}"
    exit 100
fi
find -L ${TASKDIR}/${src}/audio/${prefix}${d} -name "*.wav" > data/${d}/tmp.wav.lst

if ! test -s data/${d}/tmp.wav.lst ; then
    echo "ERROR: no wav found in ${TASKDIR}/${src}/audio/${prefix}${d}"
    exit 100
fi
cat data/${d}/tmp.wav.lst >> data/${d}/wav.unsrt.lst

if [ ! -f ${TASKDIR}/${src}/audio/${tfix}${d}.${sup_sfx} ]; then
    echo "ERROR: sup transcriptions file not found: ${TASKDIR}/${src}/audio/${tfix}${d}.${sup_sfx}"
    exit 100
fi
cat ${TASKDIR}/${src}/audio/${tfix}${d}.${sup_sfx} | sort >> data/${d}/text.tmp

# prepare FBK data
src="ETLT2021_FBK_EN"
for prefix in TLT2017 TLT1618; do
    tfix=${prefix}

    echo "${TASKDIR}/${src}/audio/${prefix}${d}"
    if [ ! -d ${TASKDIR}/${src}/audio/${prefix}${d} ] ; then
        echo "ERROR: data source directory not found: ${TASKDIR}/${src}/audio/${prefix}${d}"
        exit 100
    fi
    find -L ${TASKDIR}/${src}/audio/${prefix}${d} -name "*.wav" > data/${d}/tmp.wav.lst
    if ! test -s data/${d}/tmp.wav.lst ; then
        echo "ERROR: no wav found in ${TASKDIR}/${src}/audio/${prefix}${d}"
        exit 100
    fi
    cat data/${d}/tmp.wav.lst >> data/${d}/wav.unsrt.lst

    if [ ! -f ${TASKDIR}/${src}/audio/${tfix}${d}.${sup_sfx} ]; then
        echo "ERROR: sup transcriptions file not found: ${TASKDIR}/${src}/audio/${tfix}${d}.${sup_sfx}"
        exit 100
    fi

    if [ ${tfix} == 'TLT1618' ]; then
        cat ${TASKDIR}/${src}/audio/TLT1618train.norm.trn | sort >> data/${d}/text.tmp
    else
        cat ${TASKDIR}/${src}/audio/${tfix}${d}.${sup_sfx} | sort >> data/${d}/text.tmp
    fi
done

# data augment for train
#if [[ $(echo ${DATAAUG} | awk '{print tolower($0)}') == *"true"* ]]; then
#    mkdir -pv ${CORPUS} > /dev/null 2>&1
#    local/data_aug/data_aug.py -i data/${d}/wav.unsrt.lst -is data/${d}/text.tmp -c ${CORPUS} -o data/${d}/wav.unsrt.lst -os data/${d}/text.tmp -s 16000 -st ${d} -d ${DATAAUG}
#fi

# find empty files and remove in combined train data files
if [ ! -f data/${d}/text.tmp ]; then
    echo "ERROR: intermediate data file not found: data/${d}/text.tmp"
    exit 100
fi
# first cut the utt_id column
sort -u data/${d}/text.tmp | sed '/^[[:space:]]*$/d' | awk -f local/spellcorrect.awk - > data/${d}/text

if [ ! -f data/${d}/wav.unsrt.lst ]; then
    echo "ERROR: intermediate data file not found: data/${d}/wav.unsrt.lst"
    exit 100
fi
sort -u data/${d}/wav.unsrt.lst | sed '/^[[:space:]]*$/d' | awk -f local/getwavlst.awk data/${d}/text a=1 - > data/${d}/wav.lst

# complete setting up train data
awk '{n=split($1,b,"/");m=split(b[n],c,".wav");print c[1], $1;}' data/${d}/wav.lst | sort > data/${d}/wav.scp

awk -f local/wav2spkr.awk data/${d}/wav.scp > data/${d}/speakers 

if [ ! -f data/${d}/speakers ]; then
    echo "ERROR: speakers file not created: data/${d}/speakers"
    exit 100
fi
paste data/${d}/wav.scp data/${d}/speakers | awk '{print $1,$3}' > data/${d}/utt2spk
utils/utt2spk_to_spk2utt.pl data/${d}/utt2spk > data/${d}/spk2utt

utils/fix_data_dir.sh data/${d}

# make train LM data
mkdir -pv texts
lm_train="texts/${LMID}train.trn.txt"
lm_traintext="${TASKDIR}/ETLT2021_FBK_EN/texts/TLT2016Wtrain.trn.txt"

if [ ! -f ${lm_traintext} ]; then
    echo "ERROR: LM training text not found: ${lm_traintext}"
    exit 100
fi
awk -f local/spellcorrect_text.awk ${lm_traintext} > texts/tmp.train.trn.txt
awk '{$1=""; print}' data/train/text | cat - texts/tmp.train.trn.txt >  ${lm_train}
\rm texts/tmp.train.trn.txt

# prepare dev data
echo "B. Preparing dev data"
d=dev
src=ETLT2021_ETS_EN
prefix=""
tfix=ETS2021
if [ -d data/${d} ]; then
    \rm -r data/${d}
fi
mkdir -pv data/${d}

echo "${TASKDIR}/${src}/audio/${prefix}${d}"
if [ ! -d ${TASKDIR}/${src}/audio/${prefix}${d} ] ; then
    echo "ERROR: data source directory not found: ${TASKDIR}/${src}/audio/${prefix}${d}"
    exit 100
fi
find -L ${TASKDIR}/${src}/audio/${prefix}${d} -name "*.wav" > data/${d}/tmp.wav.lst
if ! test -s data/${d}/tmp.wav.lst ; then
    echo "ERROR: no wav found in ${TASKDIR}/${src}/audio/${prefix}${d}"
    exit 100
fi
cat data/${d}/tmp.wav.lst >> data/${d}/wav.unsrt.lst
    
if [ ! -f ${TASKDIR}/${src}/audio/${tfix}${d}.${sup_sfx} ]; then
    echo "ERROR: sup transcriptions file not found: ${TASKDIR}/${src}/audio/${tfix}${d}.${sup_sfx}"
    exit 100
fi
cat ${TASKDIR}/${src}/audio/${tfix}${d}.${sup_sfx} | sort >> data/${d}/text.tmp

# find empty files and remove
sort -u data/${d}/text.tmp | awk -f local/remempty.awk - | awk -f local/spellcorrect.awk - > data/${d}/text
sort -u data/${d}/wav.unsrt.lst | awk -f local/getwavlst.awk data/${d}/text a=1 - > data/${d}/wav.lst

# complete setting up test set data
awk '{n=split($1,b,"/");m=split(b[n],c,".wav");print c[1], $1;}' data/${d}/wav.lst | sort > data/${d}/wav.scp

awk -f local/wav2spkr.awk data/${d}/wav.scp > data/${d}/speakers 
paste data/${d}/wav.scp data/${d}/speakers | awk '{print $1,$3}' > data/${d}/utt2spk
utils/utt2spk_to_spk2utt.pl data/${d}/utt2spk > data/${d}/spk2utt

utils/fix_data_dir.sh data/${d}

lm_dev=texts/${LMID}dev.trn.txt
awk '{$1=""; print}' data/dev/text > ${lm_dev}

\rm data/*/tmp.wav.lst
\rm data/*/wav.unsrt.lst

