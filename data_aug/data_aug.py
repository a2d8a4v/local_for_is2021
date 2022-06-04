#!/usr/bin/env python
# coding: utf-8

import soundfile as sf
import os, argparse, librosa, random, logging

## VARIABLES
sup = "bak"

## TOOLS
def mkdir(path):
    if not os.path.exists(os.path.abspath(path)):
        os.makedirs(os.path.abspath(path))
    return

def main(args):

    if not os.path.exists(os.path.abspath(args.in_file)):
        logging.exception("{} dose not exists".format(os.path.abspath(args.in_file)))
    if not os.path.exists(os.path.abspath(args.in_sup_file)):
        logging.exception("{} dose not exists".format(os.path.abspath(args.in_sup_file)))
    mkdir(args.corpus_path)

    ## augment list
    aug_list = args.data_aug_on.lower().replace("false","").split(":")
    sup_dict = { x.split()[0]:" ".join( [str(y) for y in x.split()[1:]] ) for x in open(args.in_sup_file, "r").read().splitlines() }

    ## import moduels
    for i , b in enumerate(aug_list):
        if bool(b):
            if i == 0:
                from fronted.cutmix import CutMix
                mkdir(os.path.join(args.corpus_path, "cm"))
            elif i == 1:
                from fronted.samplepairing import SamplePairing
                mkdir(os.path.join(args.corpus_path, "sp"))
            elif i == 2:
                from fronted.vtlp import VtlpAug
                mkdir(os.path.join(args.corpus_path, "vtlp"))
            elif i == 3:
                from fronted.pitch_modification import PitchModification
                mkdir(os.path.join(args.corpus_path, "pm"))
            elif i == 4:
                from fronted.speaking_rate_using_stftm import SpeakingRateUsingStftm
                mkdir(os.path.join(args.corpus_path, "srus"))
            elif i == 5:
                from fronted.timstretching import TimeStretch
                mkdir(os.path.join(args.corpus_path, "ts"))
            elif i == 6:
                from fronted.speaker_normalization import SpeakerNormalization
                mkdir(os.path.join(args.corpus_path, "sn"))

    ## data augment start
    with open(os.path.abspath(args.in_file)) as fp:
        files = fp.read().splitlines()
        for i, file in enumerate(files):
            x1, sr = librosa.core.load(file)
            sr = sr if not args.sample_rate else args.sample_rate
            for k, b in enumerate(aug_list):
                if bool(b):
                    if k == 0:
                        j = random.randrange(len(files))
                        x2, _ = librosa.core.load(files[j])
                        cutmix = CutMix(i, j)
                        save_file(args, file, cutmix(x1, x2), sr, "cm")
                        save_sup(args, file, sup_dict, "cm")
                        save_list(args, file, "cm")
                    elif k == 1:
                        j = random.randrange(len(files))
                        x2, _ = librosa.core.load(files[j])
                        samplepairing = SamplePairing(i, j)
                        save_file(args, file, samplepairing(x1, x2), sr, "sp")
                        save_sup(args, file, sup_dict, "sp")
                        save_list(args, file, "sp")
                    elif k == 2:
                        vtlpaug = VtlpAug(sampling_rate=sr, factor=(0.95, 1.05))
                        save_file(args, file, vtlpaug(x1), sr, "vtlp")
                        save_sup(args, file, sup_dict, "vtlp")
                        save_list(args, file, "vtlp")
                    elif k == 3:
                        pitchmodification = PitchModification()
                        save_file(args, file, pitchmodification(x1), sr, "pm")
                        save_sup(args, file, sup_dict, "pm")
                        save_list(args, file, "pm")
                    elif k == 4:
                        speakingrateusingstftm = SpeakingRateUsingStftm()
                        save_file(args, file, speakingrateusingstftm(x1), sr, "srus")
                        save_sup(args, file, sup_dict, "srus")
                        save_list(args, file, "srus")
                    elif k == 5:
                        timestretch = TimeStretch(factor=0.8)
                        save_file(args, file, timestretch(x1), sr, "ts")
                        save_sup(args, file, sup_dict, "ts")
                        save_list(args, file, "ts")
                    elif k == 6:
                        speakernormalization = SpeakerNormalization(sr)
                        save_file(args, file, speakernormalization(x1), sr, "sn")
                        save_sup(args, file, sup_dict, "sn")
                        save_list(args, file, "sn")

def save_file(args, file, data, sr, aug_type):
    f_name, f_extn = os.path.splitext(os.path.basename(file))
    rwd_path = os.path.join(args.corpus_path, aug_type, "{}_{}.{}".format(f_name, aug_type, f_extn.replace(".","")))
    ned_path = os.path.join(args.corpus_path, aug_type, "{}_{}.{}{}".format(f_name, aug_type, f_extn.replace(".",""), sup))
    if os.path.isfile(rwd_path):
        if os.path.isfile(ned_path):
            os.remove(ned_path)
        os.rename(rwd_path, ned_path)
    sf.write(rwd_path, data, sr)
    return

def save_sup(args, file, sup_dict, aug_type):
    f_name, _ = os.path.splitext(os.path.basename(file))
    with open(os.path.abspath(args.out_sup_path), "a") as fp:
        fp.write("\n")
    with open(os.path.abspath(args.out_sup_path), "a") as fp:
        fp.write( "{}_{} {}\n".format(f_name, aug_type, sup_dict[f_name]) )
    return

def save_list(args, file, aug_type):
    f_name, f_extn = os.path.splitext(os.path.basename(file))
    with open(os.path.abspath(args.out_path), "a") as fp:
        fp.write("\n")
    with open(os.path.abspath(args.out_path), "a") as fp:
        fp.write( "{}\n".format(os.path.join(args.corpus_path, aug_type, "{}_{}.{}".format(f_name, aug_type, f_extn.replace(".","")))) )
    return

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--in_file',
                        type=str,
                        required=True,
                        help='path to the input wav list file')
    parser.add_argument('-is', '--in_sup_file',
                        type=str,
                        required=True,
                        help='path to the input wav sup/transcript file')
    parser.add_argument('-c', '--corpus_path',
                        type=str,
                        required=True,
                        help='path to save new augmented wav file')
    parser.add_argument('-o', '--out_path',
                        type=str,
                        default=True,
                        help='path of the output path of wav list file')
    parser.add_argument('-os', '--out_sup_path',
                        type=str,
                        default=True,
                        help='path of the output path of wav sup/transcript file')
    parser.add_argument('-s', '--sample_rate',
                        type=int,
                        required=False,
                        help='Sample Rate')
    parser.add_argument('-st', '--stage',
                        type=str,
                        required=True,
                        help='Train , dev or eval stage')
    parser.add_argument('-d', '--data_aug_on',
                        type=str,
                        required=True,
                        help='Which kind of data aug method would be used')
    args = parser.parse_args()
    main(args)

