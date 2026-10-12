# SPDX-License-Identifier: GPL-3.0-only
"""Frame deadline and interpolation helpers; rates are targets, never timing guarantees."""


class FramePacer:
    def __init__(self,hz=240):
        self.hz=hz
        self.deadline=0.

    def due(self,now):
        if now < self.deadline:
            return False
        period=1/self.hz
        # Skip missed deadlines instead of accumulating a burst of queued redraws.
        if self.deadline==0:
            self.deadline=now+period
        else:
            self.deadline+=period
            if self.deadline<now:
                self.deadline=now+period
        return True


class SmoothRegistration:
    """Interpolate observed matrices for a short fixed interval; never extrapolate."""
    def __init__(self):
        self.previous=None
        self.target=None
        self.changed_at=0.
        self.duration=.012

    def clear(self):
        self.previous=self.target=None

    def accept(self,registration,now):
        self.previous=self.at(now) or registration
        self.target=registration
        self.changed_at=now

    def at(self,now):
        if self.target is None:
            return None
        if self.previous is None:
            return self.target
        from app.modules.overlay.tracking import Registration
        alpha=min(1.,max(0.,(now-self.changed_at)/self.duration))
        matrix=self.previous.matrix*(1-alpha)+self.target.matrix*alpha
        return Registration(matrix,self.target.inliers,self.target.confidence)
