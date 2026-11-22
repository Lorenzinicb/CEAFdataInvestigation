"""
motor_datasus.py
----------------
Módulo interno (motor) para download e descompressão de arquivos .dbc do DATASUS.
Você NÃO precisa editar nem executar este arquivo. Use o 00_tradutor_dbc_para_csv.py ou a Skill tradutor-dbc-datasus.
"""

import ftplib
import hashlib
import os
import sqlite3
import struct
import pandas as pd
from dbfread import DBF

_conexao_ram = None


def converter_cns_criptografado(valor_bruto: str) -> str:
    """Converte os 15 símbolos criptografados do DATASUS em um número fixo de 15 dígitos ('700...')."""
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


def ativar_sql():
    """Lê os arquivos apac_*.csv da pasta direto para a memória RAM e ativa o %%sql."""
    global _conexao_ram
    from IPython import get_ipython
    from IPython.core.magic import register_cell_magic

    _conexao_ram = sqlite3.connect(":memory:")
    arquivos_anuais = sorted(
        [a for a in os.listdir(".") if a.startswith("apac_sc_20") and a.endswith(".csv")]
    )
    if arquivos_anuais:
        arquivos_para_carregar = arquivos_anuais
    else:
        arquivos_para_carregar = sorted(
            [a for a in os.listdir(".") if a.startswith("apac_") and a.endswith(".csv")]
        )

    dfs_todos = []
    for _arq in arquivos_para_carregar:
        _partes = _arq.replace(".csv", "").split("_")
        _sufixo = _partes[-1]
        if len(_sufixo) == 4 and _sufixo.startswith("20"):
            _ano = _sufixo
        else:
            _ano = f"20{_sufixo[:2]}"
        _tabela = f"apac_{_ano}"
        _df = pd.read_csv(_arq, dtype=str)
        if "AP_VL_AP" in _df.columns:
            _df["AP_VL_AP"] = pd.to_numeric(_df["AP_VL_AP"], errors="coerce")
        if "AP_NUIDADE" in _df.columns:
            _df["AP_NUIDADE"] = pd.to_numeric(_df["AP_NUIDADE"], errors="coerce")
        _df.to_sql(_tabela, _conexao_ram, if_exists="replace", index=False)
        dfs_todos.append(_df)
        print(f"Carregado na RAM: {_arq} -> tabela SQL '{_tabela}' ({len(_df)} linhas)")

    if dfs_todos:
        _df_completo = pd.concat(dfs_todos, ignore_index=True)
        _df_completo.to_sql("apac_psoriase", _conexao_ram, if_exists="replace", index=False)
        print(
            f"Tabela consolidada criada na RAM: 'apac_psoriase' ({len(_df_completo)} linhas somando todos os anos)"
        )

    _arq_limpo = "apac_sc_psoriase_limpa.csv"
    if os.path.exists(_arq_limpo):
        _df_limpo = pd.read_csv(_arq_limpo, dtype=str)
        if "AP_VL_AP" in _df_limpo.columns:
            _df_limpo["AP_VL_AP"] = pd.to_numeric(_df_limpo["AP_VL_AP"], errors="coerce")
        if "AP_NUIDADE" in _df_limpo.columns:
            _df_limpo["AP_NUIDADE"] = pd.to_numeric(_df_limpo["AP_NUIDADE"], errors="coerce")
        _df_limpo.to_sql("apac_psoriase_limpa", _conexao_ram, if_exists="replace", index=False)
        print(f"Base higienizada carregada na RAM: '{_arq_limpo}' -> tabela SQL 'apac_psoriase_limpa' ({len(_df_limpo)} linhas)")

    _arq_sigtap = os.path.join("dicionarios", "sigtap_psoriase.csv")
    if os.path.exists(_arq_sigtap):
        _df_sigtap = pd.read_csv(_arq_sigtap, dtype=str)
        _df_sigtap.to_sql("dicionario_sigtap", _conexao_ram, if_exists="replace", index=False)
        print(f"Dicionário carregado na RAM: '{_arq_sigtap}' -> tabela SQL 'dicionario_sigtap' ({len(_df_sigtap)} linhas)")

    _arq_ibge = os.path.join("dicionarios", "ibge_municipios_sc.csv")
    if os.path.exists(_arq_ibge):
        _df_ibge = pd.read_csv(_arq_ibge, dtype=str)
        _df_ibge.to_sql("dicionario_ibge", _conexao_ram, if_exists="replace", index=False)
        print(f"Dicionário carregado na RAM: '{_arq_ibge}' -> tabela SQL 'dicionario_ibge' ({len(_df_ibge)} linhas)")

    _ipython = get_ipython()
    if _ipython is not None:
        @register_cell_magic
        def sql(line, cell):
            """Executa SQL puro diretamente sobre as tabelas carregadas na memória RAM."""
            return pd.read_sql(cell, _conexao_ram)


class _BlastDecoder:
    """Implementação em Python puro do algoritmo PKWARE DCL (Blast) usado pelo DATASUS."""

    LITLEN_BITS = [
        11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8,
        9, 7, 6, 7, 8, 7, 6, 55, 8, 23, 24, 12, 11, 7, 9, 11, 12, 6, 7, 22, 5,
        7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38, 7, 9, 8, 25, 11, 8, 11, 9, 12,
        8, 12, 5, 38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7, 24, 10, 27,
        44, 253, 253, 253, 252, 252, 252, 13, 12, 45, 12, 45, 12, 61, 12, 45,
        44, 173
    ]
    LEN_BITS = [2, 35, 36, 53, 38, 23]
    DIST_BITS = [2, 20, 53, 230, 247, 151, 248]
    BASE = [3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264]
    EXTRA = [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8]

    @staticmethod
    def _construct(rep_bytes):
        length = []
        for b in rep_bytes:
            count = (b >> 4) + 1
            bits = b & 15
            length.extend([bits] * count)
        MAXBITS = 13
        cnt = [0] * (MAXBITS + 1)
        for l in length:
            cnt[l] += 1
        offs = [0] * (MAXBITS + 1)
        for bits in range(1, MAXBITS):
            offs[bits + 1] = offs[bits] + cnt[bits]
        symbol = [0] * len(length)
        for sym, l in enumerate(length):
            if l != 0:
                symbol[offs[l]] = sym
                offs[l] += 1
        return cnt, symbol

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.bitbuf = 0
        self.bitcnt = 0
        self.litcode = self._construct(self.LITLEN_BITS)
        self.lencode = self._construct(self.LEN_BITS)
        self.distcode = self._construct(self.DIST_BITS)

    def _bits(self, need: int) -> int:
        val = self.bitbuf
        while self.bitcnt < need:
            if self.pos >= len(self.data):
                raise EOFError("Fim inesperado do fluxo comprimido .dbc")
            val |= self.data[self.pos] << self.bitcnt
            self.pos += 1
            self.bitcnt += 8
        self.bitbuf = val >> need
        self.bitcnt -= need
        return val & ((1 << need) - 1)

    def _decode(self, huff) -> int:
        cnt, symbol = huff
        code = first = index = 0
        for length in range(1, 14):
            code |= self._bits(1) ^ 1
            count = cnt[length]
            if code < first + count:
                return symbol[index + (code - first)]
            index += count
            first = (first + count) << 1
            code <<= 1
        raise ValueError("Código Huffman inválido no arquivo .dbc")

    def decompress(self, max_bytes: int = 0) -> bytearray:
        lit = self._bits(8)
        if lit > 1:
            raise ValueError(f"Cabeçalho Blast inválido (lit={lit})")
        dict_bits = self._bits(8)
        if dict_bits < 4 or dict_bits > 6:
            raise ValueError(f"Cabeçalho Blast inválido (dict={dict_bits})")

        out = bytearray()
        while True:
            if max_bytes and len(out) >= max_bytes:
                break
            if self._bits(1):
                symbol = self._decode(self.lencode)
                length = self.BASE[symbol] + self._bits(self.EXTRA[symbol])
                if length == 519:
                    break
                dist_extra = 2 if length == 2 else dict_bits
                dist = self._decode(self.distcode) << dist_extra
                dist += self._bits(dist_extra) + 1
                for _ in range(length):
                    out.append(out[-dist] if dist <= len(out) else 0)
            else:
                byte = self._decode(self.litcode) if lit else self._bits(8)
                out.append(byte)
        return out


def extrair_dataframe_dbc(
    caminho_dbc: str,
    max_registros: int = 0,
    filtro_cid_prefixo: str = "",
) -> pd.DataFrame:
    """Descomprime um .dbc em memória e retorna um DataFrame limpo (com filtro opcional por CID)."""
    with open(caminho_dbc, "rb") as f:
        conteudo = f.read()

    tamanho_cabecalho = struct.unpack("<H", conteudo[8:10])[0]
    tamanho_registro = struct.unpack("<H", conteudo[10:12])[0]
    cabecalho_dbf = conteudo[:tamanho_cabecalho]
    fluxo_comprimido = conteudo[tamanho_cabecalho + 4 :]

    # Lê os metadados das colunas diretamente do cabeçalho DBF (32 bytes por coluna a partir do byte 32)
    colunas = []
    pos_campo = 1  # byte 0 do registro é o marcador de exclusão (' ' ou '*')
    offset = 32
    offset_cid = None
    tam_cid = 0
    while offset + 32 <= tamanho_cabecalho and cabecalho_dbf[offset] != 0x0D:
        bloco = cabecalho_dbf[offset : offset + 32]
        nome_col = bloco[:11].split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
        tam_col = bloco[16]
        colunas.append((nome_col, pos_campo, pos_campo + tam_col))
        if nome_col == "AP_CIDPRI":
            offset_cid = pos_campo
            tam_cid = tam_col
        pos_campo += tam_col
        offset += 32

    max_bytes = max_registros * tamanho_registro if max_registros else 0
    corpo = _BlastDecoder(fluxo_comprimido).decompress(max_bytes=max_bytes)
    num_registros = len(corpo) // tamanho_registro

    prefixo_bytes = filtro_cid_prefixo.upper().encode("iso-8859-1") if filtro_cid_prefixo else b""
    linhas = []
    mv = memoryview(corpo)

    for i in range(num_registros):
        ini = i * tamanho_registro
        reg = mv[ini : ini + tamanho_registro]
        if reg[0] == 0x2A:  # registro deletado ('*')
            continue
        if prefixo_bytes and offset_cid is not None:
            val_cid = bytes(reg[offset_cid : offset_cid + tam_cid]).lstrip()
            if not val_cid.startswith(prefixo_bytes):
                continue

        d = {}
        for nome_col, c_ini, c_fim in colunas:
            d[nome_col] = bytes(reg[c_ini:c_fim]).decode("iso-8859-1", errors="replace").strip()
        linhas.append(d)

    df = pd.DataFrame(linhas, columns=[c[0] for c in colunas])
    if not df.empty and "AP_CNSPCN" in df.columns:
        df["AP_CNSPCN"] = df["AP_CNSPCN"].apply(converter_cns_criptografado)
    return df


def converter_dbc_para_dbf(caminho_dbc: str, caminho_dbf: str, max_registros: int = 20000) -> None:
    """Descomprime um arquivo .dbc do DATASUS gerando um arquivo .dbf."""
    with open(caminho_dbc, "rb") as f:
        conteudo = f.read()

    tamanho_cabecalho = struct.unpack("<H", conteudo[8:10])[0]
    tamanho_registro = struct.unpack("<H", conteudo[10:12])[0]

    cabecalho_dbf = bytearray(conteudo[:tamanho_cabecalho])
    fluxo_comprimido = conteudo[tamanho_cabecalho + 4 :]

    max_bytes = max_registros * tamanho_registro if max_registros else 0
    corpo = _BlastDecoder(fluxo_comprimido).decompress(max_bytes=max_bytes)

    num_registros = len(corpo) // tamanho_registro
    corpo = corpo[: num_registros * tamanho_registro]
    cabecalho_dbf[4:8] = struct.pack("<I", num_registros)

    with open(caminho_dbf, "wb") as f_out:
        f_out.write(cabecalho_dbf)
        f_out.write(corpo)
        f_out.write(b"\x1a")


def obter_arquivo_dbc(tipo_tabela: str, uf: str, ano_mes: str) -> str:
    """Verifica se o .dbc já existe em 'dadosApac/'. Se não existir, baixa do FTP do DATASUS."""
    os.makedirs("dadosApac", exist_ok=True)
    nome_dbc = f"{tipo_tabela.upper()}{uf.upper()}{ano_mes}.dbc"
    caminho_local = os.path.join("dadosApac", nome_dbc)

    if os.path.exists(caminho_local) and os.path.getsize(caminho_local) > 0:
        return caminho_local

    ftp = ftplib.FTP("ftp.datasus.gov.br", timeout=60)
    ftp.login()
    ftp.cwd("/dissemin/publicos/SIASUS/200801_/Dados")
    with open(caminho_local, "wb") as f_out:
        ftp.retrbinary(f"RETR {nome_dbc}", f_out.write)
    ftp.quit()
    return caminho_local


def traduzir_dbc(
    uf: str = "SC",
    lista_ano_mes: list[str] = None,
    tipo_tabela: str = "AM",
    limite: int = 20000,
    filtro_cid: str = "",
):
    """Traduz um ou mais arquivos .dbc (ex: ['2301', '2401', '2501', '2601']) para .csv."""
    if lista_ano_mes is None:
        lista_ano_mes = ["2301", "2401", "2501", "2601"]

    uf_lower = uf.lower()
    for ano_mes in lista_ano_mes:
        caminho_dbc = obter_arquivo_dbc(tipo_tabela=tipo_tabela, uf=uf, ano_mes=ano_mes)
        caminho_csv = f"apac_{uf_lower}_{ano_mes}.csv"
        df_apac = extrair_dataframe_dbc(
            caminho_dbc, max_registros=limite, filtro_cid_prefixo=filtro_cid
        )
        df_apac.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
        print(f"   -> Gerado '{caminho_csv}' ({len(df_apac)} linhas e {len(df_apac.columns)} colunas)")
