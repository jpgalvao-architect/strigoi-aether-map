# Backend do Live Sync

Projeto independente de Cloudflare Workers. O botão **Implantar na Cloudflare** no Azphelumbra copia este diretório para a conta do caller. O arquivo `wrangler.jsonc` provisiona um binding de Durable Objects com SQLite. Consulte o [guia de configuração do Live Sync](https://jpgalvao-architect.github.io/strigoi-aether-map/live-sync.html).

O aplicativo usa Deploy to Cloudflare porque a distribuição de um cliente OAuth para contas de terceiros exige registro do cliente público e domínio verificado. O app prova que a implantação conhece a chave de vinculação sem transmitir a chave por HTTP ou WebSocket. [Registro de clientes OAuth da Cloudflare](https://developers.cloudflare.com/fundamentals/oauth/create-an-oauth-client/).

## Contrato v1

| Pedido | Permissão | Resposta |
| --- | --- | --- |
| `GET /v1/health` | Pública | Protocolo e presença de uma chave válida |
| `GET /v1/setup/:nonce` | Pública, upgrade WebSocket | `ready` com HMAC-SHA256 de `setup-v1:<nonce>`. A resposta vem de um Durable Object SQLite |
| `POST /v1/sessions/:id` | Prova de vinculação | Cria a sessão na versão 0 |
| `GET /v1/sessions/:id` | Publicação | Versão e quantidade de sockets de jogadores |
| `GET /v1/sessions/:id/watch` | Leitura ou publicação | Upgrade WebSocket. Mensagens `version`, `revoked` e `closed` |
| `GET /v1/sessions/:id/snapshot` | Leitura ou publicação | Preset v3, `X-Siege-Version` e ETag SHA-256. `204` antes da primeira publicação e `304` se a ETag coincide |
| `PUT /v1/sessions/:id/snapshot` | Publicação | Recebe o preset v3 e `X-Base-Version`. Retorna `409` com a revisão atual em caso de conflito |
| `PUT /v1/sessions/:id/invite` | Publicação | Recebe a nova chave de leitura como texto ASCII. Revoga a anterior |
| `DELETE /v1/sessions/:id` | Publicação | Remove o snapshot, fecha os sockets e encerra a sessão |

O identificador usa 16 bytes aleatórios em hex. As chaves de leitura e publicação são distintas, cada uma com 32 bytes aleatórios em hex. Use `Authorization: Bearer <chave>` nas chamadas de sessão. Na criação, o corpo contém `reader`, `publisher` e `time` (Unix em milissegundos). O bearer é o HMAC-SHA256 de `create-v1:<id>:<time>:<reader>:<publisher>`, calculado com a representação ASCII de `LIVE_SYNC_OWNER_KEY`. A assinatura expira em cinco minutos. A chave de vinculação fica no segredo do Worker e protegida pelo DPAPI no Windows. A sessão armazena apenas os hashes das chaves de leitura e publicação.

Um convite usa `azphelumbra-live:v1:https://worker.conta.workers.dev#<id>.<reader>`. Esse texto fica no Azphelumbra. Após extrair os campos, o cliente usa HTTPS/WSS e envia a credencial de leitura no cabeçalho. O Worker rejeita origens de navegador. Os códigos de seis caracteres na interface servem para identificar a sessão.

A publicação grava o snapshot e o número da revisão em uma operação SQLite, compara a revisão-base e limita novos envios a um por 1,5 segundo. Corpos acima de 512 KiB são recusados. É permitido repetir os mesmos bytes sem criar revisão duplicada. O Worker usa a API de hibernação para notificar os sockets com a revisão e o hash. O cliente confirma a integridade antes de aplicar o preset, espalha os downloads com jitter e recupera a revisão atual ao reconectar. O limite configurado por sessão é de 2.500 conexões de jogadores. Ele é um limite do app, sujeito aos limites da plataforma.

O snapshot fica no Worker até o caller encerrar a sessão ou até o alarme após 12 horas. A cópia recebida fica em memória no aplicativo. Use **Gerar novo convite** para revogar a leitura. A troca do segredo do Worker revoga a capacidade de criar sessões com a chave anterior. Para revogar uma sessão já criada, encerre a sessão ou remova o Worker.

## Desenvolver e testar localmente

Com Node.js e npm, execute na pasta do backend:

```powershell
npm ci
npx wrangler dev --local --ip 127.0.0.1 --port 8976 --var ('LIVE_SYNC_OWNER_KEY:' + ('a' * 64))
```

Em outro terminal, execute `npm test`. Na raiz do projeto Python, defina `AZPHELUMBRA_LIVE_SYNC_LOCAL_TEST=1` para executar também o teste de integração Qt em `app/tests/test_live_sync.py`. O valor acima é público e serve para o emulador local.

Para desenvolvimento com uma conta própria e autorização explícita, `npx wrangler login` abre o consentimento no navegador. Depois use `npm run deploy` e `npx wrangler secret put LIVE_SYNC_OWNER_KEY` para implantar este mesmo modelo e registrar a chave que o Azphelumbra gerou. O assistente do app permite usar o endereço criado. Para remover essa implantação, confirme a conta e o nome do Worker no painel antes de excluí-lo.

## Testes de carga

Use um ambiente local isolado. No Windows, execute na pasta do backend:

```powershell
npm ci
./measure-local.ps1
./measure-local.ps1 -Participants 2000 -Generators 1
./measure-local.ps1 -Participants 2000 -Close graceful
```

A matriz cobre 100, 250, 500, 750, 1.000, 1.500 e 2.000 conexões num Workerd novo a cada cenário. O script reúne CPU, memória e handles do runtime local, CPU e uso do event loop dos geradores, falhas por etapa, p50/p95/p99, solicitações, reconexões e bytes de payload. Os relatórios vão para `.wrangler/load/`. Use `-Stride` para espaçar as tentativas e `-ReconnectAttempts 1` para medir a primeira tentativa isolada. O gerador também roda contra o Wrangler local com `npm run load -- 1000 4`.

Os bytes excluem cabeçalhos, frames, compressão e TLS. O script rejeita destinos fora de loopback. A avaliação de uma conta Cloudflare exige autorização e um limite separado de carga. Na raiz do repositório do Azphelumbra, consulte `docs/LIVE_SYNC_VALIDATION.md` para os resultados e a pendência de produção.
