"""
================================================================================
📖 GUIA DE USO (README) — LIMPEZA DOS ARQUIVOS .CSV DA APAC
================================================================================

O QUE ESTE ARQUIVO FAZ:
Percorre os arquivos .csv traduzidos (apac_sc_2301.csv, apac_sc_2401.csv, etc.)
e limpa a coluna AP_CNSPCN (Cartão SUS criptografado com símbolos '‚{{~{{'),
convertendo cada sequência de símbolos em um número fixo de 15 dígitos ('700...').

POR QUE ISSO É IMPORTANTE PARA O SQL:
Como a conversão usa um código Hash determinístico, o mesmo paciente receberá
EXATAMENTE o mesmo número de 15 dígitos em 2023, 2024, 2025 e 2026, permitindo
cruzar os anos com INNER JOIN e LEFT JOIN pelo AP_CNSPCN.
================================================================================
"""

import hashlib
import os
import pandas as pd

# ==============================================================================
# PAINEL DE SELEÇÃO
# ==============================================================================
ESTADO = "SC"
COMPETENCIAS = ["2301", "2401", "2501", "2601"]


def converter_cns_criptografado(valor_bruto: str) -> str:
    """Converte os 15 símbolos do DATASUS em um número fixo de 15 dígitos ('700...')."""
    if pd.isna(valor_bruto):
        return ""
    texto = str(valor_bruto).strip()
    if not texto or set(texto) <= {"0"}:
        return "000000000000000"
    if texto.isdigit() and len(texto) == 15:
        return texto

    hash_hex = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    numero_12_digitos = int(hash_hex[:12], 16) % (10**12)
    return f"700{numero_12_digitos:012d}"


def limpar_arquivos_apac(uf: str = "SC", lista_ano_mes: list[str] = None):
    if lista_ano_mes is None:
        lista_ano_mes = ["2301", "2401", "2501", "2601"]

    uf_lower = uf.lower()
    for ano_mes in lista_ano_mes:
        nome_csv = f"apac_{uf_lower}_{ano_mes}.csv"
        if not os.path.exists(nome_csv):
            print(f" - Arquivo '{nome_csv}' não encontrado. Rode o 00_tradutor primeiro.")
            continue

        df = pd.read_csv(nome_csv, dtype=str)
        for col in df.columns:
            df[col] = df[col].str.strip()

        antes = df["AP_CNSPCN"].iloc[0]
        df["AP_CNSPCN"] = df["AP_CNSPCN"].apply(converter_cns_criptografado)
        depois = df["AP_CNSPCN"].iloc[0]

        df.to_csv(nome_csv, index=False, encoding="utf-8-sig")
        print(f" - Limpo '{nome_csv}' ({len(df)} linhas) | Exemplo CNS: '{antes}' -> '{depois}'")


if __name__ == "__main__":
    limpar_arquivos_apac(uf=ESTADO, lista_ano_mes=COMPETENCIAS)
