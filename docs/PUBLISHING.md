# Repositório, downloads e página

Repositório: https://github.com/jpgalvao-architect/strigoi-aether-map

Site: https://jpgalvao-architect.github.io/strigoi-aether-map/

O HTML está em `website/`. Não depende de framework, APIs, cookies de análise
ou compilação. A escolha de idioma do site usa somente armazenamento local
do navegador. Os downloads e doações acessam serviços externos ao clicar.
As telas exibidas são renderizações reais do aplicativo em dados de teste
isolados; não são mockups nem capturas da sessão pessoal do usuário.

GitHub Pages publica somente `website/` por meio do workflow
`.github/workflows/pages.yml`, em alterações de site na branch `main`.
O código do aplicativo fica no repositório, e instalador/portátil ficam nas
Releases, evitando colocar pacotes grandes no histórico Git.

## Nova versão

1. Verifique o aplicativo e os pacotes antes de publicar.
2. Crie uma tag/release com a versão, anexando instalador, portátil, ZIP de
   código-fonte, `SHA256SUMS.txt` e manifesto da entrega.
3. Atualize os links/versão/tamanhos em `website/index.html` e `downloads.json`.
4. Atualize as telas do app quando houver mudanças visuais.
5. Mantenha `website/terms.html` e os TXT consistentes com os termos do
   instalador. Mudanças nas condições precisam de nova versão dos termos.
6. Envie as mudanças para `main`; acompanhe o job Publish app website e
   confira o site e os links dos arquivos após a publicação.

O pacote 0.8.0 mantém os binários e hashes já validados antes da página ser
criada. Seu ZIP de fontes contém o código correspondente ao aplicativo;
o repositório acrescenta a página e a configuração de hospedagem.

Não publique dados pessoais, ambientes virtuais, logs, notas locais,
chaves ou credenciais. `.gitignore` exclui esses itens. As licenças de mapas,
dados e terceiros continuam separadas da GPLv3 do código próprio.
