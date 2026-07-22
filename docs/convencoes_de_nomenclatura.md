# Convenções de nomenclatura em português

## Diretriz geral

Todo código próprio do projeto deve usar português brasileiro nos nomes de arquivos, módulos, pacotes internos, funções, classes, métodos, parâmetros, variáveis, constantes, testes, comandos e campos produzidos pelo sistema.

Identificadores Python e nomes de arquivos devem usar apenas caracteres ASCII, sem acentos, em `snake_case`. Classes devem usar `PascalCase`. Constantes devem usar `MAIUSCULAS_COM_SUBLINHADO`.

## Exceções

Permanecem em inglês apenas:

- nomes exigidos por bibliotecas e protocolos externos;
- nomes especiais da linguagem Python, como `__init__`, `__main__` e `__version__`;
- chaves de formatos externos cuja especificação determine o nome;
- nomes de pacotes de terceiros;
- siglas consolidadas, como PDF, OCR, JSON, SHA-256, DPI e UTM.

## Vocabulário canônico

| Inglês anterior | Português canônico |
|---|---|
| batch | lote |
| converter | conversor |
| convert | converter |
| diagnostic | diagnostico |
| assess | avaliar |
| assessment | avaliacao |
| extract | extrair |
| extraction | extracao |
| manifest | manifesto |
| model | modelo |
| page | pagina |
| map | mapa |
| table | tabela |
| raster | raster |
| visual | visual |
| coordinate | coordenada |
| quality | qualidade |
| review | revisao |
| warning | aviso |
| repeated graphic | grafico recorrente |
| decorative | decorativo |
| route | rota |
| candidate | candidato |
| confirmed | confirmado |
| unknown | desconhecido |
| source | origem |
| output | saida |
| input | entrada |
| text normalization | normalizacao de texto |
| hashing | resumo criptografico |

## Exemplos

```python
# Antes
assessment = assess_raster_visual(image)
map_pages = []

# Depois
avaliacao = avaliar_visual_raster(imagem)
paginas_de_mapa = []
```

```text
src/conversor_his/raster_visual.py
src/conversor_his/visual_raster.py

tests/test_raster_visual.py
tests/test_visual_raster.py
```

## Compatibilidade transitória

Durante uma única versão de transição, os nomes antigos podem existir apenas como adaptadores finos que importam e reexportam os nomes novos. Nenhuma lógica nova deve ser implementada nos adaptadores antigos.

Os adaptadores devem conter aviso de descontinuação e ser removidos na versão principal seguinte.

## Manifestos

Os novos manifestos devem usar campos em português. Durante a versão de transição, o leitor deve aceitar tanto os campos antigos quanto os novos. O escritor deve produzir apenas os campos novos, salvo quando o modo de compatibilidade for explicitamente solicitado.

## Critério de conclusão

A refatoração somente será considerada concluída quando:

1. não houver módulos próprios com nomes em inglês;
2. não houver funções, classes, métodos ou variáveis públicas próprias em inglês;
3. os testes estiverem integralmente em português;
4. a documentação e o CLI usarem apenas os nomes novos;
5. a suíte de testes e o Ruff forem aprovados;
6. uma busca automatizada não encontrar símbolos antigos fora dos adaptadores de compatibilidade.
