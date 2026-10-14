# Validação da entrega

Data: 12/10/2026. Ambiente de execução: Windows 11 x64, Python 3.12.10, PySide6 6.12.0, Pydantic 2.14.0, OpenCV 5.0.0.93, MSS 10.2.0, pytest 9.1.1, PyInstaller 6.22.3. Consulte `requirements-lock.txt` para as dependências transitivas.

## Testes automatizados

**103 testes passaram**, cobrindo:

- Integridade da base principal: 2 fundos reais WebP com pontos comunitários, 21 recursos catalogados mais vestígios e duas camadas de cubos, 9.582 coordenadas armazenadas (9.356 ativas por padrão), sete eventos no perfil SA inicial e agenda anterior disponível. Comparação de cada coordenada com o snapshot e dos arquivos com seus hashes.
- Referência de inspiração preservada no código-fonte e novos assets renderizáveis; migração com backup e preservação de dados customizados; relógio LATAM e resets UTC; captura condicionada à ativação explícita na sessão, com monitor automático no mapa grande e seleção própria no minimapa.
- Fixture demonstrativa antiga preservada para testar filtros e contratos.
- Rejeição de coordenadas fora de faixa, IDs duplicados, mapas ausentes, recursos inexistentes e relações categoria/subcategoria inválidas.
- Combinação de filtros, busca, raridade, cubos, exclusões, visibilidade de overlay e visitas.
- Recorrência diária/semanal/única, conversão de timezone, virada de dia, saltos e ambiguidades de horário de verão.
- Rejeição de timezone/horários/dias inválidos e timestamp sem offset para evento único.
- Countdown, alertas por preferência, tolerância limitada e deduplicação após reinício.
- Persistência, recuperação de JSON corrompido e preservação de cache em falha de provider.
- Recusa de URL não HTTPS/credenciais embutidas e de travessia de diretório em assets.
- Detector visual sobre imagens sintéticas: duas referências, perda de referência, tela uniforme, resolução alterada e projeção do viewport.
- Sonar começa desligado, reconhece referência baixa em ruído sintético, rejeita controles e libera worker ao parar; heartbeat vazio não apaga consenso.
- Navegação das dez áreas, clique em categoria, marcação de visita, busca vazia, zoom e preferências compartilhadas/recarregadas.
- Consentimento de captura resetado ao iniciar, importação inválida sem substituir a base e cópia de imagem externa válida para a base local.
- Ocultação do overlay diante de detecção negativa e watchdog sem retorno.

A versão 0.2.1 acrescenta verificações das imagens WebP e seus hashes, seleção inicial de Altgard em todas as listas de mapa, preservação de escolhas posteriores e migração das coordenadas da 0.2.0 sem perda de visitas.

## Validação do reconhecimento dinâmico

Os testes reconhecem recortes, pan e zoom de Altgard e rejeitam uma imagem
de Verteron, tela uniforme e imagem aleatória. Verificam seleção por mouse,
cancelamento com Esc, persistência somente dos limites, conversão de DPI
com origem negativa, ocultação na primeira falha e regras de fuso do perfil SA.

Uma janela nativa própria exibiu o mapa real em dois enquadramentos. MSS
capturou somente a região opaca dessa janela. O reconhecimento encontrou
1.096 e 933 correspondências consistentes; levou aproximadamente 110 e
109 ms, com erro de alinhamento de 0,24 e 0,15 pixel, respectivamente.
Esses valores são duas medições locais; não representam latência garantida,
uma matriz completa de monitores ou teste dentro do AION 2.

O worker real MSS/Qt também foi exercitado sobre essa janela própria: o
overlay apareceu após duas detecções, acompanhou pan/zoom com 874 detalhes
consistentes e ficou oculto quando a janela de teste exibiu uma área preta.
A captura terminou normalmente ao desligar o serviço. O painel de eventos
também foi testado para permanecer fechado após o encerramento do app.

## Minimapa e frequência da 0.4.0

Sete testes adicionais cobrem o recorte real do minimapa retangular enviado
pelo usuário, rejeição de tela uniforme/aleatória, deslocamento visual e
ocultação ao perder a referência, deadlines de 240 Hz sem rajadas, interpolação
limitada e limpeza, área automática do monitor inteiro e seleção independente
do minimapa. Somente o recorte do terreno de 332 × 214 pixels é incluído como
fixture; o screenshot completo com chat e nomes não foi incorporado.

O reconhecimento offline encontrou 25 correspondências consistentes nesse
recorte, com evidência distribuída. A imagem completa do mapa grande enviada
pelo usuário (2559 × 1438) também foi reconhecida sem recorte, com 35
correspondências consistentes e confiança calculada de 85,4%. No pipeline nativo, MSS capturou somente
a região opaca de uma janela própria exibindo o mesmo recorte. Um marcador
exclusivo do teste foi colocado dentro do recorte para medir o desenho, sem
afirmar a existência de um cubo nesse local. A janela mediu aproximadamente
239,9–240,2 chamadas de desenho/s e 50–52 observações/s no teste inicial,
com meta 240 Hz e limite de leitura 60 Hz. O overlay foi ocultado ao mostrar
uma área preta, e a solicitação de precisão do timer foi liberada ao desligar.

Essas medições são locais, com poucos pontos e monitor reportando 240 Hz;
não garantem 240 quadros distintos apresentados nem a mesma taxa no jogo.
A interface informa o desenho e o rastreamento separadamente. O usuário
confirmou os pontos da versão anterior no mapa grande; não houve validação
do novo minimapa dentro do jogo pelo agente.

## Correção do minimapa e troca automática • 0.4.1

O novo recorte de Battlescar Mound (330 × 220), com cone de visão e quest,
reproduziu a falha da 0.4.0. A referência reduzida tinha poucas correspondências;
o refinamento na resolução original encontrou 46 detalhes consistentes,
mantendo o mínimo final de 18, distribuição espacial e verificações geométricas.
Somente o recorte do minimapa foi incorporado, sem o screenshot completo.

Quatro testes novos cobrem esse recorte, revalidação periódica com os próprios
ícones mascarados, rejeição de imagem aleatória mesmo com indicação prévia,
prioridade do mapa grande, retorno ao minimapa, mudança de geometria/DPI
e confirmação antes de mostrar cada modo. O status distingue camada vazia
de referência não reconhecida.

O worker real capturou somente uma janela própria opaca ocupando o monitor.
A simulação alternou minimapa → mapa grande → minimapa → tela preta. As
quatro etapas passaram, com verificação do alinhamento e ocultação na perda
do terreno. Um marcador exclusivo do teste permitiu medir o desenho sem
afirmar a presença de um cubo. Foram medidos 240,2/240,0 redesenhos/s e
33,9/33,2 leituras/s nas etapas do minimapa; no mapa grande, 237,6 e 11,3.
O monitor reportou 240 Hz. As taxas são locais, dependem da carga e não
garantem quadros apresentados ou resultados dentro do cliente do jogo.

## Revisão da base e densidade • 0.5.0

Os testes comparam todos os 2.811 candidatos com os snapshots licenciados,
conferindo hashes, IDs, grupos, coordenadas x/100 e y/100 e ausência de uma
inversão adicional de Y. Os 226 registros antigos voltam à transformação
original e permanecem em camada separada. Todos os pontos são possíveis;
não há validação individual em SA nem ocupação simultânea garantida.

A migração restaura somente a substituição exata de Basfelt da 0.4.2,
preserva edições próprias, notas de outros pontos, visitas, filtros e agenda
alternativa. Acrescenta candidatos apenas a mapas conhecidos sem alterações,
preserva recursos personalizados e IDs existentes, gera backup e é idempotente.
Reativar a camada histórica é uma escolha persistente. Não há transferência
de visitas por proximidade. O recorte de Basfelt reconhece dois candidatos
distintos: B2-01 a menos de 10 pixels do personagem e B2-02 a mais de 30.
Isso não prova o centro exato do cubo visível nem a identidade do registro antigo.

O rebuild comunitário seguido da extensão reproduziu o dataset byte a byte:
SHA-256 `f945017ed29cab978ef4696145eb6e28ca317d8987c41d300a3c63534c3b9ce4`.
Os arquivos de origem e os fundos dos mapas permanecem intactos.

Na janela própria opaca, com monitor 3840 × 2160 e escala 150%, o candidato
B2-01 apresentou diferença de 1,72 pixel entre projeção calculada e centro
do ícone desenhado; o controle apresentou 1,12 pixel. Houve 87 detalhes
consistentes no recorte. Essa medição comprova o caminho de DPI/desenho,
sem converter o candidato em spawn exato no jogo.

Com todos os 1.371 candidatos de Altgard habilitados, o worker real alternou
minimapa → mapa grande → minimapa → tela preta sobre uma janela de simulação
própria, sem captura do jogo. Foram usados os pontos reais da base, sem
substituir a camada por um marcador de teste. A troca automática, o alinhamento
ao terreno e a ocultação na perda da referência passaram.

| Etapa | Pontos visíveis | Desenhos/s | Observações/s |
|---|---:|---:|---:|
| Minimapa | 15 | 239,8 | 37,2 |
| Mapa grande | 849 | 85,5 | 6,7 |
| Retorno ao minimapa | 15 | 241,9 | 37,5 |

O primeiro ensaio com muitos candidatos revelou custo alto ao unir regiões
de pintura e uma máscara excessiva dos próprios ícones. A pintura foi
vetorizada, os símbolos rasterizados ficam em cache na resolução do monitor
e a máscara dos cubos segue sua silhueta, preservando terreno entre candidatos.
Dois regressores adicionais cobrem projeção/corte em DPI e cache dos símbolos.
Com 849 pontos visíveis, o mapa grande **não atingiu 240 desenhos/s** neste
ensaio. A interface mantém a meta ajustável e informa a taxa efetiva.
Desenho, captura e quadros apresentados pelo monitor são medidas distintas.

## Execução e inspeção visual

O app foi iniciado com a plataforma nativa Qt/Windows, percorreu as oito áreas e encerrou normalmente. Foram renderizadas prévias de Dashboard, Atlas, Gatherables, Hidden Cubes, Events, Settings e Overlay. Dashboard, Atlas, Event Tracker e a nova página de Overlay foram inspecionados visualmente quanto a legibilidade, hierarquia e disposição.

O teste `--smoke-test` registra `SMOKE_OK` apenas depois de construir e percorrer as páginas. O modo `--screenshot` renderiza a própria janela; não captura o desktop nem o jogo. O teste de UI usa a plataforma offscreen e pastas temporárias.

## Executável portátil

O build final PyInstaller foi executado diretamente como `StrigoiAetherMap.exe --smoke-test --screenshot ...`, com base de dados isolada. Resultado: **código de saída 0**, log `SMOKE_OK: all 8 pages rendered` e imagem da janela produzida. A inicialização normal com splash também foi exercitada pelo código-fonte e encerrada normalmente.

Durante a validação de empacotamento, a análise inicial capturou DLLs antigas de outras ferramentas presentes no PATH do ambiente de build. O `.spec` foi corrigido para usar um PATH controlado e o pacote foi reconstruído; a validação acima corresponde ao executável final corrigido. O teste não representa uma máquina limpa sem Python instalado, mas o executável utiliza seu runtime Python/Qt incluído.

Na 0.5.0, o executável também abriu uma base isolada equivalente à 0.4.2,
com visita de Basfelt, filtro, anotação local e agenda alternativa. A substituição
aproximada foi retirada, os 2.811 candidatos foram incorporados e o backup
correspondeu à base anterior. IDs/visitas/filtros/notas/agenda foram preservados;
as visitas não foram transferidas para os candidatos. Saída do executável: 0.
Dados e manifestos do portátil foram comparados byte a byte com o código-fonte,
incluindo a revisão de cubos, os dois mapas, o mascote e os perfis de horários.

## Rodada de UX • 0.6.0

Nove casos adicionais verificam a agenda do dia no fuso de exibição,
inclusão dos horários anteriores, exclusão do dia seguinte, dias de 23/25
horas por DST, troca de modos/persistência do painel, vazio, alteração de
feed com mesmos IDs, próximo evento amanhã, posição restaurada na tela,
transparência dos mascotes, SVGs renderizáveis e remoção de textos técnicos
da UI. O teste do cache também cobre a versão compacta do símbolo de cubo.

A inspeção visual incluiu Início, Cubos, Eventos, Overlay, Sobre e painel
recolhido/expandido. O painel reuniu 35 horários do perfil SA para o dia
da inspeção, com rolagem, ícones e diferenciação de horários anteriores.
Os nomes, tooltips e foco dos botões foram conferidos. A nova identidade
aparece na abertura, navegação, página inicial, Sobre e ícone do executável.
Não houve sessão de pesquisa com grupo de usuários nem certificação de
acessibilidade. Dados e visitas não foram alterados por esta revisão.

O pipeline nativo foi exercitado novamente após o novo símbolo de cubo.
Símbolos compactos no minimapa preservam mais terreno para reconhecimento.
As medições anteriores são históricas; taxa efetiva continua disponível em
Ajustes avançados e depende da carga/densidade. O ensaio usa janela própria.

## Limites da evidência

- Nenhum cliente AION 2 foi acessado pelo agente; o usuário relatou os pontos no mapa grande da versão anterior. Verificação de fontes públicas não equivale a confirmar coordenadas no Global/LATAM, agenda dentro do jogo ou compatibilidade geral com o cliente. O escopo das fontes está em SOURCES.md.
- A captura MSS e a janela externa estão implementadas; o pipeline foi testado com imagens sintéticas e sinais de controle, com uma janela nativa própria, sem validação ponta a ponta no jogo ou uma matriz completa de monitores/DPI.
- O sistema solicita notificações ao Windows via Qt. Não foi confirmada visualmente a entrega de um alerta pelo sistema com configurações reais de Não Perturbe/permissões.
- Não foi usado endpoint remoto real; cache e regras de provider foram testados localmente. Uma URL compatível pode ser fornecida pelo usuário.
- Sonar implementado e testado em processo próprio. Não foi validado no áudio do AION 2 nem em corpus independente de combate/música/efeitos; os ensaios sintéticos não comprovam precisão em SA.
- A execução local não substitui validação de distribuição em máquina limpa sem Python, assinatura digital, acessibilidade completa ou teste prolongado de memória/CPU.

## Reproduzir

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m app.main --smoke-test
```

Use `STRIGOI_DATA_DIR` para isolar manualmente as preferências de smoke tests. Os testes pytest fazem isso automaticamente via diretórios temporários.

## Sonar, evento escolhido e camadas • 0.7.0

Os 16 casos novos cobrem detecção fraca em -20/-30 dB, canais com fases
opostas, quatro controles negativos, PCM inválido, buffer limitado,
reinício sem captura automática, liberação do worker, heartbeat vazio,
evento escolhido/persistência/agenda sem esse evento, camadas compartilhadas
nos dois modos, aviso de teste e abertura dos canais institucionais.
A suíte completa anterior à correção de heartbeat teve 100 testes passando;
os 14 casos novos passaram novamente depois da correção e inclusão desse
regressor, A suíte final completa reúne 103 casos, incluindo um canal invertido isolado
e a proteção do intervalo entre avisos durante descontinuidades.

O helper WASAPI foi compilado com Visual Studio x64 e runtime estático.
Um processo próprio reproduziu a referência misturada a ruído branco em
-20 dB de relação sinal/ruído e volume muito baixo. O serviço real recebeu
float32 estéreo 48 kHz, emitiu um aviso e encerrou o helper com código zero.
O primeiro ensaio revelou que heartbeats vazios apagavam a confirmação;
a correção foi reproduzida no ensaio nativo e coberta por um regressor.
O controle invertido também revelou uma confusão no detector inicial;
a comparação da ordem temporal retirou o alerta no ensaio correspondente.
Não foram usadas gravações do jogo nem medida de falsos positivos por hora.

As telas Sonar, Donate, Sobre, Eventos e Overlay, o painel com evento escolhido
e o aviso visual de teste foram renderizados e inspecionados. O texto em Sobre
registra a finalidade exclusiva de acessibilidade auditiva, sem afirmar que
o jogo carece de qualquer suporte ou que todos os ouvintes encontram cubos
facilmente. Não há pesquisa com pessoas surdas ou certificação de acessibilidade.

O painel foi reduzido de 380 para 260 pixels lógicos de largura. A vista
compacta ocupa cerca de 100 pixels lógicos de altura, com uma faixa curta
de cabeçalho e uma linha de evento em dois níveis. O seletor foi movido
para um menu no cabeçalho. A expansão apresenta até seis linhas antes da
rolagem. A referência do usuário guiou a densidade e hierarquia da HUD;
fontes e cores próprias foram mantidas.

A versão portátil 0.7.0 abriu as dez telas com saída zero, e o smoke validou
o detector, a referência e a execução do helper com --version sem captura.
Assets, imagens dos mapas, fontes de dados e perfis regionais coincidem
byte a byte com a fonte. Uma base isolada equivalente à atualização antiga
preservou visitas, filtros, notas, agenda alternativa e backup. O ensaio
nativo adicional, em sensibilidade equilibrada, reconheceu a mistura em
-30 dB de relação sinal/ruído e volume muito baixo no processo próprio, com
um aviso e parada limpa. Novamente, isso não comprova precisão no AION 2.

## Apoio ao criador • 0.7.1

O teste de Donate foi atualizado para verificar os três destinos autorizados:
o link pessoal fornecido e os dois canais institucionais. O caso passou,
assim como a rejeição de destinos não configurados. A tela foi renderizada
e inspecionada com o apoio pessoal identificado separadamente. Nenhuma
transação foi realizada; o verificador web não carregou o link pessoal.

## Mensagem do sonar • 0.7.2

Após relatar sucesso do sonar no jogo e enviar uma imagem com o cubo visível,
o usuário solicitou uma orientação de exploração no aviso. O subtítulo foi
trocado para Procure nos arredores antes que outro jogador colete!, mantendo
o título Possível cubo por perto. A renderização confirmou quebra em duas
linhas sem corte. O detector não foi alterado. O relato do usuário não mede
precisão ou falsos alertas por hora.

## Sobre e mascote • 0.7.2

A seção Como o aplicativo funciona descreve janelas externas, imagem da tela
e áudio pelo Windows. Explicita ausência de injeção em DLLs, alteração dos
arquivos e leitura da memória do jogo. As telas Início e Sobre foram
renderizadas e inspecionadas com Aether v2. As duas PNGs têm alpha real e
cantos transparentes; o ICO foi atualizado nos tamanhos 16–256 pixels.

## Idiomas e instalador • 0.8.0

106 testes passaram em 38,21 s. Os novos casos verificam o idioma do
instalador como padrão antes de uma preferência explícita, troca imediata
PT-BR/en-US com preservação de seleção de evento, visitas e texto digitado,
além de datas/horários dos EUA sem alterar o instante ou fuso do evento.
As telas em inglês e o alerta/painel flutuante foram renderizados e
inspecionados. Termos existem nos dois idiomas e podem ser consultados em Sobre.
Notas de fontes e nomes institucionais mantêm sua língua original.

O portátil final abriu as dez páginas em português e inglês, verificou a
referência e o helper de áudio sem captura, e conservou todos os mapas,
coordenadas e assets de sonar byte a byte. O pacote inclui GPLv3 e o código
fonte correspondente. O novo mascote e avatar têm transparência real.

NSIS Unicode 3.12 compilou o mesmo script em modo isolado de teste, com
registro separado e sem atalhos. Em ambos os idiomas foram verificados:

- instalação silenciosa sem aceite termina com código 2 antes de instalar;
- os 959 arquivos extraídos coincidem com todo o payload preparado;
- versão/hash dos termos e idioma são registrados;
- idioma inicial do app segue a escolha do instalador;
- reinstalação mantém o conteúdo de preferências e arquivos desconhecidos;
- desinstalação remove aplicativo, DLLs e registro do teste, preservando
  preferências, visitas e arquivos desconhecidos;
- as preferências reais do usuário permanecem byte a byte inalteradas.

A página interativa usa `LicenseForceSelection checkbox` da Modern UI,
com texto de aceite nos dois idiomas. O teste de ciclo usou o modo silencioso
com aceite explícito; não representa uma máquina limpa nem assinatura digital.
Relatório do ciclo: `outputs/installer-validation-v080.json` na entrega.
O script não exige privilégio de administrador nem toca arquivos do AION 2.

## Legibilidade e intensidade — beta 6

Os testes verificam os símbolos ampliados em DPI 150% e 200%, a preservação
da projeção e a máscara dos pixels efetivamente pintados, incluindo as setas.
A extração de alturas usa somente os indicadores presentes na fonte; pontos
editados ou sem dado não recebem altura inferida.

Com a referência fornecida atenuada em um ensaio controlado, a leitura ficou
próxima de -61,10 dBFS com ganho 0,01 e -55,08 dBFS com ganho 0,02. Dobrar o
ganho elevou a leitura em aproximadamente 6,02 dB, sem aumentar o score de
semelhança normalizado. Dobrar o ruído mantendo a referência no mesmo nível
alterou a estimativa em menos de 1,5 dB no controle testado. Ruído sem a
referência não gerou leitura confirmada. As atualizações durante o cooldown,
o desaparecimento após silêncio e a rejeição de sinais enfileirados após a
parada são exercitados separadamente.

Esses ensaios não medem distância nem validam a barra em combate real. As
pré-visualizações PT-BR/EN-US usam ensaio de interface e não captura do jogo.

## Visibilidade automática — beta 7

Os testes cobrem seis janelas, chamadas periódicas de atualização enquanto
ocultas, restauração, alterações de preferências durante a ocultação,
preservação da sessão de combate, descarte de avisos do Sonar e de respostas
visuais antigas após Alt+Tab. As verificações de propriedade da janela
incluem nomes exatos de executáveis, minimização, origem negativa de um
monitor secundário e foco em um overlay versus na janela principal do app.

Em análise local de imagens fornecidas anteriormente pelo usuário, o OCR
do Windows distinguiu Settings, Map: Altgard e uma tela normal do jogo.
As imagens e o texto extraído não acompanham o código ou os downloads.
Geometria de fechamento e títulos conhecidos também são exercitados com
dados sintéticos em várias resoluções. Isso não comprova cobertura de
todos os menus nem representa um teste ao vivo da alternância Alt+Tab.

## Correção de visibilidade — beta 8

Em monitoramento autorizado do jogo em 3840 × 2160, foram registrados sinais
de fechamento sem título de menu reconhecido enquanto a janela continuava
ativa. A beta 7 ocultava os painéis nesse caso, inclusive antes do retorno
do OCR. A beta 8 remove essa ocultação antecipada e exige o reconhecimento
do título. Os registros locais contêm somente decisões e horários, sem
imagens, áudio ou nomes de jogadores, e não acompanham a distribuição.

Os testes de regressão verificam que o sinal geométrico isolado mantém o
modo normal e que o monitor não emite um estado transitório de menu antes
da classificação. Os controles de Settings e Map: Altgard permanecem
corretos. O usuário confirmou o funcionamento do Alt+Tab na beta 7.
Não foi confirmado qual elemento específico da cidade originou a forma
parecida com “X”, nem a cobertura de todos os menus do jogo.

## Spirits e ícones — beta 9

Os ensaios cobrem a soma retroativa de dano/DPS/participação sem duplicação,
dois SMs com sinais distintos ou iguais, prioridade e preservação do dono
explícito, variantes de conjuração ambíguas, ausência de fallback escalar no
PvP e nova vida de um spirit após desaparecimento. O helper exercita o ID
ancorado com nome presente, a emissão do tipo 0x1C sem dono, a variante bruta
de conjuração e a conservação do multiplicador. Não há pacotes brutos nos
testes: os exemplos são sintéticos. A validação dessa correção em SA ainda
depende de uma partida com Spiritmaster.

Os oito PNGs de classes foram obtidos do site oficial de personagens da NC
em 14/10/2026. O mapeamento acompanha o catálogo Global e os hashes conferem
com os bytes originais; nenhuma cor ou forma foi redesenhada. Classes sem
imagem oficial verificada usam símbolo neutro. Esses assets mantêm direitos
separados da licença do código.
