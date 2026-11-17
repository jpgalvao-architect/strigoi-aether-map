# Flight Rings na beta.19

## Causa confirmada

A captura do caller na beta.17 mostrava 12 objetivos e 0/49 anéis
posicionados, com campos de coordenadas e fonte vazios. A cópia do
catálogo empacotado na beta.18 confirmou os 49 registros sem posição.
O perfil de referência exibia 49/49 porque carregava o arquivo
`siege-ring-catalogue.json` do perfil. O mapa e os objetivos tinham
outra origem e carregavam nas duas instalações.

O Live Sync enviava o preset e as calibrações incluídas no preset.
Quando o caller usava posições do catálogo local, a estratégia podia
omiti-las. O jogador tentava resolver os IDs com seu próprio catálogo.

## Correção

- [Catálogo base](../app/data/siege-ring-base.json) e
  [manifesto cartográfico](../data-sources/siege-reshanta.json) registram
  os 49 IDs estáveis, os códigos e a revisão `lower-reshanta-positions-1`.
  Os pares X/Y coincidem com o perfil de referência e com a cópia de
  trabalho. A documentação da conversão de Y foi corrigida.
- [Serviço do Siege](../app/modules/siege/service.py) carrega a base do
  pacote e combina catálogos locais pelo ID. Um registro pendente não
  substitui uma posição verificada. Os presets, nomes e calibrações
  existentes são preservados. Calibrações antigas com IDs pendentes
  continuam disponíveis sem atribuição automática a outro anel.
- [Esquema dos presets](../schemas/siege-preset.schema.json) e
  [Live Sync](../backend/live-sync/README.md) enviam o catálogo efetivo,
  com revisão e hash, junto de pins, formas e nomes. O jogador renderiza
  o catálogo da estratégia sem gravá-lo no perfil. O importador informa
  quando um JSON antigo ainda depende de dados locais.
- [Teste de instalação limpa](../scripts/check-clean-installer.ps1)
  verifica se o executável instalado carrega 49 posições da base, com
  origem e revisão registradas no diagnóstico.

O backup `siege-command.pre-catalogue.json` é criado antes da migração
de um perfil antigo ou da primeira persistência de um preset que inclui
um catálogo publicado. Para suporte, use **Siege Command → Catálogo de
anéis → Copiar diagnóstico do catálogo**. O relatório inclui versões,
origem, contagens, ajustes ativos e indicadores de erro. Ele omite
caminhos locais, nomes de presets pessoais, convites e segredos.

## Atualização

Atualize o caller e os jogadores para a beta.19. Callers que já hospedam
precisam atualizar o Worker na própria conta com
[`backend/live-sync`](../backend/live-sync), mantendo a vinculação.
A publicação continua a partir do botão **Publicar alterações**.

A verificação dos 49 pontos é cartográfica. A altitude e a conferência de
cada anel no servidor SA ficam pendentes. As coordenadas normalizadas
têm origem no Aion2t. A distribuição foi autorizada pelo mantenedor do
Azphelumbra. Os termos da fonte condicionam a redistribuição à permissão.
[Mapa de referência](https://aion2t.com/map?zone=2616&types=flight_ring) ·
[Termos da fonte](https://aion2t.com/terms).
