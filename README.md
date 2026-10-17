# Azphelumbra

**AION 2 Companion App · 0.10.0-beta.5 · Windows x64**

A beta 5 acrescenta as janelas diárias da Battlefield e mantém o contador até o fechamento. Immortal Gartua recebe uma previsão única pela leitura do contador na tela do jogo, sem presumir um spawn diário. Bosses do Abyss usam referência Global identificada na agenda, ainda sem confirmação individual em SA. Veja [Eventos e contadores](docs/EVENTS.md).

A beta 4 acompanha ganhos de almas mesmo quando o app é aberto com o personagem já logado. Sem total inicial, mostra os ganhos desta captura; abrir os detalhes do pet confirma o total sem somar coletas duas vezes. Leituras sem identificação ficam na memória, sem alterar perfis salvos. Menus como Enhancement passam a exigir título, abas, separador e botão de fechar para ocultar os overlays. Veja [Pets](docs/PETS.md).

A Rotina acrescenta o Panorama de personagens e acompanha Odyle básica e
recarregada por leitura passiva. O overlay alterna entre Pulso compacto e
Faixa, com estilo, posição e recursos salvos. A leitura inicial foi conferida
em SA; limites e reposições não são presumidos. Veja [Rotina](docs/ROUTINE.md).

A interface Vigília reúne os módulos ao lado da sessão. O overlay de combate Impacto mostra barras proporcionais ao DPS, com ícones e cores por classe. A faixa Fita acompanha eventos em formato compacto e expande os horários do dia. Use o emblema flutuante para abrir o menu rápido. Preferências, visitas e coleções anteriores são preservadas.

A beta 12 deixa os controles de frequência à vista em **Overlay → Fluidez do overlay**. Escolha de 15 a 360 Hz para o desenho e de 10 a 60 fps para a leitura do minimapa (até 30 fps no mapa grande), com aplicação imediata e preferência salva. Novas instalações começam em 60 Hz/30 fps; escolhas anteriores são preservadas. Marcadores parados deixam de ser redesenhados continuamente, e o processamento visual usa um orçamento menor de threads. A melhoria de FPS no jogo ainda precisa ser conferida após atualizar.

A beta 11 acrescenta a coleção de Pets, com 208 retratos originais, favoritos, metas de Insight, filtro por mapa e um painel compacto no menu rápido. A coleção inicial foi conferida em duas entradas SA. Os locais de farm são referências do cliente, sem garantia de presença atual; distância e direção de um radar ao vivo ainda não estão disponíveis. Veja [Pets](docs/PETS.md).

A beta 10 torna a leitura do grupo mais resistente a registros incompletos:
dados opcionais de poder não descartam identidades válidas, e o leitor
continua procurando membros após posições vazias ou registros ilegíveis.
A recuperação de três para cinco jogadores passou nos testes controlados;
a confirmação numa nova instância SA ainda está pendente.

A beta 9 melhora a atribuição do dano de spirits ao Spiritmaster: prioriza
o dono anunciado, conserva vínculos em atualizações incompletas e usa sinais
de conjuração e uma inferência conservadora de combate em PvE. Casos ambíguos
continuam não atribuídos. Os ícones das oito classes Global são os PNGs
oficiais, com suas cores originais. A correção de atribuição passou em testes
controlados; ainda precisa de confirmação ao vivo em SA.

A beta 8 corrige os sumiços indevidos dos overlays durante o jogo: um desenho parecido com “X” na tela não basta para reconhecer um menu. A ocultação por Alt+Tab continua funcionando. Menus dependem da leitura local de títulos conhecidos; a cobertura não é universal. O mapa grande preserva seus marcadores, a medição continua em segundo plano e avisos antigos do Sonar não reaparecem.

O aplicativo amplia os símbolos do minimapa em 100%, mostra setas nas posições de cubos com altura informada e acrescenta uma barra com histórico de intensidade ao Sonar. As setas seguem a altura relativa do grupo registrada na fonte; a barra estima o som reconhecido e também depende do volume do jogo. A proximidade no jogo ainda precisa de validação.

O aplicativo mostra o painel de combate nas dungeons e arenas 1v1/5v5 identificadas e o oculta ao sair. Foram observados os sinais de entrada e saída de um mapa de cada modalidade em SA; outros mapas da rotação ainda precisam de identificação. O dano PvP contabiliza ataques de participantes confirmados e exclui o dano recebido. O cálculo continua experimental, sem validação de precisão ao vivo; no 5v5, a lista completa do time ainda não foi confirmada. O menu rápido permite ocultar o painel sem parar a medição.

[Página do aplicativo](https://jpgalvao-architect.github.io/strigoi-aether-map/) ·
[Instalador e downloads](https://github.com/jpgalvao-architect/strigoi-aether-map/releases/tag/v0.10.0-beta.1) ·
[English](README.en-US.md)

Seu caderno de exploração: mapas, coletas, cubos e eventos em um só lugar.
Aether, o pequeno vampiro asmodiano, acompanha sua jornada.

A beta 0.9.0 acrescenta o medidor experimental de dano em instâncias,
com painel, DPS/participação, invocações atribuídas, filtro por alvo e
histórico local. A leitura ainda precisa de validação em SA; resultados
são identificados como dados parciais. O Setup conduz o download oficial
e abre o assistente do Npcap quando necessário. Veja [Combate](docs/COMBAT.md).

Na 0.8.0, o instalador oferece português do Brasil e inglês dos EUA e exige
aceite dos termos antes de instalar. A escolha define o idioma inicial;
Configurações permite trocar imediatamente, preservando visitas e filtros.
Leia os [termos](docs/TERMS.pt-BR.txt) e as
[instruções de instalação](docs/INSTALLER.md).
O código próprio usa GPLv3; dados, mapas e componentes mantêm suas licenças.
O código-fonte correspondente acompanha o aplicativo em `source/`.

Na 0.7.2, Aether tem uma expressão mais malvada e roupa escura sem os enfeites
brancos. O aviso do Sonar orienta a procurar nos arredores. A aba Sobre explica
o funcionamento: overlays externos, análise da imagem da tela e áudio recebido
pelo Windows, sem injeção nas DLLs, alteração de arquivos ou leitura da memória
do jogo.

A 0.7.0 acrescenta o sonar de cubos, a escolha do evento no painel flutuante
e as mesmas camadas do Atlas no minimapa e no mapa grande. A aba Donate
abre canais oficiais de apoio a associações brasileiras de pessoas surdas.
A 0.7.1 acrescenta o apoio pessoal ao criador pelo Mercado Pago.

## Abrir a versão portátil

1. Extraia todo o ZIP `StrigoiAetherMap-windows-x64.zip` numa pasta nova.
2. Abra `StrigoiAetherMap/StrigoiAetherMap.exe`.
3. Explore o Atlas ou ative o painel flutuante em Eventos.

Mantenha `_internal` ao lado do executável. Não é necessário instalar Python
nem executar como administrador. O app usa mapas e agenda locais.

## Explorar

- **Atlas:** escolha o mapa, role para aproximar e arraste para explorar.
- **Coletas:** habilite as camadas que quer ver no atlas e no overlay.
- **Cubos ocultos:** selecione uma posição e marque sua visita. Origem e
  coordenadas estão em Ver origem e coordenadas.
- **Eventos:** escolha a agenda e ative Mostrar painel flutuante. A seta do
  painel alterna a vista compacta com os horários de hoje. Escolha o evento
  acompanhado no painel ou deixe a seleção automática. Arraste o
  cabeçalho para mover; expansão e posição são salvas.
- **Overlay:** escolha mapa e monitor e ative. No modo minimapa, selecione
  apenas seu terreno uma vez. Ao abrir M, o mapa grande tem prioridade;
  ao fechar, o minimapa retorna. Escolha a frequência em Fluidez do overlay; comece em 60 Hz/30 fps.
  Ajustes avançados reúne precisão e referência fixa.
- **Sonar:** abra o jogo, atualize a lista de aplicativos, selecione o AION 2
  e clique em Ativar sonar. O aviso visual indica som compatível com o cubo;
  não fornece posição nem distância. Testar aviso visual não detecta áudio.
- **Donate:** apoie o criador pelo Mercado Pago ou abra o canal oficial da
  instituição escolhida no navegador. As opções indicam quem recebe o apoio.
- **Configurações:** escolha fuso e notificações. Alertas exigem o app aberto.
- **Combate:** a medição começa automaticamente e aguarda o jogo. Escolha a
  visão e o alvo; uma nova instância reconhecida reinicia o placar. Desative a
  medição nas Configurações quando quiser. Não há envio de resultados.
- **Menu rápido:** clique no mascote flutuante para controlar Sonar, os mapas,
  o placar e os eventos. Ocultar o placar mantém a medição. Arraste para mover.

Altgard é o padrão inicial. Escolhas posteriores, filtros e visitas persistem.
Fechar a janela encerra o app; minimizar o mantém em execução.

## Dados e atualização

5.425 posições de coleta, 1.120 vestígios e 2.811 locais possíveis de cubos
em Altgard e Verteron. Os 226 registros antigos KR/TW ficam em camada separada,
inicialmente desligada, com visitas preservadas. Locais possíveis não significam
ocupação simultânea nem confirmação individual em SA; confira no jogo.

Os dados comunitários seguem **CC BY-NC 4.0, para uso não comercial**.
Autoria, origem, revisão e transformação estão em [SOURCES.md](docs/SOURCES.md).
A agenda SA é independente da geografia; outras agendas podem ser selecionadas
ou importadas. O horário do jogo prevalece em caso de divergência.

Ao atualizar, use uma pasta nova. Dados locais ficam em
`%LOCALAPPDATA%\StrigoiAetherMap`. A migração preserva visitas, filtros, notas
e agenda alternativa; faz backup antes de alterar uma base conhecida.
Veja [a revisão de cubos](docs/COORDINATE_CORRECTION.md).

## Privacidade

Captura visual começa somente ao ativar o overlay nesta sessão. Imagens
ficam na memória; a seleção salva somente seus limites. Preferências e visitas
ficam neste computador. O sonar captura somente o áudio do aplicativo
escolhido e seus processos filhos, em memória, sem microfone ou gravação.
Overlay e sonar começam desligados a cada abertura. A medição de combate
começa automaticamente quando habilitada nas Configurações e Npcap está
disponível. Não há telemetria.
Rede é usada apenas para uma
agenda online configurada voluntariamente. `STRIGOI_DATA_DIR` permite uma
pasta de dados alternativa. O app é um projeto independente de AION 2.

## Executar e construir o código

Python 3.12+ e Windows x64. O sonar exige Windows 10 build 20348 ou mais
recente (incluindo Windows 11). Para recompilar seu componente nativo,
instale o Visual Studio com ferramentas C++ x64 e Windows SDK. Dentro da pasta do código-fonte:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.main
```

Testes e build:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[overlay,dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m app.main --smoke-test
& .\scripts\build-sonar.ps1
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean strigoi.spec
```

O `.spec` reúne dados, mapas, PNGs, SVGs, timezones e dependências opcionais.
Distribua a pasta inteira em `dist/StrigoiAetherMap`. `requirements-lock.txt`
registra o ambiente validado. O build usa um PATH controlado para evitar DLLs
de outros programas. `--smoke-test --screenshot dashboard.png` renderiza a
própria janela, sem captura do desktop. Testes usam pastas isoladas.

## Documentação

- [Sonar: funcionamento e limites](docs/SONAR.md)
- [Doações e fontes institucionais](docs/DONATE.md)
- [Rodada de UX](docs/UX_REVIEW.md)
- [Mascote, ícones e prompts](docs/BRANDING.md)
- [Fontes e dados](docs/SOURCES.md)
- [Overlay](docs/OVERLAY.md)
- [Validação e limites](docs/VALIDATION.md)
- [Avisos de terceiros](THIRD_PARTY.md)
