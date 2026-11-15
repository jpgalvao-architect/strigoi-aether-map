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
        self.mini_missing_since = None
        self.next_full_search = 0.

    def observe(self, read_frame, now, *, minimum, large_only=False, probe_large=None):
        if large_only or self.large_active or now>=self.next_large_check:
            self.next_large_check=now+self.interval
            registration, method = None, 'search'
            confirming = getattr(self.large, 'pending', None) is not None
            lost_minimap = self.mini_missing_since is not None and now-self.mini_missing_since >= 1.2
            retry_full = lost_minimap and now >= self.next_full_search
            if self.large_active or large_only or confirming or retry_full or probe_large is None or probe_large():
                self.next_full_search = now + 1.
                frame,mask=read_frame(self.full_area)
                registration,method=self.large.observe(frame,now,minimum=minimum,feature_mask=mask)
            if registration is not None:
                if not self.large_active:
                    self.minimap.reset()
                self.large_active=True
                self.mini_missing_since = None
                return registration,method,self.full_area
            if self.large_active:
                self.minimap.reset()
            self.large_active=False
            # A full-width match awaiting confirmation is enough to keep the
            # minimap crop out of the player-region estimate for this frame.
            if getattr(self.large, 'pending', None) is not None:
                self.next_large_check = now
                return None, method, self.full_area
            if large_only:
                return None, method, self.full_area
        frame,mask=read_frame(self.mini_area)
        registration,method=self.minimap.observe(frame,now,minimum=minimum,feature_mask=mask)
        if registration is not None:
            self.mini_missing_since = None
        elif self.mini_missing_since is None:
            self.mini_missing_since = now
        return registration,method,self.mini_area
