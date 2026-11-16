# Live Sync · validação para publicação

## Situação da entrega

| Classificação | Situação |
| --- | --- |
| Implementado | Wizard BYOC, Worker, Durable Object SQLite, revogação, publicação manual, recepção automática e guias PT-BR, EN-US e ES-419 |
| Validado localmente | Empacotamento Wrangler, prova de posse, HTTP/WebSocket de loopback, dois processos Qt separados, hibernação forçada, isolamento entre sessões, validação dos snapshots e preservação do preset pessoal |
| Validado na Cloudflare real | Pendente |
| Pendente de validação | HTTPS/WSS público, implantação e consentimento reais, consumo de cotas por conta, capacidade de produção e inspeção visual no mapa grande e no minimapa do AION 2 |
| Bloqueado por autorização | Publicar o branch no GitHub, abrir o PR e provisionar uma implantação em conta Free do proprietário |

O [repositório oficial](https://github.com/jpgalvao-architect/strigoi-aether-map) e o [site oficial](https://jpgalvao-architect.github.io/strigoi-aether-map/) respondiam na verificação. A pasta de implantação ainda retornava 404 em `main`. O assistente aponta para `backend/live-sync` no repositório oficial, e o guia sai no GitHub Pages após a entrada dessas mudanças em `main`. O [workflow de Pages](../.github/workflows/pages.yml) publica o diretório `website`.

## Testes locais

- **Vincular e entrar.** A chave correta passou na prova de posse do Durable Object pelo WebSocket. A chave incorreta foi rejeitada. O participante recebeu a primeira estratégia já publicada em um processo Qt independente e sem vinculação Cloudflare.
- **Publicação explícita.** O participante continuou na revisão anterior enquanto o caller criou um pin, moveu P1, desenhou seta, círculo e retângulo e apagou um pin. Após a publicação, o participante recebeu exatamente essas alterações.
- **Reconexão.** O participante ficou offline por duas publicações, preservou a última estratégia visível e voltou diretamente à versão mais recente. Sair restaurou seu overlay local, com o arquivo do preset preservado byte a byte.
- **Permissões.** Convite recusado para publicar, encerrar ou criar sessão. Convites revogados e credenciais de outra sala foram rejeitados. Corpos fora do schema e grandes demais foram rejeitados; a sessão continuou funcionando.
- **Hibernação.** O Miniflare desalojou o Durable Object com o socket aberto. Ao reativar, o objeto recuperou a contagem, enviou a nova revisão pelo mesmo socket e removeu a conexão da contagem após a saída.
- **Overlay.** O teste conferiu pins, P1, exclusões e formas no pipeline de renderização compartilhado. A verificação visual no cliente do jogo continua pendente para mapa grande e minimapa.
- **Pacote.** Wrangler 4.163.0 reuniu script, SQLite, migração e limites no build a seco. `npm audit --omit=dev` retornou zero vulnerabilidades na consulta. As chaves repetidas dos testes são fixtures locais. A chave real do host fica no segredo da sua implantação e protegida pelo Windows no aplicativo.
- **Regressão e site.** A suíte Python passou com 420 testes, incluindo os cenários Qt locais. Os quatro testes de protocolo e o teste de hibernação passaram. O Microsoft Edge renderizou o guia em PT-BR, EN-US e ES-419, com um único artigo visível em cada idioma.

## Carga em Windows

A matriz progressiva usou o mesmo bundle do Wrangler em um socket direto do Workerd, com SQLite, rate limits e quatro processos geradores. Uma publicação de teste distribuiu um preset pequeno. A fila de downloads inclui o jitter de 3,5 s, 6,5 s ou 10 s da aplicação. A primeira matriz mediu a primeira tentativa, sem retries, com reconexões iniciadas a cada 5 ms e uma pausa individual de 1–2 s. As latências abaixo incluem o jitter e consideram as operações que terminaram. CPU, memória e handles correspondem ao processo local; a memória nativa por processo inclui mais que o isolate.

| Clientes abertos / publicados | Reconexões | Publicação p50 / p95 / p99 | Reconexão p95 | HTTP + upgrades | Payload | CPU / RSS pico / handles |
| ---: | ---: | --- | ---: | ---: | ---: | --- |
| 100 / 100 | 100 | 1,70 / 3,34 / 3,45 s | 1,97 s | 303 | 75.900 B | 0,48 s / 177,8 MiB / 508 |
| 250 / 250 | 250 | 1,77 / 3,32 / 3,52 s | 1,96 s | 753 | 189.750 B | 2,97 s / 278,8 MiB / 824 |
| 500 / 500 | 500 | 1,87 / 3,40 / 3,54 s | 1,95 s | 1.503 | 379.500 B | 3,91 s / 450,5 MiB / 1.323 |
| 750 / 750 | 750 | 3,48 / 6,30 / 6,54 s | 1,99 s | 2.253 | 569.250 B | 3,95 s / 614,9 MiB / 1.839 |
| 1.000 / 1.000 | 1.000 | 3,37 / 6,25 / 6,51 s | 1,96 s | 3.003 | 759.000 B | 6,39 s / 780,2 MiB / 2.356 |
| 1.500 / 1.500 | 1.500 | 5,41 / 9,64 / 10,00 s | 1,96 s | 4.503 | 1.140.000 B | 8,77 s / 1.136,4 MiB / 3.388 |
| 2.000 / 2.000 | 1.312 | 5,23 / 9,62 / 10,00 s | 13,15 s | 6.003 | 1.431.936 B | 22,67 s / 1.182,5 MiB / 3.502 |

**Diagnóstico.** A falha registrada foi `connect ECONNREFUSED 127.0.0.1` no estabelecimento TCP, antes de um upgrade HTTP. Ela também ocorreu sem o proxy Wrangler. No diagnóstico direto inicial, o código anterior entregou a publicação a todos os 2.000 clientes e só 322 completaram a reconexão abrupta; a matriz após a revisão do contador completou 1.312. Distribuir a carga entre processos permite medir a saturação do gerador. No caso de 2.000 da matriz, a maior ocupação medida de um event loop gerador ficou abaixo de 9%, com 118.212 KiB de RSS máximo por gerador. O Windows reportou 16.384 portas TCP dinâmicas IPv4. A recusa apareceu na reconexão de um processo Workerd que permaneceu ativo. A medição identifica a etapa e o ambiente da falha. O motivo interno da recusa no listener Windows/Workerd, como backlog ou pressão nas filas de fechamento, permanece em aberto.

**Ajustes pontuais.** O Durable Object passou a manter a capacidade e presença por identificador de conexão. Ele reconstrói o conjunto ao sair da hibernação. Isso elimina a enumeração de todos os sockets a cada nova conexão. A publicação continua enviando um aviso pequeno; o snapshot continua versionado e conferido por ETag/hash. O cliente espaça a primeira tentativa de reconexão e só consulta HTTP após falhas repetidas de WebSocket. Retentativas usam backoff. A implantação segue com um único Durable Object por sala.

**Rodada final com 2.000.** Após ajustar a resposta ao fechamento anormal e o intervalo de retentativa, os 2.000 clientes receberam a revisão e os 2.000 reconectaram em uma rodada com quatro geradores e até três tentativas. As 1.396 recusas temporárias foram recuperadas. O p50/p95/p99 da publicação foi 5,22/9,63/10,03 s. Para reconexão, 3,79/25,04/26,84 s. Foram 2.003 requisições HTTP, 5.396 tentativas de upgrade e 1.520.000 bytes de payload, com CPU de 28,5 s, RSS de pico de 1.180,2 MiB e pico amostrado de 3.491 handles no Workerd. O ensaio anterior de fechamento normal com 2.000 clientes recuperou 400 e registrou 1.471 timeouts aguardando o fechamento, mais 129 recusas de TCP após as tentativas. Outro ensaio de reconexão abrupta, com apenas um gerador, recuperou 1.970; a falha apareceu com um ou com quatro geradores. Os resultados variaram com o padrão de fechamento e o espaçamento, portanto a rodada final serve como prova de recuperação local sob aquelas condições.

**Cotas e capacidade.** Em contas Workers Free, cada cota de 100.000 solicitações/dia é compartilhada pelas atividades da conta. No cenário de 2.000, 6.003 operações representam cerca de 6% de cada cota diária, como estimativa conservadora que conta todas as tentativas no transporte. O cenário inclui entrada, uma publicação e reconexão. Na prática cada participante faz um GET inicial para entrar, além dos upgrades. O limite local de 8.000 operações por IP em 60 s pode ser atingido numa rede que compartilhe um IP. Os avisos de saída por WebSocket e os pings de protocolo têm tratamento próprio na cobrança. A Cloudflare documenta um limite flexível de 1.000 solicitações por segundo por objeto individual e até 32.768 WebSockets hibernáveis por objeto, sujeito ao consumo do serviço. CPU, memória do isolate, duração faturada e capacidade real continuam por medir em conta autorizada. [Cotas de Workers](https://developers.cloudflare.com/workers/platform/limits/) · [Cotas e duração de Durable Objects](https://developers.cloudflare.com/durable-objects/platform/pricing/) · [Limites do objeto](https://developers.cloudflare.com/durable-objects/platform/limits/) · [WebSocket Hibernation](https://developers.cloudflare.com/durable-objects/api/state/).

## Procedimento pendente

1. Após aprovação, enviar o branch local ao repositório oficial, abrir PR, validar o workflow e confirmar o guia e o modelo públicos depois da integração. A distribuição pública para jogadores também requer uma versão desktop que inclua Live Sync.
2. Abrir **Configurar Cloudflare** em uma instância Azphelumbra com Live Sync. O proprietário escolhe sua conta Free e confirma a implantação no navegador. O assistente gera a chave de vinculação e o proprietário cola a chave na Cloudflare. Senhas e tokens administrativos permanecem com o proprietário.
3. Vincular o endpoint de produção, criar uma sala descartável, publicar um cenário de teste e entrar de outra instalação ou perfil. Confirmar HTTPS, WSS, persistência SQLite, revisão recebida, reconexão, revogação e encerramento.
4. Com duas instâncias do jogo ou dois jogadores, conferir pins e formas no mapa grande e minimapa. Encerrar a sala após o teste. Combinar uma rodada separada com limites definidos antes de aplicar carga em conta real.

O cliente se comunica com o Worker do caller. O GitHub do projeto hospeda o modelo e o guia; os snapshots das guildas ficam na conta que implantou o Worker.

## Arquivos

- [Cliente Live Sync](../app/modules/siege/live_sync.py), [assistente](../app/ui/live_sync_panel.py), [integração do overlay](../app/modules/overlay/service.py) e [testes Qt](../app/tests/test_live_sync.py).
- [Worker](../backend/live-sync/worker.mjs), [configuração](../backend/live-sync/wrangler.jsonc), [testes de protocolo](../backend/live-sync/worker.test.mjs), [teste de hibernação](../backend/live-sync/hibernation.test.mjs) e [medição local](../backend/live-sync/measure-local.ps1).
- [Guia PT-BR](../website/live-sync.md), [guia EN-US](../website/live-sync.en-US.md), [guia ES-419](../website/live-sync.es-419.md) e [HTML](../website/live-sync.html).
