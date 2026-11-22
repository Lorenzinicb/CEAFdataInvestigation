# Persistência e Volume de Dispensações de Adalimumabe na Psoríase em Santa Catarina (SUS / CEAF, 2020–2025)

Projeto de farmacoepidemiologia e análise de dados públicos do **Sistema Único de Saúde (SUS)** focado no rastreamento longitudinal de pacientes com **Psoríase (`CID-10 L40`)** atendidos pelo Componente Especializado da Assistência Farmacêutica (**CEAF / SIA-SUS**), com ênfase no uso de **Adalimumabe 40 mg**.

---

## 1. Pergunta de Pesquisa

> *Qual é o volume de dispensações e o tempo de persistência (permanência em tratamento) de pacientes com Psoríase (`CID-10 L400, L401, L404, L408`) em uso de Adalimumabe 40 mg em Santa Catarina entre janeiro de 2020 e dezembro de 2025?*

---

## 2. Fonte de Dados e Dicionário de Variáveis (`SIA-SUS / AM`)

Os microdados foram extraídos diretamente do repositório público oficial do **DATASUS** (`ftp.datasus.gov.br`, diretório `/dissemin/publicos/SIASUS/200801_/Dados`), utilizando os arquivos mensais de **APAC de Medicamentos (`AM`)** de Santa Catarina (`AMSC2001.dbc` a `AMSC2512.dbc`, totalizando **72 competências**).

### Principais variáveis utilizadas

| Variável DATASUS | Descrição | Uso no Pipeline |
| :--- | :--- | :--- |
| **`AP_CNSPCN`** | Cartão Nacional de Saúde (CNS) pseudonimizado | Identificador longitudinal do paciente |
| **`AP_CMP`** | Competência da dispensação (`AAAAMM`) | Cálculo de início, fim, meses ativos e dias de acompanhamento |
| **`AP_PRIPAL`** | Código do procedimento/medicamento (SIGTAP) | Cruzamento com `sigtap_psoriase.csv` e seleção do Adalimumabe |
| **`AP_CIDPRI`** | CID-10 principal | Filtragem da coorte (`L400`, `L401`, `L404`, `L408`) |
| **`AP_AUTORIZ`** | Número da autorização APAC | Contagem de fichas/dispensações |
| **`AP_SEXO`** | Sexo do paciente (`M` / `F`) | Auditoria de consistência cadastral e estratificação |
| **`AP_NUIDADE`** | Idade do paciente na competência | Auditoria de amplitude etária ao longo dos 6 anos |
| **`AP_MUNPCN`** | Código IBGE do município de residência (6 dígitos) | Cruzamento com `ibge_municipios_sc.csv` (6 vs. 7 dígitos) |

### Códigos SIGTAP de Adalimumabe 40 mg incluídos
* `0604380011` — Adalimumabe 40 mg injetável (Originador)
* `0604380062` — Adalimumabe 40 mg injetável
* `0604380127` — Adalimumabe 40 mg injetável (Biossimilar A)
* `0604380135` — Adalimumabe 40 mg injetável (Biossimilar B)

---

## 3. Arquitetura do Pipeline e Arquivos do Projeto

1. **Extração e Descompressão em Python Puro ([`motor_datasus.py`](motor_datasus.py) e Skill [`.agents/skills/tradutor-dbc-datasus/`](.agents/skills/tradutor-dbc-datasus/SKILL.md)):**
   * Implementa o algoritmo PKWARE DCL (`_BlastDecoder`) em Python puro para descomprimir arquivos `.dbc` do DATASUS no Windows sem depender de compiladores C/Rust.
   * Filtra 100% dos registros de cada mês para `AP_CIDPRI` iniciado por `L40` (evitando cortes amostrais que criariam falsos abandonos) e consolida em arquivos anuais (`apac_sc_2020.csv` a `apac_sc_2025.csv`).
   * Disponibiliza `ativar_sql()` para carregar todas as tabelas e dicionários em SQLite na memória RAM com suporte a `%%sql`.
2. **Tabelas Auxiliares ([`00c_criar_dicionarios_auxiliares.py`](00c_criar_dicionarios_auxiliares.py)):**
   * [`dicionarios/sigtap_psoriase.csv`](dicionarios/sigtap_psoriase.csv): Dicionário com 22 códigos SIGTAP do protocolo de Psoríase (biológicos, imunossupressores sistêmicos, retinoides e tópicos).
   * [`dicionarios/ibge_municipios_sc.csv`](dicionarios/ibge_municipios_sc.csv): Os 295 municípios oficiais de Santa Catarina obtidos via API do IBGE, trazendo tanto o código de **7 dígitos** (padrão IBGE) quanto a chave de **6 dígitos** (`codigo_ibge_6`, sem o dígito verificador) compatível com `AP_MUNPCN`.
   * Cobertura verificada: **100% (`94.370 / 94.370`)** das fichas cruzadas com sucesso em ambos os dicionários.
3. **Auditoria e Higienização do Identificador ([`00d_auditoria_qualidade_cns.py`](00d_auditoria_qualidade_cns.py)):**
   * Gera o relatório de elegibilidade e salva a base tratada [`apac_sc_psoriase_limpa.csv`](apac_sc_psoriase_limpa.csv).
4. **Cadernos de Análise:**
   * [`01_sql_consultas_sus.ipynb`](01_sql_consultas_sus.ipynb): Consultas SQL didáticas (`INNER JOIN`, `LEFT JOIN`, `WHERE`, `GROUP BY`, `HAVING`, `CASE WHEN`) para rastreamento por paciente.
   * [`02_analise_persistencia_adalimumabe.ipynb`](02_analise_persistencia_adalimumabe.ipynb): Análise em Python (`pandas`, `matplotlib`, `seaborn`) com cruzamentos `pd.merge`, cálculo de persistência (`pd.to_datetime`, `.dt.days`), faixas de permanência, perfil por sexo e mesorregião de SC e filtro por subtipo de Psoríase (`L400`, `L401`, `L404`, `L408`).

---

## 4. Rastreamento por CNS, Higienização e Critérios de Exclusão

### Como o CNS é tratado entre 2020 e 2025
1. **Criptografia de origem (DATASUS):** Por sigilo (LGPD), o DATASUS não divulga o número real do Cartão SUS. Desde 2008, o órgão aplica uma substituição determinística de caracteres sobre o CNS real, fazendo com que um mesmo CNS gere a mesma sequência de símbolos em qualquer mês ou ano.
2. **Padronização local (`converter_cns_criptografado`):** Para permitir cruzamentos limpos em SQL e Python, a sequência de símbolos do DATASUS é convertida por hash determinístico (`SHA-256`) em um código numérico fixo de 15 dígitos (`700...`). Por ser determinístico, **a mesma sequência de símbolos do DATASUS em 2020 gera exatamente o mesmo identificador `700...` em 2025**.

### Auditoria de Qualidade e Fluxo de Exclusões (2020–2025)

Como dados administrativos podem conter erros de digitação local ou colisões de identificador, aplicamos três critérios de exclusão sobre o `AP_CNSPCN`:
* CNS vazio ou zerado (`000000000000000`);
* **Sexo conflitante:** mesmo `AP_CNSPCN` registrado simultaneamente com sexo `M` e `F`;
* **Idade incoerente:** variação de idade superior a `7 anos` dentro da janela de 6 anos (`2020`–`2025`), ou idades fora do intervalo `[0, 110]`.

| Etapa da Coorte | Psoríase Geral (`L40`) — Pacientes (Fichas) | Adalimumabe 40 mg — Pacientes (Fichas) |
| :--- | :---: | :---: |
| **Base Bruta (Antes de tratar)** | **4.431** (`94.370`) | **1.480** (`26.632`) |
| (-) CNS vazio ou zerado | `0` | — |
| (-) Sexo conflitante (`M` e `F`) | `-4` | — |
| (-) Idade incoerente (variação `> 7` anos) | `-2` | — |
| **Total excluído na higienização** | **-6** (`0,14%`) / (`-225` fichas) | **-3** (`0,20%`) / (`-66` fichas) |
| **Base Tratada (Final)** | **4.425** (`94.145`) | **1.477** (`26.566`) |

### Resumo Descritivo da Coorte Tratada de Adalimumabe (`n = 1.477`)
* **Média de meses dispensados:** `18,0 meses`
* **Mediana de meses dispensados:** `12,0 meses`
* **Mediana de acompanhamento (`data_fim - data_inicio`):** `365 dias`

---

## 5. Limitações dos Dados Administrativos

1. **Duplicidade de CNS (1 paciente com 2 ou mais cartões):** Embora o hash preserve a ligação de um mesmo CNS entre 2020 e 2025, se um mesmo indivíduo tiver emitido um segundo número de Cartão SUS ao longo do período, os registros públicos anonimizados (sem nome ou CPF) o enxergarão como dois pacientes distintos, podendo fragmentar o histórico e superestimar levemente a interrupção do tratamento.
2. **Colisão não detectável:** Erros de digitação em que duas pessoas diferentes do **mesmo sexo** e da **mesma faixa etária** compartilhem um mesmo CNS não são separáveis apenas com variáveis da APAC.
3. **Natureza administrativa (faturamento vs. uso clínico):** A APAC registra a autorização/dispensação ambulatorial do medicamento, mas não contém prontuário clínico, escore de gravidade (PASI), adesão real à aplicação domiciliar ou motivo clínico detalhado de troca (*switch*) ou suspensão.
4. **Ausência de valor financeiro (`AP_VL_AP`):** Por integrar o Grupo 1A do CEAF (aquisição centralizada pelo Ministério da Saúde), o valor aprovado na APAC costuma ser registrado como `R$ 0,00`; por isso, a análise foi direcionada para **volume de dispensações e persistência**.

---

## 6. Como Reproduzir no Ambiente Local

```powershell
# 1. Ativar o ambiente virtual e instalar dependências
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Gerar tabelas auxiliares (SIGTAP e IBGE/SC)
.\.venv\Scripts\python.exe 00c_criar_dicionarios_auxiliares.py

# 3. Executar auditoria de qualidade e gerar apac_sc_psoriase_limpa.csv
.\.venv\Scripts\python.exe 00d_auditoria_qualidade_cns.py
```

Em seguida, abra [`02_analise_persistencia_adalimumabe.ipynb`](02_analise_persistencia_adalimumabe.ipynb) no VS Code / Jupyter com o kernel `.venv` selecionado.
