# SPDX-License-Identifier: GPL-3.0-only
"""Whitened template matching, channel-wise, with temporal agreement.

The score is a match statistic, never a calibrated probability.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Match:
    score: float
    reference_start: float
    templates: int


class CubeDetector:
    rate = 48000
    window_seconds = 3.25
    step_seconds = .35

    def __init__(self, reference, sensitivity='balanced'):
        reference=np.asarray(reference,dtype=np.float64).reshape(-1)
        if len(reference)<self.rate or not np.isfinite(reference).all():
            raise ValueError('Referência de áudio inválida')
        self.length=96000
        self.offsets=np.arange(0,len(reference)-self.length+1,24000)
        self.nfft=1 << (int(self.window_seconds*self.rate)+self.length-1).bit_length()
        frequency=np.fft.rfftfreq(self.nfft,1/self.rate)
        self.band=(frequency>=800)&(frequency<=11500)
        self.frequency=frequency
        self.templates=np.array([reference[o:o+self.length] for o in self.offsets])
        self.spectra=np.fft.rfft(self.templates,n=self.nfft,axis=1)
        self.reverse_spectra=np.fft.rfft(self.templates[:,::-1],n=self.nfft,axis=1)
        self.threshold=8.5 if sensitivity=='balanced' else 6.5
        self.reset()

    def reset(self):
        self.buffer=np.empty((0,2),dtype=np.float32)
        self.samples_seen=0
        self.since_analysis=0
        self.previous=None
        self.last_alert=-float('inf')
        self.last_score=0.

    def match(self, audio):
        audio=np.asarray(audio,dtype=np.float64)
        if not np.isfinite(audio).all() or np.mean(audio*audio)<1e-14:
            return None
        frames=np.lib.stride_tricks.sliding_window_view(audio,4096)[::2048]
        power=np.abs(np.fft.rfft(frames*np.hanning(4096),axis=1))**2
        # Smooth the estimated noise spectrum; keep narrow reference components.
        noise=np.mean(power,axis=0)
        noise=np.convolve(noise,np.ones(17)/17,mode='same')
        noise=np.interp(self.frequency,np.fft.rfftfreq(4096,1/self.rate),noise)
        floor=max(float(np.median(noise[self.band]))*.08,1e-20)
        weight=self.band/np.maximum(noise,floor)
        weight/=max(float(weight.max()),1e-30)
        # Applying equal whitening to observation and reference gives this
        # inverse-noise weighting in their cross spectrum.
        signal=np.fft.rfft(audio,n=self.nfft)
        correlation=np.fft.irfft(signal[None,:]*np.conj(self.spectra)*weight,
                                  n=self.nfft,axis=1)[:,:len(audio)-self.length+1]
        reference_energy=(np.abs(self.spectra)**2*weight).sum(axis=1)*2/self.nfft
        whitened=np.fft.irfft(signal*np.sqrt(weight),n=self.nfft)[:len(audio)]
        energy=np.concatenate([[0.],np.cumsum(whitened*whitened)])
        local=energy[self.length:]-energy[:-self.length]
        denominator=np.sqrt(np.maximum(reference_energy[:,None]*local[None,:],1e-30))
        # Noise-normalized statistic. Acceptance is measured against negatives.
        statistics=np.abs(correlation)/denominator*np.sqrt(self.length*.45)
        peaks=np.argmax(statistics,axis=1)
        scores=statistics[np.arange(len(peaks)),peaks]
        starts=(peaks-self.offsets)/self.rate
        best=None
        for index,score in enumerate(scores):
            agree=(np.abs(starts-starts[index])<.008)&(scores>=self.threshold)
            count=int(agree.sum())
            if count>=2:
                ordered=np.sort(scores[agree])
                value=float(ordered[-2])
                if best is None or value>best.score:
                    best=Match(value,float(np.median(starts[agree])),count)
        if best is not None:
            # A time-reversed control has the same averaged spectrum. Reject
            # candidates that fit it better: tones alone do not establish order.
            backwards=np.fft.irfft(signal[None,:]*np.conj(self.reverse_spectra)*weight,
                n=self.nfft,axis=1)[:,:len(audio)-self.length+1]
            reverse_score=float(np.max(np.abs(backwards)/denominator*np.sqrt(self.length*.45)))
            if best.score<reverse_score*1.2:
                return None
        return best

    def push(self, audio):
        """Accept stereo float32 PCM and return a confirmed match occasionally."""
        audio=np.asarray(audio,dtype=np.float32)
        if audio.ndim!=2 or audio.shape[1]!=2 or not np.isfinite(audio).all():
            raise ValueError('PCM estéreo float32 inválido')
        self.samples_seen+=len(audio)
        self.since_analysis+=len(audio)
        capacity=int(self.rate*self.window_seconds)
        self.buffer=np.concatenate([self.buffer,audio])[-capacity:]
        if len(self.buffer)<capacity or self.since_analysis<self.rate*self.step_seconds:
            return None
        self.since_analysis=0
        matches=[self.match(self.buffer[:,channel]) for channel in range(2)]
        matches=[m for m in matches if m is not None]
        now=self.samples_seen/self.rate
        self.last_score=max((m.score for m in matches),default=0.)
        if not matches:
            self.previous=None
            return None
        candidate=max(matches,key=lambda m:m.score)
        absolute=candidate.reference_start+(self.samples_seen-len(self.buffer))/self.rate
        previous=self.previous
        self.previous=(absolute,now)
        coherent=previous is not None and abs(previous[0]-absolute)<.08 and now-previous[1]<1.
        if coherent and now-self.last_alert>=15.:
            self.last_alert=now
            return candidate
        return None
