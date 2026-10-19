# SPDX-License-Identifier: GPL-3.0-only
"""Fast inter-frame visual updates with bounded age and periodic map revalidation."""
import math


class FastMapTracker:
    def __init__(self, reference, *, interval=.5):
        self.reference = reference
        self.interval = interval
        self.last_verified = -float('inf')
        self.registration = None
        self.previous = None
        self.points = None

    def reset(self):
        self.registration = self.previous = self.points = None

    def observe(self, image, now, *, minimum, feature_mask=None):
        import cv2
        import numpy as np
        gray = self.reference.gray(image)
        h,w=gray.shape
        factor=min(1.,1000/max(h,w))
        small=cv2.resize(gray,(round(w*factor),round(h*factor)),interpolation=cv2.INTER_AREA) if factor<1 else gray
        mask=cv2.resize(feature_mask,(small.shape[1],small.shape[0]),interpolation=cv2.INTER_NEAREST) if feature_mask is not None else None
        verification_due = now-self.last_verified >= self.interval
        if self.registration is not None and (self.reference.minimap or not verification_due):
            # Move the search hint into this frame BEFORE reference verification.
            # Comparing today's terrain to yesterday's camera rejects ordinary
            # walking (>8 px), alternately losing and rediscovering the minimap.
            motion=self._motion(small,mask,factor,minimum)
            if motion is None:
                self.reset()  # Reacquire from fresh reference evidence in this frame.
            elif not verification_due:
                return motion,'flow'
        registration=self.reference.find(image,minimum=minimum,feature_mask=feature_mask,
            hint=self.registration if self.reference.minimap else None)
        if registration is None:
            self.reset()
            return None,'search'
        self.registration=registration
        self.last_verified=now
        if registration.support_points is not None and len(registration.support_points)>=minimum:
            support=np.asarray(registration.support_points,dtype=np.float32)*factor
            self.points=support[:300].reshape(-1,1,2)
        else:
            self.points=cv2.goodFeaturesToTrack(small,maxCorners=300,qualityLevel=.015,minDistance=8,mask=mask)
        self.previous=small
        return registration,'reference'

    def _motion(self,small,mask,factor,minimum):
        import cv2
        import numpy as np
        from app.modules.overlay.tracking import Registration
        if self.previous is None or self.previous.shape != small.shape or self.points is None or len(self.points)<12:
            return None
        forward,status,_=cv2.calcOpticalFlowPyrLK(self.previous,small,self.points,None,
            winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,20,.03))
        if forward is None:
            return None
        backward,back_status,_=cv2.calcOpticalFlowPyrLK(small,self.previous,forward,None,
            winSize=(21,21),maxLevel=3)
        if backward is None:
            return None
        before=self.points.reshape(-1,2);after=forward.reshape(-1,2)
        valid=(status.ravel()==1)&(back_status.ravel()==1)&(np.linalg.norm(backward.reshape(-1,2)-before,axis=1)<1.2)
        valid &= (after[:,0]>=0)&(after[:,0]<small.shape[1])&(after[:,1]>=0)&(after[:,1]<small.shape[0])
        if mask is not None:
            indices=np.round(after).astype(int)
            indices[:,0]=np.clip(indices[:,0],0,small.shape[1]-1)
            indices[:,1]=np.clip(indices[:,1],0,small.shape[0]-1)
            valid &= mask[indices[:,1],indices[:,0]]>0
        if int(valid.sum())<max(12,minimum):
            return None
        before,after=before[valid],after[valid]
        motion,inliers=cv2.estimateAffinePartial2D(before,after,method=cv2.RANSAC,ransacReprojThreshold=2,maxIters=1000,confidence=.99)
        if motion is None or inliers is None:
            return None
        keep=inliers.ravel().astype(bool)
        count=int(keep.sum());ratio=count/len(after)
        span=np.ptp(after[keep],axis=0) if count else np.array([0,0])
        scale=math.hypot(motion[0,0],motion[1,0])
        angle=math.degrees(math.atan2(motion[1,0],motion[0,0]))
        # Large jumps, sparse support and flat frames require a new map match.
        if count<max(12,minimum) or ratio<.65 or not .94<scale<1.06 or abs(angle)>2 or span[0]<small.shape[1]*.15 or span[1]<small.shape[0]*.15 or small.std()<6:
            return None
        motion[:,2]/=factor
        combined=np.vstack([motion,[0,0,1]])@np.vstack([self.registration.matrix,[0,0,1]])
        registration=Registration(combined[:2],count,min(self.registration.confidence,ratio),after[keep]/factor)
        self.registration=registration
        self.previous=small
        self.points=after[keep].reshape(-1,1,2).astype(np.float32)
        return registration
