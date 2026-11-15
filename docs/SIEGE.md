# Siege Command

O Siege Command é o editor tático de Chaotic Lower Reshanta. O mapa também
fica disponível no Atlas para consulta de Coletas e Pets.

## Editar pins

1. Abra **Siege Command → Editar pins** e clique em **Adicionar pin**.
2. Clique no ponto desejado, inclusive sobre a água ou entre ilhas.
   O primeiro pin no preset oficial cria e seleciona **Minhas marcações**.
3. Selecione o pin no mapa ou na lista para editar nome, categoria, cor,
   tamanho e visibilidade. Arraste o pin no mapa para reposicioná-lo.
   As mudanças são salvas ao concluir cada edição.
4. Use **Excluir pin** para remover um pin do preset.
   **Cancelar edição** ou **Esc** abandonam o posicionamento em curso.

Use **Ilhas** para enquadrar a área jogável e **Mapa inteiro** para ver toda
a extensão. Role para ampliar e arraste o terreno para deslocar o mapa.
Os anéis usam um símbolo circular com código abaixo. Objetivos e marcações
personalizadas usam pins. Quando falta espaço para um rótulo, os objetivos
e os anéis de siege têm prioridade.

## Ver as marcações no jogo

1. Deixe o instalador preparar o mapa de Lower Reshanta com acesso à internet.
   Depois, o mapa abre offline. Na versão portátil, ou se a conexão cair
   durante a instalação, use **Baixar mapa** no Siege Command.
2. Ative **Overlay de Reshanta** no Siege Command ou **Reshanta / Siege**
   no menu rápido. Os dois controles usam a mesma preferência.
3. Se for sua primeira configuração, clique em **Selecionar minimapa** e
   demarque a área de terreno do minimapa no jogo.
4. Em Lower Reshanta, pressione **M** para ver o mesmo preset sobre o mapa
   do jogo. Ao fechar o mapa, os marcadores retornam ao minimapa quando
   o terreno é reconhecido.

O overlay geral mostra as camadas de exploração do mapa reconhecido.
O controle **Overlay de Reshanta** atua nos objetivos, nos anéis e nos
pins do preset ativo. A aba **Camadas e presets** controla as categorias
e a aparência do preset. O modo de mapa com referência fixa usa somente
a referência importada. O modo automático acompanha a região exibida no jogo.

## Compartilhar marcações

Clique em **Exportar marcações (.json)** no editor para salvar o preset
ativo. Em outra instalação, use **Importar marcações (.json)**. O programa
valida e seleciona o preset importado. Se já existir um preset com aquele
nome, escolha **Importar como novo** para manter ambos ou **Substituir preset**
para atualizar a cópia com o mesmo nome. O preset oficial é sempre protegido.

A exportação e a importação funcionam offline. O JSON inclui os pins e
as preferências de visualização do preset. Anéis oficiais, imagens, dados de
pets e calibrações administrativas têm seus próprios arquivos. Um apelido de
anel pode ser importado antes do catálogo e passa a aparecer quando o
respectivo anel estiver disponível.

O [esquema de marcações](../schemas/siege-preset.schema.json) descreve os
campos aceitos. Use `schema_version` igual a `1`, `map_id` igual a
`lower-reshanta` e `map_frame` igual a `Abyss_Reshanta_A`. Arquivos antigos
com versão 1 também são aceitos quando omitem `map_frame`.

- `name` identifica o preset. `layers` controla as camadas desenhadas.
  Inclua `CustomMarkers` para mostrar os pins.
- Cada entrada em `markers` tem um `id` único dentro do preset começando
  com `local-`, um `name` e uma `position` com `x` e `y` numéricos
  entre 0 e 1. A origem fica no canto superior esquerdo do quadro.
  Mantenha o ID ao editar ou compartilhar novas revisões do mesmo pin.
- `color` usa `#RRGGBB` ou `null` para herdar a cor da camada. `scale`
  multiplica o tamanho do preset entre 0,65 e 1,8. `category` é um nome
  livre com até 32 caracteres. `visible` indica se o pin aparece.
- `colors`, `marker_scale`, `aliases` e `use_local_calibration` guardam
  as preferências de camada, tamanho, apelidos e uso de calibração local.

## Configurar anéis e camadas

**Siege Global v1** mostra os 12 objetivos e os anéis com posição
disponível. Em **Camadas e presets**, duplique o preset para ajustar cores,
tamanho, camadas e apelidos. **Restaurar Global** volta ao preset oficial.

Em **Catálogo de anéis**, use **Importar catálogo local** com um
[catálogo compatível](../schemas/siege-ring-catalogue.schema.json) no
quadro `Abyss_Reshanta_A/4096-north-up`. Os downloads públicos incluem
a lista de pendências por zona. As posições individuais de anéis são
importadas à parte.

Para calibrar um anel, abra **Catálogo de anéis**, escolha o registro, clique
em **Posicionar no mapa** e selecione a posição conferida. Ajuste X e Y se
necessário e registre a fonte. Marque a posição como conferida apenas depois
da revisão. Salve e habilite **Aplicar calibrações locais** no preset
personalizado. Use **Restaurar posição do anel** para remover o ajuste local.

Um anel pendente fica no catálogo sem marcador. Um ponto provisório fica
pontilhado no mapa. **Fixar novos callsigns** numera os anéis
conferidos que ainda não têm código, conservando todos os códigos anteriores.
A ordenação inicial considera faixas de 8 px de norte a sul e posições de
oeste a leste na mesma faixa. Uma importação posterior pode acrescentar IDs.
A troca de setor ou callsign de um ID já registrado é rejeitada.

Os 30 anéis de trânsito do catálogo de referência recebem códigos fixos por
ID de origem. **BF** agrupa Black Fragments, **DR** agrupa Devastated Remnants,
**ER** e **WR** identificam as aproximações das bases Eastern e Western Root,
e **LR** cobre os corredores gerais de Lower Reshanta. A nomenclatura é
tática do Azphelumbra e permanece estável ao aplicar uma calibração local.

## Cartografia e fontes

- **Base.** Mosaico integral dos 16 tiles `Abyss_Reshanta_A` da referência
  comunitária. A licença do repositório declara CC BY-NC 4.0 para
  `public/data`. Os tiles consultados estão em `public/UI`. A arte de AION 2
  é da NCSOFT. O instalador baixa os tiles da origem, confere o SHA-256
  de cada arquivo e do quadro final e guarda o mapa na pasta de dados do app.
  [Tiles no commit consultado](https://github.com/aion2-interactive-map/aion2-interactive-map/tree/89ce3984d569ff1a03ee6311d064231211212981/public/UI/Map/WorldMap/Abyss_Reshanta_A/Res).
- **Objetivos.** As pontas dos marcadores da imagem do usuário foram medidas
  no arquivo de 1782 × 759. Cada recorte usa uma transformação afim própria
  a partir de ilhas, bordas e acidentes do terreno. Dividir X e Y resultantes
  por 4096 os coloca no sistema do Atlas, com origem no canto superior
  esquerdo. Os resíduos medidos ao retirar um controle por vez chegam a
  cerca de 32 px no MID, 35 px no BOT e 72 px no TOP no quadro de 4096 px.
  Os pontos são referências táticas, com conferência em jogo pendente.
  No TOP, a etiqueta 8 repetida à direita foi transcrita como **P9**, com
  a ponta do marcador mantida. O BOT continua com **P8**.
- **Anéis.** A revisão de 14/11/2026 encontrou **49** registros individuais
  publicados para Lower Reshanta. No quadro do Atlas, X é
  `(2048 + longitude/100)/4096` e Y é
  `(2048 - latitude/100)/4096`. O mosaico foi comparado ao quadro da fonte.
  Os Kibelisks Latesran Eastern Root e Western Root, e os três artefatos,
  foram usados para conferir orientação, origem e escala. O catálogo local
  fixa 2 anéis em MID, 10 em BOT e 7 em TOP. A classificação é tática
  e inclui as aproximações. Os outros 30 ficam em trânsito. A fonte
  consultada fornece X/Y. A altitude e a confirmação no servidor SA
  ficam em aberto.
  [Coordenadas no mapa Aion2t](https://aion2t.com/map?zone=2616&types=flight_ring),
  [contagem e cobertura do MetaBot](https://metabot.gg/en/aion-2/map/chaotic-lower-reshanta/flight-rings).
- **Catálogo local.** A resposta de coordenadas foi conferida para a prévia
  pessoal. Os termos da fonte condicionam a cópia e redistribuição à
  permissão. O repositório tem o catálogo de pendências por zona. A prévia
  lê o catálogo posicionado de um arquivo local separado, sem consulta de
  rede em tempo de execução.
  [Termos do Aion2t](https://aion2t.com/terms).
- **Exploração.** A camada Coletas contém 240 posições possíveis de Lesser
  Odyle. A camada Pets liga 990 posições de monstros a 23 pets do catálogo
  existente. Os pontos passam pelo mesmo quadro e ficam disponíveis no
  Atlas, no filtro do catálogo de Coletas e na aba Pets. Os locais de pets
  ficam na prévia pessoal. No instalador público, use **Camadas e presets →
  Importar locais de pets** para carregar um JSON compatível com o
  [esquema pet-sites](../schemas/pet-sites.schema.json) que você tenha
  permissão para usar.
  [Coletas do mapa comunitário](https://data-aion2.tc-imba.com/markers/Abyss_Reshanta_A.json),
  [extração de spawns do cliente](https://github.com/SkeeveAN/Aion-DPS-Meter/blob/c933676e6a4f47cc861d7472f892c14e6bc49244/Client/assets/aion2/pets/spawns.json).

Para montar o PNG a partir dos tiles originais obtidos para uso local, execute
`python scripts/prepare_reshanta_map.py <pasta-dos-tiles> <destino.png>`.
O script confere cada hash e o mosaico final. Os pontos de controle, matrizes
e hashes estão em [data-sources/siege-reshanta.json](../data-sources/siege-reshanta.json).
Os contratos de importação ficam em [schemas](../schemas).

## Arquitetura

`SiegeService` salva presets, ajustes de anéis e a preferência do overlay
em `siege-command.json`. O mapa e o catálogo local ficam em arquivos
separados. O reconhecimento reutiliza a janela transparente do overlay geral
e projeta as coordenadas normalizadas no minimapa e no mapa aberto com M.
Uma mudança de resolução ou DPI recalcula a área de captura a partir da
seleção salva. O código e os dados de Call tática e HUD compacto ficam
preservados para uso futuro.
