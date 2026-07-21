# Conversor HIS

Ferramenta para diagnosticar, converter e validar diplomas legais municipais em Markdown estruturado, com OCR seletivo, rastreabilidade e controle de qualidade.

Versão atual: **0.6.1**.

## Princípios

- utiliza exclusivamente os diplomas indicados pelo município;
- preserva integralmente os arquivos originais;
- diagnostica cada página antes de escolher a rota de conversão;
- aplica extração nativa quando possível e OCR quando necessário;
- preserva simultaneamente imagem e texto em páginas visuais;
- preserva tabelas confirmadas, candidatas, mistas e continuações como texto bruto e imagem;
- compara extrações `layout` e simples quando encontra rotação ou espaçamento excessivo;
- normaliza espaços e caracteres invisíveis na versão textual pesquisável;
- mantém o `layout` bruto para diagnóstico estrutural e preservação tabular;
- registra decisões, avisos, tempos e artefatos em manifestos auditáveis;
- grava Markdown e manifestos de forma atômica;
- permite limitar, interromper e retomar lotes municipais.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,ocr]"
```

## Uso

### Diagnóstico individual

```powershell
conversor-his diagnosticar `
  --entrada "D:\corpus\originais\lei.pdf" `
  --saida "D:\corpus\processado"
```

### Conversão individual

```powershell
conversor-his converter `
  --entrada "D:\corpus\originais\lei.pdf" `
  --saida "D:\corpus\processado"
```

### Lote completo

O valor `0` em `--documentos` processa todos os PDFs elegíveis:

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio" `
  --documentos 0
```

### Amostra limitada

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio_teste" `
  --documentos 10
```

A forma abreviada é `-n 10`.

### Retomada

```powershell
conversor-his converter-lote `
  --entrada "D:\corpus\originais\municipio.zip" `
  --saida "D:\corpus\processado\municipio" `
  --documentos 0 `
  --retomar
```

A retomada exige coincidência entre hash da fonte, versão do conversor, DPI e produtos finais existentes.

Por padrão, uma pasta-raiz única do ZIP é removida. Use `--manter-raiz-comum` para preservá-la.

## Detecção tabular

A classificação é executada sobre o texto bruto em modo `layout`, antes da normalização destinada à pesquisa. O detector considera:

- títulos de tabela, quadro e anexo;
- cabeçalhos urbanísticos;
- posições horizontais recorrentes;
- códigos de zonas e macrozonas;
- lote, testada, recuos, taxas, gabarito e coeficiente de aproveitamento;
- linhas compactas com valores e requisitos;
- continuidade de matrizes em páginas sem cabeçalho repetido;
- páginas mistas, com prosa e quadro na mesma página;
- penalizações para incisos, definições jurídicas, parágrafos longos e coordenadas.

Estados possíveis:

- `confirmed`;
- `candidate`;
- `mixed_candidate`;
- `continuation_candidate`;
- `not_table`.

As quatro primeiras classes preservam imagem e texto bruto para revisão estrutural.

## Comportamento do lote

- ordena os PDFs por caminho para tornar amostras reproduzíveis;
- relaciona arquivos não PDF no manifesto como ignorados;
- rejeita travessia de diretórios, caminhos absolutos e links simbólicos;
- detecta duplicidade de caminho e conteúdo por SHA-256;
- isola falhas por documento;
- atualiza o manifesto geral antes e depois de cada PDF;
- registra `started_at`, `updated_at` e `completed_at`;
- distingue `completed`, `completed_with_limit` e `completed_with_failures`;
- mantém produtos concluídos quando a execução é interrompida.

## Produtos gerados

- `<documento>.md`: conteúdo pesquisável e rastreável por página;
- `<documento>.manifest.json`: hashes, rotas, evidências, avisos, artefatos e tempo;
- `<documento>_assets/`: imagens visuais e tabulares;
- `<nome-do-zip>.lote.manifest.json`: inventário incremental do lote.

## Histórico de versões

### 0.6.1 — detecção tabular orientada pelo corpus normativo

- corrige a classificação para usar o `layout` bruto, sem perder os espaços que representam colunas;
- recupera matrizes de parâmetros urbanísticos como a página 131 do Plano Diretor de Abreu e Lima;
- mantém listas de definições jurídicas como `not_table`;
- reconhece códigos de zona, parâmetros urbanísticos e linhas compactas de valores;
- acrescenta `mixed_candidate` para páginas parcialmente tabulares;
- acrescenta `continuation_candidate` para quadros que prosseguem sem cabeçalho repetido;
- registra no manifesto evidências como linhas numéricas, códigos de zona, parâmetros encontrados e perfil do conteúdo;
- incorpora testes derivados de exemplos reais do corpus, sem regras específicas por município ou página.

### 0.6.0 — validação operacional em corpus normativo real

- promovida após execução sem falhas em amostra real de dez documentos e 332 páginas;
- corrige referências Markdown de imagens cujos caminhos contêm espaços;
- normaliza Unicode, espaços posicionais excessivos e caracteres de largura zero;
- compara extração simples com `layout` quando há espaçamento anômalo;
- preserva o texto bruto de tabelas em bloco próprio;
- reforça penalizações contra falsos positivos tabulares em listas jurídicas;
- registra caminhos de arquivos não PDF ignorados;
- preserva o instante inicial do lote e acrescenta instante de conclusão;
- usa o estado `completed_with_limit` quando apenas a amostra solicitada foi concluída.

### 0.5.3 — preservação visual e execução retomável

- acrescenta `--documentos`, `-n` e `--retomar`;
- cria manifesto incremental;
- detecta duplicados por conteúdo;
- captura texto rotacionado;
- preserva texto e imagem em páginas visuais e tabulares.

## Estado atual

A série 0.6.x é operacional para conversão controlada. A detecção tabular permanece em calibração progressiva sobre corpus real, com prioridade para evitar falsos negativos em matrizes de parâmetros urbanísticos sem reintroduzir falsos positivos em listas jurídicas.

## Licenciamento

- código-fonte, testes e automações próprios: **MIT License**;
- documentação e metodologia: **CC BY 4.0**;
- dados sintéticos expressamente identificados: **CC0 1.0**;
- dependências e modelos: licença própria;
- legislação e conteúdos de terceiros não são relicenciados.

## Segurança documental

O repositório não deve armazenar corpus municipais, modelos de OCR, arquivos convertidos nem dados de trabalho.
