# Contrato de dados

Os arquivos completos e válidos para copiar são `app/data/dataset.json` e `app/data/events.json`. Os schemas em `schemas/` são gerados diretamente dos modelos. O app rejeita campos desconhecidos para detectar erros de digitação cedo.

## Atlas

Raiz: `schema_version: 1`, `demo`, `title`, `regions`, `maps`, `categories`, `subcategories`, `resources`, `points`, `cubes`. Cada entidade tem ID único dentro do seu grupo; points e cubes compartilham o espaço de IDs.

`demo: false` indica conteúdo não fictício; não é um certificado de exatidão ou compatibilidade. `release`, `coverage` e `checked_on` documentam versão, alcance e data da revisão. O app sinaliza conteúdo de demonstração, mas não certifica a exatidão dos dados que o usuário importa. Use `source` para URL/citação/data de verificação e `certainty` para `confirmed`, `possible` ou `demo`.

Exemplo de ponto:

```json
{
  "id": "my-map-ore-001",
  "name": "Minério junto à margem",
  "map_id": "my-map",
  "resource_id": "my-resource",
  "x": 0.42,
  "y": 0.61,
  "enabled": true,
  "notes": "Spawn possível; requer confirmação",
  "source": "Anotação manual do autor, a verificar",
  "certainty": "possible",
  "visible_in_overlay": true
}
```

O ponto precisa ter mapa e recurso correspondentes no mesmo dataset. Coordenadas usam a imagem inteira: `(0,0)` canto superior esquerdo, `(1,1)` canto inferior direito. Não representam coordenadas nativas do jogo. Se uma imagem contiver margens ou UI, elas também fazem parte do espaço normalizado; prefira um mapa recortado apenas com sua área útil.

Para um cubo, use a lista `cubes` e acrescente `underwater: true/false/null` e `route_hint`. A categoria do recurso continua editável; a lista `cubes` determina o módulo específico. Categorias disponíveis podem ser expandidas, com formas de ícone `cube`, `diamond`, `circle`, `leaf`, `wood`, `star`. Raridades: `common`, `uncommon`, `rare`, `epic`, `unknown`. Ausência de informação usa `unknown`. Recursos têm `source` e `verification`; mapas têm `supports_overlay`, que deve ser falso quando a projeção não é compatível.

`image` aceita nomes relativos dos SVGs originais em `app/assets/`. Para mapas próprios, use PNG/JPG com caminho absoluto ou relativo ao JSON importado. Ao importar, o app valida e copia a imagem para a base local. SVG externo não é aceito nesta versão. Preserve proporção em `width` e `height`. Não reutilize arte sem permissão.

## Eventos

```json
{
  "schema_version": 1,
  "demo": true,
  "events": [
    {
      "id": "example-weekly",
      "name": "Siege — exemplo fictício",
      "kind": "Siege",
      "region": "Região demonstrativa",
      "source": "Agenda inventada para teste",
      "schedule": {
        "timezone": "America/Fortaleza",
        "recurrence": "weekly",
        "weekdays": [1, 5],
        "times": ["20:00", "23:00"]
      }
    }
  ]
}
```

Dias: 0 segunda-feira até 6 domingo. `daily` ignora a lista de dias. `once` exige `starts_at`, por exemplo `2027-01-20T20:00:00-03:00`; `times` fica sem efeito nesse modo. `duration_minutes` é metadado reservado, nulo quando desconhecido; não há UI de evento em andamento. `verified_on` e `verification` registram o alcance da consulta; `coverage` e `release` documentam o feed. `enabled: false` remove o evento da agenda/alertas. `kind` é texto livre; novos tipos aparecem nas preferências de alertas.

O endpoint remoto deve servir exatamente esse envelope, sem autenticação nesta versão. A atualização automática utiliza a URL previamente salva ao atualizar manualmente. O app busca uma agenda; não interpreta páginas HTML nem inventa horários quando a fonte falha.

## Perfis e seleção dinâmica

`app/data/schedule-profiles.json` lista agendas locais selecionáveis. Cada
perfil usa o mesmo contrato EventFeed, com origem, relógio da regra e alcance.
Agendas importadas continuam no cache e não são substituídas por uma revisão
quando seus registros divergem de uma base original conhecida.

`CaptureArea` guarda mapa, nome e geometria do monitor, DPR e retângulo local.
As coordenadas de sua seleção são lógicas; a captura e o reconhecimento usam
pixels físicos. O modo principal não guarda `reference_image`: sua referência
é a imagem raster do mapa, incluída no pacote.

## Manutenção

Mantenha IDs estáveis para preservar visitas e preferências. Alterar IDs cria entidades novas. Faça backup da pasta de dados antes de grandes mudanças. Exportar preferências não exporta mapas nem agendas: copie a base local para um backup completo. A agenda remota e a importação manual usam o mesmo cache; a última atualização válida prevalece.
