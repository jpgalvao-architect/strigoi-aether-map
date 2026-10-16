# Rotina

O Panorama reúne os personagens identificados pelo jogo e mantém os saldos
de Energia de Odyle básica e recarregada separados. Os registros ficam neste
computador, por personagem, servidor e região.

## Sincronizar

1. Abra o Azphelumbra antes de entrar no personagem. O Npcap precisa estar
   instalado para a leitura automática.
2. Entre no jogo e abra **Rotina** no menu lateral.
3. Aguarde a identificação do personagem e o saldo inicial. Se o app foi
   aberto depois do personagem, volte à seleção e entre novamente.

O saldo pode chegar antes do nome. O app espera a identificação seguinte
antes de associá-lo. Uma informação não recebida aparece como
**Aguardando leitura**; um zero recebido do jogo aparece como zero.

**Registro salvo** mostra uma leitura anterior, com seu horário. A Rotina
não estima reposição enquanto o personagem está desconectado.

## Escolher o overlay

1. Abra **Personalizar Rotina** e ative **Mostrar overlay da Rotina**, ou use
   a opção **Rotina** no menu rápido do emblema.
2. Escolha **Pulso compacto** ou **Faixa** e os recursos que quer acompanhar.
3. Durante o jogo, use o ícone de layout para alternar os estilos. A seta
   recolhe ou expande o painel; o cadeado trava a posição.

Arraste pelo título ou emblema. A escolha de estilo, os recursos, a trava e
a posição ficam salvos. Os overlays seguem a ocultação por Alt+Tab e pelos
menus reconhecidos. Ocultar o painel não desliga a sincronização.

O overlay acompanha o personagem em jogo. Consultar outro registro no
Panorama não troca o personagem medido.

## Escopo desta versão

A lista inicial de Odyle básica e recarregada foi conferida em uma entrada
real em SA. As atualizações absolutas e as formas com um componente zerado
têm testes controlados; a conferência de consumo em SA é registrada
separadamente. Não há limites, previsão de recarga, resets ou contadores
de dungeon, chave e arena presumidos a partir de outras regiões.

A leitura é passiva e compartilha o mesmo coletor de Combate e Pets. Ela não
consulta uma API pública de personagem, não envia comandos ao jogo e não
grava pacotes brutos. Desative **Sincronizar automaticamente com o jogo**
em **Personalizar Rotina** para desligar apenas esse consumidor.
