# Identidade visual • 0.7.2

**STRIGOI AETHER MAP**, AION 2 Companion App. A interface usa português.
O mascote próprio chama-se **Aether**: um vampirinho com aparência asmodiana,
cabelo branco, pele lavanda, olhos vermelhos, asas escuras e um mapa.
Na revisão 0.7.2, tem olhar severo e sorriso malicioso com presas. A roupa usa
gola escura; foram retirados a gola de pele branca, os babados e enfeites claros.
A mesma revisão aparece na abertura, Início, navegação, Sobre e ícone do executável.

## Assets

- `app/assets/aether-asmodian-v2.png`: corpo inteiro para Início, abertura e Sobre.
- `app/assets/aether-avatar-v2.png`: rosto para navegação e ícone da janela.
- `app/assets/aether.ico`: ícone do executável, convertido com Qt em 16–256 pixels, com alpha preservado.
- `app/assets/icons/*.svg`: 18 ícones vetoriais próprios para seções e eventos.
- `app/assets/branding.json`: SHA-256, método e prompts completos.

As duas ilustrações foram produzidas com a ferramenta integrada `image_gen`,
com fundo transparente. O avatar deriva do novo mascote, mantendo sua identidade.
A referência anterior permanece somente no código-fonte, em
`data-sources/branding/`, e não é usada como mascote na versão portátil.
Não houve cópia de um pacote externo de ícones. Cubos também usam um desenho
próprio com três faces no atlas e no overlay; no minimapa, o símbolo é compacto
para preservar o terreno usado no reconhecimento.

## Linguagem visual e uso

Fundo `#10121f`, cartões `#191d2e`, ação `#91dedf`, texto `#eff1f7`,
metadados `#9ba5bd`, cubos dourados e coletas verdes. A navegação combina ícone
com texto. Segoe UI; foco, contraste e nomes acessíveis nos controles.

O painel de eventos combina um fundo azul/violeta, cartões com ícones por
tipo, horário e contagem regressiva. A vista recolhida mostra o próximo evento;
a expandida reúne os horários do dia no fuso escolhido, com rolagem e destaque
para os próximos horários. Eventos anteriores usam texto mais discreto.

Fontes e coordenadas ficam nos detalhes das posições; ajustes técnicos ficam
em grupos recolhidos. A interface não anuncia funcionalidades planejadas.

## Prompts usados • revisão 0.7.2

Ferramenta integrada `image_gen`, em modo de edição e com fundo transparente.

### Mascote

Use case: precise-object-edit. Asset type: full-body transparent mascot for STRIGOI AETHER MAP Windows app. Image 1 is the edit target, existing Aether mascot. Preserve this character's identity, white tousled hair with dark undercut, pale lavender-blue skin, long pointed ears, red eyes, dark feathered wings, turquoise crystal and magical folded map, chibi proportions and polished anime cartoon rendering. Make him look more wicked: sharply lowered eyebrows, narrower intense red eyes and a confident closed mischievous smirk showing two small vampire fangs. Remove the cheerful open mouth and rosy blush. Remove ALL the white decorative fur collar, white neck ruffles, white cloth cuffs and dangling white/silver star/snowflake decoration around his outfit. Replace with a clean charcoal high collar and sleek dark purple coat with restrained violet edges. Keep white hair, pale face, and tiny fangs only; these are character features, not white outfit decorations. Single centered full-body character with complete wings, feet and some breathing room around silhouette. Transparent background with genuine alpha. No white outline, white halo, frame, background decoration, text, watermarks or scenery. Preserve the map-holding and raised-hand pose.

### Avatar

Use case: precise-object-edit. Asset type: transparent compact avatar icon for the STRIGOI AETHER MAP desktop app. The provided newly revised Aether character is the identity reference and edit target. Create a head-and-shoulders only avatar from precisely this character. Preserve white tousled hair with dark undercut, pale lavender-blue skin, long pointed ears, sharply lowered eyebrows and narrower intense red eyes, confident wicked closed smirk with two tiny vampire fangs. Preserve sleek charcoal high collar with violet edges. Face almost forward, square composition with generous transparent padding, large face readable at 32 and 64 pixels. Keep the character chibi and polished crisp anime cartoon. Remove arms, map, legs and sprawling wings. NO white fur collar, white neck ruffles, white outfit decorations, white halo, white outline, frame, background disk, text or watermark. Genuine transparent alpha background. Do not change his expression back to friendly. White hair and pale face are retained, clothing stays dark.

Os prompts e hashes da primeira revisão ficam no histórico de `branding.json`.
