# Sonar de cubos

O sonar usa a amostra fornecida pelo usuário para procurar um som compatível
no áudio do aplicativo selecionado. É um recurso de acessibilidade auditiva:
um aviso visual permite acompanhar uma pista sonora durante a exploração.

## Usar

1. Abra o AION 2 e o Strigoi Aether Map.
2. Em **Sonar**, clique em **Atualizar aplicativos** e selecione o processo
   que reproduz o áudio do jogo. O nome escolhido é lembrado; o PID é atual.
3. Escolha **Equilibrada** ou **Alta** e clique em **Ativar sonar**.
4. Um cartão **Possível cubo por perto** aparece quando o detector confirma
   correspondências. O texto de orientação é **Procure nos arredores antes que
   outro jogador colete!**. A barra e o histórico acompanham a intensidade
   estimada do som reconhecido. O cartão permanece visível enquanto há novas
   correspondências e desaparece oito segundos após a última. Você pode
   movê-lo ou dispensá-lo.
5. Clique em **Parar sonar** para encerrar a captura. Fechar o app também
   encerra o componente nativo. O sonar nunca inicia sozinho ao reabrir.

**Testar aviso visual** exibe um cartão identificado como teste, sem capturar
áudio, sem mostrar uma leitura de intensidade e sem declarar uma detecção.
O aviso funciona com o mapa fechado e
independe da ativação do overlay visual. Não há alerta sonoro obrigatório.

O aplicativo escolhido e seus processos filhos são a fonte. Não há captura
pelo microfone, gravação permanente, upload ou leitura de memória do jogo.
Outros aplicativos não entram automaticamente na captura. O modo por
aplicativo não fica vinculado a um dispositivo físico de saída específico.

## Referência

Arquivo fornecido em 2026-10-12: `c8eb3f2d9330002d-hidden-cube-hum.mp3`.
SHA-256 original: `c8eb3f2d9330002dfd717cef8172489315c4f1d5f423f59a0878d6819b3374f2`.

O arquivo é MP3 mono, 44.100 Hz, com 6,44 segundos. A análise local encontrou
picos importantes próximos de 1,68 e 3,53 kHz, além de conteúdo acima de 8 kHz.
Na estimativa espectral, 90% da energia fica entre 1,35 e 10,31 kHz. O RMS do
arquivo é aproximadamente -21,10 dBFS; isso não mede o volume no jogo.

A distribuição contém sua conversão PCM em `assets/sonar/cube-reference.npz`
e os metadados em `assets/sonar/reference.json`. O MP3 original permanece
na área de trabalho local. Origem regional, exclusividade do som e ciclo
completo de repetição não foram verificados. Direitos permanecem com seus
titulares; a amostra não recebeu uma licença própria inventada pelo projeto.

## Detecção de som baixo

O helper C++ próprio usa WASAPI process loopback e envia float32 48 kHz
estéreo ao worker por pipe. Preservar float32 evita quantizar prematuramente
um sinal muito baixo. O processamento ocorre fora da thread da interface.

Cada canal é analisado separadamente. O detector estima o fundo espectral,
reduz o peso das faixas ruidosas e aplica correlação ponderada com trechos de
dois segundos da referência. A janela recente tem 3,25 segundos; a análise
ocorre aproximadamente a cada 350 ms de PCM novo. O buffer é limitado.

São necessárias correspondências de pelo menos dois trechos com alinhamento
consistente e confirmação em análises sucessivas. Um controle com trechos
invertidos no tempo reduz confusão com efeitos que compartilhem o espectro,
mas tenham outra ordem temporal. Mensagens vazias de manutenção do pipe não
apagaram a confirmação após a correção validada no teste nativo.

O intervalo entre avisos é de pelo menos 15 segundos. O detector considera
o áudio processado e o worker mantém também um limite de tempo real, que
continua valendo quando uma descontinuidade reinicia a referência temporal.
Silêncio e PCM inválido não geram detecção. Descontinuidade reinicia a
referência temporal. Sensibilidade alta reduz o limiar e pode gerar mais
avisos. O score interno não é uma probabilidade nem aparece como certeza
percentual na interface. A filtragem não altera o áudio ouvido pelo usuário.

## Intensidade do som reconhecido

A barra e o histórico de 15 segundos aparecem na página **Sonar** e no aviso
flutuante. As leituras continuam durante o intervalo entre notificações.
**Fraco**, **Moderado** e **Forte** descrevem o sinal estimado; cores e texto
acompanham a barra. O volume configurado no jogo também muda a leitura.

O cálculo usa o ganho da referência no ponto de correlação correspondente,
ponderado pelas mesmas faixas espectrais usadas na detecção. O ganho é a
correlação dividida pela energia ponderada da referência. Multiplicá-lo pelo
RMS da referência produz uma estimativa de nível em dBFS. Esse cálculo é
independente do score normalizado e do RMS total da mistura. A barra usa uma
escala fixa de -80 a -20 dBFS; o indicador não se ajusta automaticamente para
encher quando o som está fraco.

A leitura exige confirmação temporal. Sem uma correspondência recente,
o indicador volta a **Aguardando sinal**. Parar a captura ou receber uma
descontinuidade descarta o estado anterior. O histórico fica somente na
memória. Fechar o aviso não faz cada nova leitura reabri-lo.

A estimativa não separa perfeitamente todos os efeitos e não mede distância,
direção ou altura do cubo. Ela acompanha a força da assinatura reconhecida,
com latência de análise e suavização, e pode perder a correspondência em
áudio mascarado. A relação entre essa barra e a proximidade no jogo ainda
precisa de validação em partidas reais.

## Evidência e limites

Testes controlados reconheceram a amostra misturada a ruído branco nos
níveis 0, -10, -20 e -30 dB de relação sinal/ruído. O caso de -40 dB não
foi reconhecido no ensaio exploratório. Controles de silêncio, ruído,
dois tons próximos dos picos e amostra invertida não alertaram após o ajuste.
Esses são controles sintéticos, não uma estimativa de precisão no jogo.

O caminho Windows → helper → detector → sinal Qt foi exercitado com áudio
muito baixo de um processo próprio, com ruído e referência em -20 dB e
num segundo ensaio em -30 dB, usando sensibilidade equilibrada. Houve
um aviso e a parada encerrou o helper com código zero. Nenhum cliente AION 2
foi capturado nesse teste. Em gravações reais ainda faltam medir falsos
positivos por hora, recall, latência, CPU, efeitos parecidos, combate,
reverberação e variações de reprodução/volume. A mesma amostra atenuada não
substitui validação independente em SA.

Não há separação perfeita da mistura, localização, direção ou distância.
Se o som for mascarado, não for reproduzido ou compartilhar a assinatura
com outro efeito, o sonar pode falhar ou avisar indevidamente. A amostra
mono não demonstra pistas espaciais. Use o aviso como apoio à exploração.

## Construir

O helper exige ferramentas C++ x64 do Visual Studio e Windows SDK.
`scripts/build-sonar.ps1` compila `native/sonar_capture.cpp` e atualiza o
executável em `app/assets/sonar`. A versão portátil já inclui esse arquivo.
O sistema deve ser Windows 10 build 20348 ou posterior, incluindo Windows 11.
O áudio recebe parada por EOF no pipe de entrada; o encerramento do processo
selecionado também interrompe a captura. Os pipes têm formato e tamanho
validados; falhas encerram o sonar e solicitam nova ativação.

## Referências

- [Microsoft: captura de áudio por aplicativo](https://learn.microsoft.com/en-us/samples/microsoft/windows-classic-samples/applicationloopbackaudio-sample/).
- [MIT: detecção de sinais e filtro casado em ruído, capítulo 14](https://ocw.mit.edu/courses/6-011-introduction-to-communication-control-and-signal-processing-spring-2010/61ec3ac814f18a1f05b4ce0c90e89282_MIT6_011S10_chap14.pdf).
- [SciPy: análise espectral por janelas](https://docs.scipy.org/doc/scipy/tutorial/signal.html).
- [NumPy: definição e normalização das transformadas FFT](https://numpy.org/doc/stable/reference/routines.fft.html).
