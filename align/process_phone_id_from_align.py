import argparse
from tqdm import tqdm
import numpy as np
import os
from collections import OrderedDict

import kaldiio
from kaldiio import WriteHelper

# 這裡的phone == word
parser = argparse.ArgumentParser()

parser.add_argument('--ctm_fn', type=str, default="exp/chain/cnn_tdnn1c_sp/align_train_tr_sp_hires/ctm_word/ctm")
parser.add_argument('--phn_tbl_fn', type=str, default="data/lang/words.txt")
parser.add_argument('--data_dir', type=str, default="data/train_tr_sp_hires")
parser.add_argument('--new_feats_dir', type=str, default="phn_id")
parser.add_argument('--add_eos', type=str, default="false")

args = parser.parse_args()

data_dir = args.data_dir
ctm_fn = args.ctm_fn
phn_tbl_fn = args.phn_tbl_fn
new_feats_dir = args.new_feats_dir
add_eos = args.add_eos

ctm_info_dict = {}
phn_table_dict = {}
feats_scps = set()
d = os.path.basename(data_dir)

# ctm_file
with open(ctm_fn, "r") as fn:
    for line in fn.readlines():
        info = line.split()
        utt_id, conf, s_time, dur, phn = info
        
        if utt_id not in ctm_info_dict:
            ctm_info_dict[utt_id] = []
        
        phn_info = {"phn": phn, "s_time": float(s_time), "dur": float(dur)}
        ctm_info_dict[utt_id].append(phn_info)

# phone table
num_phns = 0
ignore_ids = ["<eps>", "#0", "<s>", "</s>", "err"]
phn_list = []
err_list = []

if add_eos == "true":
    phn_table_dict["<eos>"] = num_phns
    num_phns += 1
    phn_list.append("<eos>")

with open(phn_tbl_fn, "r") as fn:
    for line in fn.readlines():
        info = line.split()
        phn, phn_id = info
        
        #if phn in ignore_ids: continue
        #elif "*" in phn: continue
        
        phn_table_dict[phn] = num_phns
        num_phns += 1
        phn_list.append(phn)
        
# read feats.scp
with open(data_dir + "/feats.scp", "r") as fn:
    for line in fn.readlines():
        info = line.split()
        utt_id = info[0]
        scp_info = info[1].split(":")[0].replace(".ark", ".scp")
        feats_scps.add(scp_info)

for feats_scp in tqdm(feats_scps):
    data_set = os.path.basename(data_dir)
    fn_prefix, split_idx, ext = os.path.basename(feats_scp).split(".")
    new_feats_scp = new_feats_dir + "/phn_id_" + data_set + "." + split_idx
    new_feats_scp_dict = OrderedDict()
    
    fbank_reader = kaldiio.load_scp(feats_scp)
    
    utt_ids = []
    with open(feats_scp) as fn:
        for line in fn.readlines():
            utt_id = line.split()[0]
            utt_ids.append(utt_id)

    for utt_id in utt_ids:
        # create one-hot vector sequence
        if utt_id not in ctm_info_dict:
            err_list.append(utt_id)
            continue

        ctm_info = ctm_info_dict[utt_id]
        mfcc_feats = fbank_reader[utt_id]
        num_frames, feats_dim = mfcc_feats.shape
        phn_ids_np = np.zeros((num_frames, num_phns))
        
        for phn_ctm_idx, phn_ctm_info in enumerate(ctm_info):
            # compatible for espnet and kaldi
            if phn_ctm_info["phn"] == "sil":
                phn_id = phn_table_dict["<space>"]
            else:
                phn_id = phn_table_dict[phn_ctm_info["phn"]]
            s_frame = int(phn_ctm_info["s_time"] * 100)
            dur_frames = int(phn_ctm_info["dur"] * 100)
            is_last = False
                
            for t in range(dur_frames):
                try:
                    phn_ids_np[s_frame + t, phn_id] = 1
                except:
                    is_last = True
            
            if is_last:
                last_frame = s_frame + dur_frames
                if phn_ctm_idx != len(ctm_info) -1:
                    print("[WARNING] phone compt.", phn_ctm_idx, len(ctm_info))
                break
                
            last_frame = s_frame + dur_frames
        
        missing_rate = 100 - min(last_frame / num_frames * 100, 100)
        if missing_rate > 1:
            print("WARNING", missing_rate)
        
        new_feats_scp_dict[utt_id] = phn_ids_np
    
    with WriteHelper('ark,scp:{0}.ark,{0}.scp'.format(new_feats_scp)) as writer:
        for k, v in new_feats_scp_dict.items():
            writer(k, v)

with open(data_dir + "/phn_list.txt", "w") as fn:
    for phn in phn_list:
        phn_id = phn_table_dict[phn] 
        fn.write(phn + " " + str(phn_id) + "\n")

with open(data_dir + "/phn_error_uttid.txt", "w") as fn:
    for utt_id in err_list:
        fn.write("{}\n".format(utt_id))