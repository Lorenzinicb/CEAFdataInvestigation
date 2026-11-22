"""
================================================================================
📖 GUIA DE USO — CRIAÇÃO DAS TABELAS AUXILIARES (SIGTAP E IBGE/SC)
================================================================================

O QUE ESTE ARQUIVO FAZ:
Cria duas tabelas pequenas de tradução ("dicionários") na pasta 'dicionarios/':
1. 'dicionarios/sigtap_psoriase.csv': Traduz os códigos numéricos de medicamentos
   (AP_PRIPAL) do PCDT de Psoríase para nome, princípio ativo e classe terapêutica.
2. 'dicionarios/ibge_municipios_sc.csv': Consulta a API oficial do IBGE para
   baixar os 295 municípios de Santa Catarina, gerando o código de 6 dígitos
   (igual ao AP_MUNPCN do DATASUS) e o código de 7 dígitos (padrão IBGE),
   além da microrregião e mesorregião.
================================================================================
"""

import json
import os
import urllib.request
import pandas as pd


def criar_dicionario_sigtap(pasta_saida: str = "dicionarios") -> str:
    """Gera a tabela auxiliar SIGTAP com os medicamentos usados na Psoríase (CID L40)."""
    os.makedirs(pasta_saida, exist_ok=True)
    registros = [
        # Anti-TNF: Adalimumabe
        ("0604380011", "Adalimumabe 40 mg injetável (Originador)", "Adalimumabe", "Biológico Anti-TNF"),
        ("0604380062", "Adalimumabe 40 mg injetável", "Adalimumabe", "Biológico Anti-TNF"),
        ("0604380127", "Adalimumabe 40 mg injetável (Biossimilar A)", "Adalimumabe", "Biológico Anti-TNF"),
        ("0604380135", "Adalimumabe 40 mg injetável (Biossimilar B)", "Adalimumabe", "Biológico Anti-TNF"),
        # Anti-TNF: Etanercepte
        ("0604380020", "Etanercepte 25 mg injetável", "Etanercepte", "Biológico Anti-TNF"),
        ("0604380038", "Etanercepte 50 mg injetável (Originador)", "Etanercepte", "Biológico Anti-TNF"),
        ("0604380100", "Etanercepte 50 mg injetável (Biossimilar)", "Etanercepte", "Biológico Anti-TNF"),
        # Outros Biológicos (Anti-IL17 / Anti-IL12-23 / Anti-IL23)
        ("0604690029", "Secuquinumabe 150 mg/ml injetável", "Secuquinumabe", "Biológico Anti-IL17"),
        ("0604690037", "Ustequinumabe 45 mg/0,5 ml injetável", "Ustequinumabe", "Biológico Anti-IL12/23"),
        ("0604690045", "Risanquizumabe 75 mg/0,83 ml injetável", "Risanquizumabe", "Biológico Anti-IL23"),
        ("0604690053", "Risanquizumabe 150 mg/ml caneta aplicadora", "Risanquizumabe", "Biológico Anti-IL23"),
        # Imunossupressores / Retinoides sistêmicos
        ("0604340028", "Ciclosporina 25 mg cápsula", "Ciclosporina", "Imunossupressor Sistêmico"),
        ("0604340036", "Ciclosporina 50 mg cápsula", "Ciclosporina", "Imunossupressor Sistêmico"),
        ("0604340044", "Ciclosporina 100 mg cápsula", "Ciclosporina", "Imunossupressor Sistêmico"),
        ("0604340052", "Ciclosporina 100 mg/ml solução oral", "Ciclosporina", "Imunossupressor Sistêmico"),
        ("0604530021", "Metotrexato 2,5 mg comprimido", "Metotrexato", "Imunossupressor Sistêmico"),
        ("0604530030", "Metotrexato 25 mg/ml injetável", "Metotrexato", "Imunossupressor Sistêmico"),
        ("0604600011", "Acitretina 10 mg cápsula", "Acitretina", "Retinoide Sistêmico"),
        ("0604600020", "Acitretina 25 mg cápsula", "Acitretina", "Retinoide Sistêmico"),
        # Tópicos
        ("0604700016", "Calcipotriol 50 mcg/g pomada (bisnaga 30 g)", "Calcipotriol", "Tópico"),
        ("0604710011", "Clobetasol 0,5 mg/g creme (bisnaga 30 g)", "Clobetasol", "Tópico"),
        ("0604710020", "Clobetasol 0,5 mg/g solução capilar (frasco 50 g)", "Clobetasol", "Tópico"),
    ]
    df = pd.DataFrame(
        registros,
        columns=["codigo_sigtap", "nome_medicamento", "principio_ativo", "classe_terapeutica"],
    )
    caminho = os.path.join(pasta_saida, "sigtap_psoriase.csv")
    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    print(f" - Gerado '{caminho}' ({len(df)} medicamentos do PCDT de Psoríase)")
    return caminho


def criar_dicionario_ibge_sc(pasta_saida: str = "dicionarios") -> str:
    """Baixa os 295 municípios de SC da API oficial do IBGE e cria a chave de 6 dígitos (DATASUS)."""
    os.makedirs(pasta_saida, exist_ok=True)
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/SC/municipios"
    with urllib.request.urlopen(url, timeout=20) as resp:
        dados = json.loads(resp.read().decode("utf-8"))

    linhas = []
    for item in dados:
        cod_7 = str(item["id"])
        cod_6 = cod_7[:6]  # DATASUS remove o 7º dígito verificador
        linhas.append(
            {
                "codigo_ibge_6": cod_6,
                "codigo_ibge_7": cod_7,
                "nome_municipio": item["nome"],
                "microrregiao": item["microrregiao"]["nome"],
                "mesorregiao": item["microrregiao"]["mesorregiao"]["nome"],
                "uf": "SC",
            }
        )

    df = pd.DataFrame(linhas).sort_values("codigo_ibge_6").reset_index(drop=True)
    caminho = os.path.join(pasta_saida, "ibge_municipios_sc.csv")
    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    print(f" - Gerado '{caminho}' ({len(df)} municípios oficiais de SC)")
    return caminho


if __name__ == "__main__":
    print("Criando tabelas auxiliares em 'dicionarios/'...")
    criar_dicionario_sigtap()
    criar_dicionario_ibge_sc()

