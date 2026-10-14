# Overlay dinâmico • 0.7.0

O mapa grande usa automaticamente o monitor escolhido. O minimapa usa uma
seleção própria do terreno no canto superior direito. Nenhum modo exige
que você tire screenshots ou mova arquivos. Ativar o minimapa também mantém a busca do mapa grande no mesmo monitor.
Ambos leem pixels da tela para reconhecer o terreno; as imagens ficam na memória e a captura permanece
desligada a cada abertura do aplicativo.

## Usar o mapa grande

1. Abra o mapa do jogo com **M**, ocupando a tela do monitor escolhido.
2. Em **Overlay**, escolha **Mapa grande • monitor inteiro**,
   **Altgard** ou **Verteron**, e o monitor.
3. Em **Camadas do Atlas**, habilite as categorias desejadas. Elas também
   podem ser escolhidas no Atlas e combinadas, por exemplo ervas e cubos.
4. Clique em **Ativar overlay**. O Strigoi minimiza a própria janela,
   prepara o reconhecimento e mostra os pontos após duas observações válidas.
5. Ao fechar o mapa ou perder a referência, os pontos são ocultados. Ao
   reabrir o mapa e reconhecê-lo novamente, os pontos retornam.

Não é preciso destacar uma área nesse modo. O app verifica a imagem da tela;
ele não observa a tecla M. Prefira janela sem bordas; fullscreen exclusivo
pode impedir a captura.

## Usar o minimapa

1. Mantenha visível o minimapa **retangular, com norte fixo**.
2. Escolha **Minimapa + mapa grande automático**, o mapa e o monitor.
3. Clique em **Selecionar minimapa**. A janela do Strigoi desaparece
   temporariamente. Arraste um retângulo somente sobre o terreno do minimapa
   no canto superior direito, sem a barra de título e as missões abaixo.
4. Solte o mouse para salvar os limites; Esc cancela. Clique em Ativar overlay.
5. O reconhecimento projeta apenas os pontos dentro do recorte e acompanha
   o deslocamento do terreno. Ao abrir o mapa grande com M, ele tem prioridade;
   ao fechar, o overlay retorna ao minimapa. Não é preciso trocar o modo.
   As seleções do mapa grande e minimapa são separadas.

Refaça a seleção se o minimapa mudar de posição/tamanho, monitor ou DPI.
Escolha uma área de terreno com detalhes suficientes. A seleção precisa
ficar dentro de um único monitor. Para parar a captura, retorne ao Strigoi
e clique em **Desligar overlay**.

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
limite de 10 a 60 leituras/s, e o mapa grande tem teto de 30. Enquanto usa o minimapa, o monitor inteiro é consultado a cada 0,5 segundo
para procurar o mapa grande. O mapa ativo é revalidado a cada 0,5 segundo; entre verificações, o deslocamento visual é
acompanhado por fluxo óptico. Uma interpolação curta de 12 ms suaviza as
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

SIFT e uma transformação robusta comparam o terreno capturado com o mapa
raster incluído no app. O minimapa usa uma referência mais detalhada e
refinamento local na resolução original do mapa. Na revalidação, a última
transformação observada limita a região pesquisada, mas são exigidas novas
correspondências de terreno: uma referência antiga nunca mantém os pontos
visíveis se a verificação falhar. A evidência precisa estar distribuída no terreno, com
correspondências suficientes, escala plausível e norte fixo.

O fluxo óptico acompanha somente detalhes previamente reconhecidos. A
primeira falha oculta os pontos; duas observações válidas permitem mostrá-los
novamente. Um watchdog oculta a janela após 1,5 segundo sem retorno, depois
que a observação começou. As posições dos próprios ícones são mascaradas na
leitura para reduzir a interferência do overlay no reconhecimento.

A janela é externa, transparente e deixa os cliques passarem. Não altera
arquivos ou processos do jogo, observa teclas, deduz a posição do personagem
ou envia comandos. O modo dinâmico salva apenas um JSON com mapa, monitor,
DPI e limites. **Usar imagem já existente** preserva a calibração fixa das
versões anteriores, com posição e zoom fixos.

## Mapa reconhecido sem pontos

O status informa quando a camada escolhida não tem pontos no recorte. Isso
é diferente de **Mapa não reconhecido**. No exemplo de Battlescar Mound
enviado pelo usuário, a base contém cinco pontos de outras categorias e
nenhum cubo naquele recorte. Para testar nessa região, habilite recursos de coleta em **Camadas do Atlas**;
visitas e exclusões salvas continuam valendo. A seleção de categorias vale
para Atlas, minimapa e mapa grande, sem um filtro adicional de somente cubos.

## Limites e sonar

O usuário confirmou pontos no mapa grande da 0.3.0. O novo minimapa foi
testado com o recorte enviado e captura nativa de uma janela própria; ainda
precisa de teste dentro do cliente AION 2. Minimapas circulares ou rotativos,
HDR, mudanças importantes no terreno, fullscreen exclusivo e oclusão podem
impedir o reconhecimento. Uma imagem do mesmo mapa também pode ser detectada:
o detector verifica os pixels, não o processo do jogo.

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
permanecem disponíveis. O reconhecimento usa o botão de fechar dos menus
em tela cheia e títulos conhecidos em inglês/português, por OCR local do
Windows. A análise recebe apenas um recorte superior da janela ativa do
jogo, em memória, sem salvar imagens ou texto. Funciona independentemente
do overlay de mapas estar ativado. A janela ativa é conferida a cada 100 ms;
menus são verificados em segundo plano e podem levar cerca de um segundo
ou mais para serem reconhecidos, conforme o computador.

Nem todo menu, idioma ou disposição de interface foi validado. Se o OCR
do Windows estiver indisponível, a ocultação ao sair do jogo continua
funcionando, e a identificação visual fica limitada ao botão de fechar
dos menus em tela cheia. O app não intercepta teclas nem injeta código.

Ao usar **Testar aviso visual** fora do jogo, a prévia abre dentro de um
diálogo normal do aplicativo. Ela não captura áudio nem cria um overlay
permanente sobre outras janelas.
