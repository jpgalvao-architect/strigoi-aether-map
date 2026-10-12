# Fontes e alcance da base • 0.5.0

Consulta em **11/10/2026**, para a região escolhida pelo usuário: **LATAM**. A verificação realizada consiste em conferir os registros nas fontes públicas e validar a transformação dos dados. Não houve acesso ao cliente nem confirmação de cada ponto dentro do jogo. Fontes comunitárias não equivalem a uma certificação da NCSOFT.

## Catálogo de recursos

21 nomes e categorias foram conferidos no catálogo
[Aion 2 Maps — Gathering](https://aion2maps.com/gathering/).
A versão 0.3.0 acrescenta 5.425 posições de coleta dos conjuntos CC BY-NC
publicados por problem-xyz: 2.692 em Altgard e 2.733 em Verteron. Os dados
originais estão em `data-sources/object-sets/`; o hash, a origem e a
transformação constam em `app/data/gathering-provenance.json`. As coordenadas
percentuais da fonte são divididas por 100, sem inverter novamente Y.
Os testes comparam cada coordenada incorporada com o registro de origem.
Raridade permanece **Não informada**. As outras três camadas do catálogo são vestígios, posições possíveis de cubos e registros antigos KR/TW.

O botão de consulta abre a fonte no navegador para localizar recursos na base atual do publicador. Não existe download ou atualização automática dessas coordenadas no app.

## Perfil SA do projeto consultado

O perfil inicial **SA • agenda do projeto de referência** corresponde a
`global-sa` no arquivo `assets/timers/schedule.json`, atualizado pelo autor
em 7 de outubro de 2026. Os fatos de horários foram convertidos para o
contrato do Strigoi, mantendo o fuso de cada regra. A seleção de SA usa
`America/Sao_Paulo` quando a regra não define outro fuso.

| Evento | Regra do perfil publicado | Exibição em SA |
|---|---|---|
| Shugo | Cada hora, minuto 00 | Cada hora, minuto 00 |
| Fendas | A cada 3h desde 00h UTC | A cada 3h desde 21h SA |
| Cerco | Seg/qui/sáb, 21h UTC | Seg/qui/sáb, 18h SA |
| Chefes do cerco | Seg/qui/sáb, 21h30 UTC | Seg/qui/sáb, 18h30 SA |
| Nahma | Sex/dom, 21h UTC | Sex/dom, 18h SA |
| Reset diário | 09h regional | 09h SA |
| Reset semanal | Quarta, 09h regional | Quarta, 09h SA |

Fonte:
[agenda do snapshot consultado](https://github.com/problem-xyz/aion2-map-overlay/blob/a23dc90849fd18b1ef4fba01d2f1bb0f851bdcbd/assets/timers/schedule.json).
Isso reproduz o perfil publicado; não confirma seus horários dentro do jogo.
Outras fontes indicam cerco às 21h regionais e reset às 07h UTC. A agenda
anterior continua selecionável como **SA • fontes da versão anterior**.
Os perfis ficam separados. Nenhum campo é apresentado como horário oficial.

## Agenda anterior, também disponível

| Agenda | Regra incorporada | Fonte |
|---|---|---|
| Festival de Shugo | Cada hora, minuto 00 | [MetaBot Events](https://metabot.gg/en/aion-2/events) |
| Invasão dimensional | Cada hora, minuto 30 | [MetaBot Events](https://metabot.gg/en/aion-2/events) |
| Fendas | A cada 3 horas, começando às 02h | [Aion 2 Maps — Abyss](https://aion2maps.com/guides/abyss/) |
| Watcher Kaira | A cada 3 horas, começando à 01h | [Aion 2 Maps — Abyss](https://aion2maps.com/guides/abyss/) |
| Cerco | Seg/qui/sáb, preparação às 21h; combate às 21h10 | [Aion 2 Maps — Abyss](https://aion2maps.com/guides/abyss/) |
| Executors | Seg/qui/sáb às 21h30 | [Aion 2 Maps — Abyss](https://aion2maps.com/guides/abyss/) |
| Guardian Lord Nahma | Sex/dom às 21h | [Aion 2 Maps — Abyss](https://aion2maps.com/guides/abyss/) |
| Reset diário | 07h UTC, exibido como 04h em Brasília | [Aion 2 Maps — Daily and weekly](https://aion2maps.com/guides/daily-and-weekly/) |
| Reset semanal | Quarta-feira às 07h UTC, 04h em Brasília | [Aion 2 Maps — Daily and weekly](https://aion2maps.com/guides/daily-and-weekly/) |

Os sete primeiros seguem `America/Sao_Paulo`. Os resets usam `UTC`. Fuso de exibição pode ser alterado nas configurações sem mudar o instante de origem. A distinção entre relógio regional e reset fixo foi corroborada pela [referência LATAM](https://aion2db.lat/wiki/eventos-y-horarios) e pela [lista de regiões do Global](https://aion2maps.com/guides/launch-info/). Existem contadores comunitários com suposições diferentes de fuso; o relógio do jogo prevalece em caso de divergência. Durações desconhecidas permanecem nulas. O app notifica o início da preparação do cerco, não inventa um segundo alerta de combate.

Cada evento conserva URL, data da consulta, nota e fuso de origem. Não há promessa de atualização após a data acima. Alterações de patch exigem nova revisão ou importação de agenda. Horários de Arena/Battlefield sem confirmação suficiente foram omitidos.

## Atlas comunitário: referência KR/TW

Origem: [Aion2 Interactive Map](https://github.com/aion2-interactive-map/aion2-interactive-map), por **Yihao Liu (tc-imba) e colaboradores**. Snapshot fixado no commit `89ce3984d569ff1a03ee6311d064231211212981`.

| Mapa | Vestígios (`monolithMaterial`) | Hidden Cubes |
|---|---:|---:|
| Verteron / World_L_A | 560 | 118 |
| Altgard / World_D_A | 560 | 108 |
| Total incorporado | 1.120 | 226 |

Os números representam os registros selecionados da base asiática, **não totais nem posições confirmadas do Global/LATAM**. Os pontos de coleta foram incorporados da distribuição citada acima; outros mapas permanecem fora desta versão. Nenhuma posição foi inventada ou transferida para recursos de coleta.

Os fundos são imagens reais de Altgard e Verteron, em WebP de 8192 × 8192 pixels, preservadas sem edição. Origem: [problem-xyz/aion2-map-overlay](https://github.com/problem-xyz/aion2-map-overlay), commit `a23dc90849fd18b1ef4fba01d2f1bb0f851bdcbd`, arquivos `assets/maps/{altgard,verteron}/detail.webp`, derivados do Aion2 Interactive Map. O distribuidor atribui esses arquivos a CC BY-NC 4.0 e ressalva os direitos da NCSOFT sobre a arte. O aviso integral está em `third-party-notices/map-art/NOTICE.txt`. SHA-256, Git blob e URL fixa de cada imagem constam em `app/data/map-art-provenance.json`. A transformação dos pontos usa a imagem inteira: `x = source_x / 8192`, `y = 1 - source_y / 8192`. Os valores exatos, hashes dos arquivos-fonte e fórmula constam em `app/data/community-provenance.json`; o script `scripts/build_curated_data.py` reproduz a transformação. Os 1.346 registros originais são comparados com o snapshot nos testes. O ajuste aproximado de Basfelt publicado na 0.4.2 foi retirado na 0.5.0;
o UUID antigo volta à coordenada da fonte, conforme
[COORDINATE_CORRECTION.md](COORDINATE_CORRECTION.md).

## Cubos: posições possíveis incorporadas na 0.5.0

Revisão de 12/10/2026. Os conjuntos de objetos licenciados do mesmo snapshot
de problem-xyz contêm 1.371 posições em Altgard e 1.440 em Verteron. O aviso
de origem descreve todos os locais possíveis por grupo, sem garantir presença
simultânea. O cliente/região que originou os grupos não foi declarado.
**Esta entrega não certifica essas posições como específicas ou verificadas
em SA.** O perfil SA de horários é independente da geografia.

Esses candidatos formam a camada principal, com `x/100, y/100`, origem no
topo esquerdo e sem uma segunda inversão de Y. Os grupos e alturas relativas
ficam nas notas; condição subaquática permanece desconhecida. O manifesto
`app/data/cube-sites-provenance.json` registra contagens, hashes, transformação,
licença e limitações. A camada histórica mantém seus 226 IDs e visitas,
inicialmente desligada, sem migração de identidade por distância.

Cada ponto está marcado `possible`. Os mapas raster agora aceitam o overlay experimental, com reconhecimento independente do terreno e controles de camada. A transformação da imagem não certifica a presença de objetos no servidor SA. Rota e condição subaquática também não foram confirmadas.

## Licença e atribuição

Os arquivos de `/public/data` do projeto de origem são disponibilizados em **[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**. Esta adaptação conserva autoria, licença, fonte e alterações. **O pacote de dados comunitários é para uso não comercial**; uso comercial requer autorização dos titulares. O aviso original acompanha `data-sources/community/LICENSE.txt` no código-fonte e `third-party-notices/community/LICENSE.txt` no portátil.

Alterações nos dados: seleção de dois mapas e tipos de ponto, conversão de coordenadas, tradução de rótulos e metadados de cobertura. As imagens são cópias intactas da distribuição citada acima, que documenta sua origem e termos separadamente. Não foi copiado código do projeto de origem ou do distribuidor.

Aether é o mascote próprio do app, criado com geração de imagens a partir de inspiração visual solicitada pelo usuário. Os ícones SVG são originais do projeto. A licença comunitária de dados não se aplica às novas ilustrações, aos ícones próprios, aos nomes do jogo ou ao código próprio. Os assets e prompts estão em BRANDING.md.

O perfil SA corresponde a uma região de horários; os conjuntos geográficos do projeto consultado não têm uma edição exclusiva SA. Veja [o estudo](REFERENCE_REVIEW.md).
