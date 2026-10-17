# Pets

A aba **Pets** reúne o catálogo, os favoritos e seu progresso. A versão
0.10.0-beta.4 inclui retratos originais de 208 pets. O catálogo de referência
não garante que todos estejam disponíveis na sua região.

## Sincronizar a coleção

1. Abra o Azphelumbra. O contador também funciona com o personagem já logado.
2. Na aba **Pets**, confirme a região e deixe **Sincronizar com o jogo** ativo.
3. Favorite os pets que deseja acompanhar. Os ganhos recebidos aparecem como
   **+N almas nesta captura**, mesmo antes de conhecer o total da coleção.
4. Abra os detalhes de um pet no jogo: o app lê **Pet Insight**, as almas e
   o total exibido, sem preencher campos ou importar arquivos. Duas leituras
   iguais confirmam o valor. Na tela em inglês, lê `Lv. 2 (63/75)` como
   **Insight 2, 63/75 almas**, sem confundir com o nível de família.
5. Depois dessa leitura, o contador acompanha o total e os próximos ganhos.
   O total lido já inclui as coletas anteriores; elas não são somadas novamente.

A leitura da conexão usa Npcap, compartilhado com Combate e Rotina. O leitor
visual reutiliza a captura dos menus e só analisa os detalhes quando o menu
Pets é reconhecido. Imagens e texto da
tela ficam na memória, sem gravação. Desativar a
sincronização não apaga sua coleção. A coleção manual funciona sem Npcap.
Os perfis ficam separados por região, servidor e personagem. Os dados
permanecem neste computador e não são enviados a um serviço de coleção.

Se a captura começou depois do login e a identidade do personagem não chegou,
os ganhos e a leitura da tela ficam apenas na captura atual, sem alterar um
perfil salvo. Para salvar a sincronização por personagem, abra o app antes
de entrar nele. Uma reconexão ou troca de personagem reinicia os ganhos dessa
captura. Ganhos recebidos não comprovam o total quando a leitura inicial falta;
após uma interrupção, o contador de ganhos pode ser parcial.

**Pet Insight** é diferente do nível da família mostrado no jogo. Uma
informação ainda não recebida aparece como desconhecida, sem presumir zero.
**Ajustar manualmente** é uma alternativa: o valor manual fica guardado,
mas uma leitura confirmada da tela passa a mostrar o valor atual do jogo.
O painel distingue registros manuais ou salvos dos sincronizados.
**Importar coleção** preserva uma cópia anterior;
**Exportar coleção** permite fazer seu próprio backup.

O snapshot inicial foi conferido em SA em duas entradas. Ganhos de almas de
Kailin e Duduka foram recebidos ao vivo em SA. Evoluções ainda precisam de
conferência ao vivo. Se houver perda de dados ou uma evolução que não
possa ser conciliada, reabra os detalhes desse pet para sincronizar o total.
As prints SA fornecidas pelo usuário foram lidas como 62/75 e 63/75; a
sequência tela → coleta também passou em testes controlados. A captura ao
vivo após instalar esta correção ainda precisa ser conferida.

## Escolher o que acompanhar

Busque pelo nome do pet ou de um monstro. Use os filtros de família, mapa,
progresso e favoritos. Escolha uma meta de Insight e marque **Favorito**.
Um favorito continua marcado depois de ser adquirido.

Ative **Mostrar painel de pets** ou use a opção **Painel de pets** no menu
rápido. O painel acompanha os favoritos: recolhido mostra uma linha;
expandido mostra até três e permite rolar pelos demais. Arraste pelo título,
trave a posição e ajuste a opacidade na aba Pets. **Restaurar painel** traz
um painel perdido de volta à área visível. Fechá-lo mantém a sincronização.
Alt+Tab e menus reconhecidos ocultam o painel temporariamente.

## Encontrar locais de farm

Use **Ver locais no Atlas** no detalhe de um pet. A camada Pets pode aparecer
junto de cubos e coletas e segue as mesmas escolhas nos overlays dos mapas.
O filtro **Nos mapas** permite acompanhar todos, favoritos ou metas pendentes.

Os 11.624 locais são referências documentadas de monstros nos mapas completos
de Altgard e Verteron, identificadas como posições possíveis. A presença atual
e a compatibilidade regional não foram certificadas. Pets sem local conhecido
continuam consultáveis sem criar um marcador inventado.

Esta versão acompanha a coleção e os locais de referência. Ainda não rastreia
NPCs em movimento nem apresenta distância ou direção de um radar ao vivo.
Fontes e direitos estão em [SOURCES.md](SOURCES.md) e `THIRD_PARTY.md`.
