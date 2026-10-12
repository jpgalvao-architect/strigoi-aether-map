# Revisão das posições de cubos • 0.5.0

Revisão em **12/10/2026**. A camada principal passa a incluir todos os locais
possíveis de aparecimento publicados nos conjuntos de objetos licenciados:
1.371 em Altgard e 1.440 em Verteron. A lista antiga de 108 e 118 cubos era
parcial e podia omitir o local visto pelo usuário.

## Basfelt: retirada do ajuste aproximado

A 0.4.2 associou o cubo visível ao UUID antigo mais próximo e moveu esse
registro para a posição aproximada do personagem. A print não comprova
essa identidade. A fonte ampliada contém duas posições diferentes:

| Registro | x normalizado | y, origem no topo | Distância ao personagem no recorte |
|---|---:|---:|---:|
| `BasfeltRuins_01_B2-01` | 0,655640 | 0,428960 | cerca de 7 px |
| `BasfeltRuins_01_B2-02` | 0,652340 | 0,426290 | cerca de 39 px |
| UUID antigo `4d774abb-5349-48af-ad28-160df500b190` | 0,652588 | 0,426392 | cerca de 37 px |

O primeiro candidato está próximo da posição do personagem junto ao cubo.
Essa proximidade apoia a inclusão do candidato, sem provar o centro exato
do objeto ou confirmar toda a base para SA. O UUID antigo volta à coordenada
original. Os dois candidatos são mantidos com identidades independentes.

`app/data/coordinate-corrections.json` conserva o registro da alteração
anterior, marcada `withdrawn`, e a razão da retirada. A evidência usa somente
o recorte do minimapa, sem incorporar os screenshots completos ou dados
pessoais. Nenhum deslocamento global foi aplicado.

## Origem e significado

Os arquivos `data-sources/object-sets/{altgard,verteron}.json` vêm do snapshot
`a23dc90849fd18b1ef4fba01d2f1bb0f851bdcbd` de
[problem-xyz/aion2-map-overlay](https://github.com/problem-xyz/aion2-map-overlay).
O aviso de licença descreve locais possíveis por grupo. Isso não significa
que todos estejam ocupados ao mesmo tempo. A versão regional do cliente
não foi declarada; o perfil SA do projeto é uma agenda de horários.

O app usa `x/100, y/100`, com origem no topo esquerdo e sem inverter Y.
Os IDs são `spawn-{map_id}-{node_id}`. O grupo e a posição ficam nas notas.
`level=up/down` indica altura relativa à mediana do grupo na fonte; não
comprova condição subaquática. Todos os candidatos continuam `possible`.
Hashes, contagens, origem, licença e transformação constam em
`app/data/cube-sites-provenance.json`. Os snapshots permanecem intactos.

## Visitas e atualização

Os 226 registros antigos continuam disponíveis numa camada separada,
inicialmente desligada. As caixas de Hidden Cubes e Gatherables permitem
ativá-la; a escolha permanece após reiniciar. Visitas antigas conservam
seus IDs e não são transferidas por proximidade. Marcar um candidato como
visitado também não certifica sua origem regional.

A migração acrescenta candidatos apenas a mapas conhecidos sem alterações,
preserva notas, filtros, visitas e agenda, e faz backup da base local em
`dataset.v042-backup.json` antes de modificá-la. Só retira a substituição
exata da 0.4.2; coordenadas ou notas editadas pelo usuário são preservadas.
Recursos e IDs personalizados não são sobrescritos. A migração é idempotente.

## Resolução e limites

3840 × 2160 físicos a 150% correspondem a 2560 × 1440 lógicos. Captura e
transformação trabalham em pixels físicos; o desenho converte pelo DPI.
O rótulo físico introduzido na versão anterior permanece. Validar esse
caminho comprova a posição desenhada relativa à base, não o spawn no jogo.
Veja [VALIDATION.md](VALIDATION.md).
