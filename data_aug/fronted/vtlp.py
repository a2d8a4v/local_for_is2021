#!/usr/bin/env python
# coding: utf-8

import random, librosa
import numpy as np


## Vocal Tract Length Perturbation
# @http://www.cs.toronto.edu/~hinton/absps/perturb.pdf
class VtlpAug(object):
    def __init__(self, sampling_rate, zone=(0.2, 0.8), coverage=0.1, fhi=4800, factor=(0.9, 1.1), name='Vtlp_Aug', verbose=0, stateless=True , duration=None):
        super().__init__()
        self.sampling_rate = sampling_rate
        self.fhi = fhi
        self.zone = zone
        self.coverage = coverage
        self.factor = factor
        self.name = name
        self.verbose = verbose
        self.stateless = stateless
        self.duration = duration
        self.model = Vtlp(sampling_rate=sampling_rate)

    def __call__(self, xs):
        return self.augment(xs)

    def get_random_factor(self, low=None, high=None, dtype='float'):
        lower_bound = self.factor[0] if low is None else low
        upper_bound = self.factor[1] if high is None else high
        if dtype == 'int':
            return random.randint(lower_bound, upper_bound)
        elif dtype == 'float':
            return random.uniform(lower_bound, upper_bound)

        return random.uniform(lower_bound, upper_bound)

    def get_augment_range_by_coverage(self, data):
        zone_start, zone_end = int(len(data) * self.zone[0]), int(len(data) * self.zone[1])
        zone_size = zone_end - zone_start

        target_size = int(zone_size * self.coverage)
        last_start = zone_start + int(zone_size * (1 - self.coverage))

        if zone_start == last_start:
            start_pos = zone_start
            end_pos = zone_end
        else:
            start_pos = random.randint(zone_start, last_start)
            end_pos = start_pos + target_size

        return start_pos, end_pos

    def get_augment_range_by_duration(self, data):
        zone_start, zone_end = int(len(data) * self.zone[0]), int(len(data) * self.zone[1])
        zone_size = zone_end - zone_start

        target_size = int(self.sampling_rate * self.duration)

        if target_size >= zone_size:
            start_pos = zone_start
            end_pos = zone_end
        else:
            last_start = zone_start + zone_size - target_size
            start_pos = random.randint(zone_start, last_start)
            end_pos = start_pos + target_size

        return start_pos, end_pos

    def augment(self, data):
        sampling_rate = self.sampling_rate
        if self.duration is None:
            start_pos, end_pos = self.get_augment_range_by_coverage(data)
        else:
            start_pos, end_pos = self.get_augment_range_by_duration(data)

        warp_factor = self.get_random_factor()

        if not self.stateless:
            self.start_pos, self.end_pos, self.aug_factor = start_pos, end_pos, warp_factor

        return self.model.manipulate(data, start_pos=start_pos, end_pos=end_pos, sampling_rate=sampling_rate, warp_factor=warp_factor)


class Vtlp(object):
    def __init__(self, sampling_rate):
        super().__init__()
        self.sampling_rate = sampling_rate
        # self.device = device

    @classmethod
    def get_scale_factors(self, freq_dim, sampling_rate, fhi=4800, alpha=0.9):
        factors = []
        freqs = np.linspace(0, 1, freq_dim)

        scale = fhi * min(alpha, 1)
        f_boundary = scale / alpha
        half_sr = sampling_rate / 2

        for f in freqs:
            f *= sampling_rate
            if f <= f_boundary:
                factors.append(f * alpha)
            else:
                warp_freq = half_sr - (half_sr - scale) / (half_sr - scale / alpha) * (half_sr - f)
                factors.append(warp_freq)
        return np.array(factors)

    # https://github.com/YerevaNN/Spoken-language-identification/blob/master/augment_data.py#L26
    def manipulate(self, data, start_pos, end_pos, sampling_rate, warp_factor):

        stft = librosa.core.stft(data[start_pos:end_pos])
        time_dim, freq_dim = stft.shape
        factors = self.get_scale_factors(freq_dim=freq_dim, sampling_rate=sampling_rate, alpha=warp_factor)
        factors *= (freq_dim - 1) / max(factors)
        new_stft = np.zeros([time_dim, freq_dim], dtype=type(stft[0][0]))

        for i in range(freq_dim):
            # first and last freq
            if i == 0 or i + 1 >= freq_dim:
                new_stft[:, i] += stft[:, i]
            else:
                warp_up = factors[i] - np.floor(factors[i])
                warp_down = 1 - warp_up
                pos = int(np.floor(factors[i]))

                new_stft[:, pos] += warp_down * stft[:, i]
                new_stft[:, pos+1] += warp_up * stft[:, i]

        return np.concatenate((data[:start_pos], librosa.core.istft(new_stft), data[end_pos:]), axis=0).astype(type(data[0]))

