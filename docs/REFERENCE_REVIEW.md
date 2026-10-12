# Estudo do projeto de referência

Consulta: 11 de outubro de 2026. Projeto:
[problem-xyz/aion2-map-overlay](https://github.com/problem-xyz/aion2-map-overlay).
Snapshot: `a23dc90849fd18b1ef4fba01d2f1bb0f851bdcbd`.

## O que significa SA nesse projeto

O arquivo
[schedule.json](https://github.com/problem-xyz/aion2-map-overlay/blob/a23dc90849fd18b1ef4fba01d2f1bb0f851bdcbd/assets/timers/schedule.json)
define `global-sa`, com o fuso `America/Sao_Paulo`, no grupo `global`.
Cada regra pode especificar seu próprio fuso. Quando especifica `UTC`, escolher
SA converte o horário para exibição; quando não especifica fuso, usa o relógio
da região. Portanto, SA não é uma segunda versão da geografia dos mapas.

No perfil publicado pelo autor, o cerco começa às 21h UTC, equivalente a 18h
em SA, e os resets usam 09h do relógio regional. Esses valores diferem das
fontes da versão 0.2.1 do Strigoi. O app oferece os dois perfis separadamente,
com suas fontes identificadas. Não combina regras divergentes nem apresenta
o perfil do autor como confirmação da NCSOFT. A seleção inicial atende ao
pedido do usuário: **SA • agenda do projeto de referência**.

Os conjuntos de pontos estão em
[assets/object-sets](https://github.com/problem-xyz/aion2-map-overlay/tree/a23dc90849fd18b1ef4fba01d2f1bb0f851bdcbd/assets/object-sets).
São dois conjuntos compartilhados, Altgard e Verteron, sem separação por SA.
O README e o NOTICE atribuem os pontos de coleta ao serviço público de
tc-imba, consultado em 2 de outubro de 2026. A existência de um perfil SA
não comprova que cada ponto tenha sido validado no servidor sul-americano.

## Comportamentos estudados e adaptação

| Comportamento observado | Adaptação no Strigoi |
|---|---|
| Selecionar um retângulo sobre a tela | Janela própria de seleção; arrastar e soltar confirma, Esc cancela |
| Usar o mapa incluído como referência | Reconhecimento da imagem WebP incluída, sem screenshot manual |
| Acompanhar pan e zoom | Correspondências SIFT e transformação de escala/translação a cada frame |
| Ocultar a rota quando perde o mapa | Ocultação na primeira falha; duas observações para reaparecer |
| Selecionar região dos eventos | Perfis SA, NA, Europa, Ásia, KR e TW, com regras de fuso explícitas |
| Painel de eventos sobre outras janelas | Painel opcional, movível pelo cabeçalho, com os próximos três eventos |
| Exibir recursos de coleta | 5.425 posições licenciadas incorporadas, com filtros por recurso |

Foram examinados os módulos `qt/region_selector.py`, `vision/features.py`,
`vision/tracker.py`, `timers/data.py` e `timers/schedule.py`, além dos arquivos
de agenda e de dados. O código do Strigoi foi implementado separadamente com
Qt, MSS e operações públicas do OpenCV. Não foi importado código desses
módulos nem dependência do aplicativo de referência.

## Decisões de implementação

O Strigoi usa uma transformação de similaridade: escala uniforme, translação
e pequena tolerância de rotação. Rejeita evidência insuficiente ou concentrada
em uma região pequena. Procura novamente o mapa em cada observação; uma
transformação anterior não permanece válida depois que o mapa desaparece.

A seleção representa a área visível do mapa, que pode conter apenas um
recorte da imagem completa. Os marcadores fora dela são cortados. Se a janela
do jogo mudar de posição ou de monitor, a área deve ser selecionada novamente.
Alterações de resolução/DPI também exigem nova seleção.

O worker lê somente a área selecionada. Frames ficam na memória, e a
persistência guarda limites, monitor, escala e mapa escolhido. Uma máscara
das posições desenhadas reduz a influência dos próprios marcadores na
observação seguinte. O overlay não depende de observar a tecla M.

Na 0.5.0, os 2.811 locais possíveis de aparecimento passam à camada principal.
Os 226 registros antigos KR/TW são mantidos separadamente, inicialmente
desligados, para preservar IDs e visitas. O ajuste aproximado de Basfelt
da 0.4.2 foi retirado. Os candidatos não representam ocupação simultânea
nem foram individualmente validados em SA. Consulte
[a revisão da base](COORDINATE_CORRECTION.md).

## Licença e evidência

A [licença do aplicativo](https://github.com/problem-xyz/aion2-map-overlay/blob/a23dc90849fd18b1ef4fba01d2f1bb0f851bdcbd/LICENSE)
permite estudar o código, mas restringe sua redistribuição e adaptação.
O trabalho aqui usa uma implementação própria. Os mapas e conjuntos de
objetos têm termos separados, CC BY-NC 4.0, documentados no
[NOTICE](https://github.com/problem-xyz/aion2-map-overlay/blob/a23dc90849fd18b1ef4fba01d2f1bb0f851bdcbd/NOTICE).
Esse aviso acompanha a distribuição, com atribuição e descrição das alterações.

Os testes cobrem imagens reais dos mapas, transformações controladas e
captura nativa de uma janela de teste própria. O cliente AION 2 não foi
acessado. HDR, estilos diferentes de mapa, fullscreen exclusivo e grande
oclusão podem impedir o reconhecimento. Consulte [a validação](VALIDATION.md).
