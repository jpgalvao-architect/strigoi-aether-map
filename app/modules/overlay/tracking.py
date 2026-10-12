# SPDX-License-Identifier: GPL-3.0-only
"""Independent map-to-screen registration using public OpenCV primitives.

The app matches its bundled map art to the explicitly selected capture area.
No game process, input hooks, or inferred player position are involved.
"""
from dataclasses import dataclass
from pathlib import Path
import math


@dataclass(frozen=True)
class Registration:
    matrix: object  # 2x3, normalized map coordinates -> physical ROI pixels
    inliers: int
    confidence: float
    support_points: object = None

    def project(self, x, y):
        m = self.matrix
        return float(m[0, 0]*x+m[0, 1]*y+m[0, 2]), float(m[1, 0]*x+m[1, 1]*y+m[1, 2])


class MapRegistration:
    """SIFT matches and a constrained similarity transform for pan and zoom.

    Large-map features use a grid; minimaps use a denser global reference with
    local refinement to preserve features in small terrain crops. Each reference
    verification matches independently:
    an old successful transform is never reused after a failed observation.
    """
    def __init__(self, image, *, should_stop=lambda: False, minimap=False):
        import cv2
        import numpy as np
        self.cv2 = cv2
        self.np = np
        self.minimap = minimap
        if isinstance(image, (Path, str)):
            image = cv2.imdecode(np.fromfile(image, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("A imagem do mapa não pôde ser carregada")
        gray = self.gray(image)
        self.detail_image = gray if minimap else None
        h, w = gray.shape
        factor = min(1.0, (4096 if minimap else 2400)/max(h, w))
        gray = cv2.resize(gray, (round(w*factor), round(h*factor)), interpolation=cv2.INTER_AREA)
        h, w = gray.shape
        coordinates, descriptors = [], []
        grid = 1 if minimap else 5
        reference_detector = cv2.SIFT_create(nfeatures=80000 if minimap else 450, contrastThreshold=.008 if minimap else .025)
        for row in range(grid):
            for col in range(grid):
                if should_stop():
                    raise InterruptedError("Preparação cancelada")
                left, top = col*w//grid, row*h//grid
                right, bottom = (col+1)*w//grid, (row+1)*h//grid
                x0, y0 = max(0, left-32), max(0, top-32)
                kp, desc = reference_detector.detectAndCompute(gray[y0:min(h,bottom+32), x0:min(w,right+32)], None)
                if desc is None:
                    continue
                for k, d in zip(kp, desc):
                    x, y = k.pt[0]+x0, k.pt[1]+y0
                    if left <= x < right and top <= y < bottom:
                        coordinates.append((x/w, y/h))
                        descriptors.append(d)
        if len(coordinates) < 30:
            raise ValueError("O mapa não tem detalhes suficientes para reconhecimento")
        self.reference_points = np.asarray(coordinates, dtype=np.float32)
        self.reference_descriptors = np.asarray(descriptors,dtype=np.float32)
        self.matcher = cv2.FlannBasedMatcher(dict(algorithm=1, trees=4), dict(checks=64))
        self.matcher.add([np.asarray(descriptors, dtype=np.float32)])
        self.matcher.train()
        self.frame_detector = cv2.SIFT_create(nfeatures=2000, contrastThreshold=.008 if minimap else .025)
        self.detail_detector = cv2.SIFT_create(nfeatures=10000, contrastThreshold=.008) if minimap else None
        self.aspect = w/h

    def gray(self, image):
        cv2 = self.cv2
        if image.ndim == 2:
            return image
        return cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)

    def find(self, image, *, minimum=14, feature_mask=None, hint=None):
        cv2, np = self.cv2, self.np
        if not self.minimap:
            hint=None
        height, width = image.shape[:2]
        if min(height, width) < 80:
            return None
        factor = min(1.0, 1200/max(height, width))
        frame = self.gray(image)
        if factor < 1:
            frame = cv2.resize(frame, (round(width*factor), round(height*factor)), interpolation=cv2.INTER_AREA)
            if feature_mask is not None:
                feature_mask = cv2.resize(feature_mask,(frame.shape[1],frame.shape[0]),interpolation=cv2.INTER_NEAREST)
        kp, desc = self.frame_detector.detectAndCompute(frame, feature_mask)
        if desc is None or len(kp) < minimum:
            return None
        candidates = self.matcher.knnMatch(desc, k=2)
        # Each reference feature contributes at most once to geometric evidence.
        selected = {}
        for pair in candidates:
            if len(pair) != 2:
                continue
            best, runner = pair
            if best.distance < (.78 if self.minimap else .72)*runner.distance:
                if best.trainIdx not in selected or best.distance < selected[best.trainIdx].distance:
                    selected[best.trainIdx] = best
        matches = list(selected.values())
        seed_minimum = max(6,min(10,minimum//3)) if self.minimap else minimum
        if hint is None and len(matches) < seed_minimum:
            return None
        src = self.reference_points[[m.trainIdx for m in matches]].copy()
        # Work in square reference units so the estimator has the right aspect ratio.
        src[:, 0] *= self.aspect
        dst = np.asarray([kp[m.queryIdx].pt for m in matches], dtype=np.float32)/factor
        if hint is not None and self.minimap:
            # A hint narrows the search; acceptance still needs fresh reference
            # matches below. It never supplies evidence or preserves a failure.
            matrix=hint.matrix.copy();matrix[:,0]/=self.aspect
            mask=np.ones((len(matches),1),dtype=np.uint8)
        else:
            matrix, mask = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                ransacReprojThreshold=3.5/factor, maxIters=2000, confidence=.995, refineIters=10)
        if matrix is None or mask is None or not np.isfinite(matrix).all():
            return None
        if self.minimap:
            # Verify a broad global candidate by matching independently in its local area.
            # The final registration still requires the configured full inlier count.
            seed_count = int(mask.sum())
            if hint is None and seed_count < seed_minimum:
                return None
            angle = math.degrees(math.atan2(matrix[1,0],matrix[0,0]))
            if abs(angle)>3:
                return None
            normalized_seed=matrix.copy();normalized_seed[:,0]*=self.aspect
            inverse=cv2.invertAffineTransform(normalized_seed)
            corners=np.float32([[0,0],[width,0],[width,height],[0,height]])
            reference_corners=cv2.transform(corners.reshape(-1,1,2),inverse).reshape(-1,2)
            # A reduced whole-map reference loses small terrain details behind
            # quest icons and the vision cone. Verify the candidate against the
            # original-resolution terrain, without relaxing the final minimum.
            h,w=self.detail_image.shape
            low=np.maximum(0,np.floor((reference_corners.min(axis=0)-.015)*[w,h]).astype(int))
            high=np.minimum([w,h],np.ceil((reference_corners.max(axis=0)+.015)*[w,h]).astype(int))
            x,y=low;right,bottom=high
            if right-x<80 or bottom-y<80:
                return None
            local_kp,local_descriptors=self.detail_detector.detectAndCompute(self.detail_image[y:bottom,x:right],None)
            if local_descriptors is None or len(local_kp)<minimum:
                return None
            local_points=(np.float32([k.pt for k in local_kp])+[x,y])/[w,h]
            local=cv2.FlannBasedMatcher(dict(algorithm=1,trees=4),dict(checks=96))
            pairs=local.knnMatch(desc,local_descriptors,k=2)
            unique={}
            for pair in pairs:
                if len(pair)==2 and pair[0].distance < .78*pair[1].distance:
                    best=pair[0]
                    if best.trainIdx not in unique or best.distance<unique[best.trainIdx].distance:
                        unique[best.trainIdx]=best
            local_matches=list(unique.values())
            if len(local_matches)<minimum:
                return None
            src=local_points[[m.trainIdx for m in local_matches]].copy()
            src[:,0]*=self.aspect
            dst=np.float32([kp[m.queryIdx].pt for m in local_matches])/factor
            refined,refined_mask=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,
                ransacReprojThreshold=3.5/factor,maxIters=2000,confidence=.995,refineIters=10)
            if refined is None or refined_mask is None:
                return None
            refined_normalized=refined.copy();refined_normalized[:,0]*=self.aspect
            difference=cv2.transform(reference_corners.reshape(-1,1,2),refined_normalized).reshape(-1,2)-corners
            if np.linalg.norm(difference,axis=1).max()>8:
                return None
            matrix,mask,matches=refined,refined_mask,local_matches
        keep = mask.ravel().astype(bool)
        count = int(keep.sum())
        ratio = count/len(matches)
        if count < minimum or ratio < .45:
            return None
        angle = math.degrees(math.atan2(matrix[1,0], matrix[0,0]))
        full_height = math.hypot(matrix[0,0], matrix[1,0])
        if abs(angle) > 3 or not .4*max(width,height) < full_height < (80 if self.minimap else 18)*max(width,height):
            return None
        measured = dst[keep]
        # Require support over a meaningful portion of the capture, not a tiny icon.
        span = np.ptp(measured, axis=0)
        if span[0] < width*.15 or span[1] < height*.15:
            return None
        hull_area = cv2.contourArea(cv2.convexHull(measured))
        if hull_area < width*height*.025:
            return None
        normalized = matrix.copy()
        normalized[:,0] *= self.aspect
        confidence = min(1.0, ratio*min(1.0,count/30))
        return Registration(normalized, count, confidence, dst[keep].copy())
