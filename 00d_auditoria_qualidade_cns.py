"""
================================================================================
📖 GUIA DE USO — AUDITORIA E HIGIENIZAÇÃO DO IDENTIFICADOR (AP_CNSPCN)
================================================================================

O QUE ESTE ARQUIVO FAZ:
Lê os 6 arquivos anuais de Psoríase (apac_sc_2020.csv a apac_sc_2025.csv),
audita a consistência do identificador do paciente (AP_CNSPCN) e gera:
1. Um relatório completo (Antes -> Excluídos por critério -> Base Limpa),
   tanto para toda a Psoríase (CID L40) quanto para o recorte de Adalimumabe.
2. O arquivo limpo 'apac_sc_psoriase_limpa.csv', pronto para análise estatística
   e visualização sem pacientes com cadastro inconsistente.
================================================================================
"""

import glob
import os
import pandas as pd

CODIGOS_ADALIMUMABE = ("0604380011", "0604380062", "0604380127", "0604380135")


def auditar_e_limpar_coorte(salvar_csv: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Audita inconsistências no AP_CNSPCN, imprime o fluxograma de exclusão e salva a base limpa."""
    arquivos = sorted(glob.glob("apac_sc_202?.csv"))
    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo 'apac_sc_202X.csv' encontrado na pasta.")

    df_bruto = pd.concat([pd.read_csv(a, dtype=str) for a in arquivos], ignore_index=True)
    df_bruto["_idade_num"] = pd.to_numeric(df_bruto["AP_NUIDADE"], errors="coerce")

    # Resumo por paciente para detectar inconsistências longitudinais
    perfil = df_bruto.groupby("AP_CNSPCN").agg(
        n_sexos=("AP_SEXO", "nunique"),
        idade_min=("_idade_num", "min"),
        idade_max=("_idade_num", "max"),
    )
    perfil["amp_idade"] = perfil["idade_max"] - perfil["idade_min"]

    ids_cns_invalido = set(
        df_bruto.loc[df_bruto["AP_CNSPCN"].isna() | df_bruto["AP_CNSPCN"].isin(["", "000000000000000"]), "AP_CNSPCN"]
    )
    ids_sexo_conflitante = set(perfil.index[perfil["n_sexos"] > 1])
    ids_idade_incoerente = set(perfil.index[(perfil["amp_idade"] > 7) | (perfil["idade_max"] > 110) | (perfil["idade_min"] < 0)])

    ids_excluidos = ids_cns_invalido | ids_sexo_conflitante | ids_idade_incoerente

    df_limpo = df_bruto[~df_bruto["AP_CNSPCN"].isin(ids_excluidos)].drop(columns=["_idade_num"]).copy()
    df_bruto_sem_aux = df_bruto.drop(columns=["_idade_num"])

    # Monta tabela comparativa (Antes -> Excluídos -> Depois) para Psoríase Geral e Adalimumabe
    adali_bruto = df_bruto_sem_aux[df_bruto_sem_aux["AP_PRIPAL"].isin(CODIGOS_ADALIMUMABE)]
    adali_limpo = df_limpo[df_limpo["AP_PRIPAL"].isin(CODIGOS_ADALIMUMABE)]

    print("\n=== RELATÓRIO DE AUDITORIA E HIGIENIZAÇÃO (2020–2025) ===")
    print(f"1. BASE BRUTA (ANTES DE TRATAR) - Psoríase (L40):")
    print(f"   - Total de fichas (APACs): {len(df_bruto_sem_aux)}")
    print(f"   - Pacientes únicos (AP_CNSPCN): {df_bruto_sem_aux['AP_CNSPCN'].nunique()}")

    print(f"\n2. CRITÉRIOS DE EXCLUSÃO APLICADOS:")
    print(f"   - CNS vazio ou zerado: {len(ids_cns_invalido)} pacientes")
    print(f"   - Sexo conflitante (M e F no mesmo CNS): {len(ids_sexo_conflitante)} pacientes")
    print(f"   - Idade incoerente (variação > 7 anos ou <0 / >110): {len(ids_idade_incoerente)} pacientes")
    fichas_excluidas = len(df_bruto_sem_aux) - len(df_limpo)
    print(f"   -> Total excluído (Psoríase Geral): {len(ids_excluidos)} pacientes ({fichas_excluidas} fichas)")

    print(f"\n3. BASE TRATADA (FINAL) - Psoríase (L40):")
    print(f"   - Total de fichas válidas: {len(df_limpo)}")
    print(f"   - Pacientes únicos válidos: {df_limpo['AP_CNSPCN'].nunique()}")

    print(f"\n4. RECORTE ADALIMUMABE (40 mg):")
    print(f"   - Antes de tratar: {adali_bruto['AP_CNSPCN'].nunique()} pacientes ({len(adali_bruto)} fichas)")
    print(f"   - Excluídos na auditoria: {adali_bruto['AP_CNSPCN'].nunique() - adali_limpo['AP_CNSPCN'].nunique()} pacientes ({len(adali_bruto) - len(adali_limpo)} fichas)")
    print(f"   - Base tratada (final): {adali_limpo['AP_CNSPCN'].nunique()} pacientes ({len(adali_limpo)} fichas)")

    if salvar_csv:
        caminho_saida = "apac_sc_psoriase_limpa.csv"
        df_limpo.to_csv(caminho_saida, index=False, encoding="utf-8-sig")
        print(f"\n[OK] Arquivo limpo salvo em: '{caminho_saida}'")

    return df_bruto_sem_aux, df_limpo


if __name__ == "__main__":
    auditar_e_limpar_coorte(salvar_csv=True)
