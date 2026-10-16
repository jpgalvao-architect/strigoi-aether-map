# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC,datetime
from app.infrastructure.storage import atomic_json,recover_model
from app.modules.routine.models import CounterReading,RoutineCollection,RoutineProfile,profile_key


class RoutineStore:
    def __init__(self,directory):
        self.path=directory/'routine.json'
        self.collection,self.warning=recover_model(self.path,RoutineCollection,RoutineCollection())

    def commit(self,candidate):
        candidate=RoutineCollection.model_validate(candidate.model_dump())
        atomic_json(self.path,candidate)
        self.collection=candidate

    def identify(self,region,server,character,job=0):
        profile=RoutineProfile(region=region,server=server,character=character,job=job)
        key=profile_key(region,server,character)
        previous=self.collection.profiles.get(key)
        if previous and (previous.job==job or job==0) and self.collection.last_profile==key:
            return key
        candidate=self.collection.model_copy(deep=True)
        if previous:
            profile.counters=previous.counters
            if not job:profile.job=previous.job
        candidate.profiles[key]=profile
        candidate.last_profile=key
        self.commit(candidate)
        return key

    def observe(self,key,basic,charged,*,stamp=None):
        if key not in self.collection.profiles:
            raise ValueError('Unidentified routine owner')
        stamp=stamp or datetime.now(UTC)
        readings={resource:CounterReading(value=value,observed_at=stamp)
                  for resource,value in [('odyle',basic),('odyle_charged',charged)]}
        candidate=self.collection.model_copy(deep=True)
        candidate.profiles[key].counters=readings
        self.commit(candidate)

    def reading(self,key,resource):
        profile=self.collection.profiles.get(key)
        return profile.counters.get(resource) if profile else None
