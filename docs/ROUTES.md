# Rotas de farm

Abra **Rotas** na barra lateral ou use **Criar rota** no Atlas, nas Coletas
ou nos detalhes de um pet. O módulo usa os locais cadastrados no Atlas.

## Criar uma rota

1. Escolha o mapa e um ou mais alvos, como Azpha, cubos ou almas de pets.
2. Escolha **Circuito**, para retornar ao início, ou **Só ida**.
3. Ajuste o número de paradas. O planejador agrupa locais próximos e sugere
   uma ordem de visita. **Marcar início** permite escolher a primeira parada.
4. Confira a prévia. Use **Ajustar trajeto** para inserir passagens entre os
   pontos; **Desfazer ajuste** recupera a edição anterior.
5. Use **Salvar** para manter a rota neste computador ou **Iniciar no
   minimapa** para acompanhar o percurso.

Sem locais cadastrados para seu alvo, use **Marcar meus pontos**. Essa opção
inicia um novo percurso com os locais que você marcar no mapa. São necessários
pelo menos dois. **Minhas rotas** permite carregar, excluir, importar e
exportar rotas em JSON. Arquivos importados aceitam até 16 MB.

## Acompanhar no jogo

O trajeto aparece no minimapa e no mapa grande pelo mesmo reconhecimento do
overlay. O número destacado indica a próxima parada. Se ainda não selecionou
a área do minimapa, o app abre a seleção ao iniciar a rota.

O personagem ocupa o centro do terreno do minimapa; apenas o compasso gira.
Com o jogo em primeiro plano e o terreno reconhecido, o app projeta esse centro
no Atlas e acompanha as paradas automaticamente. Não é necessário indicar
ou calibrar a seta. Ícones e o número da parada podem cobri-la sem interromper
a posição. No mapa grande, o acompanhamento fica suspenso: seu centro pode
ser deslocado e não representa a posição do personagem.

Selecione somente o terreno do minimapa, sem o título e os controles abaixo.
Se mudar a resolução, a escala ou o monitor, selecione essa área novamente.

O guia **Fio** mostra o alvo e a parada em uma faixa de 303 × 38 pixels.
Nas opções **···**, alterne para **Guia**, com uma segunda linha de estado.
Você pode pausar, retomar, pular uma parada, repetir ou encerrar a rota.
Arraste o guia para reposicioná-lo. O menu rápido permite ocultá-lo sem
encerrar o percurso.

O avanço exige leituras atuais e cerca de 0,35 segundo próximo à parada. Menus,
Alt+Tab ou perda do reconhecimento interrompem o acompanhamento e preservam
o progresso. Trocar de área ou personagem pausa a rota até você retomá-la.
Sem leitura confiável, use **Pular parada** para avançar manualmente.

## Conferir passagens

Linhas tracejadas são ligações geométricas sugeridas. O app não possui uma
rede de estradas transitáveis e não conhece todos os muros, penhascos ou
desníveis. Uma linha não garante que seja possível caminhar por ela.

Depois de ajustar ou registrar um trecho, confira-o no jogo e marque
**Conferi as passagens ajustadas**. Só esses trechos ficam contínuos e podem
ser reaproveitados pelo planejador no mesmo sentido e entre os mesmos locais.
Rotas importadas exigem nova conferência.

**Gravar meu percurso** registra apenas coordenadas reconhecidas. Inicie a
gravação antes de visitar a primeira parada. Um trecho interrompido por perda
de leitura não é ligado ao próximo. Use **Revisar percurso registrado** para
ver os trechos completos e salvar uma nova rota após conferi-los.

## O que os indicadores significam

- Paradas visitadas não confirmam coleta nem aumentam contadores de itens.
- Pontos do Atlas são referências; a presença atual depende do jogo.
- Os 150 locais de Azpha em Altgard vêm da base comunitária, sem confirmação
  individual em SA.
- Não há estimativa de distância em metros, rendimento, respawn ou tempo de
  chegada. O módulo não move o personagem nem envia comandos ao jogo.
- A projeção, a gravação e o avanço passaram em testes controlados. A posição central e a passagem do ponto 1 ao 2 foram conferidas
  em testes controlados; uma rodada de movimento em SA ainda está pendente.

Rotas salvas ficam em `routes.json` na pasta de dados do app. O percurso ativo
não é retomado automaticamente ao reabrir o programa. A frequência escolhida
em **Overlay → Fluidez do overlay** continua sendo usada.
