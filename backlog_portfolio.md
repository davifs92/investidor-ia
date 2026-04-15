# Backlog Técnico — Análise de Portfólio (Investidor-IA)
> Versão revisada com correções aplicadas — Abril/2026

## Contexto

O Investidor-IA já possui análise individual por ticker, com coleta de dados de mercado, execução de analistas especializados, consolidação por persona investidora, persistência local e geração de PDF. A nova funcionalidade de análise de portfólio deve reaproveitar essa base existente para permitir uma leitura consolidada de uma carteira com múltiplos ativos, incluindo diagnóstico estrutural, score, riscos, forças, fragilidades e sugestões de rebalanceamento.

## Objetivo da Epic

Permitir que o usuário monte uma carteira com múltiplos ativos e receba uma análise consolidada do portfólio, usando os analistas já existentes por ticker e uma nova camada de agregação com diagnóstico, score, riscos e sugestões de rebalanceamento.

## Diretrizes Gerais para Implementação

- Linguagem: Python 3.11+
- Seguir a arquitetura atual do projeto
- Reutilizar código existente e evitar duplicação
- Manter separação clara entre domínio, serviço, interface e persistência
- Usar tipagem forte
- Implementar tratamento de erro e logs claros
- Não quebrar funcionalidades existentes
- Escrever testes unitários em cada componente de lógica (não apenas ao final)
- Evitar acoplamento da lógica de negócio à interface Streamlit
- Carteiras mistas BR/US devem sempre ser processadas com moeda de referência unificada
- O pipeline por ativo deve operar em modo portfólio por padrão (subconjunto de analistas), não modo completo
- O limite padrão de ativos por análise é 20; carteiras maiores exibem aviso de tempo estimado

---

## STORY 1 — Criar modelos de domínio de portfólio

### Contexto
A funcionalidade precisa de estruturas padronizadas para representar os ativos de uma carteira, os dados de entrada da análise, os resultados individuais por ativo e a saída consolidada final.

### Objetivo
Criar modelos de domínio claros e reutilizáveis para suportar toda a funcionalidade de análise de portfólio.

### Escopo
Criar um novo módulo para modelos de portfólio contendo estruturas para:
- item da carteira
- entrada da análise
- resultado individual por ativo
- resultado consolidado da carteira

Os modelos de `PortfolioItem` devem incluir campos: `ticker`, `market`, `weight` (peso manual), `quantity` (opcional), `avg_price` (opcional), `current_price` (preenchido em runtime pela Story 2B), `market_value` (calculado), `normalized_weight` (calculado pela Story 4), `sector` (preenchido em runtime pela Story 8) e `currency`.

A estrutura de saída consolidada (`PortfolioAnalysisOutput`) deve incluir campos para `portfolio_sentiment`, `weighted_confidence`, `concentration_metrics`, `diversification_score`, `overall_score`, `subscores`, `objective_fit`, `strengths`, `weaknesses`, `risks`, `rebalancing_suggestions`, `persona_analysis`, `asset_analyses`, `failed_assets` e `analysis_metadata`.

### Critérios de aceite
- Existe uma estrutura para representar cada ativo da carteira com ticker, mercado, peso e campos opcionais de quantidade, preço médio, preço atual e setor
- Existe uma estrutura para representar a entrada da análise com lista de ativos, objetivo da carteira, persona, moeda de referência e modo de análise
- Existe uma estrutura para representar a análise individual de cada ativo
- Existe uma estrutura para representar a saída consolidada da análise com todos os campos necessários para UI, PDF e persistência
- Os modelos possuem tipagem explícita
- Os modelos podem ser reutilizados por serviços, interface, persistência e PDF

### Arquivos candidatos
- `src/portfolio/models.py`

### Dependências
Nenhuma

---

## STORY 2 — Criar orquestrador principal da análise de portfólio

### Contexto
A funcionalidade precisa de um ponto central para coordenar todas as etapas da análise, desde a validação da carteira até a geração do parecer final.

### Objetivo
Implementar um serviço principal que execute o pipeline completo da análise de portfólio.

### Escopo
Criar um serviço central responsável por:
1. validar entrada (Story 3)
2. obter preços atuais e calcular valores de mercado (Story 2B)
3. normalizar pesos (Story 4)
4. disparar análise por ativo em paralelo (Stories 5 e 6)
5. consolidar resultados e calcular métricas (Stories 7 e 8)
6. calcular scores (Stories 9 e 10)
7. avaliar adequação ao objetivo (Story 11)
8. gerar insights e sugestões (Story 12)
9. chamar a consolidação por persona quando disponível — **a persona é injetada como dependência opcional; o orquestrador retorna resultado completo sem persona quando ela não for fornecida**

### Critérios de aceite
- Existe um serviço principal único de análise de portfólio
- O pipeline possui etapas bem definidas e organizadas
- A lógica não fica acoplada à UI
- A saída final segue o modelo consolidado definido na Story 1
- O orquestrador aceita `persona_consolidator=None` e retorna saída completa sem bloquear quando a persona não estiver disponível
- O fluxo é extensível para futuras métricas ou novas personas

### Arquivos candidatos
- `src/portfolio/analyzer.py`

### Dependências
- Story 1

---

## STORY 2B — Obter preço atual e calcular valor de mercado por posição ⚡ *[nova]*

### Contexto
Uma carteira com ativos BR (BRL) e US (USD) não pode ter pesos e concentrações calculados corretamente sem converter todos os valores para uma moeda de referência comum. Além disso, o cálculo de P/L por posição exige o preço atual de mercado.

### Objetivo
Buscar preços atuais, calcular o valor de mercado de cada posição e converter para a moeda de referência para permitir cálculos corretos em carteiras mistas.

### Escopo
Implementar um módulo que:
- Busca preço atual de cada ativo via `yfinance.Ticker(ticker).history(period='1d')` (já usado no projeto)
- Quando `quantity` for informada, calcula `market_value = quantity × current_price`
- Quando apenas `weight` for informado, usa o peso manual como proxy de valor relativo
- Para carteiras mistas BR/US, obtém cotação USD/BRL via `yfinance.Ticker('BRL=X')` e converte todos os valores para a moeda de referência (BRL ou USD, configurável em `src/settings.py`, padrão: BRL)
- Recalcula os pesos reais a partir dos valores de mercado quando `quantity` for disponível
- Usa os pesos manuais normalizados quando `quantity` não for disponível
- Registra falha de obtenção de preço por ativo sem derrubar o pipeline, usando `weight` como fallback

### Critérios de aceite
- O sistema obtém preço atual via `yfinance` para cada ativo antes dos cálculos de concentração
- Carteiras com `quantity` informada têm pesos calculados a partir do valor de mercado real
- Carteiras sem `quantity` usam os pesos manuais normalizados
- A moeda de referência é configurável (padrão BRL)
- Ativos US têm seus valores convertidos para a moeda de referência usando cotação em tempo real
- Falha na obtenção de preço não derruba o pipeline; o sistema usa peso manual e registra aviso
- Os campos `current_price`, `market_value` e `normalized_weight` ficam preenchidos no modelo antes da análise

### Arquivos candidatos
- `src/portfolio/price_fetcher.py`
- `src/portfolio/models.py` (extensão dos campos)
- `src/settings.py` (constante `PORTFOLIO_REFERENCE_CURRENCY`)

### Dependências
- Story 1

---

## STORY 3 — Implementar validação da carteira informada

### Contexto
A análise de portfólio depende de dados mínimos consistentes. Entradas inválidas devem ser barradas antes da execução.

### Objetivo
Garantir que a carteira recebida esteja válida antes do início da análise.

### Escopo
Implementar validações para:
- carteira vazia
- ticker ausente
- mercado inválido (fora de `['BR', 'US']`)
- pesos negativos
- soma total de pesos menor ou igual a zero
- carteira com mais de 20 ativos (exibe aviso de performance, não bloqueia)

### Critérios de aceite
- O sistema rejeita carteira sem ativos
- O sistema rejeita item sem ticker
- O sistema rejeita peso negativo
- O sistema rejeita mercado fora do conjunto suportado
- O sistema retorna erro claro e acionável
- A validação é executada antes do início das análises individuais
- Carteiras acima do limite configurável de ativos exibem aviso mas permitem execução
- **O módulo possui cobertura de teste unitário para cada regra de validação e para mensagens de erro**

### Arquivos candidatos
- `src/portfolio/validators.py`
- `tests/portfolio/test_validators.py`

### Dependências
- Story 1

---

## STORY 4 — Implementar normalização de pesos da carteira

### Contexto
Usuários podem informar pesos que não somam exatamente 100. A análise precisa trabalhar com pesos normalizados.

### Objetivo
Normalizar proporcionalmente os pesos da carteira para garantir consistência nos cálculos.

### Escopo
Implementar rotina de normalização que:
- calcula a soma dos pesos
- normaliza proporcionalmente quando a soma for diferente de 100
- preserva os demais campos dos ativos
- armazena resultado em `normalized_weight` no modelo, sem sobrescrever o `weight` original

### Critérios de aceite
- Carteiras com soma igual a 100 permanecem inalteradas
- Carteiras com soma diferente de 100 são normalizadas corretamente
- A soma final dos pesos normalizados é 100 dentro de tolerância numérica aceitável (1e-6)
- A normalização não altera indevidamente outros campos dos ativos
- O peso original informado pelo usuário é preservado junto ao peso normalizado
- Os pesos finais usados na análise ficam disponíveis para exibição
- **O módulo possui cobertura de teste unitário para somas acima, abaixo e exatamente em 100, incluindo casos extremos (um ativo, pesos muito pequenos)**

### Arquivos candidatos
- `src/portfolio/normalizers.py`
- `tests/portfolio/test_normalizers.py`

### Dependências
- Story 1
- Story 3

---

## STORY 5 — Reutilizar pipeline existente para análise individual por ativo

### Contexto
O sistema já possui pipeline de análise individual por ticker. Essa lógica deve ser reaproveitada, mas em modo portfólio: executando apenas o subconjunto de analistas necessário para extrair sinal de qualidade, valuation e momentum — sem o custo e tempo do pipeline completo.

### Objetivo
Executar a análise de cada ativo da carteira usando a infraestrutura atual do projeto em modo otimizado para portfólio.

### Escopo
Criar uma camada que:
- Recebe um item da carteira
- **Verifica o cache `diskcache` e os relatórios existentes em `db/reports.json` antes de executar nova análise. Análises recentes (dentro de TTL configurável, padrão 24h para modo portfólio) são reutilizadas com indicação visual**
- Quando não há cache disponível, invoca os analistas `financial`, `valuation` e `technical` — **não o pipeline completo de 6 analistas**
- Os analistas `news`, `macro` e `earnings_release` são opcionais e ativados por flag `PORTFOLIO_FULL_ANALYSIS=true` em `src/settings.py`
- Extrai do resultado: `ticker`, `weight`, `sentiment`, `confidence`, `financial_summary`, `valuation_summary`
- Adapta o resultado para o modelo `PortfolioAssetAnalysis`

### Critérios de aceite
- Cada ativo da carteira gera um `PortfolioAssetAnalysis` com pelo menos ticker, peso, sentimento, confiança e resumo
- O sistema verifica cache antes de executar nova análise; cache hit é sinalizado visualmente
- Por padrão, apenas 3 analistas são executados por ativo (financial, valuation, technical)
- O modo completo (6 analistas) é ativável via configuração
- O adaptador funciona tanto para mercado BR quanto US
- O resultado individual pode ser usado na agregação
- O sistema não duplica lógica já implementada no fluxo de relatório por ticker

### Arquivos candidatos
- `src/portfolio/asset_pipeline.py`
- `src/portfolio/adapters.py`
- `src/settings.py` (constantes `PORTFOLIO_ANALYSIS_TTL` e `PORTFOLIO_FULL_ANALYSIS`)

### Dependências
- Story 1
- Story 2

---

## STORY 6 — Executar análise dos ativos em paralelo

### Contexto
Carteiras podem ter múltiplos ativos. Executar a análise em série aumentaria desnecessariamente o tempo total.

### Objetivo
Reduzir tempo de execução da análise de portfólio por meio de paralelismo.

### Escopo
Adaptar o orquestrador para:
- disparar análises individuais de forma concorrente usando `asyncio.gather` (padrão já adotado no projeto)
- tratar falhas isoladas sem interromper o processamento completo
- consolidar os resultados retornados

### Critérios de aceite
- As análises dos ativos são executadas de forma concorrente
- Erro em um ativo não interrompe a análise dos demais
- O sistema registra quais ativos falharam
- O resultado final suporta sucesso parcial
- O comportamento é compatível com a estratégia de paralelismo já usada no projeto com `asyncio.gather`

### Arquivos candidatos
- `src/portfolio/analyzer.py`

### Dependências
- Story 2
- Story 5

---

## STORY 19 — Tratar falhas parciais com resiliência ⚡ *[movida para Sprint 1]*

### Contexto
Em uma carteira com vários ativos, é importante que falhas pontuais não invalidem toda a análise. Esta story foi movida para Sprint 1 porque a estratégia de fallback é parte da fundação do pipeline, não um polimento posterior.

### Objetivo
Garantir comportamento resiliente diante de falhas por ativo ou por fonte de dados desde a primeira versão do pipeline.

### Escopo
Implementar estratégia para:
- fallback por ativo com captura de exceções no nível de `asset_pipeline.py`
- registro estruturado de erro com `ticker`, `market`, `error_type` e `error_message`
- continuação da análise com os demais ativos
- sinalização de sucesso parcial no relatório final via campo `failed_assets`

### Critérios de aceite
- Um ativo com falha não derruba a análise completa
- O relatório final contém lista `failed_assets` com ticker, mercado e motivo da falha
- O sistema registra logs úteis para depuração (logger estruturado)
- O cálculo consolidado trata corretamente os ativos com falha (exclui do denominador de médias ponderadas)
- O usuário vê claramente que a análise foi concluída com dados parciais quando houver falhas
- A estratégia de fallback é testada com ativos de ticker inválido e com timeout simulado

### Arquivos candidatos
- `src/portfolio/analyzer.py`
- `src/portfolio/asset_pipeline.py`
- `tests/portfolio/test_resilience.py`

### Dependências
- Story 5
- Story 6

---

## STORY 7 — Consolidar sinais individuais no nível da carteira

### Contexto
A análise da carteira precisa traduzir os resultados individuais dos ativos em uma leitura consolidada.

### Objetivo
Gerar métricas agregadas de sentimento e confiança da carteira.

### Escopo
Calcular:
- percentual ponderado da carteira em ativos bullish
- percentual ponderado em ativos neutral
- percentual ponderado em ativos bearish
- confiança média ponderada da carteira
- mapeamento de sentimento para score numérico: BULLISH=1.0, NEUTRAL=0.5, BEARISH=0.0

### Critérios de aceite
- O cálculo usa os pesos normalizados dos ativos
- O sistema consolida corretamente os sentimentos individuais
- A confiança média ponderada é calculada de forma consistente
- Ativos inválidos ou não analisados são excluídos do cálculo com peso redistribuído proporcionalmente
- A consolidação pode ser reutilizada pelos cálculos de score e insights
- **O módulo possui cobertura de teste unitário para carteiras 100% bullish, 100% bearish, mistas e com ativos inválidos**

### Arquivos candidatos
- `src/portfolio/aggregator.py`
- `tests/portfolio/test_aggregator.py`

### Dependências
- Story 1
- Story 5
- Story 6

---

## STORY 8 — Calcular métricas de concentração da carteira

### Contexto
Uma das utilidades centrais da análise de portfólio é detectar concentração excessiva em ativo, mercado ou setor.

### Objetivo
Identificar riscos estruturais ligados à concentração da carteira.

### Escopo
Implementar cálculo e leitura de concentração para:
- peso excessivo por ativo (limite configurável, padrão 25%)
- concentração por mercado BR/US
- concentração por setor, com estratégia explícita de obtenção:
  - Ativos BR: setor via dados do provider (StatusInvest/Fundamentus)
  - Ativos US: setor via `yfinance.Ticker(ticker).info['sector']` como fallback quando o provider não retornar (já que `screener()` US não está implementado)
  - Quando o setor não puder ser obtido por nenhuma fonte: registrar como "Setor não disponível" e exibir aviso claro na interface
- alertas derivados das concentrações identificadas
- cálculo do índice HHI (Herfindahl-Hirschman Index) normalizado por ativo para uso no score geral

### Critérios de aceite
- O sistema identifica ativos com peso acima do limite configurável
- O sistema identifica concentração excessiva por mercado
- O sistema tenta obter setor via provider BR ou `yfinance.info` para US antes de marcar como indisponível
- O sistema exibe aviso claro quando setor não estiver disponível para um ou mais ativos
- Os alertas gerados são claros e acionáveis
- O HHI normalizado fica disponível para consumo pelo score geral (Story 10)
- As métricas ficam disponíveis para uso em UI, relatório e PDF
- **O módulo possui cobertura de teste unitário para cenários de concentração alta, balanceada e com setor indisponível**

### Arquivos candidatos
- `src/portfolio/metrics.py`
- `src/portfolio/aggregator.py`
- `src/portfolio/sector_resolver.py` *(novo — encapsula lógica de obtenção de setor por mercado)*
- `tests/portfolio/test_metrics.py`

### Dependências
- Story 1
- Story 2B
- Story 4
- Story 5

---

## STORY 9 — Calcular score de diversificação da carteira

### Contexto
O usuário precisa de uma leitura simples e rápida sobre a saúde estrutural da carteira.

### Objetivo
Gerar uma nota de diversificação baseada em critérios transparentes.

### Escopo
Criar um score de diversificação que considere, em ordem decrescente de peso:
1. Risco de concentração por ativo: penaliza se qualquer ativo > 30% (peso 40%)
2. Número de ativos: escala logarítmica, satura em 15 ativos (peso 25%)
3. Concentração por mercado: penaliza se um mercado > 80% (peso 20%)
4. Concentração por setor: penaliza se um setor > 50% quando dado disponível (peso 15%)

Score final na escala de 0 a 10, com uma casa decimal. A explicação textual do score deve listar o principal fator penalizante.

### Critérios de aceite
- O score possui escala 0–10 e regra de composição documentada no código
- O score penaliza concentração excessiva de forma proporcional
- O cálculo é determinístico para os mesmos inputs
- O score possui explicação textual identificando o principal fator de penalização
- O resultado pode ser consumido pelo score geral da carteira
- **O módulo possui cobertura de teste unitário para carteiras concentradas, balanceadas, com 1 ativo e com setor indisponível**

### Arquivos candidatos
- `src/portfolio/scoring.py`
- `tests/portfolio/test_scoring.py`

### Dependências
- Story 8

---

## STORY 10 — Calcular score geral da carteira

### Contexto
Além de métricas isoladas, o usuário precisa de uma visão executiva consolidada da carteira.

### Objetivo
Produzir uma nota geral da carteira com base em múltiplas dimensões com fórmula explícita e reproduzível.

### Escopo
Compor o score geral a partir das seguintes dimensões com os pesos abaixo:

| Dimensão | Peso | Fonte |
|---|---|---|
| Qualidade dos ativos (média ponderada de `confidence × sentiment_score` por ativo) | 30% | Story 7 |
| Diversificação (score da Story 9) | 25% | Story 9 |
| Adequação ao objetivo | 20% | Story 11 |
| Risco de concentração (1 − HHI normalizado) | 15% | Story 8 |
| Valuation médio ponderado (derivado da confiança dos analistas de valuation) | 10% | Story 5 |

Score final na escala de 0 a 10, arredondado para uma casa decimal. Os pesos são definidos como constantes nomeadas em `src/portfolio/scoring.py` para facilitar ajuste futuro sem quebrar a estrutura. Quando Story 11 não estiver disponível (MVP), a dimensão de adequação ao objetivo é redistribuída proporcionalmente entre as demais.

### Critérios de aceite
- O score geral possui faixa 0–10 e composição documentada no código
- As dimensões que compõem o score ficam visíveis como `subscores` no modelo de saída
- A fórmula é reproduzível: mesmos inputs geram sempre o mesmo score
- O score geral alimenta o resumo final da análise
- Os pesos são configuráveis via constantes sem alterar a interface do serviço
- **O módulo possui cobertura de teste unitário para a fórmula de composição e para cenários com dimensões parcialmente ausentes**

### Arquivos candidatos
- `src/portfolio/scoring.py`
- `tests/portfolio/test_scoring.py`

### Dependências
- Story 7
- Story 8
- Story 9

---

## STORY 11 — Avaliar adequação da carteira ao objetivo do investidor

### Contexto
Uma carteira pode parecer boa em termos gerais e ainda assim estar desalinhada com o objetivo declarado pelo usuário. A persona escolhida deve ser consistente com o objetivo.

### Objetivo
Comparar a composição e os sinais da carteira com o objetivo informado pelo investidor, identificando desalinhamentos incluindo inconsistências entre objetivo e persona.

### Escopo
Implementar avaliação de adequação para objetivos:
- `dividendos`: verifica presença de ativos com histórico de dividendos, alerta se peso em crescimento puro > 40%
- `crescimento`: verifica presença de ativos com valuation de crescimento, alerta se peso em ativos de renda > 50%
- `equilibrio`: valida distribuição entre estilos
- `longo_prazo_conservador`: verifica qualidade e estabilidade dos ativos

Verificar também consistência objetivo × persona: se objetivo for `dividendos` e persona for `Lynch`, ou objetivo `crescimento` e persona `Barsi`, emitir alerta de inconsistência explicando a divergência.

### Critérios de aceite
- O sistema recebe o objetivo da carteira como insumo
- O sistema gera um parecer de alinhamento com o objetivo
- O sistema identifica desalinhamentos relevantes entre composição e objetivo
- O sistema alerta inconsistências entre objetivo declarado e persona escolhida
- A leitura de adequação retorna um score de 0 a 10 para uso na Story 10
- A lógica é extensível para novos objetivos
- **O módulo possui cobertura de teste unitário para cada combinação objetivo/persona e para os cenários de alinhamento e desalinhamento**

### Arquivos candidatos
- `src/portfolio/objective_fit.py`
- `tests/portfolio/test_objective_fit.py`

### Dependências
- Story 7
- Story 8
- Story 10

---

## STORY 12 — Gerar forças, fragilidades, riscos e sugestões de rebalanceamento

### Contexto
A análise de portfólio deve ser útil na prática, destacando o que está funcionando, o que preocupa e o que pode ser ajustado.

### Objetivo
Transformar métricas e sinais consolidados em insights acionáveis.

### Escopo
Gerar:
- principais forças da carteira (ex: diversificação setorial adequada, alta confiança nos ativos bullish)
- principais fragilidades (ex: concentração excessiva em único ativo, exposição cambial não gerenciada)
- principais riscos (ex: sensibilidade a juros com SELIC alta, ativos bearish com peso significativo)
- sugestões de rebalanceamento do tipo: reduzir ativo X acima do peso alvo, aumentar exposição internacional, revisar ativo com sinal bearish e peso > 15%

As sugestões não devem fazer promessas de retorno e devem ser coerentes com o disclaimer já existente nos PDFs do projeto. O tom das sugestões deve ser adaptado à persona escolhida.

### Critérios de aceite
- O sistema gera listas claras e legíveis
- Os insights derivam das métricas e análises reais da carteira, não de templates genéricos
- Há pelo menos três itens por categoria quando os dados permitirem
- As sugestões não fazem promessas de retorno
- As sugestões são coerentes com o diagnóstico consolidado
- O tom das sugestões respeita o estilo da persona escolhida
- **O módulo possui cobertura de teste unitário verificando que insights derivam de dados reais e não de strings hardcoded**

### Arquivos candidatos
- `src/portfolio/insights.py`
- `tests/portfolio/test_insights.py`

### Dependências
- Story 7
- Story 8
- Story 10
- Story 11

---

## STORY 13 — Estender personas existentes para consolidação de portfólio ⚡ *[reescrita]*

### Contexto
O produto já possui personas investidoras em `src/agents/`. A nova funcionalidade deve preservar essa experiência também no nível da carteira, **sem criar arquivos duplicados** das personas. A lógica de personalidade existe em um único lugar.

### Objetivo
Gerar parecer final da carteira segundo a ótica da persona escolhida, estendendo as personas existentes com suporte ao novo contexto de portfólio.

### Escopo
Estender cada persona existente (`buffett.py`, `graham.py`, `barsi.py`, `lynch.py`) para aceitar um novo tipo de input via parâmetro de contexto `analysis_mode='portfolio'`:
- Quando `analysis_mode='portfolio'`, a persona recebe `PortfolioAnalysisOutput` como insumo (score geral, sentimento ponderado, subscores, principais riscos, adequação ao objetivo, forças e fragilidades)
- Quando `analysis_mode='ticker'` (padrão), o comportamento atual é preservado sem alterações
- O parecer de portfólio inclui: avaliação estratégica da composição, comentário sobre os maiores riscos identificados, recomendação de manutenção, observação ou rebalanceamento — tudo no estilo da persona

Criar uma interface compartilhada em `src/portfolio/persona_interface.py` que define o contrato de input/output para o modo portfólio, sem duplicar código de personalidade.

### Critérios de aceite
- Cada persona existente suporta `analysis_mode='portfolio'` sem alterar o comportamento atual em modo ticker
- Cada persona produz um parecer final coerente com seu estilo ao analisar o portfólio
- O texto final reflete a identidade da persona (Buffett: moat e longo prazo; Graham: margem de segurança; Barsi: renda e dividendos; Lynch: GARP e crescimento sustentável)
- O sistema respeita as restrições já existentes por mercado e persona (Barsi apenas BR, Lynch apenas US)
- A conclusão final da carteira passa obrigatoriamente por uma persona
- Nenhum arquivo de lógica de persona é duplicado

### Arquivos candidatos
- `src/agents/buffett.py` (extensão)
- `src/agents/graham.py` (extensão)
- `src/agents/barsi.py` (extensão)
- `src/agents/lynch.py` (extensão)
- `src/portfolio/persona_interface.py` *(novo — define contrato de portfólio)*

### Dependências
- Story 10
- Story 11
- Story 12

---

## STORY 14 — Criar página de análise de portfólio no Streamlit

### Contexto
A nova funcionalidade precisa de uma interface dedicada para montagem e análise da carteira.

### Objetivo
Disponibilizar uma nova página no app para entrada dos dados e execução da análise.

### Escopo
Criar uma nova página que permita:
- adicionar múltiplos ativos (formulário incremental com botão "Adicionar ativo")
- informar peso por ativo (número entre 0 e 100)
- selecionar mercado (BR ou US) por ativo
- definir objetivo da carteira (dropdown: dividendos, crescimento, equilíbrio, longo prazo conservador)
- escolher persona (respeitando restrições por mercado já existentes)
- iniciar a análise com botão único de ação

### Critérios de aceite
- Existe uma nova página acessível no app
- O usuário consegue montar uma carteira com múltiplos ativos
- O usuário consegue escolher objetivo e persona
- O botão de análise aciona o pipeline correto
- A UI segue o padrão visual já usado no projeto
- O formulário não permite submeter carteira vazia ou com erros de validação óbvios

### Arquivos candidatos
- `pages/portfolio.py`

### Dependências
- Story 2
- Story 3
- Story 4

---

## STORY 15 — Exibir resultado consolidado da análise de portfólio

### Contexto
Após a execução, o usuário precisa visualizar a carteira de forma clara e organizada, incluindo visualizações gráficas que comuniquem concentração e sentimento de forma imediata.

### Objetivo
Apresentar o resultado da análise de portfólio em uma estrutura útil, legível e visualmente informativa.

### Escopo
Exibir as seguintes seções em ordem:
1. **Score geral e subscores** — indicador visual (gauge ou barra de progresso) para o score geral; tabela de subscores por dimensão
2. **Composição da carteira** — tabela de ativos com ticker, peso, peso normalizado, sentimento e confiança
3. **Visualizações gráficas** via `st.plotly_chart`:
   - Gráfico de pizza/donut com alocação por ativo
   - Barra empilhada com distribuição de sentimento ponderado (% BULLISH / NEUTRAL / BEARISH)
   - Mapa de calor simples de concentração por setor/mercado quando disponível
4. **Alertas** — seção de alertas de concentração e riscos
5. **Forças e fragilidades** — listas lado a lado
6. **Sugestões de rebalanceamento** — lista acionável
7. **Parecer final da persona** — seção em destaque com estilo da persona
8. **Ativos com falha** — quando houver, seção informativa sobre quais ativos não foram analisados

### Critérios de aceite
- O resultado aparece organizado pelas seções acima
- O usuário consegue identificar rapidamente os principais pontos da carteira pelo score e pelos gráficos
- Os dados individuais por ativo ficam acessíveis na tabela de composição
- O parecer final da persona aparece em destaque visual
- A exibição reutiliza ao máximo componentes e padrões já existentes no projeto
- Gráficos são exibidos com título e legenda descritivos

### Arquivos candidatos
- `pages/portfolio.py`

### Dependências
- Story 10
- Story 12
- Story 13
- Story 14

---

## STORY 16 — Exibir progresso e status da análise por ativo

### Contexto
A análise de portfólio pode levar mais tempo que a análise individual, especialmente em carteiras maiores.

### Objetivo
Dar transparência ao usuário durante a execução da análise.

### Escopo
Adaptar o padrão atual de feedback visual com `st.empty()` (já usado em `pages/generate.py`) para mostrar:
- andamento da análise por ativo (ícone de status: aguardando / analisando / concluído / falha)
- indicação de cache hit quando análise for reutilizada
- estado geral da execução (barra de progresso geral)

### Critérios de aceite
- O usuário visualiza o progresso da análise por ativo usando o padrão `st.empty()` já adotado no projeto
- É possível identificar ativos com falha e cache hits
- O feedback visual não interrompe o processamento
- O sistema apresenta claramente se a análise terminou com sucesso total ou parcial

### Arquivos candidatos
- `pages/portfolio.py`
- `src/portfolio/analyzer.py`

### Dependências
- Story 6
- Story 14

---

## STORY 17 — Persistir relatórios de portfólio

### Contexto
Assim como já ocorre com relatórios individuais, a análise de portfólio deve poder ser salva para consulta posterior.

### Objetivo
Permitir armazenamento local dos relatórios de portfólio.

### Escopo
Implementar persistência para:
- salvar análise consolidada após conclusão
- listar análises anteriores
- recuperar análise salva posteriormente

### Critérios de aceite
- O relatório de portfólio é salvo localmente em `db/portfolio_reports.json`
- O formato de armazenamento não conflita com os relatórios individuais em `db/reports.json`
- O relatório salvo contém metadados suficientes: data, ativos, objetivo, persona, score geral
- A persistência é reutilizável por interface e exportação PDF

### Arquivos candidatos
- `src/portfolio/persistence.py`
- `db/portfolio_reports.json`

### Dependências
- Story 15

---

## STORY 17B — Gerenciar portfólios salvos (composição) ⚡ *[nova]*

### Contexto
Story 17 persiste o **relatório de análise**, mas não a **composição da carteira**. O usuário precisa poder salvar, editar e reanalisar a mesma carteira semanas depois sem redigitar todos os ativos.

### Objetivo
Permitir que o usuário salve, carregue, edite, duplique e exclua portfólios por composição, independentemente das análises realizadas.

### Escopo
- Salvar composição de ativos (lista de `PortfolioItem` com ticker, mercado, peso e campos opcionais) em `db/portfolios.json`
- Listar portfólios salvos com nome, data de criação, data de última análise e número de ativos
- Carregar composição salva na página de análise (preenchendo o formulário automaticamente)
- Editar composição existente (adicionar/remover ativos, alterar pesos)
- Duplicar portfólio (para criar variações sem alterar o original)
- Excluir portfólio com confirmação (padrão já usado na página de relatórios)
- A gestão de portfólios não conflita com a persistência de relatórios de análise

### Critérios de aceite
- O usuário pode salvar a composição atual com um nome
- Portfólios salvos aparecem em lista acessível na interface
- Um portfólio salvo pode ser carregado para reanálise sem redigitar ativos
- Edições em um portfólio salvo não alteram relatórios de análise anteriores
- Exclusão de portfólio exibe confirmação antes de executar

### Arquivos candidatos
- `src/portfolio/persistence.py` (extensão)
- `db/portfolios.json`
- `pages/portfolio.py` (seção de gerenciamento)

### Dependências
- Story 14
- Story 17

---

## STORY 18 — Gerar PDF da análise de portfólio

### Contexto
O sistema já gera PDF para relatórios individuais. A nova funcionalidade deve oferecer exportação equivalente para carteira.

### Objetivo
Permitir exportação da análise consolidada de portfólio em PDF.

### Escopo
Adaptar ou estender a infraestrutura atual em `src/utils_pdf.py` para incluir:
- resumo executivo com score geral e subscores
- composição da carteira em tabela
- alertas de concentração
- forças, fragilidades e riscos
- sugestões de rebalanceamento
- parecer final da persona
- disclaimer com o mesmo texto já usado nos relatórios individuais

### Critérios de aceite
- O PDF é gerado a partir do relatório consolidado da carteira
- O layout é consistente com o padrão já existente no projeto
- O PDF inclui o disclaimer padrão do projeto
- O arquivo pode ser baixado pela interface

### Arquivos candidatos
- `src/utils_pdf.py` (extensão)
- `src/portfolio/pdf_export.py`

### Dependências
- Story 15
- Story 17

---

## STORY 20 — Implementar testes de integração da funcionalidade

### Contexto
Os testes unitários são responsabilidade de cada story de lógica (Stories 3, 4, 7, 8, 9, 10, 11, 12 e 19 já incluem critérios de aceite com testes unitários). Esta story cobre os testes de integração do pipeline completo.

### Objetivo
Cobrir o pipeline completo de análise de portfólio com testes de integração que validem a interação entre os componentes.

### Escopo
Criar testes de integração para:
- pipeline completo com carteira válida (mock dos analistas)
- pipeline com falha parcial (um ativo com erro)
- pipeline com carteira mista BR/US
- normalização + consolidação + score (fluxo end-to-end)
- geração de PDF a partir de resultado consolidado

### Critérios de aceite
- Existem testes de integração cobrindo o pipeline ponta a ponta com mocks
- Cenários de falha parcial são testados com verificação do campo `failed_assets`
- Carteiras mistas BR/US são testadas com mock de câmbio
- Os testes são independentes da interface Streamlit
- A funcionalidade principal pode evoluir com menor risco de regressão

### Arquivos candidatos
- `tests/portfolio/test_pipeline_integration.py`
- `tests/portfolio/test_models.py`
- `tests/portfolio/test_validators.py`
- `tests/portfolio/test_normalizers.py`
- `tests/portfolio/test_aggregator.py`
- `tests/portfolio/test_scoring.py`
- `tests/portfolio/test_insights.py`
- `tests/portfolio/test_objective_fit.py`
- `tests/portfolio/test_resilience.py`

### Dependências
- Stories do núcleo já implementadas

---

## Ordem Recomendada de Implementação

### Sprint 1 — Fundação, Dados e Resiliência
- Story 1 — Criar modelos de domínio de portfólio
- Story 2 — Criar orquestrador principal da análise de portfólio
- Story 2B — Obter preço atual e calcular valor de mercado por posição *(nova)*
- Story 3 — Implementar validação da carteira informada
- Story 4 — Implementar normalização de pesos da carteira
- Story 5 — Reutilizar pipeline existente para análise individual por ativo
- Story 6 — Executar análise dos ativos em paralelo
- Story 19 — Tratar falhas parciais com resiliência *(movida para cá)*

### Sprint 2 — Métricas e Inteligência
- Story 7 — Consolidar sinais individuais no nível da carteira
- Story 8 — Calcular métricas de concentração da carteira
- Story 9 — Calcular score de diversificação da carteira
- Story 10 — Calcular score geral da carteira
- Story 11 — Avaliar adequação da carteira ao objetivo do investidor
- Story 12 — Gerar forças, fragilidades, riscos e sugestões de rebalanceamento

### Sprint 3 — Persona e Interface
- Story 13 — Estender personas existentes para consolidação de portfólio
- Story 14 — Criar página de análise de portfólio no Streamlit
- Story 15 — Exibir resultado consolidado da análise de portfólio
- Story 16 — Exibir progresso e status da análise por ativo

### Sprint 4 — Persistência, PDF e Testes de Integração
- Story 17 — Persistir relatórios de portfólio
- Story 17B — Gerenciar portfólios salvos (composição) *(nova)*
- Story 18 — Gerar PDF da análise de portfólio
- Story 20 — Implementar testes de integração da funcionalidade

---

## MVP Recomendado

Para uma primeira versão funcional e consistente, o conjunto mínimo recomendado é:

| Story | Justificativa |
|---|---|
| Story 1 — Modelos | Fundação de tudo |
| Story 2 — Orquestrador | Ponto central do pipeline |
| Story 2B — Preço atual *(nova)* | Necessário para pesos corretos em carteiras mistas |
| Story 3 — Validação | Necessário antes de qualquer execução |
| Story 4 — Normalização | Necessário para cálculos consistentes |
| Story 5 — Análise por ativo (modo portfólio) | Core da funcionalidade |
| Story 6 — Paralelismo | UX inaceitável para 3+ ativos sem isso |
| Story 19 — Robustez *(movida para Sprint 1)* | Fundação, não polimento |
| Story 7 — Consolidação de sinais | Primeiro resultado agregado real |
| Story 8 — Concentração | Insight mais valioso da feature |
| Story 9 — Score de diversificação | Dependência obrigatória de Story 10 |
| Story 10 — Score geral | Visão executiva — Story 11 ausente no MVP; dimensão de adequação redistribuída proporcionalmente |
| Story 12 — Forças, riscos e sugestões | Insight acionável principal |
| Story 14 — Página Streamlit | Interface |
| Story 15 — Resultado consolidado | Interface com visualizações |
| Story 16 — Progresso da análise | UX durante execução |

Stories 11 (adequação ao objetivo), 13 (persona), 17, 17B (persistência), 18 (PDF) e 20 (testes de integração) ficam para as sprints seguintes sem comprometer a primeira versão funcional.

---

## Resultado Esperado da Epic

Ao final da implementação, o sistema deverá oferecer uma funcionalidade de análise de portfólio baseada em:
- reaproveitamento dos analistas já existentes por ticker em modo otimizado para portfólio
- obtenção de preços atuais e unificação de moeda para carteiras mistas BR/US
- agregação de sinais no nível da carteira
- leitura estrutural de concentração e diversificação com índice HHI
- score consolidado com fórmula explícita e dimensões visíveis
- adequação ao objetivo do investidor com detecção de inconsistência objetivo × persona
- parecer final orientado por persona estendida sem duplicação de código
- interface dedicada com visualizações gráficas, persistência de composição e exportação em PDF

Isso posiciona a funcionalidade como uma camada superior de inteligência sobre a análise individual já existente, mantendo o DNA do produto e ampliando seu valor prático para o investidor.
