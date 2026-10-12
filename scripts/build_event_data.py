# SPDX-License-Identifier: GPL-3.0-only
"""Published schedules reviewed on 2026-10-11; source clock and display clock are distinct."""
import json
from pathlib import Path

events=[]
ABYSS='https://aion2maps.com/guides/abyss/'
DAILY='https://aion2maps.com/guides/daily-and-weekly/'

def add(key,name,kind,times,source,notes,days=None,zone='America/Sao_Paulo',duration=None):
    events.append(dict(id=key,name=name,kind=kind,region='LATAM',source=source,notes=notes,
        verified_on='2026-10-11',verification='Conferido em fonte pública; não validado nesta sessão no jogo',
        duration_minutes=duration,schedule=dict(timezone=zone,recurrence='weekly' if days else 'daily',
        times=times,weekdays=days or list(range(7)))))

add('latam-shugo','Festival de Shugo','Festival',[f'{h:02}:00' for h in range(24)],
    'https://metabot.gg/en/aion-2/events','Abertura a cada hora. Horário publicado; duração não informada.')
add('latam-invasion','Invasão dimensional','Invasão',[f'{h:02}:30' for h in range(24)],
    'https://metabot.gg/en/aion-2/events','Abertura no minuto 30. Horário publicado; duração não informada.')
add('latam-rift','Fenda espaço-temporal','Fenda',[f'{h:02}:00' for h in range(2,24,3)],ABYSS,
    'A fonte usa hora regional. Portal aberto por 10 minutos.',duration=10)
add('latam-watcher','Watcher Kaira','Chefe',[f'{h:02}:00' for h in range(1,24,3)],ABYSS,
    'A fonte usa hora regional. Duração não informada.')
add('latam-siege','Cerco de artefatos • preparação','Cerco',['21:00'],ABYSS,
    'Preparação às 21h; combate às 21h10. Segunda, quinta e sábado no fuso regional.',[0,3,5],duration=10)
add('latam-executors','Executors Tamasa, Argo e Kaira','Chefe',['21:30'],ABYSS,
    'Segunda, quinta e sábado, após o cerco. Duração não informada.',[0,3,5])
add('latam-nahma','Guardian Lord Nahma','Chefe',['21:00'],ABYSS,
    'Sexta e domingo no fuso regional. Duração não informada.',[4,6])
add('global-daily-reset','Reset diário','Reset',['07:00'],DAILY,
    'Instante global fixo: 07h UTC = 04h em Brasília. Não é 07h no relógio LATAM.',zone='UTC')
add('global-weekly-reset','Reset semanal','Reset',['07:00'],DAILY,
    'Quarta-feira, 07h UTC = 04h em Brasília.',[2],zone='UTC')

feed=dict(schema_version=1,demo=False,release='latam-2026-10-11',
    coverage='LATAM • fontes consultadas em 11/10/2026 • eventos em São Paulo; resets em UTC',events=events)
(Path(__file__).resolve().parents[1]/'app/data/events.json').write_text(
    json.dumps(feed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('9 agendas LATAM geradas')
