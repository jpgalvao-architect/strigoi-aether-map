# SPDX-License-Identifier: GPL-3.0-only
"""Full-screen map takes precedence while a selected minimap is active."""


class AutomaticMapTracker:
    def __init__(self, minimap, large, mini_area, full_area, *, interval=.5):
        self.minimap=minimap
        self.large=large
        self.mini_area=mini_area
        self.full_area=full_area
        self.interval=interval
        self.next_large_check=0.
        self.large_active=False

    def observe(self, read_frame, now, *, minimum):
        if self.large_active or now>=self.next_large_check:
            self.next_large_check=now+self.interval
            frame,mask=read_frame(self.full_area)
            registration,method=self.large.observe(frame,now,minimum=minimum,feature_mask=mask)
            if registration is not None:
                if not self.large_active:
                    self.minimap.reset()
                self.large_active=True
                return registration,method,self.full_area
            if self.large_active:
                self.minimap.reset()
            self.large_active=False
        frame,mask=read_frame(self.mini_area)
        registration,method=self.minimap.observe(frame,now,minimum=minimum,feature_mask=mask)
        return registration,method,self.mini_area
