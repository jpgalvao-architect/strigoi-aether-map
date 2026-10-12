# Especificação funcional e técnica — 0.7.0

## Visão do produto

STRIGOI AETHER MAP é um caderno desktop de exploração para Windows, apresentado como AION 2 Companion App. Sua utilidade principal é independente do cliente: consultar mapas, escolher camadas, registrar visitas e acompanhar uma agenda. A identidade usa Aether, um mascote próprio com aparência asmodiana, e ícones vetoriais originais.

A versão 0.3.0 incorpora 21 recursos catalogados e perfis de agenda consultados em fontes públicas, além de 6.771 posições comunitárias compartilhadas em dois mapas reais. Essas posições não estão confirmadas para LATAM; 5.425 coordenadas de coleta foram incorporadas com fonte e licença. Recursos e categorias são extensíveis via JSON, sem presumir API oficial. Consulte SOURCES.md para origem, licença e alcance.

## Stack e decisões

| Decisão | Motivo e consequência |
|---|---|
| Python 3.12+, PySide6 | UI nativa, serviços tipados e integração de janela Windows em uma única stack |
| QGraphicsView + SVG/raster | Zoom/pan local sem servidor de tiles, mapas offline e marcadores com tamanho constante |
| Pydantic 2 | Validação de schemas, referências e coordenadas antes de substituir dados válidos |
| JSON atômico | Dados pequenos, exportáveis e auditáveis. SQLite fica reservado para volumes/edição concorrente futuros |
| OpenCV + MSS opcionais | Captura visual externa e comparação de referências; importação tardia preserva uso do app base sem essas bibliotecas |
| QThread em captura/rede | A UI mantém interação durante I/O. Timers no loop principal atualizam clocks e alertas |
| Qt system tray | Notificação integrada ao sistema sem serviço residente; exige app aberto |
| PyInstaller em pasta | Python/Qt distribuídos junto do executável; evita extrair tudo a cada abertura |

Referências técnicas consultadas: [QSystemTrayIcon](https://doc.qt.io/qtforpython-6.11/PySide6/QtWidgets/QSystemTrayIcon.html), [captura MSS](https://python-mss.readthedocs.io/stable/examples.html), [modelos Pydantic](https://docs.pydantic.dev/latest/concepts/models/). As versões concretamente executadas constam do lockfile.

## Limites e responsabilidades dos módulos

```text
UI Qt ── AppContext ── modelos Pydantic
               ├── filtro compartilhado ── atlas / cubes / overlay
               ├── providers ── agenda validada ── cache JSON
               └── preferências ── armazenamento atômico

timer ── ocorrências UTC ── AlertEngine ── notificação Qt + status no app

ativação explícita ── MSS worker ── detector visual ── sinais Qt
                                                    └── janela transparente
```

O domínio de agenda, filtros e detector não depende das páginas. `AppContext` é a fronteira de persistência compartilhada e emite sinais de alteração para as páginas. As estruturas podem crescer para repositórios SQLite sem mudar o formato lógico dos modelos.

## Telas e critérios funcionais

| Área | Comportamento entregue |
|---|---|
| Splash | Marca e indicação de preparação enquanto se carregam dados locais |
| Dashboard | Atalho para atlas/cubos, próximos 3 eventos, countdown, contagem de pontos, recursos, visitas e status |
| Atlas | Mapa selecionável, zoom/pan, categorias, busca, raridade, tooltip, notas, origem e visitas |
| Gatherables | Filtros combinados de categoria, subcategoria, mapa e raridade; visibilidade por recurso; habilitar/desabilitar todos |
| Hidden Cubes | Vista específica usando o mesmo atlas e filtros, informações subaquáticas e sugestão de rota textual |
| Event Tracker | Próximo horário de cada evento ou primeiras 24 ocorrências em 8 dias; timezone configurado, fonte consultável, importação, provider HTTPS e cache |
| Configurações | Idioma PT-BR/en-US com troca imediata, timezone, alertas 5/15/30, tipos de evento, atualização remota e importação/exportação |
| Overlay | Mapa grande automático no monitor, minimapa retangular com seleção própria e norte fixo; pan/zoom reconhecido; meta de desenho 240 Hz com taxas medidas; camadas, painel de eventos e modo fixo avançado; ajustes técnicos recolhidos |
| Sonar | Captura WASAPI por aplicativo, assinatura da amostra, consenso temporal, intervalo entre avisos e aviso visual independente do mapa; início explícito a cada sessão |
| Donate | Apoio pessoal ao criador pelo Mercado Pago e doações à ASSJP e ASC, com destinatários indicados; sem processamento de pagamentos no aplicativo |
| Sobre | Identidade, funcionamento externo por overlay, finalidade de acessibilidade auditiva e limites do aviso do sonar |

Os filtros persistentes são exclusões de categorias/recursos, mapa selecionado, visitados e ocultação de visitas. Busca, subcategoria e raridade são filtros de exploração temporários da tela. Desmarcar categoria tem precedência sobre recurso individual. A interface identifica o mapa de cada região; não há filtro de múltiplas regiões simultâneas.

## Modelos e invariantes

- `Region`, `MapDefinition`: identidade, origem, imagem e dimensões; todo mapa precisa referenciar região existente.
- `Category`, `Subcategory`, `Gatherable`: IDs únicos, relação consistente, cor hexadecimal e forma de ícone conhecida; raridade normalizada.
- `PointOfInterest`, `HiddenCube`: recurso/mapa existentes, coordenadas finitas em [0,1], notas, origem, certeza, habilitação, visibilidade de overlay; cubos acrescentam condição subaquática e rota textual.
- `GameEvent`, `EventSchedule`: identidade, tipo livre, região textual, origem, recurrence e timezone. Agendas `once` exigem timestamp com offset.
- `Preferences`, `NotificationSettings`, `OverlaySettings`: estado tipado com limites e defaults seguros; chave desconhecida é rejeitada.

Para horários locais inexistentes em transições de DST, a ocorrência é descartada. Em horários ambíguos, usa-se a primeira ocorrência (`fold=0`). O usuário visualiza offset UTC, evitando nomes longos/ambíguos do Windows. Todos os cálculos do countdown usam instantes UTC.

## Resiliência

Gravações de JSON usam arquivo temporário no mesmo diretório, flush, fsync e troca atômica. Configurações/dados corrompidos são preservados com sufixo `invalid-...` quando possível e substituídos em memória pelos defaults. A falha aparece na barra de status/log. Uma falha de importação mantém a base anterior. Logs não incluem frames ou áudio.

Provider remoto exige HTTPS, sem credenciais embutidas, limite de 2 MB, timeout de socket de 10 segundos e validação antes de atualização do cache. Redirecionamentos para esquemas não HTTPS são recusados. Atlas JSON local é limitado a 12 MB; os demais JSON locais a 5 MB; mapas externos são PNG/JPG até 40 MB e 16000 pixels por dimensão. Falhas preservam a última agenda válida. Conteúdo importado é tratado como dados, nunca como código executável.

Alertas persistem chave evento/instante/antecedência e expiram após 14 dias. Uma janela de tolerância de 90 segundos evita perder um disparo entre ticks, sem inundar o usuário ao retomar uma máquina suspensa. Eventos já iniciados não alertam. Não há execução enquanto o app estiver fechado.

Captura só inicia após ação explícita na sessão. Duas coincidências consecutivas habilitam a renderização; a primeira falha oculta o overlay. Um watchdog oculta a janela após 1,5 segundo sem retorno. Erros encerram a captura. A resolução e o mapeamento DPI precisam coincidir; monitores ambíguos fazem o módulo permanecer oculto.

## Pipeline visual da 0.4.1

A área do mapa grande é o monitor inteiro; o minimapa usa limites próprios
persistidos em `CaptureArea`, com `view_kind`, mapa e geometria/DPI validados.
SIFT com referência global reduzida e refinamento local na resolução original
reconhece recortes pequenos. Uma região sugerida pelo fluxo óptico precisa
ser comprovada por novas correspondências na revalidação, sem reutilizar
a evidência anterior. Ativar o minimapa também procura o mapa grande a cada
0,5 segundo, com prioridade para ele e retorno ao minimapa ao fechar. Um
único worker coordena as duas áreas e uma única janela desenha o modo ativo.
As máscaras dos próprios ícones pertencem à área em que foram desenhadas.
A revalidação global ocorre a cada 0,5 segundo; fluxo óptico acompanha
detalhes verificados entre leituras, com testes de consistência e distribuição.

O desenho tem meta selecionável de 60/120/240 Hz, usa relógio de alta precisão,
timer Qt preciso, regiões dos ícones e interpolação limitada de 12 ms, sem
extrapolação. A leitura tem limite de 60 Hz no minimapa e 30 Hz no mapa grande.
No Windows, a resolução do timer é solicitada apenas enquanto o overlay
dinâmico estiver visível, com liberação ao ocultá-lo. As taxas medidas são
exibidas separadamente; chamadas de desenho não comprovam quadros apresentados.

Referências: [QTimer](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QTimer.html),
[fluxo óptico OpenCV](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html)
e [timeBeginPeriod](https://learn.microsoft.com/en-us/windows/win32/api/timeapi/nf-timeapi-timebeginperiod).

## Camada de posições possíveis • 0.5.0

2.811 candidatos dos conjuntos de objetos licenciados, mais 226 registros
antigos separados. Origem superior esquerda, percentuais divididos por 100;
sem validação regional individual. Manifesto `cube-sites-provenance.json`.
Retirada seletiva da substituição de Basfelt da 0.4.2. Backup antes da
migração, IDs antigos preservados e nenhuma transferência por proximidade.
Preferência `cube_data_release` controla o padrão inicial da camada histórica,
sem alterar a escolha de agenda protegida por `content_release`.

## Áudio • 0.7.0

Um helper C++ próprio usa process loopback externo do Windows e envia PCM
float32 48 kHz estéreo por pipe limitado. EOF na entrada solicita parada;
encerramento do processo escolhido também encerra a captura. O worker Qt
processa os canais separadamente, com ponderação inversa do fundo espectral,
filtro casado de trechos da referência e verificação da ordem temporal.
Mensagens de manutenção vazias não interrompem confirmação. O aviso indica
compatibilidade sonora, sem coordenadas ou probabilidade calibrada.

O estado de captura salvo nunca inicia dispositivos ao abrir o app. O código
e os testes existentes estão descritos em [SONAR.md](SONAR.md).

O painel flutuante usa largura fixa de 260 pixels lógicos, faixa de cabeçalho
curta e evento em dois níveis. EventPicker oferece a escolha num menu de
cabeçalho, compartilhado com a seleção da página Eventos.
