"""
================================================================================
📖 GUIA DE USO (README) — TRADUTOR DE DADOS .DBC DO SUS PARA .CSV
================================================================================

O QUE ESTE ARQUIVO FAZ:
Lê os arquivos comprimidos (.dbc) da pasta 'dadosApac/' (ou baixa do DATASUS
se não estiverem na pasta) e converte cada um para um arquivo .csv:
  - AMSC2301.dbc  ->  apac_sc_2301.csv
  - AMSC2401.dbc  ->  apac_sc_2401.csv
  - AMSC2501.dbc  ->  apac_sc_2501.csv
  - AMSC2601.dbc  ->  apac_sc_2601.csv

COMO USAR:
1. Escolha a sigla do ESTADO e a lista de COMPETENCIAS (Ano+Mês) abaixo.
2. Execute este arquivo (botão Play).
3. Em seguida, execute o arquivo '00b_limpeza_dados_sus.py' para limpar o CNS.
================================================================================
"""

from motor_datasus import traduzir_dbc

# ==============================================================================
# PAINEL DE SELEÇÃO
# ==============================================================================
ESTADO = "SC"                                    # Sigla do estado ("SC", "RS", "PR"...)
COMPETENCIAS = ["2301", "2401", "2501", "2601"]  # Lista de Ano+Mês a converter
TIPO_TABELA = "AM"                               # "AM" = APAC de Medicamentos
LIMITE_LINHAS = 20000                            # Linhas por arquivo (ou None para todas)

if __name__ == "__main__":
    traduzir_dbc(
        uf=ESTADO,
        lista_ano_mes=COMPETENCIAS,
        tipo_tabela=TIPO_TABELA,
        limite=LIMITE_LINHAS,
    )
