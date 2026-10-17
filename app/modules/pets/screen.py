# SPDX-License-Identifier: GPL-3.0-only
"""Read only the selected pet's Insight row, never the separate genus level."""
from dataclasses import dataclass
import re
import unicodedata


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if c.isalnum())


@dataclass(frozen=True)
class PetScreenReading:
    pet_id: int
    level: int
    souls: int
    required: int


def insight_anchor(lines):
    anchors=[line for line in lines if re.match(r'^(pet insight|insight do pet)\b',
             line.get('text','').strip(),re.I) and line.get('height',0)>=10]
    return anchors[0] if len(anchors)==1 else None


def parse_detail(lines, pets):
    anchor=insight_anchor(lines)
    if anchor is None:return None
    ax,ay,ah=(anchor[k] for k in ('x','y','height'))
    names={normalized(pet.name):pet.id for pet in pets}
    identities={names[normalized(line.get('text',''))] for line in lines
        if normalized(line.get('text','')) in names and ah<=ay-line.get('y',0)<=ah*7
        and abs(line.get('x',0)-ax)<=ah*8}
    if len(identities)!=1:return None
    values=set()
    for line in lines:
        if abs(line.get('y',0)-ay)>ah*.8 or line.get('x',0)<=ax:continue
        match=re.fullmatch(r'(?:Lv\.?|N[ií]vel)\s*(\d{1,2})\s*\(\s*(\d{1,6})\s*/\s*(\d{1,6})\s*\)',
                          line.get('text','').strip(),re.I)
        if match:
            level,souls,required=map(int,match.groups())
            if 0<=level<=10 and 0<=souls<=required<=100000 and required>0:
                values.add((level,souls,required))
    if len(values)!=1:return None
    return PetScreenReading(identities.pop(),*values.pop())


class PetScreenReader:
    def __init__(self,ocr,pets):self.ocr,self.pets=ocr,pets

    def recognize(self,frame):
        import cv2
        largest=max(frame.shape[:2])
        if largest>1800:
            ratio=1800/largest;frame=cv2.resize(frame,None,fx=ratio,fy=ratio)
        lines=self.ocr.recognize(frame)
        anchor=insight_anchor(lines)
        if anchor is None:return None
        # A control immediately above the row can prevent whole-panel OCR from
        # finding the numbers. A narrow, enlarged row excludes that control.
        y=max(0,round(anchor['y']-anchor['height']*.35))
        bottom=min(frame.shape[0],round(anchor['y']+anchor['height']*1.35))
        band=frame[y:bottom]
        if band.size:
            scale=min(2,1920/band.shape[1])
            refined=self.ocr.recognize(cv2.resize(band,None,fx=scale,fy=scale))
            for line in refined:
                if re.match(r'^(?:Lv\.?|N[ií]vel)\s*\d',line.get('text',''),re.I):
                    lines.append(dict(text=line['text'],x=line['x']/scale,y=y+line['y']/scale,height=line['height']/scale))
        return parse_detail(lines,self.pets)


class ReadingConsensus:
    def __init__(self):self.last=None;self.count=0

    def observe(self,scope,reading):
        current=(scope,reading) if scope is not None and reading is not None else None
        self.count=self.count+1 if current is not None and current==self.last else 1
        self.last=current
        return reading if current is not None and self.count>=2 else None
