#!/bin/bash

# 1i is like 1h, while it introduces 'apply-cmvn-online' that does
# cmn normalization both for i-extractor and TDNN input.

set -e -o pipefail

# First the options that are passed through to run_ivector_common.sh
# (some of which are also used in this script directly).
stage=18
nj=16
train_set=train_si284
test_sets="test_dev93 test_eval92"
gmm=tri4b        # this is the source gmm-dir that we'll use for alignments; it
                 # should have alignments for the specified training data.

num_threads_ubm=2

nj_extractor=8
# It runs a JOB with '-pe smp N', where N=$[threads*processes]
num_threads_extractor=2
num_processes_extractor=2

nnet3_affix="_online_cmn"   # affix for exp dirs, e.g. it was _cleaned in tedlium.

# Options which are not passed through to run_ivector_common.sh
affix=1i   #affix for TDNN+LSTM directory e.g. "1a" or "1b", in case we change the configuration.
common_egs_dir=
reporting_email=

# Setting 'online_cmvn' to true replaces 'apply-cmvn' by
# 'apply-cmvn-online' both for i-vector extraction and TDNN input.
# The i-vector extractor uses the config 'conf/online_cmvn.conf' for
# both the UBM and the i-extractor. The TDNN input is configured via
# '--feat.cmvn-opts' that is set to the same config, so we use the
# same cmvn for i-extractor and the TDNN input.
online_cmvn=true

# LSTM/chain options
train_stage=-10
xent_regularize=0.1
dropout_schedule='0,0@0.20,0.5@0.50,0'

# training chunk-options
chunk_width=140,100,160
# we don't need extra left/right context for TDNN systems.
chunk_left_context=0
chunk_right_context=0

# training options
epochs=10
srand=0
remove_egs=true

#decode options
ngr=4
test_online_decoding=false  # if true, it will run the last decoding stage.
decode_id=decode_test${ngr}gr
graph=exp/chain/tree_a_sp/graph_test${ngr}gr


# End configuration section.
echo "$0 $@"  # Print the command line for logging



. ./cmd.sh
. ./path.sh
. ./utils/parse_options.sh


if ! cuda-compiled; then
  cat <<EOF && exit 1
This script is intended to be used with GPUs but you have not compiled Kaldi with CUDA
If you want to use GPUs (and have them), go to src/, and configure and make on a machine
where "nvcc" is installed.
EOF
fi

gmm_dir=exp/${gmm}
ali_dir=exp/${gmm}_ali_${train_set}_sp
lat_dir=exp/chain${nnet3_affix}/${gmm}_${train_set}_sp_lats
dir=exp/chain${nnet3_affix}/tdnn${affix}_sp
train_data_dir=${DATA}/${train_set}_sp_hires
train_ivector_dir=exp/nnet3${nnet3_affix}/ivectors_${train_set}_sp_hires
lores_train_data_dir=${DATA}/${train_set}_sp

# note: you don't necessarily have to change the treedir name
# each time you do a new experiment-- only if you change the
# configuration in a way that affects the tree.
tree_dir=exp/chain${nnet3_affix}/tree_a_sp
# the 'lang' directory is created by this script.
# If you create such a directory with a non-standard topology
# you should probably name it differently.
lang=${DATA}/lang_chain

if [ ${stage} -le 11 ] && [ ! -e ${DATA}/.done_stage_11 ]; then

    echo "============================================================================"
    echo "         $0: STAGE 11 ... I-Vector                                          "
    echo "============================================================================"

    local/nnet3/run_ivector_common.sh \
        --stage $stage --nj $nj \
        --train-set $train_set \
        --test-sets "$test_sets" \
        --gmm $gmm \
        --online-cmvn-iextractor $online_cmvn \
        --num-threads-ubm $num_threads_ubm \
        --nj-extractor $nj_extractor \
        --num-processes-extractor $num_processes_extractor \
        --num-threads-extractor $num_threads_extractor \
        --nnet3-affix "$nnet3_affix"

    for f in $train_data_dir/feats.scp $train_ivector_dir/ivector_online.scp \
        $lores_train_data_dir/feats.scp $gmm_dir/final.mdl \
        $ali_dir/ali.1.gz $gmm_dir/final.mdl; do
    [ ! -f $f ] && echo "$0: expected file $f to exist" && exit 1
    done

    touch ${DATA}/.done_stage_11 && echo "Finish data preparation (stage: 11)."
fi

if [ ${stage} -le 12 ] && [ ! -e ${DATA}/.done_stage_12 ]; then

    echo "============================================================================"
    echo "         $0: STAGE 12 ... creating lang directory ${lang} with chain-type topology"
    echo "============================================================================"

    # Create a version of the lang/ directory that has one state per phone in the
    # topo file. [note, it really has two states.. the first one is only repeated
    # once, the second one has zero or more repeats.]
    if [ -d ${lang} ]; then
        if [ ${lang}/L.fst -nt ${DATA}/lang/L.fst ]; then
        echo "$0: ${lang} already exists, not overwriting it; continuing"
        else
        echo "$0: ${lang} already exists and seems to be older than data/lang..."
        echo " ... not sure what to do.  Exiting."
        exit 1;
        fi
    else
        cp -r ${DATA}/lang ${lang}
        silphonelist=$(cat ${lang}/phones/silence.csl) || exit 1;
        nonsilphonelist=$(cat ${lang}/phones/nonsilence.csl) || exit 1;
        # Use our special topology... note that later on may have to tune this
        # topology.
        steps/nnet3/chain/gen_topo.py $nonsilphonelist $silphonelist >${lang}/topo
    fi
fi

if [ ${stage} -le 13 ] && [ ! -e ${DATA}/.done_stage_13 ]; then

    echo "============================================================================"
    echo "         $0: STAGE 13 ... Get the alignments as lattices                    "
    echo "============================================================================"

    # Get the alignments as lattices (gives the chain training more freedom).
    # use the same num-jobs as the alignments
    steps/align_fmllr_lats.sh --nj ${nj} --cmd "$train_cmd" ${lores_train_data_dir} \
        ${DATA}/lang $gmm_dir $lat_dir
    rm $lat_dir/fsts.*.gz # save space

    touch ${DATA}/.done_stage_13 && echo "Finish data preparation (stage: 13)."
fi

if [ ${stage} -le 14 ] && [ ! -e ${DATA}/.done_stage_14 ]; then

    echo "============================================================================"
    echo "         $0: STAGE 14 ... Build a tree using topology                       "
    echo "============================================================================"

    # Build a tree using our new topology.  We know we have alignments for the
    # speed-perturbed data (local/nnet3/run_ivector_common.sh made them), so use
    # those.  The num-leaves is always somewhat less than the num-leaves from
    # the GMM baseline.
    if [ -f $tree_dir/final.mdl ]; then
        echo "$0: $tree_dir/final.mdl already exists, refusing to overwrite it."
        exit 1;
    fi

    steps/nnet3/chain/build_tree.sh \
        --frame-subsampling-factor 3 \
        --context-opts "--context-width=2 --central-position=1" \
        --cmd "$train_cmd" 3500 ${lores_train_data_dir} \
        ${lang} $ali_dir $tree_dir

    touch ${DATA}/.done_stage_14 && echo "Finish data preparation (stage: 14)."
fi

if [ ${stage} -le 15 ] && [ ! -e ${DATA}/.done_stage_15 ]; then

    echo "============================================================================"
    echo "         $0: STAGE 15 ... creating neural net configs using the xconfig parser"
    echo "============================================================================"

    mkdir -pv $dir

    num_targets=$(tree-info $tree_dir/tree |grep num-pdfs|awk '{print $2}')
    learning_rate_factor=$(echo "print(0.5/$xent_regularize)" | python)

    cnn_opts="l2-regularize=0.01"
    ivector_affine_opts="l2-regularize=0.01"
    tdnnf_opts="l2-regularize=0.01 dropout-proportion=0.0 bypass-scale=0.66"
    tdnnf_first_opts="l2-regularize=0.01 dropout-proportion=0.0 bypass-scale=0.0"
    linear_opts="l2-regularize=0.01 orthonormal-constraint=-1.0"
    prefinal_opts="l2-regularize=0.01"
    output_opts="l2-regularize=0.005"

    mkdir -pv $dir/configs
    cat <<EOF > $dir/configs/network.xconfig
input dim=100 name=ivector
input dim=40 name=input

# this takes the MFCCs and generates filterbank coefficients.  The MFCCs
# are more compressible so we prefer to dump the MFCCs to disk rather
# than filterbanks.
idct-layer name=idct input=input dim=40 cepstral-lifter=22 affine-transform-file=$dir/configs/idct.mat

linear-component name=ivector-linear $ivector_affine_opts dim=200 input=ReplaceIndex(ivector, t, 0)
batchnorm-component name=ivector-batchnorm target-rms=0.025

batchnorm-component name=idct-batchnorm input=idct
spec-augment-layer name=idct-spec-augment freq-max-proportion=0.5 time-zeroed-proportion=0.2 time-mask-max-frames=20
combine-feature-maps-layer name=combine_inputs input=Append(idct-spec-augment, ivector-batchnorm) num-filters1=1 num-filters2=5 height=40

conv-relu-batchnorm-layer name=cnn1 $cnn_opts height-in=40 height-out=40 time-offsets=-1,0,1 height-offsets=-1,0,1 num-filters-out=64 max-change=0.25
conv-relu-batchnorm-layer name=cnn2 $cnn_opts height-in=40 height-out=40 time-offsets=-1,0,1 height-offsets=-1,0,1 num-filters-out=64
conv-relu-batchnorm-layer name=cnn3 $cnn_opts height-in=40 height-out=20 height-subsample-out=2 time-offsets=-1,0,1 height-offsets=-1,0,1 num-filters-out=128
conv-relu-batchnorm-layer name=cnn4 $cnn_opts height-in=20 height-out=20 time-offsets=-1,0,1 height-offsets=-1,0,1 num-filters-out=128
conv-relu-batchnorm-layer name=cnn5 $cnn_opts height-in=20 height-out=10 height-subsample-out=2 time-offsets=-1,0,1 height-offsets=-1,0,1 num-filters-out=256
conv-relu-batchnorm-layer name=cnn6 $cnn_opts height-in=10 height-out=10 time-offsets=-1,0,1 height-offsets=-1,0,1 num-filters-out=256

# the first TDNN-F layer has no bypass (since dims don't match), and a larger bottleneck so the
# information bottleneck doesn't become a problem.  (we use time-stride=0 so no splicing, to
# limit the num-parameters).
tdnnf-layer name=tdnnf7 $tdnnf_first_opts dim=1024 bottleneck-dim=256 time-stride=0
tdnnf-layer name=tdnnf8 $tdnnf_opts dim=1024 bottleneck-dim=128 time-stride=3
tdnnf-layer name=tdnnf9 $tdnnf_opts dim=1024 bottleneck-dim=128 time-stride=3
tdnnf-layer name=tdnnf10 $tdnnf_opts dim=1024 bottleneck-dim=128 time-stride=3
tdnnf-layer name=tdnnf11 $tdnnf_opts dim=1024 bottleneck-dim=128 time-stride=3
tdnnf-layer name=tdnnf12 $tdnnf_opts dim=1024 bottleneck-dim=128 time-stride=3
tdnnf-layer name=tdnnf13 $tdnnf_opts dim=1024 bottleneck-dim=128 time-stride=3
tdnnf-layer name=tdnnf14 $tdnnf_opts dim=1024 bottleneck-dim=128 time-stride=3
tdnnf-layer name=tdnnf15 $tdnnf_opts dim=1024 bottleneck-dim=128 time-stride=3
linear-component name=prefinal-l dim=192 $linear_opts

prefinal-layer name=prefinal-chain input=prefinal-l $prefinal_opts big-dim=1024 small-dim=192
output-layer name=output include-log-softmax=false dim=$num_targets $output_opts

prefinal-layer name=prefinal-xent input=prefinal-l $prefinal_opts big-dim=1024 small-dim=192
output-layer name=output-xent dim=$num_targets learning-rate-factor=$learning_rate_factor $output_opts
EOF
    steps/nnet3/xconfig_to_configs.py --xconfig-file $dir/configs/network.xconfig --config-dir $dir/configs/
fi


if [ ${stage} -le 16 ] && [ ! -e ${DATA}/.done_stage_16 ]; then

    echo "============================================================================"
    echo "         $0: STAGE 16 ... Training                                          "
    echo "============================================================================"
  
    $cuda_cmd $dir/log/train_chain.log \
    steps/nnet3/chain/train.py --stage=$train_stage \
        --cmd="run.pl" \
        --feat.online-ivector-dir=$train_ivector_dir \
        --feat.cmvn-opts="--config=conf/online_cmvn.conf" \
        --chain.xent-regularize $xent_regularize \
        --chain.leaky-hmm-coefficient=0.1 \
        --chain.l2-regularize=0.0 \
        --chain.apply-deriv-weights=false \
        --chain.lm-opts="--num-extra-lm-states=2000" \
        --trainer.dropout-schedule $dropout_schedule \
        --trainer.add-option="--optimization.memory-compression-level=2" \
        --trainer.srand=$srand \
        --trainer.max-param-change=2.0 \
        --trainer.num-epochs=${epochs} \
        --trainer.frames-per-iter=5000000 \
        --trainer.optimization.num-jobs-initial=1 \
        --trainer.optimization.num-jobs-final=1 \
        --trainer.optimization.initial-effective-lrate=0.0005 \
        --trainer.optimization.final-effective-lrate=0.00005 \
        --trainer.num-chunk-per-minibatch=128,64 \
        --trainer.optimization.momentum=0.0 \
        --egs.chunk-width=$chunk_width \
        --egs.chunk-left-context=0 \
        --egs.chunk-right-context=0 \
        --egs.dir="$common_egs_dir" \
        --egs.opts="--frames-overlap-per-eg 0 --online-cmvn $online_cmvn" \
        --cleanup.remove-egs=$remove_egs \
        --use-gpu=wait \
        --reporting.email="$reporting_email" \
        --feat-dir=$train_data_dir \
        --tree-dir=$tree_dir \
        --lat-dir=$lat_dir \
        --dir=$dir  || exit 1;

    touch ${DATA}/.done_stage_16 && echo "Finish data preparation (stage: 16)."
fi

if [ ${stage} -le 17 ] && [ ! -e ${DATA}/.done_stage_17 ]; then

    echo "============================================================================"
    echo "         $0: STAGE 17 ... check_phones_compatible and make HCLG graph       "
    echo "============================================================================"

    # The reason we are using data/lang here, instead of ${lang}, is just to
    # emphasize that it's not actually important to give mkgraph.sh the
    # lang directory with the matched topology (since it gets the
    # topology file from the model).  So you could give it a different
    # lang directory, one that contained a wordlist and LM of your choice,
    # as long as phones.txt was compatible.

    utils/lang/check_phones_compatible.sh ${DATA}/lang_test${ng}gr/phones.txt ${lang}/phones.txt
    utils/mkgraph.sh --self-loop-scale 1.0 ${DATA}/lang_test${ngr}gr $tree_dir $graph || exit 1;

fi

if [ ${stage} -le 18 ] && [ ! -e ${DATA}/.done_stage_18 ]; then

    echo "============================================================================"
    echo "         $0: STAGE 18 ... Decode                                            "
    echo "============================================================================"
        
    frames_per_chunk=$(echo $chunk_width | cut -d, -f1)
    rm $dir/.error 2>/dev/null || true

    for data in $test_sets; do
        steps/nnet3/decode.sh \
            --acwt 1.0 --post-decode-acwt 10.0 \
            --extra-left-context 0 --extra-right-context 0 \
            --extra-left-context-initial 0 \
            --extra-right-context-final 0 \
            --frames-per-chunk $frames_per_chunk \
            --nj $nj --cmd "$decode_cmd"  \
            --online-ivector-dir exp/nnet3${nnet3_affix}/ivectors_${data}_hires \
        --skip_diagnostics true \
            $graph ${DATA}/${data}_hires ${dir}/${decode_id}_${data} || exit 1
    done  
fi

exit 0;
