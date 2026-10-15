// SPDX-License-Identifier: GPL-3.0-only
window.StrigoiGuide = {
  "topics": [
    {
      "id": "install",
      "icon": "overlay",
      "title": {
        "pt_BR": "Primeiros passos",
        "en_US": "Getting started"
      },
      "description": {
        "pt_BR": "Instale e deixe tudo pronto para jogar.",
        "en_US": "Install and get ready to play."
      },
      "image": "home",
      "steps": [
        {
          "title": {
            "pt_BR": "Escolha como usar",
            "en_US": "Choose your edition"
          },
          "where": {
            "pt_BR": "Site → Downloads",
            "en_US": "Website → Downloads"
          },
          "body": {
            "pt_BR": "Use o instalador para ter atalhos e desinstalação. O portátil funciona ao extrair a pasta inteira. Os dois oferecem os mesmos recursos. Escolha sua opção abaixo para adaptar as próximas instruções.",
            "en_US": "Use the installer for shortcuts and an uninstaller. The portable edition runs after extracting the entire folder. Both offer the same features. Choose below to adapt the next instructions."
          },
          "tip": {
            "pt_BR": "Já instalou? Pule diretamente para o módulo que quer configurar.",
            "en_US": "Already installed? Jump straight to the module you want to configure."
          },
          "action": {
            "href": "index.html#download",
            "label": {
              "pt_BR": "Ver downloads",
              "en_US": "View downloads"
            }
          }
        },
        {
          "title": {
            "pt_BR": "Prepare o aplicativo",
            "en_US": "Set up the app"
          },
          "where": {
            "pt_BR": "Instalador ou pasta extraída",
            "en_US": "Installer or extracted folder"
          },
          "body": {
            "pt_BR": "Siga as instruções da edição escolhida.",
            "en_US": "Follow the instructions for your edition."
          },
          "tip": {
            "pt_BR": "Npcap é necessário somente para Combate. Atlas, eventos e Sonar funcionam sem esse componente.",
            "en_US": "Npcap is needed only for Combat. Atlas, events, and Sonar work without it."
          },
          "installer": {
            "pt_BR": "Execute o Setup, escolha português ou inglês, leia e aceite os termos e conclua a instalação. Se o fluxo oferecer Npcap, conclua o assistente oficial para usar Combate. O assistente do driver pode pedir permissão de administrador.",
            "en_US": "Run Setup, choose Portuguese or English, read and accept the terms, and complete installation. If Npcap is offered, complete its official wizard to use Combat. The driver wizard may request administrator permission."
          },
          "portable": {
            "pt_BR": "Extraia todo o ZIP antes de abrir StrigoiAetherMap.exe. Mantenha a pasta _internal ao lado do executável. Para usar Combate, instale Npcap pelo canal oficial; ele não vem embutido no portátil.",
            "en_US": "Extract the entire ZIP before opening StrigoiAetherMap.exe. Keep _internal beside the executable. For Combat, install Npcap through its official channel; it is not embedded in the portable edition."
          },
          "action": {
            "href": "https://npcap.com/#download",
            "label": {
              "pt_BR": "Npcap oficial · somente para Combate",
              "en_US": "Official Npcap · Combat only"
            }
          }
        },
        {
          "title": {
            "pt_BR": "Abra e mantenha em execução",
            "en_US": "Open and keep it running"
          },
          "where": {
            "pt_BR": "Azphelumbra → Configurações",
            "en_US": "Azphelumbra → Settings"
          },
          "body": {
            "pt_BR": "Abra o Azphelumbra antes de entrar na instância, principalmente ao testar Combate. Em Configurações, confira o idioma e o fuso dos eventos. Pode minimizar a janela para jogar; fechar o aplicativo encerra seus recursos.",
            "en_US": "Open Azphelumbra before entering the instance, especially when testing Combat. In Settings, check language and event time zone. Minimize the window to play; closing the app stops its features."
          },
          "tip": {
            "pt_BR": "Trocar para inglês não muda a região da agenda ou o fuso.",
            "en_US": "Switching to English does not change the schedule region or time zone."
          }
        }
      ],
      "help": [
        {
          "question": {
            "pt_BR": "Como atualizar?",
            "en_US": "How do I update?"
          },
          "answer": {
            "pt_BR": "Feche o Azphelumbra antes de executar o novo instalador. No portátil, extraia a nova versão em outra pasta. Preferências e visitas ficam na pasta de dados do app.",
            "en_US": "Close Azphelumbra before running the new installer. For portable updates, extract into another folder. Preferences and visits stay in the app data folder."
          }
        }
      ]
    },
    {
      "id": "menu",
      "icon": "overlay",
      "title": {
        "pt_BR": "Menu rápido",
        "en_US": "Quick menu"
      },
      "description": {
        "pt_BR": "Controle os módulos sem abrir a janela principal.",
        "en_US": "Control modules without opening the main window."
      },
      "image": "quick-menu",
      "steps": [
        {
          "title": {
            "pt_BR": "Abra o menu do emblema",
            "en_US": "Open the emblem menu"
          },
          "where": {
            "pt_BR": "Mascote flutuante",
            "en_US": "Floating emblem"
          },
          "body": {
            "pt_BR": "Clique no emblema para expandir. Use a seta do painel ou clique no emblema novamente para recolher. Arraste o emblema para mover; sua posição fica salva.",
            "en_US": "Click the emblem to expand. Use the panel arrow or click the emblem again to collapse. Drag the emblem to move it; its position is saved."
          },
          "tip": {
            "pt_BR": "Posicione o menu onde não atrapalhe sua HUD.",
            "en_US": "Place the menu where it does not obstruct your HUD."
          }
        },
        {
          "title": {
            "pt_BR": "Escolha o que aparece",
            "en_US": "Choose what appears"
          },
          "where": {
            "pt_BR": "Menu → quatro controles",
            "en_US": "Menu → four controls"
          },
          "body": {
            "pt_BR": "Sonar liga ou desliga a análise do áudio. Mapa + minimapa controla os dois mapas juntos. Painel de combate habilita a exibição automática em instâncias; fora delas, mostra Aguardando instância. Painel de eventos mostra ou oculta a agenda. Configure primeiro o minimapa e o Sonar nas respectivas abas.",
            "en_US": "Sonar turns audio analysis on or off. Map + minimap controls both maps. Combat panel arms automatic display in instances; outside them, it shows Waiting for instance. Events panel shows or hides the schedule. Set up the minimap and Sonar in their tabs first."
          },
          "tip": {
            "pt_BR": "Ocultar o placar mantém a medição de combate ativa.",
            "en_US": "Hiding the meter keeps combat measurement running."
          }
        },
        {
          "title": {
            "pt_BR": "Ajuste os controles",
            "en_US": "Adjust the controls"
          },
          "where": {
            "pt_BR": "Engrenagem → Configurações",
            "en_US": "Gear → Settings"
          },
          "body": {
            "pt_BR": "A engrenagem abre Configurações. Em Controles durante o jogo, você pode ocultar o menu rápido ou desativar Medir combate automaticamente.",
            "en_US": "The gear opens Settings. Under In-game controls, you can hide the quick menu or disable Measure combat automatically."
          },
          "tip": {
            "pt_BR": "Sonar e mapas começam desligados a cada abertura. Combate inicia quando a opção automática está habilitada e Npcap está disponível.",
            "en_US": "Sonar and maps start off each session. Combat starts when automatic measurement is enabled and Npcap is available."
          }
        }
      ],
      "help": [
        {
          "question": {
            "pt_BR": "O emblema não aparece.",
            "en_US": "The emblem is missing."
          },
          "answer": {
            "pt_BR": "Na janela principal, abra Configurações e habilite Mostrar menu rápido de overlay.",
            "en_US": "In the main window, open Settings and enable Show overlay quick menu."
          }
        }
      ]
    },
    {
      "id": "pets",
      "icon": "pets",
      "title": {
        "pt_BR": "Coleção de pets",
        "en_US": "Pet collection"
      },
      "description": {
        "pt_BR": "Favoritos, Insight e locais de farm.",
        "en_US": "Favorites, Insight and farming locations."
      },
      "image": "pets",
      "steps": [
        {
          "title": {
            "pt_BR": "Sincronize ao entrar",
            "en_US": "Sync at login"
          },
          "where": {
            "pt_BR": "Pets → Sincronizar com o jogo",
            "en_US": "Pets → Sync with game"
          },
          "body": {
            "pt_BR": "Abra o Azphelumbra antes de entrar no personagem e confira a região. A coleção é recebida na entrada; não precisa deixar o menu do jogo aberto. A leitura automática usa Npcap.",
            "en_US": "Open Azphelumbra before logging into your character and check the region. The collection arrives during login; you do not need to leave the game menu open. Automatic reading uses Npcap."
          },
          "tip": {
            "pt_BR": "Abriu o app depois de entrar? Volte à seleção de personagem e entre novamente quando puder. A coleção manual funciona sem Npcap.",
            "en_US": "Opened the app after login? Return to character selection and log in again when convenient. Manual records work without Npcap."
          }
        },
        {
          "title": {
            "pt_BR": "Escolha seus favoritos",
            "en_US": "Choose your favorites"
          },
          "where": {
            "pt_BR": "Pets → Busca, filtros e detalhe",
            "en_US": "Pets → Search, filters and details"
          },
          "body": {
            "pt_BR": "Busque por pet ou monstro, filtre pelo mapa e escolha uma meta de Insight. Marque Favorito para acompanhar no painel. Pet Insight é diferente do nível da família.",
            "en_US": "Search by pet or monster, filter by map and choose an Insight goal. Mark Favorite to track it in the panel. Pet Insight differs from the genus level."
          },
          "tip": {
            "pt_BR": "Informações não recebidas ficam desconhecidas. Registros manuais são separados e podem ser desfeitos com Usar informação do jogo.",
            "en_US": "Unread information stays unknown. Manual records remain separate and can be undone with Use game information."
          }
        },
        {
          "title": {
            "pt_BR": "Leve a coleção para o jogo",
            "en_US": "Take your collection into the game"
          },
          "where": {
            "pt_BR": "Pets ou menu rápido → Painel de pets",
            "en_US": "Pets or quick menu → Pets panel"
          },
          "body": {
            "pt_BR": "Ative o painel, arraste pelo título e trave a posição. Recolha para uma linha ou expanda para até três, com rolagem para os demais favoritos. A aba Pets oferece opacidade e Restaurar painel.",
            "en_US": "Enable the panel, drag its title and lock its position. Collapse to one row or expand to three, with scrolling for more favorites. Pets offers opacity and Restore panel controls."
          },
          "tip": {
            "pt_BR": "Fechar o painel mantém a sincronização ativa. Alt+Tab e menus reconhecidos o ocultam temporariamente.",
            "en_US": "Closing the panel keeps sync running. Alt+Tab and recognized menus hide it temporarily."
          }
        },
        {
          "title": {
            "pt_BR": "Encontre locais de farm",
            "en_US": "Find farming locations"
          },
          "where": {
            "pt_BR": "Detalhe do pet → Ver locais no Atlas",
            "en_US": "Pet details → View locations in Atlas"
          },
          "body": {
            "pt_BR": "A camada Pets pode aparecer junto de cubos e coletas nos mapas. Use Todos, Favoritos ou Metas pendentes. Os locais são referências documentadas do cliente, sem confirmação da presença atual em SA.",
            "en_US": "The Pets layer can appear alongside cubes and gatherables on maps. Choose All, Favorites or Pending goals. Locations are documented client references; current SA presence is unconfirmed."
          },
          "tip": {
            "pt_BR": "A coleção inicial foi conferida em SA. Ganho de almas ainda aguarda conferência real. Distância e direção de radar ao vivo não estão disponíveis nesta versão.",
            "en_US": "The initial collection matched SA gameplay. Soul gains still await a live check. Live radar distance and direction are not available in this version."
          }
        }
      ],
      "help": [
        {
          "question": {
            "pt_BR": "Por que minha coleção está vazia?",
            "en_US": "Why is my collection empty?"
          },
          "answer": {
            "pt_BR": "A coleção é recebida na entrada do personagem. Abra o Azphelumbra antes de entrar, confirme a região e a opção de sincronização e verifique se Npcap está instalado. Informações ainda não recebidas ficam desconhecidas.",
            "en_US": "The collection arrives when logging into a character. Open Azphelumbra before login, check the region and sync option, and verify Npcap is installed. Unread progress stays unknown."
          }
        },
        {
          "question": {
            "pt_BR": "Esse painel é um radar de monstros?",
            "en_US": "Is this panel a monster radar?"
          },
          "answer": {
            "pt_BR": "Nesta versão, o painel acompanha seus pets favoritos e o progresso da coleção. Os mapas mostram locais de referência. Rastreamento de NPCs, distância e direção ainda dependem de validação no jogo.",
            "en_US": "In this version the panel tracks favorite pets and collection progress. Maps show reference sites. NPC tracking, distance and direction still require in-game validation."
          }
        }
      ]
    },
    {
      "id": "atlas",
      "icon": "atlas",
      "title": {
        "pt_BR": "Atlas e camadas",
        "en_US": "Atlas and layers"
      },
      "description": {
        "pt_BR": "Escolha recursos, explore o mapa e registre visitas.",
        "en_US": "Choose resources, explore the map, and record visits."
      },
      "image": "atlas",
      "steps": [
        {
          "title": {
            "pt_BR": "Escolha seu mapa",
            "en_US": "Choose your map"
          },
          "where": {
            "pt_BR": "Atlas → mapa",
            "en_US": "Atlas → map"
          },
          "body": {
            "pt_BR": "Selecione a região onde está. Altgard é o padrão inicial. Use a roda do mouse para aproximar e arraste para explorar. Enquadrar mapa recupera a visão geral.",
            "en_US": "Select your current region. Altgard is the initial default. Use the mouse wheel to zoom and drag to explore. Fit map restores the overview."
          },
          "tip": {
            "pt_BR": "Escolha o mesmo mapa na aba Overlay antes de usar os pontos sobre o jogo.",
            "en_US": "Choose the same map in Overlay before using markers over the game."
          }
        },
        {
          "title": {
            "pt_BR": "Combine suas camadas",
            "en_US": "Combine your layers"
          },
          "where": {
            "pt_BR": "Camadas do Atlas",
            "en_US": "Atlas layers"
          },
          "body": {
            "pt_BR": "Marque as categorias desejadas, como ervas e cubos. Essa seleção é compartilhada com o minimapa e o mapa grande. Você também pode editar as camadas pela aba Overlay.",
            "en_US": "Enable categories such as herbs and cubes. This selection is shared with the minimap and full map. You can also edit layers in Overlay."
          },
          "tip": {
            "pt_BR": "Busca e raridade são filtros temporários da página, não a seleção de categorias do overlay.",
            "en_US": "Search and rarity are temporary page filters, not the overlay category selection."
          }
        },
        {
          "title": {
            "pt_BR": "Registre sua exploração",
            "en_US": "Record your exploration"
          },
          "where": {
            "pt_BR": "Marcador → Caderno de campo",
            "en_US": "Marker → Field journal"
          },
          "body": {
            "pt_BR": "Clique num marcador para consultar detalhes e usar Marcar como visitado. Ver origem e coordenadas mostra informações da base. Ocultar visitados ajuda a acompanhar o que falta explorar.",
            "en_US": "Click a marker to view details and use Mark visited. Show source and coordinates displays dataset information. Hide visited helps track what remains to explore."
          },
          "tip": {
            "pt_BR": "Os pontos indicam locais possíveis, não a disponibilidade atual do objeto no servidor.",
            "en_US": "Points indicate possible locations, not the object’s current availability on the server."
          }
        }
      ],
      "help": [
        {
          "question": {
            "pt_BR": "Os pontos sumiram.",
            "en_US": "Markers disappeared."
          },
          "answer": {
            "pt_BR": "Confira Camadas do Atlas, Ocultar visitados e as exclusões de recursos que você salvou.",
            "en_US": "Check Atlas layers, Hide visited, and your saved resource exclusions."
          }
        }
      ]
    },
    {
      "id": "maps",
      "icon": "overlay",
      "title": {
        "pt_BR": "Mapa e minimapa",
        "en_US": "Map and minimap"
      },
      "description": {
        "pt_BR": "Selecione o terreno uma vez e acompanhe os dois mapas.",
        "en_US": "Select terrain once and track both maps."
      },
      "image": "overlay",
      "steps": [
        {
          "title": {
            "pt_BR": "Escolha modo e monitor",
            "en_US": "Choose mode and monitor"
          },
          "where": {
            "pt_BR": "Overlay → Modo, Mapa e Monitor",
            "en_US": "Overlay → Mode, Map, and Monitor"
          },
          "body": {
            "pt_BR": "Com o jogo aberto, escolha Minimapa + mapa grande automático. Selecione o mapa atual e o monitor onde o jogo aparece. O minimapa suportado é retangular, com norte fixo.",
            "en_US": "With the game open, choose Minimap + automatic full map. Select the current map and monitor showing the game. The supported minimap is rectangular with north fixed."
          },
          "tip": {
            "pt_BR": "Para usar só o mapa grande, escolha Mapa grande • monitor inteiro. Nesse modo não precisa selecionar uma área.",
            "en_US": "For full map only, choose Full map • entire monitor. No area selection is needed."
          }
        },
        {
          "title": {
            "pt_BR": "Selecione somente o terreno",
            "en_US": "Select terrain only"
          },
          "where": {
            "pt_BR": "Overlay → Selecionar minimapa",
            "en_US": "Overlay → Select minimap"
          },
          "body": {
            "pt_BR": "Clique em Selecionar minimapa. A janela do Azphelumbra desaparece temporariamente. Arraste um retângulo sobre o terreno do minimapa, sem incluir a barra com o nome da região nem as missões abaixo. Solte para salvar; Esc cancela.",
            "en_US": "Click Select minimap. Azphelumbra temporarily hides its window. Drag a rectangle over minimap terrain, excluding the region title bar and quests below. Release to save; Esc cancels."
          },
          "tip": {
            "pt_BR": "Não precisa tirar screenshot nem mover arquivos. O app salva os limites da área.",
            "en_US": "No screenshot or file moving is needed. The app saves area bounds."
          }
        },
        {
          "title": {
            "pt_BR": "Ative suas camadas",
            "en_US": "Enable your layers"
          },
          "where": {
            "pt_BR": "Overlay → Mostrar / Ativar overlay",
            "en_US": "Overlay → Show / Enable overlay"
          },
          "body": {
            "pt_BR": "Escolha as categorias em Camadas do Atlas e clique em Ativar overlay. O Azphelumbra minimiza e procura detalhes do terreno para posicionar os pontos. Depois, use o menu rápido para controlar os mapas.",
            "en_US": "Choose categories in Atlas layers and click Enable overlay. Azphelumbra minimizes and looks for terrain details to place markers. Then use the quick menu to control maps."
          },
          "tip": {
            "pt_BR": "Os símbolos do minimapa têm tamanho 2× maior. Nos cubos, ↑ e ↓ indicam altura acima ou abaixo da mediana do grupo na fonte; não comparam com o personagem. Sem reconhecer o terreno, o app oculta os pontos. Alt+Tab oculta todos os overlays. Menus reconhecidos também ocultam os painéis; o mapa grande mantém seus marcadores. A medição continua.",
            "en_US": "Minimap symbols are 2× larger. Cube arrows ↑ and ↓ mean above or below the source group's median height; they do not compare with your character. Without terrain recognition, markers are hidden. Alt+Tab hides every overlay. Recognized menus also hide panels; the full map keeps its markers. Measurement continues."
          }
        },
        {
          "title": {
            "pt_BR": "Abra o mapa grande",
            "en_US": "Open the full map"
          },
          "where": {
            "pt_BR": "Jogo → M",
            "en_US": "Game → M"
          },
          "body": {
            "pt_BR": "Abra o mapa grande com M. Quando reconhecido, ele tem prioridade sobre o minimapa. Feche para voltar ao minimapa sem trocar o modo no Azphelumbra.",
            "en_US": "Press M to open the full map. When recognized, it takes priority over the minimap. Close it to return to the minimap without changing Azphelumbra mode."
          },
          "tip": {
            "pt_BR": "O app reconhece a imagem do mapa na tela. O mapa grande não exige recorte manual.",
            "en_US": "The app recognizes the map image on screen. The full map needs no manual selection."
          }
        },
        {
          "title": {
            "pt_BR": "Ajuste quando a tela mudar",
            "en_US": "Adjust after display changes"
          },
          "where": {
            "pt_BR": "Overlay → seleção / Fluidez do overlay",
            "en_US": "Overlay → selection / Overlay performance"
          },
          "body": {
            "pt_BR": "Refaça a seleção após mudar tamanho ou posição do minimapa, monitor, resolução ou escala do Windows. Ajuste Opacidade e Tamanho dos ícones. Em Fluidez do overlay, escolha a frequência visual (15–360 Hz) e a leitura do mapa (10–60 fps no minimapa; até 30 fps no mapa grande). Os controles ficam visíveis e funcionam com o overlay ligado.",
            "en_US": "Repeat selection after changing minimap size or position, monitor, resolution, or Windows scaling. Adjust Opacity and Icon size. In Overlay performance, choose the draw limit (15–360 Hz) and map reading rate (10–60 fps on the minimap; up to 30 fps on the full map). The controls are visible and work while the overlay is enabled."
          },
          "tip": {
            "pt_BR": "Comece com 60 Hz e 30 fps; reduza para 30 Hz/15 fps se houver lentidão. A preferência é salva. Desenho e leitura têm limites separados; marcadores parados só são redesenhados quando necessário.",
            "en_US": "Start at 60 Hz and 30 fps; lower to 30 Hz/15 fps if the game slows down. Your preference is saved. Drawing and reading have separate limits; stationary markers redraw only when needed."
          }
        }
      ],
      "help": [
        {
          "question": {
            "pt_BR": "Mapa reconhecido, mas sem pontos.",
            "en_US": "Map recognized, but no markers."
          },
          "answer": {
            "pt_BR": "Confira camadas e Ocultar visitados. Pode não haver pontos das categorias escolhidas naquele recorte; teste outra categoria ou região.",
            "en_US": "Check layers and Hide visited. That area may have no points in your chosen categories; try another category or region."
          }
        },
        {
          "question": {
            "pt_BR": "Os pontos parecem deslocados.",
            "en_US": "Markers look misaligned."
          },
          "answer": {
            "pt_BR": "Confira mapa e monitor, refaça a seleção só sobre o terreno e teste janela sem bordas. Ao reportar, informe mapa, resolução, escala do Windows e uma print.",
            "en_US": "Check map and monitor, reselect terrain only, and try borderless window mode. Report map, resolution, Windows scaling, and a screenshot."
          }
        }
      ]
    },
    {
      "id": "sonar",
      "icon": "sonar",
      "title": {
        "pt_BR": "Sonar de cubos",
        "en_US": "Cube Sonar"
      },
      "description": {
        "pt_BR": "Transforme a pista sonora do cubo em um aviso visual.",
        "en_US": "Turn the cube sound cue into a visual alert."
      },
      "image": "sonar",
      "steps": [
        {
          "title": {
            "pt_BR": "Selecione o áudio do jogo",
            "en_US": "Select game audio"
          },
          "where": {
            "pt_BR": "Sonar → Atualizar aplicativos",
            "en_US": "Sonar → Refresh applications"
          },
          "body": {
            "pt_BR": "Abra o AION 2. Em Sonar, clique em Atualizar aplicativos e selecione o aplicativo que reproduz o áudio do jogo. O som precisa estar sendo reproduzido para ser analisado.",
            "en_US": "Open AION 2. In Sonar, click Refresh applications and select the application playing game audio. Sound must be playing for analysis."
          },
          "tip": {
            "pt_BR": "O Sonar não usa o microfone. O aviso funciona com o mapa fechado.",
            "en_US": "Sonar does not use the microphone. Alerts work with the map closed."
          }
        },
        {
          "title": {
            "pt_BR": "Comece com Equilibrada",
            "en_US": "Start with Balanced"
          },
          "where": {
            "pt_BR": "Sonar → Sensibilidade / Ativar sonar",
            "en_US": "Sonar → Sensitivity / Enable Sonar"
          },
          "body": {
            "pt_BR": "Escolha Equilibrada e clique em Ativar sonar. Depois, use o menu rápido para ligar e desligar. Alta pode ajudar com sinais difíceis, mas também gerar mais avisos.",
            "en_US": "Choose Balanced and click Enable Sonar. Then use the quick menu to turn it on and off. High can help with difficult signals, but may produce more alerts."
          },
          "tip": {
            "pt_BR": "O detector procura indícios do som do cubo; não separa perfeitamente todos os efeitos do jogo.",
            "en_US": "The detector looks for signs of the cube sound; it does not perfectly separate every game effect."
          }
        },
        {
          "title": {
            "pt_BR": "Explore ao receber o aviso",
            "en_US": "Explore when alerted"
          },
          "where": {
            "pt_BR": "Aviso → Possível cubo por perto",
            "en_US": "Alert → Possible cube nearby"
          },
          "body": {
            "pt_BR": "Quando o cartão aparecer, procure nos arredores. A barra e o histórico acompanham a intensidade estimada do som reconhecido. O volume do jogo influencia a leitura, que não indica distância em metros. Você pode mover ou dispensar o aviso.",
            "en_US": "When the card appears, search nearby. The bar and history follow the estimated intensity of the recognized sound. Game volume affects the reading, which does not indicate distance in meters. You can move or dismiss the alert."
          },
          "tip": {
            "pt_BR": "É um recurso de acessibilidade auditiva. O aviso pode falhar ou ocorrer por um som parecido.",
            "en_US": "This is a hearing accessibility feature. Alerts may be missed or triggered by similar sounds."
          }
        },
        {
          "title": {
            "pt_BR": "Teste o cartão e pare quando quiser",
            "en_US": "Test the card and stop anytime"
          },
          "where": {
            "pt_BR": "Sonar → Testar aviso visual / Parar sonar",
            "en_US": "Sonar → Test visual alert / Stop Sonar"
          },
          "body": {
            "pt_BR": "Testar aviso visual mostra só um cartão identificado como teste, sem detectar áudio. Para parar a análise, use Parar sonar ou o menu rápido. Ao reabrir o app, ative novamente.",
            "en_US": "Test visual alert shows only a card labeled as a test, without detecting audio. Stop analysis using Stop Sonar or the quick menu. Enable it again after reopening the app."
          },
          "tip": {
            "pt_BR": "Fechar o app encerra a análise. O áudio não é gravado nem enviado.",
            "en_US": "Closing the app stops analysis. Audio is not recorded or uploaded."
          }
        }
      ],
      "help": [
        {
          "question": {
            "pt_BR": "O Sonar não liga após reiniciar o jogo.",
            "en_US": "Sonar will not enable after restarting the game."
          },
          "answer": {
            "pt_BR": "Atualize a lista de aplicativos e selecione o jogo novamente. O processo muda ao reabrir.",
            "en_US": "Refresh applications and select the game again. Its process changes after restarting."
          }
        },
        {
          "question": {
            "pt_BR": "Recebo muitos avisos.",
            "en_US": "I get too many alerts."
          },
          "answer": {
            "pt_BR": "Use Equilibrada. Ao reportar, diga qual efeito estava acontecendo e a sensibilidade selecionada.",
            "en_US": "Use Balanced. When reporting, describe the effect and selected sensitivity."
          }
        }
      ]
    },
    {
      "id": "combat",
      "icon": "combat",
      "title": {
        "pt_BR": "Combate automático",
        "en_US": "Automatic combat"
      },
      "description": {
        "pt_BR": "Acompanhe dano observado, DPS e participação.",
        "en_US": "Track observed damage, DPS, and group share."
      },
      "image": "combat",
      "steps": [
        {
          "title": {
            "pt_BR": "Deixe a leitura aguardar o jogo",
            "en_US": "Let capture wait for the game"
          },
          "where": {
            "pt_BR": "Combate → Ajustes de combate → estado da leitura",
            "en_US": "Combat → Combat settings → capture status"
          },
          "body": {
            "pt_BR": "Com Npcap instalado, abra o Azphelumbra antes de entrar na instância. A medição começa automaticamente e aguarda a conexão. Confira se o estado muda para Recebendo eventos. Não há botão para iniciar instância.",
            "en_US": "With Npcap installed, open Azphelumbra before entering the instance. Measurement starts automatically and waits for the connection. Check that status changes to Receiving events. There is no start-instance button."
          },
          "tip": {
            "pt_BR": "Se pedir Npcap, complete a instalação oficial. Confira também Medir combate automaticamente em Configurações.",
            "en_US": "If Npcap is required, complete official installation. Also check Measure combat automatically in Settings."
          }
        },
        {
          "title": {
            "pt_BR": "Acompanhe o painel automático",
            "en_US": "Follow the automatic panel"
          },
          "where": {
            "pt_BR": "Menu rápido → Painel de combate",
            "en_US": "Quick menu → Combat panel"
          },
          "body": {
            "pt_BR": "O painel aparece nas instâncias reconhecidas e se oculta ao sair. As barras acompanham o DPS e usam a cor da classe. Clique em um jogador para ver dano e participação, ou em Detalhes + para expandir todos. Use a seta para recolher ao seu DPS. Destrave o pino e arraste o título para mover.",
            "en_US": "The panel appears in recognized instances and hides on exit. Class-colored bars follow DPS. Click a player for damage and participation, or Details + to expand all rows. Use the arrow to collapse to your DPS. Unlock the pin and drag the title to move."
          },
          "tip": {
            "pt_BR": "Opacidade e Restaurar painel ficam em Ajustes de combate. Ocultar o placar mantém a medição.",
            "en_US": "Opacity and Restore panel are in Combat settings. Hiding the meter keeps measurement running."
          }
        },
        {
          "title": {
            "pt_BR": "Escolha visão e alvo",
            "en_US": "Choose view and target"
          },
          "where": {
            "pt_BR": "Combate → Encontro atual / Instância inteira",
            "en_US": "Combat → Current encounter / Entire instance"
          },
          "body": {
            "pt_BR": "Escolha a visão desejada. Para filtrar um boss, selecione o alvo depois dos golpes e marque Só o alvo selecionado. Encerrar encontro separa uma tentativa. Copiar resultado coloca texto na área de transferência.",
            "en_US": "Choose your view. To filter a boss, select the target after hits and check Selected target only. Finish encounter separates an attempt. Copy result places text on your clipboard."
          },
          "tip": {
            "pt_BR": "O módulo é experimental. Dados podem ser parciais; a atribuição completa do grupo ainda precisa de validação em SA.",
            "en_US": "The module is experimental. Data may be partial; complete group attribution still needs SA validation."
          }
        },
        {
          "title": {
            "pt_BR": "Acompanhe a próxima instância",
            "en_US": "Track the next instance"
          },
          "where": {
            "pt_BR": "Combate → Histórico / Configurações",
            "en_US": "Combat → History / Settings"
          },
          "body": {
            "pt_BR": "Uma nova entrada reconhecida salva o resultado anterior e abre um placar zerado. Consulte resultados no Histórico. Para parar a captura, desative Medir combate automaticamente em Configurações ou feche o Azphelumbra.",
            "en_US": "A recognized new entry saves the previous result and starts a fresh meter. View results in History. Stop capture by disabling Measure combat automatically in Settings or closing Azphelumbra."
          },
          "tip": {
            "pt_BR": "A troca depende do contexto recebido do jogo. Confira se o placar zera entre instâncias. Um mapa de 1v1 e um de 5v5 foram identificados em SA; outros mapas da rotação continuam pendentes. O dano PvP é experimental. No 5v5, sem a lista do time, o painel mostra apenas o dano dos participantes confirmados.",
            "en_US": "Transitions depend on context received from the game. Check that the meter resets between instances. One 1v1 and one 5v5 map were identified in SA; other rotating maps remain pending. PvP damage is experimental. Without a team roster, the 5v5 panel shows damage from confirmed participants only."
          }
        }
      ],
      "help": [
        {
          "question": {
            "pt_BR": "Só meu dano aparece.",
            "en_US": "Only my damage appears."
          },
          "answer": {
            "pt_BR": "Abra o app antes de entrar na instância. Se continuar, reporte versão, estado da leitura, composição do grupo e uma print. Dados parciais não representam o total completo do grupo.",
            "en_US": "Open the app before entering the instance. If it persists, report version, capture status, group composition, and a screenshot. Partial data is not the complete group total."
          }
        },
        {
          "question": {
            "pt_BR": "Como parar sem fechar o app?",
            "en_US": "How do I stop without closing the app?"
          },
          "answer": {
            "pt_BR": "Desative Medir combate automaticamente em Configurações. Painel de combate no menu rápido altera apenas a visibilidade.",
            "en_US": "Disable Measure combat automatically in Settings. The quick menu Combat panel control only changes visibility."
          }
        }
      ]
    },
    {
      "id": "events",
      "icon": "events",
      "title": {
        "pt_BR": "Eventos do dia",
        "en_US": "Today’s events"
      },
      "description": {
        "pt_BR": "Escolha o evento e acompanhe os horários no painel.",
        "en_US": "Choose an event and track panel times."
      },
      "image": "events",
      "steps": [
        {
          "title": {
            "pt_BR": "Confira agenda e fuso",
            "en_US": "Check schedule and time zone"
          },
          "where": {
            "pt_BR": "Eventos → agenda / Configurações → fuso",
            "en_US": "Events → schedule / Settings → time zone"
          },
          "body": {
            "pt_BR": "Em Eventos, confira a agenda América do Sul. Nas Configurações, escolha o fuso em que quer ver os horários. Trocar idioma não altera agenda nem fuso.",
            "en_US": "In Events, check the South America schedule. In Settings, choose the time zone for displayed times. Changing language does not change schedule or time zone."
          },
          "tip": {
            "pt_BR": "Em caso de divergência, o horário do jogo prevalece. Selecione o evento para consultar a origem.",
            "en_US": "If a time differs, the game’s time takes precedence. Select an event to view its source."
          }
        },
        {
          "title": {
            "pt_BR": "Escolha o evento acompanhado",
            "en_US": "Choose the tracked event"
          },
          "where": {
            "pt_BR": "Eventos → Evento no painel",
            "en_US": "Events → Panel event"
          },
          "body": {
            "pt_BR": "Escolha um evento específico ou deixe Automático para acompanhar o próximo. Ative Mostrar painel flutuante na aba ou Painel de eventos no menu rápido.",
            "en_US": "Choose a specific event or leave Automatic to track the next one. Enable Show floating panel in the tab or Events panel in the quick menu."
          },
          "tip": {
            "pt_BR": "A escolha fica salva. O painel funciona com os overlays dos mapas desligados.",
            "en_US": "Your selection is saved. The panel works with map overlays off."
          }
        },
        {
          "title": {
            "pt_BR": "Expanda, recolha e mova",
            "en_US": "Expand, collapse, and move"
          },
          "where": {
            "pt_BR": "Painel → calendário e seta",
            "en_US": "Panel → calendar and arrow"
          },
          "body": {
            "pt_BR": "O calendário permite trocar o evento. A seta alterna entre vista compacta e horários do dia da seleção atual. Arraste o cabeçalho para mover. Use o menu rápido para mostrar ou ocultar.",
            "en_US": "The calendar changes the event. The arrow switches between compact view and today’s times for the current selection. Drag the header to move. Use the quick menu to show or hide."
          },
          "tip": {
            "pt_BR": "Volte a Automático para acompanhar eventos diferentes. Mantenha o Azphelumbra aberto para atualizar a contagem.",
            "en_US": "Return to Automatic to follow different events. Keep Azphelumbra open to update the countdown."
          }
        }
      ],
      "help": [
        {
          "question": {
            "pt_BR": "O horário parece errado.",
            "en_US": "The time looks wrong."
          },
          "answer": {
            "pt_BR": "Confira agenda e fuso. Ao reportar, envie evento, região do servidor, horário do jogo e print com a contagem do painel.",
            "en_US": "Check schedule and time zone. Report event, server region, game time, and a screenshot showing the countdown."
          }
        }
      ]
    }
  ],
  "ui": {
    "pt_BR": {
      "guide.page.title": "Guia interativo — Azphelumbra",
      "guide.title": "Vamos configurar<br><em>sua aventura.</em>",
      "guide.intro": "Escolha um módulo e siga uma etapa por vez. Marque o que já fez; seu progresso fica neste navegador.",
      "guide.eyebrow": "SEU GUIA DE EXPLORAÇÃO",
      "guide.back": "← Voltar ao site",
      "guide.topics": "Escolha um módulo",
      "guide.progress": "Seu progresso",
      "guide.reset": "Recomeçar guia",
      "guide.done": "Concluí esta etapa",
      "guide.previous": "Anterior",
      "guide.next": "Próxima etapa",
      "guide.nextTopic": "Próximo módulo",
      "guide.last": "Última etapa",
      "guide.tip": "Dica do Aether",
      "guide.help": "Precisa de uma ajuda?",
      "guide.zoom": "Ampliar tela",
      "guide.close": "Fechar imagem",
      "guide.screen": "Tela real do aplicativo",
      "guide.edition": "Qual edição você usa?",
      "guide.installer": "Instalador",
      "guide.portable": "Portátil",
      "guide.step": "Etapa {current} de {total}",
      "guide.completed": "{done} de {total} etapas concluídas",
      "guide.imageAlt": "Tela de {topic} no Azphelumbra",
      "guide.local": "Marcar uma etapa acompanha apenas sua leitura; não configura o aplicativo.",
      "guide.feedback": "Encontrou um problema? Envie versão, módulo, o que estava fazendo e uma print.",
      "guide.feedbackLink": "Reportar um problema",
      "guide.ready": "Todas as etapas marcadas. Boa exploração!",
      "guide.steps": "Etapas",
      "nav.guide": "Guia de uso",
      "start.guide": "Abrir guia interativo"
    },
    "en_US": {
      "guide.page.title": "Interactive guide — Azphelumbra",
      "guide.title": "Let’s set up<br><em>your adventure.</em>",
      "guide.intro": "Choose a module and follow one step at a time. Mark what you have done; progress stays in this browser.",
      "guide.eyebrow": "YOUR EXPLORATION GUIDE",
      "guide.back": "← Back to the website",
      "guide.topics": "Choose a module",
      "guide.progress": "Your progress",
      "guide.reset": "Restart guide",
      "guide.done": "I completed this step",
      "guide.previous": "Previous",
      "guide.next": "Next step",
      "guide.nextTopic": "Next module",
      "guide.last": "Last step",
      "guide.tip": "Aether’s tip",
      "guide.help": "Need a hand?",
      "guide.zoom": "Enlarge screenshot",
      "guide.close": "Close image",
      "guide.screen": "Actual app screen",
      "guide.edition": "Which edition do you use?",
      "guide.installer": "Installer",
      "guide.portable": "Portable",
      "guide.step": "Step {current} of {total}",
      "guide.completed": "{done} of {total} steps completed",
      "guide.imageAlt": "Azphelumbra {topic} screen",
      "guide.local": "Marking a step tracks your reading only; it does not configure the app.",
      "guide.feedback": "Found a problem? Include version, module, what you were doing, and a screenshot.",
      "guide.feedbackLink": "Report a problem",
      "guide.ready": "All steps marked. Happy exploring!",
      "guide.steps": "Steps",
      "nav.guide": "User guide",
      "start.guide": "Open interactive guide"
    }
  }
};
