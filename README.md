# STRIGOI AETHER MAP

**AION 2 Companion App · 0.9.0-beta.4 · Windows x64**

A beta 0.9.0-beta.4 mostra o painel de combate automaticamente nas instâncias reconhecidas e o oculta ao sair. O menu rápido permite desativar a exibição sem parar a medição. A identificação e a medição nas arenas 1v1/5v5 ainda aguardam validação ao vivo; não são anunciadas como confirmadas.

[Página do aplicativo](https://jpgalvao-architect.github.io/strigoi-aether-map/) ·
[Instalador e downloads](https://github.com/jpgalvao-architect/strigoi-aether-map/releases/tag/v0.9.0-beta.4) ·
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
  ao fechar, o minimapa retorna. Ajustes avançados reúne precisão e frequência.
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
