# Instalação • 0.8.0

Execute `StrigoiAetherMap-Setup-0.8.0.exe`. O primeiro diálogo permite escolher
Português Brasileiro ou English. A tela de termos exige marcar o aceite;
a caixa começa desmarcada. Sem aceite, não é possível avançar para instalar.
Os termos gerais vêm primeiro, seguidos da descrição técnica e, na seção 5,
das condições sobre decisões da operadora e sanções na conta.

A instalação é por usuário, sem pedir administrador, com aplicativo em
`%LOCALAPPDATA%\Programs\StrigoiAetherMap`, atalho no menu Iniciar e atalho
opcional na área de trabalho. O instalador inclui os textos de licença e
o ZIP do código-fonte correspondente. Não instala Python globalmente e
não altera o diretório do AION 2. Feche o Strigoi antes de atualizar.

A versão dos termos, hash dos dois textos e idioma do instalador ficam
no registro HKCU, sob `Software\StrigoiAetherMap`. Não são enviados a um
servidor. O idioma inicial é lido de `installation.json` no diretório de dados.
Uma preferência de idioma já salva pelo usuário tem prioridade.
**Configurações → Idioma do aplicativo** troca a interface imediatamente;
a região SA e o fuso da agenda permanecem inalterados.

Remova o aplicativo em Aplicativos instalados do Windows ou pelo atalho
Uninstall. O desinstalador remove somente os arquivos registrados no build,
preservando arquivos desconhecidos e `%LOCALAPPDATA%\StrigoiAetherMap`
(preferências, atlas local, visitas e logs). Não usa exclusão recursiva
indiscriminada de uma pasta escolhida pelo usuário.

O executável é uma distribuição local sem assinatura de editor. Os hashes
da entrega ficam em `SHA256SUMS.txt`. O instalador precisa de Windows x64;
o Sonar exige as APIs de áudio documentadas em `SONAR.md`.

## Reconstrução

1. Reconstrua o aplicativo com o ambiente e scripts do README.
2. Prepare a pasta portátil completa: docs, avisos, LICENSE,
   LICENSE-NOTICE.md e `source/strigoi-aether-map-source.zip`.
3. Instale NSIS Unicode 3.12 ou compatível. Execute:

```powershell
.\scripts\build-installer.ps1 -Payload 'C:\build\StrigoiAetherMap' -Python '.\.venv\Scripts\python.exe'
```

`prepare-installer.py` gera os RTFs em português/inglês, hash dos termos e
lista exata de remoção, e compila o script em `installer/StrigoiAetherMap.nsi`.
Os termos originais estão em `app/assets/legal/`. Nenhuma biblioteca ou arquivo
do jogo participa da montagem.

Instalação silenciosa exige `/S /ACCEPTTERMS` e aceita `/LANG=en_US` ou
`/LANG=pt_BR`. Sem o parâmetro de aceite, termina com código 2 sem instalar.
O operador deve ler os termos antes de autorizar esse modo.
`--test-build` cria um instalador isolado com chave de registro separada e
sem atalhos; não deve ser distribuído aos usuários.

## Licença e limites dos termos

O usuário escolheu GPLv3 para o código próprio. A licença integral permanece
inalterada, separada dos termos e das licenças de terceiros. Os termos não
criam restrições adicionais às permissões da GPL.

A limitação de responsabilidade é condicionada à lei aplicável, sem promessa
de isenção absoluta. Os artigos 25 e 51 do
[Código de Defesa do Consumidor](https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm)
limitam cláusulas de exoneração quando esse regime é aplicável.
O texto usa ressalva aos direitos legalmente assegurados; revisão jurídica
é indicada antes da distribuição pública.

Referências técnicas: [NSIS Modern UI 2](https://nsis.sourceforge.io/Docs/Modern%20UI%202/Readme.html),
[GPLv3 oficial](https://www.gnu.org/licenses/gpl-3.0.html).
