# Dependências e avisos de terceiros

O código e os assets estão separados das dependências. Aether é o mascote próprio desta versão; as ilustrações foram geradas para o projeto e os ícones SVG foram desenhados no código. A referência anterior é apenas inspiração e permanece no código-fonte para rastreabilidade. Dados comunitários derivados de Aion2 Interactive Map, de Yihao Liu (tc-imba) e colaboradores, seguem CC BY-NC 4.0 (uso não comercial). Veja docs/SOURCES.md para atribuição, alterações e limites. As imagens reais dos mapas foram distribuídas por problem-xyz com atribuição a CC BY-NC 4.0 e ressalva dos direitos da NCSOFT; seu NOTICE acompanha third-party-notices/map-art. A licença dos dados não se aplica ao mascote nem ao código próprio. O usuário escolheu GPLv3 para o código próprio; o escopo está em LICENSE-NOTICE.md e o texto integral em LICENSE.

A 0.5.0 adapta também os 2.811 locais possíveis de cubos dos conjuntos de objetos com licença separada CC BY-NC 4.0. A adaptação normaliza percentuais, conserva os identificadores da fonte com prefixo de mapa e acrescenta notas de origem/altura relativa. Esses dados não garantem presença simultânea nem confirmação regional SA. O NOTICE original permanece intacto; a licença do código do aplicativo de referência não foi usada para copiar sua implementação.

`third-party-notices/manifest.json` registra versões, metadados de licença e os avisos encontrados nas distribuições instaladas. Os textos de licença disponíveis foram copiados para essa pasta. PySide6/Qt, shiboken, Python, OpenCV, NumPy, Pydantic, MSS, tzdata e dependências transitivas mantêm seus respectivos termos. PyInstaller é a ferramenta de empacotamento; seu bootloader é incluído no executável.

A distribuição usa DLLs Qt externas na pasta `_internal`, sem integração estática. Preserve essa pasta e os avisos ao copiar o build. A entrega local não realiza publicação comercial nem substitui revisão de obrigações de distribuição, fornecimento de fontes/relink e licenças de assets externos quando houver lançamento público. O arquivo `README.md` descreve como reconstruir o app.

Nenhum nome, marca ou associação oficial com os titulares de AION 2 é reivindicado. Os nomes do jogo citados identificam apenas o propósito do companion.

## Leitura de Odyle • 0.10.0-beta.2

O leitor C# de Odyle segue os layouts GPLv3 de taengu/A2Tools-DPS-Meter,
commit `db1cea2d7ec75dbc78c2f31171115cbb733a3886`. Origem, funções de referência
e adaptações estão em `native/combat/vendor/ODyle-PROTOCOL-NOTICE.md`.
O vínculo por personagem, armazenamento, Panorama e overlays são próprios.
O aviso e a GPLv3 acompanham o código-fonte correspondente.

## Ícones de classes • beta 9

Os ícones das oito classes do catálogo Global vêm da página oficial de
informações de personagens da NC Corporation, sem redesenho ou recoloração.
Esses PNGs são imagens do jogo e mantêm os direitos de seu titular,
separados da GPLv3 do código. Fonte, correspondência e hashes constam em
`data-sources/class-icons.json`; o aviso acompanha `third-party-notices/class-icons/`.
Classes sem uma imagem verificada usam o símbolo neutro.

## Referência sonora • 0.7.0

A amostra `c8eb3f2d9330002d-hidden-cube-hum.mp3` foi fornecida pelo usuário
como efeito extraído de AION 2. O arquivo original fica na área de trabalho
local. A distribuição inclui uma conversão PCM para o detector, cuja origem
e hash original constam em `app/assets/sonar/reference.json`. Não foi atribuída
uma licença própria nem confirmação regional ao efeito. Direitos sobre o
áudio do jogo permanecem com seus respectivos titulares. O helper C++
de captura é implementação própria da API do Windows; seu fonte acompanha
`native/sonar_capture.cpp`. Não houve cópia do aplicativo de referência.

## Instalador e traduções • 0.8.0

O instalador/desinstalador usa NSIS Unicode 3.12, sem modificar seus
componentes. O aviso integral e os links de fontes acompanham
`third-party-notices/NSIS/`. As licenças do núcleo e módulo de compressão
permanecem separadas da GPLv3 do script de instalação próprio.

`qtbase_pt_BR.qm` vem da instalação PySide6/Qt 6.12 e mantém os termos do Qt.
O catálogo `en_US.json` e os controles de tradução são próprios do projeto.

## Combate experimental

O helper `strigoi-combat.exe` reutiliza os componentes de captura, eventos,
GameData e protocolo de cyberbadger6969/aion2-dps-meter, commit
414de5c1d5f3d45ce35701bd25229c2dba736bb6, sob GPL-3.0. Fonte completo dos
componentes usados, licença, origem e alterações em `native/combat/vendor/`.
O motor de ranking e a UI do Strigoi são próprios; não foram incorporados
catálogos de nomes, UI ou funções de envio online do projeto de origem.

SharpPcap 6.3.1 mantém MIT, PacketDotNet 1.4.8 mantém MPL-2.0 e
K4os.Compression.LZ4 1.3.8 mantém MIT. O helper inclui runtime .NET; os
avisos e URLs das fontes estão em `app/assets/combat/notices/`.
Npcap é obtido diretamente do fabricante pelo usuário durante a instalação,
com assistente e aceite próprios; o componente não é embutido na distribuição.

## Coleção de pets

Os retratos PNG de 208 pets são cópias intactas do CDN oficial de dados de
AION 2 da NC Corporation. As imagens mantêm os direitos de seu titular,
separados da GPLv3. URLs e hashes constam em `data-sources/pet-portraits.json`;
o aviso acompanha `third-party-notices/pet-portraits/`.

Nomes, famílias, custos de Insight, monstros e locais são fatos extraídos das
páginas de dados do cliente publicadas por aion2.app, com fonte por registro.
São referências do cliente de 18 de setembro de 2026, não uma certificação
de disponibilidade em SA. O aplicativo não incorpora textos de guias,
código da interface ou imagens modificadas desse site.

Os leitores de coleção, ganho de almas e nível foram implementados a partir
dos layouts GPLv3 identificados em `native/combat/vendor/PET-PROTOCOL-NOTICE.md`.
A coleção, a interface e o armazenamento local do Strigoi são próprios.
