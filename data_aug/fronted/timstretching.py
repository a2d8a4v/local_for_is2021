#!/usr/bin/env python
# coding: utf-8

# author: Gagandeep Singh, 29 Oct, 2018
# modified: JIUN TING LI

import librosa
import numpy as np

class TimeStretch(object):
    def __init__(self, factor):
        self.factor = factor
        
    def __call__(self, xs):
        return self.stretch(xs)

    def stretch(self, x, nfft=2048):
        '''
        stretch an audio sequence by a factor using FFT of size nfft converting to frequency domain
        :param x: np.ndarray, audio array in PCM float32 format
        :param factor: float, stretching or shrinking factor, depending on if its > or < 1 respectively
        :return: np.ndarray, time stretched audio
        '''
        factor = self.factor
        stft = librosa.core.stft(x, n_fft=nfft).transpose()  # i prefer time-major fashion, so transpose
        stft_rows = stft.shape[0]
        stft_cols = stft.shape[1]

        times = np.arange(0, stft.shape[0], factor)  # times at which new FFT to be calculated
        hop = nfft/4                                 # frame shift
        stft_new = np.zeros((len(times), stft_cols), dtype=np.complex_)
        phase_adv = (2 * np.pi * hop * np.arange(0, stft_cols))/ nfft
        phase = np.angle(stft[0])

        stft = np.concatenate( (stft, np.zeros((1, stft_cols))), axis=0)

        for i, time in enumerate(times):
            left_frame = int(np.floor(time))
            local_frames = stft[[left_frame, left_frame + 1], :]
            right_wt = time - np.floor(time)                        # weight on right frame out of 2
            local_mag = (1 - right_wt) * np.absolute(local_frames[0, :]) + right_wt * np.absolute(local_frames[1, :])
            local_dphi = np.angle(local_frames[1, :]) - np.angle(local_frames[0, :]) - phase_adv
            local_dphi = local_dphi - 2 * np.pi * np.floor(local_dphi/(2 * np.pi))
            stft_new[i, :] =  local_mag * np.exp(phase*1j)
            phase += local_dphi + phase_adv

        return librosa.core.istft(stft_new.transpose())

    def stretch_wo_loop(self, x, nfft=2048):
        '''
        Functionality same as stretch()
        :param x: np.ndarray, audio array in PCM float32 format
        :param factor: float, stretching or shrinking factor, depending on if its > or < 1 respectively
        :return: np.ndarray, time stretched audio
        '''
        factor = self.factor
        stft = librosa.core.stft(x, n_fft=nfft).transpose()
        stft_rows = stft.shape[0]
        stft_cols = stft.shape[1]

        times = np.arange(0, stft.shape[0], factor)
        hop = nfft/4
        phase_adv = (2 * np.pi * hop * np.arange(0, stft_cols))/ nfft
        stft = np.concatenate((stft, np.zeros((1, stft_cols))), axis=0)

        indices = np.floor(times).astype(np.int)
        alpha = np.expand_dims(times - np.floor(times), axis=1)
        mag = (1. - alpha) * np.absolute(stft[indices, :]) + alpha * np.absolute(stft[indices + 1, :])
        dphi = np.angle(stft[indices + 1, :]) - np.angle(stft[indices, :]) - phase_adv
        dphi = dphi - 2 * np.pi * np.floor(dphi/(2 * np.pi))
        phase_adv_acc = np.matmul(np.expand_dims(np.arange(len(times) + 1),axis=1), np.expand_dims(phase_adv, axis=0))
        phase = np.concatenate( (np.zeros((1, stft_cols)), np.cumsum(dphi, axis=0)), axis=0) + phase_adv_acc
        phase += np.angle(stft[0, :])
        stft_new = mag * np.exp(phase[:-1,:]*1j)
        return librosa.core.istft(stft_new.transpose())
