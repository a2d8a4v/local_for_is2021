#!/usr/bin/env python
# coding: utf-8

import librosa, os
import numpy as np

class SpeakingRateUsingStftm(object):
    def __init__(self, scale=0.8):
        super().__init__()
        self.scale = scale

    def __call__(self, xs):
        return self.speaking_rate_using_stftm(xs)

    def speaking_rate_using_stftm(self, x):
        scale = self.scale
        x = x[np.newaxis].T
        sent_L = len(x)

        L       = 256
        S       = int(L / 4)
        m_S     = int(np.round(S/scale))
        overlap = L - S
        Nframe  = int(np.floor((sent_L-overlap)/S))
        
        a       = 0.50
        b       = -0.50
        n       = np.linspace(1, L, num=L)
        win     = np.sqrt(S)/np.sqrt((4*(a**2)+2*(b**2))*L)*(a+b*np.cos(2*np.pi*n/L))
        win     = win[np.newaxis].T
        Nit     = 5
        L_recon = int(np.round(sent_L/scale))
        xfinal  = np.zeros([L_recon,1],dtype=np.float)
        U = sum(win)[0]/m_S
        k, kk = 1, 1

        for n in range(0, Nframe, 1):
            frm = np.multiply(win, x[k-1:k+L-1])/U
            xSTFTM = abs(np.fft.fft(frm))
            
            if kk+L-1 <= L_recon:
                res = xfinal[kk-1:kk+L-1]
            else:
                res = np.concatenate((xfinal[kk-1:L_recon], np.zeros([L - (L_recon-kk+1),1])), axis=0)

            x_recon = self.iterated_recon(xSTFTM, res, Nit, win)
            
            if kk+L-1 <= L_recon:
                xfinal[kk-1:kk+L-1] = xfinal[kk-1:kk+L-1] + x_recon
            else:
                xfinal[kk-1:L_recon] = xfinal[kk-1:L_recon] + x_recon[0:L_recon-kk+1]

            k += S
            kk += m_S

        return xfinal


    def iterated_recon(self, xSTFTM, x_res, Nit, win):
        for i in range(0, Nit, 1):
            phi = np.unwrap(np.angle(np.fft.fft(win*x_res))) + np.random.randn(x_res.shape[0], x_res.shape[1])*0.01*np.pi
            x = np.multiply(xSTFTM, np.exp(1j*phi))
            x_recon = np.fft.ifft(x)
            x_res = np.real(x_recon)
        return x_res

