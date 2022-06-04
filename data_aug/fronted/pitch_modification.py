#!/usr/bin/env python
# coding: utf-8

import librosa, os
import numpy as np
from scipy import signal

class PitchModification(object):
    def __init__(self, semitone=-2):
        super().__init__()
        self.semitone = semitone

    def __call__(self, xs):
        return self.pitch_modification(xs)

    def pitch_modification(self, x):
        semitone = self.semitone
        x = x[np.newaxis].T
        sent_L = len(x)

        semitone = np.round(semitone)
        if semitone > 12 or semitone < -12:
            semitone = 0
        scale = 2**(semitone/12)
        L = 160
        S = int(L / 4)

        overlap = L - S
        Nframe = int(np.floor((sent_L-overlap)/S))
        Lq = int(np.round(L*scale))
        a = 0.50
        b = -0.50

        n = np.linspace(1,L,num=L)
        win = np.sqrt(S)/np.sqrt((4*(a**2)+2*(b**2))*L)*(a+b*np.cos(2*np.pi*n/L))
        win = win[np.newaxis].T
        n = np.linspace(1,Lq,num=Lq)
        winq = np.sqrt(S)/np.sqrt((4*(a**2)+2*(b**2))*Lq)*(a+b*np.cos(2*np.pi*n/Lq))
        winq = winq[np.newaxis].T
        Nit = 4
        xfinal = np.zeros([sent_L,1],dtype=np.float)

        U = sum(win)[0]/S
        k = 1

        for n in range(0, Nframe, 1):
            if np.linspace(k,k+Lq-1,num=int(Lq)).all() <= sent_L:
                frm = np.multiply(winq, x[k-1:k+Lq-1])/U
            else:
                frm = np.multiply(winq, np.concatenate((x[k-1:sent_L], np.zeros([Lq - (sent_L-k+1),1])), axis=0))/U

            # @http://signalsprocessed.blogspot.com/2016/08/audio-resampling-in-python.html
            frm_resamp = signal.resample(frm, int(len(frm)*L/Lq))
            xSTFTM = abs(np.fft.fft(frm_resamp))

            if k+L-1 <= sent_L:
                res = xfinal[k-1:k+L-1]
            else:
                res = np.concatenate((xfinal[k-1:sent_L], np.zeros([L - (sent_L-k+1),1])), axis=0)
            
            x_recon = self.iterated_recon(xSTFTM, res, Nit, win)
            
            if k+L-1 <= sent_L:
                xfinal[k-1:k+L-1] = xfinal[k-1:k+L-1] + x_recon
            else:
                xfinal[k-1:sent_L] = xfinal[k-1:sent_L] + x_recon[0:sent_L-k+1]
            k += S

        return xfinal

    def iterated_recon(self, xSTFTM, x_res, Nit, win):
        for i in range(1,Nit+1,1):
            phi = np.unwrap(np.angle(np.fft.fft(win*x_res))) + np.random.randn(x_res.shape[0], x_res.shape[1])*0.01*np.pi
            x = np.multiply(xSTFTM, np.exp(1j*phi))
            x_recon = np.fft.ifft(x)
            x_res = np.real(x_recon)
        return x_res

