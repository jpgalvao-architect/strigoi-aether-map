# Siege Command

O Siege Command é o editor tático de Chaotic Lower Reshanta. O mapa também
fica disponível no Atlas para consulta de Coletas e Pets.

## Editar pins no Editor tático

**Siege Global — Default** começa com P1–P12 nas coordenadas de
referência. Abra **Siege Command → Editor tático** para editar o preset ativo.

1. Clique em um pin no mapa ou selecione-o na lista. Edite nome, categoria,
   cor, tamanho e visibilidade. Arraste o pin para reposicioná-lo.
2. Use o ícone **Adicionar pin** para marcar qualquer ponto, inclusive sobre a água.
   Para criar um objetivo como P13, dê esse nome ao pin e use a categoria
   **Objetivo de siege**.
3. Use o ícone de lixeira e confirme para remover o pin selecionado.
   Use o ícone **×** ou **Esc** para cancelar a ferramenta ativa.

As mudanças são salvas ao concluir cada edição. Use **Restaurar marcações
padrão** para recuperar P1–P12 no preset atual. Confirme para substituir
as edições desses 12 pins e manter as outras marcações.

Use **Ilhas** para enquadrar a área jogável e **Mapa inteiro** para ver toda
a extensão. Role para ampliar e arraste o terreno para deslocar o mapa.
Os anéis usam um símbolo circular com o nome ou código abaixo. Todos os pins usam o
mesmo formato e podem herdar a cor da camada.

## Desenhar no Editor tático

1. No **Editor tático**, escolha o ícone de retângulo, círculo ou seta.
   Arraste no mapa para desenhar. Segure
   **Shift** para fazer um quadrado ou círculo.
2. Clique na forma ou escolha-a na lista. Arraste a forma para mover ou
   arraste uma das alças para redimensionar. Na seta, arraste as pontas
   para mudar a direção.
3. Ajuste cor, espessura, opacidade, traço e, se quiser, adicione um rótulo.
   Na seta, também dá para ajustar o tamanho da ponta.
4. Use **Duplicar forma** para criar uma cópia ou o ícone de lixeira para
   remover a seleção. Use **Esc** ou **×** para abandonar o gesto.
   **Formas táticas** controla a camada. **Forma visível** controla apenas a
   seleção atual.

Presets novos começam sem desenhos. O editor salva as mudanças ao concluir
cada edição. As formas aparecem no minimapa e no mapa aberto com M quando
a camada e o **Overlay de Reshanta** estão ativos.

Ao hospedar pelo **Live Sync**, use **Ferramentas rápidas** para editar o
mesmo mapa. Clique em **Publicar alterações** para enviar o plano ao grupo.
[Guia ilustrado do Live Sync](../website/live-sync.md).

## Personalizar nomes dos anéis

No **Editor tático**, selecione um anel no mapa ou na lista de marcações.
Digite o **Nome personalizado** e confirme com **Enter**. Use
**Restaurar nome original** para voltar ao código do anel.

O nome faz parte do preset. Ao exportar um JSON ou publicar pelo **Live Sync**,
o nome segue junto com as marcações. Para exibir o anel, o aplicativo precisa
de sua posição no catálogo ou em uma calibração do preset.

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
pins e formas do preset ativo. A aba **Camadas e presets** controla as categorias
e a aparência do preset. O modo de mapa com referência fixa usa somente
a referência importada. O modo automático acompanha a região exibida no jogo.

## Compartilhar marcações

Clique em **Exportar marcações (.json)** para salvar o preset ativo. Em
outra instalação, use **Importar marcações (.json)** e escolha **Importar
como novo** ou **Substituir preset atual**. A segunda opção mantém o nome
do preset ativo e aplica todas as marcações e opções do arquivo. A exportação
e a importação funcionam offline.

O [esquema de marcações](../schemas/siege-preset.schema.json) descreve os
campos aceitos. As exportações atuais usam `schema_version` igual a `3`,
`map_id` igual a `lower-reshanta` e `map_frame` igual a `Abyss_Reshanta_A`.
A lista `markers` contém todos os pins existentes no preset, inclusive os
ocultos. Um pin removido permanece ausente. Ao migrar um preset da versão 1,
o app incorpora os objetivos que aquela versão desenhava separadamente e
preserva os pins personalizados e as camadas existentes. A versão 2
mantém os pins como estavam e começa com a lista de formas vazia.

- Cada pin tem um `id` único dentro do preset, um `name` editável e uma
  `position` com `x` e `y` numéricos de 0 a 1. A origem das coordenadas
  fica no canto superior esquerdo. Mantenha o ID ao editar ou compartilhar
  novas revisões do mesmo pin.
- Os pins padrão usam IDs `objective-p1` a `objective-p12`. Pins criados
  no editor recebem um ID começando com `local-`. `origin` registra se
  o pin veio do modelo padrão ou foi criado pelo usuário.
- `color` usa `#RRGGBB` ou `null` para herdar a cor da camada. `scale`
  multiplica o tamanho por um valor de 0,65 a 1,8 e `visible` indica se o
  pin está habilitado.
- `category` aceita até 32 caracteres. `siege-objective` usa a camada
  `SiegeObjectives`. As outras categorias usam `CustomMarkers`.
- Cada entrada em `drawings` tem ID, tipo e coordenadas normalizadas
  `start` e `end`. Esses pontos representam cantos opostos ou as
  extremidades da seta. O JSON também guarda a cor, a largura do traço,
  a opacidade, o estilo, o tamanho da ponta, o rótulo e a visibilidade.
- `layers`, `colors`, `marker_scale`, `aliases` e `use_local_calibration`
  guardam as preferências de visualização, os apelidos e o uso de calibração
  local. Quando habilitadas, as calibrações manuais dos anéis são
  exportadas em `calibrated_rings` e aplicadas ao preset importado.
  A base do mapa, o catálogo de origem dos anéis e os locais de pets
  têm arquivos próprios.

## Configurar anéis e camadas

Em **Camadas e presets**, use **Novo preset** para começar com P1–P12
ou **Duplicar preset** para continuar a partir de uma cópia do plano atual.
Você também pode ajustar cores, tamanho, camadas e apelidos dos anéis.

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
