# Medidor de dano experimental

O módulo Combate apresenta dano observado, DPS e participação do grupo.
A leitura e o dano básico foram testados em uma instância SA em 12/10/2026.
O parser permanece experimental: a precisão completa e a atribuição de todo
o dano do grupo ainda precisam de validação. Resultados parciais são indicados.

## Usar

1. Instale pelo novo Setup. Se Npcap não estiver disponível, o próprio fluxo
   baixa a cópia oficial verificada e abre o assistente do fabricante.
   Complete o assistente e suas permissões. Npcap não é redistribuído no ZIP.
2. Abra o Strigoi. A medição começa automaticamente quando Npcap está
   disponível e aguarda a conexão do jogo. Configurações permite desativá-la.
3. Confira o estado de leitura. A primeira versão detecta automaticamente
   um único cliente e suas conexões IPv4; VPNs e outros protocolos podem
   exigir correções após a validação. Nenhuma configuração de rede é alterada.
4. Depois dos primeiros golpes, escolha o alvo para a visão Só o alvo
   selecionado. Nomes de NPCs não são inventados: se não houver nome observado,
   o alvo aparece por ID. A instância é identificada pelo contexto recebido.
5. Use Encontro atual ou Instância inteira. Encerrar encontro separa uma
   tentativa; a morte do alvo selecionado também encerra esse encontro.
6. No menu rápido, clique no mascote e ative Painel de combate.
   O menu também controla Sonar, os dois mapas juntos e Painel de eventos.
   Arraste o mascote para mover o menu; sua posição é salva.
   Destrave o placar para mover/redimensionar e trave
   para os cliques passarem ao jogo. Restaurar painel recupera posição/tamanho.
7. Ocultar o painel não interrompe a medição. Fechar o aplicativo ou
   desativar Medir combate automaticamente nas Configurações encerra a captura.
   Resultados e tentativas ficam no
   Histórico, localmente; Copiar resultado só coloca texto na área de transferência.

No portátil, use o canal oficial https://npcap.com/#download para instalar
Npcap. O fluxo integrado está no Setup interativo; instalação silenciosa do
driver não é usada. Cancelar sua instalação não bloqueia Atlas ou Sonar.

## Métricas e limites

- Ordenação por dano total inteiro, antes do arredondamento; empates compartilham posição.
- DPS usa a mesma duração para os jogadores do encontro, incluindo inatividade.
- DPS da instância usa a soma das durações dos encontros, sem deslocamentos.
- Percentuais são sobre o dano observado da visão, incluindo Não atribuído.
- Dano de invocações só vai ao dono quando há vínculo identificado.
- Jogadores fora do roster reconhecido não entram no ranking do grupo.
- Identidades sem servidor são associadas ao grupo somente se o nome for
  único, sem outro jogador homônimo observado. Ambiguidades e membros ainda
  não decodificados ficam em Não atribuído; dados parciais permanecem indicados.
- Sem roster completo, dados ausentes ou lacunas, a indicação de parcial permanece.
- Enquanto a medição automática está habilitada, a próxima entrada reconhecida salva o
  resultado anterior e abre um placar zerado automaticamente. A saída para
  outro mapa encerra o resultado, mas mantém a escuta para a próxima entrada.
- Repetições do cronômetro, mudança da espera inicial para o limite da
  instância e teletransportes internos não zeram o placar. Uma nova ocorrência
  do cronômetro permite distinguir outra entrada no mesmo mapa.
- A classe vem da identidade ou do grupo recebido do jogo. O ícone aparece
  ao lado do nome na tabela e no painel; classe ausente usa símbolo neutro.
- A leitura continua aguardando a próxima instância. Se a conexão for
  interrompida, o app tenta retomá-la automaticamente enquanto estiver aberto.
- Sem informações de contexto suficientes, separe tentativas manualmente.
- Esta versão não mede cura, não reconstrói replay nem calcula ameaça.

O collector usa captura passiva via Npcap e um parser substituível. Não envia
pacotes, injeta código, altera arquivos ou lê a memória do jogo. Pacotes brutos
não são gravados. Só eventos normalizados chegam à UI. Captura começa ao
abrir o aplicativo quando a medição automática está habilitada e Npcap está
disponível; para ao desativar essa opção ou fechar o aplicativo.

O histórico usa `combat.sqlite` na pasta de dados do app, com até 200 resultados
de instância e suas tentativas. Não há upload ou conta online. Uma base
incompatível/corrompida é preservada e desabilita apenas o histórico de combate.

## Construção

O código próprio usa GPL-3.0-only. A captura e o parser reutilizam componentes
GPL com origem, revisão e alterações em `native/combat/vendor/NOTICE.md`.
As dependências de captura mantêm suas próprias licenças e avisos.

Instale .NET 10 SDK para construir o helper, execute `scripts/build-combat.ps1`
e faça o build PyInstaller habitual. O helper distribuído é autossuficiente;
o usuário não precisa instalar .NET. Npcap continua sendo componente externo.

`strigoi-combat.exe --probe` confere disponibilidade sem capturar.
`--self-test` usa somente bytes sintéticos rotulados e testa reconstrução TCP,
retransmissão, decodificação e rejeição de registro malformado. Isso não é
validação de protocolo SA. Não existe demo misturada à sessão real.

`--diagnose` verifica a conexão durante dez segundos e emite apenas estados
e contagens por tipo de evento. Não mostra nomes nem grava pacotes. Processos
de inicialização sem conexões não contam como outro cliente em execução.
