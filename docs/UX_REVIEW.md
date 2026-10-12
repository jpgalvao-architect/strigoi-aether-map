# Rodada de UX • 0.6.0

Revisão e implementação em 12/10/2026, com inspeção da interface nativa.

| Antes | Depois |
|---|---|
| Navegação em inglês com símbolos de fonte | Início, Atlas, Coletas, Cubos ocultos, Eventos, Configurações, Overlay e Sobre; ícones vetoriais próprios |
| Textos sobre funcionalidades futuras e origem do mascote na UI | Conteúdo centrado em explorar, registrar visitas e acompanhar eventos |
| Aviso de anticheat no Sobre | Descrição breve do produto e acesso a fontes/créditos; sem alegar garantia universal de compatibilidade |
| Referência anterior como identidade visual | Mascote Aether próprio, com avatar correspondente |
| Painel flutuante com três textos | Próximo evento ou agenda completa do dia, cartões, ícones, contagem regressiva e botão de expansão |
| Detalhes técnicos sempre expostos | Origem/coordenadas opcionais; precisão e taxas do overlay em Ajustes avançados |
| Configuração de provider na tela principal | Agenda personalizada recolhida; horários e painel flutuante em primeiro plano |

O painel pode ser movido pelo cabeçalho, fechado e ativado em Eventos ou
Overlay. Expansão e posição persistem; posição restaurada é limitada à área
disponível do monitor. A agenda do dia inclui horários anteriores e futuros,
sem misturar o dia seguinte; a vista compacta pode indicar Amanhã quando
o próximo evento cair no dia seguinte. O fuso segue as Configurações.

Validação: navegação, controles, troca de modos, persistência, vazio, feed
atualizado com mesmos IDs, dia local e transições de horário de verão.
Ilustrações e ícones verificados quanto a renderização e transparência.
As visitas, dados e agendas continuam usando os contratos existentes.

As prévias de Início, Cubos ocultos, Eventos, Overlay, Sobre e dos dois modos
do painel foram inspecionadas. Não houve estudo com grupo de usuários nem
certificação de acessibilidade; esta rodada é uma revisão heurística e funcional.
