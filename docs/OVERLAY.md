# Overlay de mapas

O Azphelumbra reconhece a região pelo terreno capturado e projeta os
marcadores sobre o mapa original do AION 2. O reconhecimento usa as
referências raster disponíveis no Atlas, incluindo Altgard, Verteron e
Lower Reshanta quando a base da região está instalada.

## Configurar e usar

1. Em **Overlay**, escolha o monitor do jogo e mantenha **Minimapa + mapa
   grande automático**. Use o minimapa retangular com o norte fixo.
2. Clique em **Selecionar minimapa** e demarque apenas o terreno, sem a
   barra de título ou a lista de missões. O recorte é salvo para reutilizar
   em todas as regiões nesse monitor.
3. Use **Camadas do Atlas** para escolher os recursos e ative o overlay.
   A linha **Detecção** mostra o mapa reconhecido.
4. Abra o mapa grande com **M**. O overlay acompanha a região exibida
   nessa tela. A região física do personagem vem do minimapa e é mantida
   ao consultar outro mapa. Ao fechar o mapa grande, os marcadores voltam
   ao minimapa assim que o terreno for reconhecido.

Quem usa apenas o mapa completo pode selecionar **Mapa grande • monitor
inteiro** e ativar o overlay sem demarcar um recorte.

Na falta de evidência suficiente, o aplicativo mostra **Mapa não identificado**
e oculta os marcadores de mapa enquanto continua buscando referências.
Em **Ajustes avançados → Mapa de fallback**, você pode priorizar um mapa na
busca. Ele ainda precisa corresponder ao terreno antes de exibir pontos.
**Usar referência fixa de uma imagem** continua disponível para calibrar
manualmente uma vista de posição e zoom fixos. Escolha o mapa no ajuste de
fallback antes de abrir a calibração caso nenhuma região esteja reconhecida.

Os controles de camadas e o toggle **Reshanta / Siege** permanecem ativos
durante as viagens. Objetivos, anéis e pins táticos aparecem enquanto estiver
visível um mapa reconhecido de Lower Reshanta e a camada tática estiver ligada.

## Resolução e escala

O seletor de monitor agora mostra **pixels físicos** e a escala do Windows.
Em uma tela 3840 × 2160 a 150%, a interface usa 2560 × 1440 unidades lógicas;
a captura continua usando 3840 × 2160 pixels. O rótulo anterior mostrava a
dimensão lógica sem explicar a diferença. A área selecionada também informa
o tamanho físico da captura, inclusive o arredondamento dos limites.

A 0.5.0 retira o ajuste aproximado de Basfelt e incorpora a camada de
posições possíveis. Os registros antigos ficam separados para preservar
visitas. Veja [a revisão da base](COORDINATE_CORRECTION.md).

## Frequência e ajustes

Os símbolos do minimapa têm tamanho 2× maior a partir da beta 6. O controle
**Tamanho dos ícones** continua disponível; o fator do minimapa se aplica
ao valor escolhido. O mapa grande mantém o tamanho anterior. A projeção dos
pontos não muda com o tamanho do desenho, inclusive em monitores com DPI
diferente.

Os cubos com indicação de altura na fonte recebem **↑** ou **↓**, no Atlas,
no minimapa e no mapa grande. A seta significa acima ou abaixo da altura
mediana do grupo de locais da fonte. Ela não compara com o personagem.
Registros sem esse dado ou com coordenadas editadas ficam sem seta.
A máscara do reconhecimento exclui também os novos símbolos e as setas,
para que os próprios desenhos não sejam usados como evidência do terreno.

**Frequência visual** tem meta de 240 Hz por padrão, com opções de 60 e 120 Hz.
O contador mede chamadas reais de desenho da janela; ele não mede a quantidade
de quadros distintos que o monitor ou o compositor do Windows apresentam.
Sem pontos visíveis no recorte, não há redesenho de ícones e o contador pode
ficar em zero mesmo com o terreno reconhecido.

A leitura e o reconhecimento são separados do desenho: o minimapa permite
limite de 10 a 60 leituras/s, e o mapa grande tem teto de 30. Um recorte do cabeçalho ajuda a procurar
a abertura do mapa grande sem analisar o monitor inteiro a cada quadro.
A região ativa é verificada novamente a intervalos. Entre as
verificações, o deslocamento visual é acompanhado por fluxo óptico. Uma interpolação curta de 12 ms suaviza as
transformações observadas, sem prever posições futuras. A interface informa
as duas taxas separadamente. A meta de 240 Hz não significa 240 detecções/s.

No teste nativo local com o recorte enviado pelo usuário, a janela desenhou
cerca de 240 vezes/s no minimapa e rastreou o terreno cerca de 33 vezes/s.
No mapa grande do mesmo teste, foram medidos 238 redesenhos/s e 11 leituras/s. Hardware, carga,
quantidade de pontos, resolução e captura do jogo podem reduzir essas taxas.
Se houver custo elevado, escolha 120 ou 60 Hz.

**Detalhes mínimos** exige entre 12 e 80 correspondências consistentes;
o padrão é 18. Aumentar o valor exige evidência mais forte; diminuir pode
ajudar em recortes pequenos, mas reduz a exigência do reconhecimento.
**Opacidade** e **Tamanho dos ícones** alteram a apresentação. Os filtros
persistentes de categorias, recursos e visitas continuam valendo.

**Mostrar painel flutuante dos próximos eventos** abre um painel independente
da captura. Arraste o cabeçalho para movê-lo ou use × para fechá-lo. Ele segue
o perfil escolhido no Event Tracker e exige o aplicativo aberto.

## Reconhecimento e recuperação

SIFT e uma transformação de similaridade comparam o terreno capturado
com as referências cartográficas. A detecção reutiliza o mapa ativo
enquanto há evidência visual. Após perder o terreno, procura as outras
referências uma por vez. Uma região nova só é aceita após duas verificações
cartográficas independentes. O minimapa refina a correspondência pela
referência de maior resolução. Com falha de observação, os marcadores são
ocultados até a recuperação. Um movimento visual ainda coerente pode
cobrir uma falha breve na revalidação do minimapa por até 250 ms depois
do intervalo normal de verificação.

Os próprios ícones são mascarados para reduzir a interferência na leitura.
A janela é externa, transparente e deixa os cliques passarem. O
reconhecimento lê pixels enquanto o jogo está em primeiro plano e usa
o mesmo contexto visual que oculta o overlay em menus. Os recortes do
monitor e as preferências são salvos. A região detectada só vale na sessão.

## Mapa reconhecido sem pontos

O status informa quando a camada escolhida não tem pontos no recorte. Isso
é diferente de **Mapa não identificado**. No exemplo de Battlescar Mound
enviado pelo usuário, a base contém cinco pontos de outras categorias e
nenhum cubo naquele recorte. Para testar nessa região, habilite recursos de coleta em **Camadas do Atlas**;
visitas e exclusões salvas continuam valendo. A seleção de categorias vale
para Atlas, minimapa e mapa grande, sem um filtro adicional de somente cubos.

## Limites e sonar

Minimapas circulares ou rotativos, HDR, mudanças no terreno, fullscreen
exclusivo e oclusão podem impedir o reconhecimento.

O **Sonar** é ativado separadamente, pela análise do áudio do aplicativo
escolhido. Os marcadores do overlay continuam vindo do Atlas; não são
posições inferidas pelo som. Consulte [funcionamento e limites](SONAR.md). Os dados comunitários não confirmam que cada
objeto esteja presente no servidor. Veja [fontes e perfil SA](SOURCES.md)
e [validação](VALIDATION.md).

## Interface da 0.6.0

Precisão, taxas de captura/desenho e referência fixa estão em Ajustes avançados.
Eventos ou Overlay permitem ativar o painel flutuante, que tem vista compacta
do próximo evento e vista expandida da agenda do dia. Posição e expansão
persistem; a vista do dia usa o fuso das Configurações, com horários anteriores
mais discretos e rolagem para os próximos. Os cubos usam símbolo próprio,
compacto no minimapa para preservar detalhes do terreno.

## Camadas e evento escolhido • 0.7.0

O menu Camadas do Atlas edita as mesmas exclusões de categorias usadas pelo
Atlas. As alterações atualizam os dois modos do overlay em execução.
Recursos desabilitados e visitas ocultas continuam excluídos. Busca e raridade
são filtros temporários da página e não alteram as camadas do jogo.

Eventos e o próprio painel permitem escolher um evento específico. A escolha
persiste e filtra tanto a vista compacta quanto os horários do dia. Se esse
evento não existir numa agenda importada, o painel informa indisponibilidade
até a pessoa escolher outro evento ou voltar ao modo automático.

O painel de eventos tem cabeçalho curto e linhas compactas inspiradas na
organização da HUD do jogo. O ícone de calendário no cabeçalho abre a escolha
do evento; a seta expande ou recolhe a lista. Cores e fonte permanecem próprias.

## Visibilidade automática — beta 7

Todos os overlays se ocultam quando o AION 2 deixa de ser a janela ativa,
incluindo Alt+Tab, minimização e seleção da janela principal do Strigoi.
Ao voltar ao jogo, os painéis habilitados reaparecem conforme o contexto:
o combate continua condicionado à entrada em uma instância reconhecida.
Ocultar não desliga o Sonar nem a medição de combate e não altera as
preferências. Avisos do Sonar recebidos enquanto ocultos não são reapresentados.

Menus reconhecidos ocultam os painéis. No mapa grande, somente os marcadores
permanecem disponíveis. A partir da beta 8, o reconhecimento exige títulos
conhecidos em inglês/português, por OCR local do
Windows. A análise recebe apenas um recorte superior da janela ativa do
jogo, em memória, sem salvar imagens ou texto. Funciona independentemente
do overlay de mapas estar ativado. A janela ativa é conferida a cada 100 ms;
menus são verificados em segundo plano e podem levar cerca de um segundo
ou mais para serem reconhecidos, conforme o computador.

Nem todo menu, idioma ou disposição de interface foi validado. Se o OCR
do Windows estiver indisponível, a ocultação ao sair do jogo continua
funcionando, mas a identificação visual de menus fica indisponível.
Um desenho parecido com “X” não é suficiente para ocultar os overlays:
essa geometria também aparece na HUD e no cenário durante o jogo.
O app não intercepta teclas nem injeta código.

Ao usar **Testar aviso visual** fora do jogo, a prévia abre dentro de um
diálogo normal do aplicativo. Ela não captura áudio nem cria um overlay
permanente sobre outras janelas.
