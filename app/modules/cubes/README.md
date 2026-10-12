# Hidden Cubes

O domínio especializado é `HiddenCube` em `app/core/models.py`; os dados ficam na lista `Dataset.cubes`. A consulta usa `FilterQuery(cubes_only=True)` e a UI reutiliza `AtlasPage(cubes_only=True)`. Esta composição evita duplicar marcadores, filtros ou persistência. Adicione serviços específicos aqui quando surgirem regras de negócio próprias (rotas verificadas, agrupamentos ou progresso por região).
