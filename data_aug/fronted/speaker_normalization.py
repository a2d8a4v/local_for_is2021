#!/usr/bin/env python
# coding: utf-8

import numpy as np
import librosa

class SpeakerNormalization(object):
    def __init__(self, sampling_rate, alpha=1):
        super().__init__()
        self.sampling_rate = sampling_rate
        self.alpha = alpha

    def __call__(self, xs):
        return self.logscale_spec(xs)

    def logscale_spec(self, spec):
        sr = self.sampling_rate
        alpha = self.alpha
        f0 = 0.9
        fmax = 1

        spec = librosa.core.stft(spec)
        timebins, freqbins = spec.shape
        scale = np.linspace(0, 1, freqbins)
        
        # @https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=650310
        scale = np.array(list(map(lambda x: x * alpha if x <= f0 else (fmax-alpha*f0)/(fmax-f0)*(x-f0)+alpha*f0, scale)))
        scale *= (freqbins-1)/max(scale)

        newspec = np.complex128(np.zeros([timebins, freqbins]))
        allfreqs = np.abs(np.fft.fftfreq(freqbins*2, 1./sr)[:freqbins+1])
        freqs = [0.0 for i in range(freqbins)]
        totw = [0.0 for i in range(freqbins)]
        for i in range(0, freqbins):
            if (i < 1 or i + 1 >= freqbins):
                newspec[:, i] += spec[:, i]
                freqs[i] += allfreqs[i]
                totw[i] += 1.0
                continue
            else:
                # scale[15] = 17.2
                w_up = scale[i] - np.floor(scale[i])
                w_down = 1 - w_up
                j = int(np.floor(scale[i]))
            
                newspec[:, j] += w_down * spec[:, i]
                freqs[j] += w_down * allfreqs[i]
                totw[j] += w_down
                
                newspec[:, j + 1] += w_up * spec[:, i]
                freqs[j + 1] += w_up * allfreqs[i]
                totw[j + 1] += w_up
        
        for i in range(len(freqs)):
            if (totw[i] > 1e-6):
                freqs[i] /= totw[i]
        
        newspec = librosa.core.istft(newspec)
        return newspec

