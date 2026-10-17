# SPDX-License-Identifier: GPL-3.0-only
"""One observed Gartua deadline, scoped to the current game session."""
from dataclasses import dataclass
from datetime import UTC,datetime,timedelta
import re
from app.core.models import GameEvent,EventSchedule


@dataclass(frozen=True)
class BossReading:
    seconds: int


def read_gartua(lines):
    titles=[r for r in lines if re.sub(r'[^a-z]','',r.get('text','').casefold()) in
        ('immortalgartua','lmmortalgartua') and r.get('height',0)>=12]
    if len(titles)!=1:return None
    title=titles[0];values=set()
    for row in lines:
        if not (title['height']*.6<row.get('y',0)-title['y']<title['height']*7):continue
        if abs(row.get('x',0)-title['x'])>title['height']*8:continue
        match=re.fullmatch(r'(?:time\s*left|tempo\s*restante)\s*:?\s*'
            r'(?:(\d{1,2})\s*d\s*)?(?:(\d{1,3})\s*h\s*)?'
            r'(?:(\d{1,2})\s*(?:min|m)\s*)?(?:(\d{1,2})\s*(?:sec|s)\s*)?',
            row.get('text','').strip(),re.I)
        if not match:continue
        days,hours,minutes,seconds=[int(v or 0) for v in match.groups()]
        total=days*86400+hours*3600+minutes*60+seconds
        if 0<total<=7*86400 and minutes<60 and seconds<60:values.add(total)
    return BossReading(values.pop()) if len(values)==1 else None


class BossConsensus:
    def __init__(self):self.last=None;self.count=0

    def observe(self,scope,reading,captured):
        if scope is None or reading is None:self.last=None;self.count=0;return None
        target=captured+timedelta(seconds=reading.seconds)
        same=self.last and self.last[0]==scope and abs((target-self.last[1]).total_seconds())<=3
        self.count=self.count+1 if same else 1;self.last=(scope,target)
        return reading if self.count>=2 else None


class BossTimer:
    def __init__(self,context):
        self.context=context;self.game=None;self.identity=None;self.revision=0;self.event=None
        self.feed=None

    def bind(self,feed):
        if self.feed is feed:return
        if self.feed is not None:
            self.feed.message.disconnect(self.from_feed);self.feed.ended.disconnect(self.reset)
        self.feed=feed;feed.message.connect(self.from_feed);feed.ended.connect(self.reset)

    def reset(self):
        changed=self.event is not None
        self.event=None;self.identity=None;self.revision+=1
        if changed:self.context.events_changed.emit()

    def set_game(self,key):
        if key!=self.game:self.reset();self.game=key

    def screen_scope(self):
        return (self.game,self.revision) if self.game and self.context.prefs.boss_timers_enabled else None

    def from_feed(self,message):
        if message.get('type')=='status' and message.get('reset_zone') is True:self.reset()
        if message.get('type')!='event':return
        payload=message.get('payload',{})
        if message.get('kind')=='SelfIdentifiedEvent':
            key=(payload.get('ServerId'),payload.get('Name'))
            if type(key[0]) is int and key[0]>0 and isinstance(key[1],str) and key[1] and key!=self.identity:
                self.reset();self.identity=key
        elif message.get('kind')=='ZoneChangedEvent':
            if self.identity is None:self.reset()
            else:self.revision+=1

    def accept(self,scope,reading,captured,now=None):
        now=now or datetime.now(UTC)
        if not isinstance(now,datetime) or now.utcoffset() is None:return False
        if scope is None or scope!=self.screen_scope() or not isinstance(reading,BossReading):return False
        if type(reading.seconds) is not int or not 0<reading.seconds<=7*86400:return False
        if not isinstance(captured,datetime) or captured.utcoffset() is None or not -1<=(now-captured).total_seconds()<=6:return False
        target=captured+timedelta(seconds=reading.seconds)
        if target<=now:return False
        if self.event and abs((self.event.schedule.starts_at-target).total_seconds())<=3:return True
        self.event=GameEvent(id='observed-immortal-gartua',name='Immortal Gartua · spawn previsto',
            kind='Chefe',region='Jogo',source='game-screen://boss/immortal-gartua',
            schedule=EventSchedule(timezone='UTC',recurrence='once',starts_at=target),
            verified_on=captured.date().isoformat(),verification='Contador lido na tela do jogo nesta sessão',
            notes=f'Leitura em {captured.astimezone(UTC):%Y-%m-%d %H:%M:%S} UTC. Previsão calculada do tempo restante exibido pelo jogo; sem repetir um horário diário presumido.')
        self.context.events_changed.emit();return True

    def events(self):
        # Keep the same-day entry for the expanded calendar; never repeat it.
        return [self.event] if self.event else []
