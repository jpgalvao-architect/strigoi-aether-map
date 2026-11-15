# Siege Command

O Siege Command reúne o mapa de Chaotic Lower Reshanta, o catálogo de anéis e
o estado da call. A aba usa o mesmo mapa do Atlas para Coletas e Pets. A call
fica neste computador e **Copiar call** envia texto para a área de transferência.

## Preparar e usar

1. Com o PNG local pronto, escolha **Importar mapa local**. O aplicativo
   confere a identidade dos pixels no quadro de 4096 × 4096 antes de aceitar.
2. Em **Catálogo de anéis**, escolha **Importar catálogo local** e abra um
   [catálogo compatível](../schemas/siege-ring-catalogue.schema.json) com o
   quadro `Abyss_Reshanta_A/4096-north-up`. Os downloads públicos incluem a
   lista de pendências por zona. O mapa e as posições individuais de anéis
   são importados à parte.
3. Em **Call tática**, escolha MID, BOT ou TOP. Selecione um objetivo no
   mapa ou no seletor. Escolha um anel numerado e a ação desejada. O mapa
   destaca os alvos e **Copiar call** copia, por exemplo,
   `REAGRUPAR B3 → ATACAR P7`.
4. Em **Overlay de siege**, clique em **Ativar no mapa e minimapa**. O app
   seleciona Lower Reshanta no overlay de mapas. Se for a primeira vez,
   selecione a área do terreno do minimapa no jogo.
5. Os marcadores do preset aparecem quando o terreno de Lower Reshanta é
   reconhecido. Use **M** normalmente para abrir o mapa do jogo e ver os
   desenhos sobre ele. Ao fechá-lo, os marcadores retornam ao minimapa.
   Refaça a seleção se o minimapa mudar de área na interface do jogo.
6. Se quiser o HUD compacto de calls, habilite-o, ajuste escala e opacidade e
   arraste pelo título. Use **Clique através do HUD** depois de posicioná-lo.
   Alt+Tab e menus reconhecidos ocultam o HUD.

**Ilhas** reenquadra a área jogável. **Mapa inteiro** mostra o quadro cartográfico
completo. Role para ampliar e arraste para deslocar. Os anéis usam o mesmo
símbolo circular com código abaixo; os demais pontos usam pins. Quando falta
espaço para os códigos, os objetivos e os anéis de siege têm preferência.
Os símbolos permanecem ancorados nas coordenadas.

## Personalizar

Duplique **Siege Global v1** em **Camadas e presets** para ajustar cor,
tamanho, alias, camadas e marcadores. O preset oficial mostra objetivos, anéis
de siege e anéis de trânsito com posição disponível. O callsign continua
visível quando você acrescenta um alias. **Restaurar Global** volta às cores e posições
do preset de referência. O JSON exportado inclui opções do preset, aliases
e marcadores locais. A instalação que importa o preset precisa do catálogo
com os mesmos IDs. As posições do catálogo e os registros administrativos
de calibração ficam em arquivos separados.

Para calibrar um anel, abra **Catálogo de anéis**, escolha o registro, clique
em **Posicionar no mapa** e selecione a posição conferida. Ajuste X e Y se
necessário e registre a fonte. Marque a posição como conferida apenas depois
da revisão. Salve e habilite **Aplicar calibrações locais** no preset
personalizado. Use **Restaurar posição do anel** para remover o ajuste local.

Um anel pendente fica no catálogo sem marcador. Um ponto provisório fica
pontilhado e indisponível na call. **Fixar novos callsigns** numera os anéis
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
  é da NCSOFT. A prévia pessoal carrega a imagem em uma pasta local.
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

`SiegeService` mantém presets, ajustes de anéis e HUD em
`siege-command.json`. O mapa e o catálogo local ficam em arquivos separados.
O serviço publica `call_changed` com um estado imutável para uso por outros
componentes. As camadas do preset alimentam a janela transparente de mapas
do Azphelumbra. O reconhecimento visual alterna entre o minimapa e o mapa
grande e recalcula a projeção conforme o terreno muda de posição ou zoom.
Uma mudança de resolução ou DPI recalcula a área de captura a partir da seleção
salva. A aba Siege Command continua disponível para planejamento e presets.
