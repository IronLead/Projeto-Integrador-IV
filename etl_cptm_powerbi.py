"""
===============================================================================
SCRIPT DE ETL EM PYTHON PARA O PROJETO POWER BI — CPTM / ERP ALVO
===============================================================================
Descrição:
  Este script realiza o processo completo de Extração, Transformação e Carga (ETL)
  dos arquivos exportados do ERP ALVO (CPTM), preparando tabelas limpas e
  normalizadas com CHAVES DE LIGAÇÃO PADRONIZADAS (ID_Produto_Reduzido, 
  ID_Produto_Estruturado, ID_Centro_Custo, ID_Sigla_CC, ID_Data) para que o
  Power BI detecte e crie os relacionamentos 100% de forma AUTOMÁTICA!

Autor: Antigravity AI
Data: 2026-09-06
===============================================================================
"""

import os
import glob
import re
import pandas as pd
import numpy as np

# =============================================================================
# CONFIGURAÇÃO DE DIRETÓRIOS E CAMINHOS
# =============================================================================

DIRETORIO_RAIZ = r"g:\Meu Drive\Rangel\10_Educação\FATEC_Logistica\4_Semestre\API IV - Newton\PROJETO API IV\CPTM"

PASTA_BASES = os.path.join(DIRETORIO_RAIZ, "01_Bases_ERP")
PASTA_DIMENSOES = os.path.join(PASTA_BASES, "Dimensoes")
PASTA_FATOS = os.path.join(PASTA_BASES, "Fatos")

PASTA_SAIDA = os.path.join(PASTA_BASES, "Processados_PowerBI")
os.makedirs(PASTA_SAIDA, exist_ok=True)


# =============================================================================
# FUNÇÕES AUXILIARES DE TRATAMENTO E PADRONIZAÇÃO DE CHAVES
# =============================================================================

def obter_todos_arquivos_excel(pasta: str) -> list:
    """Busca todos os arquivos Excel (.xlsx, .xls, .xlsm) em uma pasta, ignorando arquivos temporários (~$)."""
    arquivos = []
    for ext in ("*.xlsx", "*.xls", "*.xlsm", "*.XLSX", "*.XLS"):
        arquivos.extend(glob.glob(os.path.join(pasta, ext)))
    arquivos_validos = sorted(list(set([f for f in arquivos if not os.path.basename(f).startswith("~$")])))
    if not arquivos_validos:
        raise FileNotFoundError(f"Nenhum arquivo Excel encontrado na pasta: {pasta}")
    return arquivos_validos


def extrair_data_nome_arquivo(nome_arquivo: str) -> str:
    """Extrai data YYYYMMDD do nome do arquivo e retorna em formato ISO YYYY-MM-DD."""
    match = re.search(r'(\d{4})(\d{2})(\d{2})', nome_arquivo)
    if match:
        ano, mes, dia = match.groups()
        return f"{ano}-{mes}-{dia}"
    return None


def formatar_codigo_reduzido(val) -> str:
    """
    Padroniza o código reduzido do produto como string numérica de 6 dígitos (ex: '000033', '084467').
    Remove decimais indevidos (ex: '84467.0' -> '084467') e valores nulos.
    """
    if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan":
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s.isdigit():
        return s.zfill(6)
    return s


def formatar_texto_limpo(val) -> str:
    """Remove quebras de linha (\\n), tabulações e espaços duplos nas extremidades de textos."""
    if pd.isna(val) or val is None or str(val).lower() == "nan":
        return ""
    return str(val).replace("\r", "").replace("\n", " ").strip()


def formatar_coluna_linha(val) -> str:
    """Formatador para coluna LINHA garantindo tipo TEXTO com barras espaçadas ('11 / 12 / 13')."""
    if pd.isna(val) or val is None:
        return ""
    val_str = str(val).strip()
    if "2013" in val_str:
        val_str = "11 / 12 / 13"
    val_str = re.sub(r'\s*/\s*', ' / ', val_str)
    return val_str


def reordenar_colunas_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reordena as colunas do DataFrame para colocar todas as colunas que começam com 'ID_'
    na frente (primeiras posições da tabela), mantendo as demais colunas logo em seguida.
    Isso garante que as chaves de ligação fiquem visíveis de imediato no Excel e no Power BI!
    """
    if df is None or df.empty:
        return df
    colunas_id = [col for col in df.columns if col.startswith("ID_")]
    outras_colunas = [col for col in df.columns if not col.startswith("ID_")]
    return df[colunas_id + outras_colunas]


# =============================================================================
# 1. PROCESSAMENTO DAS TABELAS DE DIMENSÃO (CADASTROS E TEMPO)
# =============================================================================

def processar_dimensao_calendario(data_inicio: str = "2014-01-01", data_fim: str = "2030-12-31") -> pd.DataFrame:
    """
    Gera a dimensão dCalendario com a chave única 'ID_Data' (formato YYYY-MM-DD).
    """
    print("\n[ETL] Gerando Dimensão: dCalendario...", flush=True)
    datas = pd.date_range(start=data_inicio, end=data_fim, freq="D")
    df = pd.DataFrame({"ID_Data": datas.strftime("%Y-%m-%d")})
    df["Data"] = pd.to_datetime(df["ID_Data"])

    df["Ano"] = df["Data"].dt.year
    df["Mes_Num"] = df["Data"].dt.month

    meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
                7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    meses_abrev_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
                      7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    df["Nome_Mes"] = df["Mes_Num"].map(meses_pt)
    df["Nome_Mes_Abrev"] = df["Mes_Num"].map(meses_abrev_pt)

    df["Ano_Mes"] = df["Data"].dt.strftime("%Y-%m")
    df["Ano_Mes_Num"] = df["Data"].dt.strftime("%Y%m").astype(int)

    df["Dia"] = df["Data"].dt.day
    df["Dia_Semana_Num"] = df["Data"].dt.dayofweek + 1

    dias_semana_pt = {1: "Segunda-feira", 2: "Terça-feira", 3: "Quarta-feira",
                      4: "Quinta-feira", 5: "Sexta-feira", 6: "Sábado", 7: "Domingo"}
    df["Nome_Dia_Semana"] = df["Dia_Semana_Num"].map(dias_semana_pt)

    df["Trimestre"] = df["Data"].dt.quarter
    df["Trimestre_Nome"] = df["Trimestre"].apply(lambda q: f"{q}º Trimestre")
    df["Semestre"] = np.where(df["Mes_Num"] <= 6, 1, 2)
    df["Semana_Ano"] = df["Data"].dt.isocalendar().week.astype(int)

    df["Eh_Fim_De_Semana"] = df["Dia_Semana_Num"].isin([6, 7])
    df["Eh_Dia_Util"] = ~df["Eh_Fim_De_Semana"]

    print(f"  -> dCalendario concluído com {len(df)} dias.", flush=True)
    return df


def processar_dimensao_produtos() -> pd.DataFrame:
    """
    Consolida TODOS os arquivos Excel da pasta dProdutos, gerando a dimensão única com as chaves:
      - 'ID_Produto_Reduzido': código reduzido de 6 dígitos.
      - 'ID_Produto_Estruturado': código estruturado.
    """
    print("\n[ETL] Processando Dimensão: dProdutos...", flush=True)
    pasta_origem = os.path.join(PASTA_DIMENSOES, "01_Produtos")
    arquivos = obter_todos_arquivos_excel(pasta_origem)

    dfs = []
    for caminho in arquivos:
        print(f"  -> Lendo arquivo: {os.path.basename(caminho)}", flush=True)
        df_temp = pd.read_excel(caminho, engine='calamine', dtype=str)
        df_temp.columns = [str(col).strip() for col in df_temp.columns]
        df_temp = df_temp.map(lambda x: str(x).strip() if pd.notna(x) else "")
        dfs.append(df_temp)

    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    # Criação das chaves primárias padronizadas
    df["ID_Produto_Reduzido"] = df["Reduzido"].apply(formatar_codigo_reduzido)
    df["ID_Produto_Estruturado"] = df["Estruturado"].apply(formatar_texto_limpo)

    # Elimina duplicatas na chave primária reduzida mantendo a última ocorrência (última atualização)
    df = df[df["ID_Produto_Reduzido"] != ""].drop_duplicates(subset=["ID_Produto_Reduzido"], keep="last")

    print(f"  -> dProdutos concluído: {len(df)} produtos únicos consolidados de {len(arquivos)} arquivo(s).", flush=True)
    return df


def processar_dimensao_estrutura() -> pd.DataFrame:
    """
    Consolida TODOS os arquivos Excel da pasta dEstruturaOrganizacional, gerando as chaves padronizadas
    'ID_Centro_Custo' (Código Estruturado) e 'ID_Sigla_CC' (Sigla CC).
    """
    print("\n[ETL] Processando Dimensão: dEstruturaOrganizacional...", flush=True)
    pasta_origem = os.path.join(PASTA_DIMENSOES, "02_Estrutura_Organizacional")
    arquivos = obter_todos_arquivos_excel(pasta_origem)

    dfs = []
    for caminho in arquivos:
        print(f"  -> Lendo arquivo: {os.path.basename(caminho)}", flush=True)
        df_temp = pd.read_excel(caminho, engine='calamine', dtype=str)
        df_temp.columns = [str(col).strip() for col in df_temp.columns]
        df_temp = df_temp.map(lambda x: str(x).strip() if pd.notna(x) else "")
        dfs.append(df_temp)

    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    df["ID_Centro_Custo"] = df["Código Estruturado"].apply(formatar_texto_limpo)
    df["ID_Sigla_CC"] = df["Sigla CC"].apply(formatar_texto_limpo)

    if "LINHA" in df.columns:
        df["LINHA"] = df["LINHA"].apply(formatar_coluna_linha)

    # Elimina duplicatas garantindo Chave Primária ÚNICA para ID_Sigla_CC (1:N com dCentroCusto)
    df = df[df["ID_Sigla_CC"] != ""].drop_duplicates(subset=["ID_Sigla_CC"], keep="first")

    print(f"  -> dEstruturaOrganizacional concluído com {len(df)} siglas únicas consolidadas de {len(arquivos)} arquivo(s).", flush=True)
    return df


def processar_dimensao_centros_custo() -> pd.DataFrame:
    """
    Consolida TODOS os arquivos Excel da pasta dCentroCusto com as chaves padronizadas:
      - 'ID_Centro_Custo': Código do Centro de Custo/Controle.
      - 'ID_Sigla_CC': Sigla da Unidade Organizacional.
    """
    print("\n[ETL] Processando Dimensão: dCentroCusto...", flush=True)
    pasta_origem = os.path.join(PASTA_DIMENSOES, "03_Centros_de_Custo")
    arquivos = obter_todos_arquivos_excel(pasta_origem)

    dfs = []
    for caminho in arquivos:
        print(f"  -> Lendo arquivo: {os.path.basename(caminho)}", flush=True)
        df_temp = pd.read_excel(caminho, engine='calamine')
        df_temp.columns = [str(col).strip() for col in df_temp.columns]
        dfs.append(df_temp)

    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    df["ID_Centro_Custo"] = df["Código"].apply(formatar_texto_limpo)
    df["ID_Sigla_CC"] = df["Sigla"].apply(formatar_texto_limpo)

    if "Inicial" in df.columns:
        df["Inicial"] = pd.to_datetime(df["Inicial"], errors="coerce", dayfirst=True)
    if "Final" in df.columns:
        df["Final"] = pd.to_datetime(df["Final"], errors="coerce", dayfirst=True)
        df["Ativo"] = df["Final"].isna()

    if "Ativo" in df.columns:
        df = df.sort_values(by=["Ativo"], ascending=False)

    # Desduplicação por chave primária exata ID_Centro_Custo (Texto)
    df = df[df["ID_Centro_Custo"] != ""].drop_duplicates(subset=["ID_Centro_Custo"], keep="first")

    print(f"  -> dCentroCusto concluído com chave primária única: {len(df)} linhas consolidadas de {len(arquivos)} arquivo(s).", flush=True)
    return df


# =============================================================================
# 2. PROCESSAMENTO DAS TABELAS FATO (TRANSAÇÕES E HISTÓRICOS)
# =============================================================================

def processar_fato_planejamento_res43() -> pd.DataFrame:
    """
    Consolida fPlanejamento_RES43 adicionando as chaves:
      - 'ID_Produto_Reduzido'
      - 'ID_Produto_Estruturado'
      - 'ID_Centro_Custo'
      - 'ID_Data'
    """
    print("\n[ETL] Processando Fato: fPlanejamento_RES43...", flush=True)
    pasta_origem = os.path.join(PASTA_FATOS, "RES43_Planejamento_Reposicao")
    arquivos = obter_todos_arquivos_excel(pasta_origem)

    dfs = []
    for caminho in arquivos:
        nome_arq = os.path.basename(caminho)
        print(f"  -> Lendo: {nome_arq}", flush=True)

        categoria = "Normal"
        if "Essencial" in nome_arq:
            categoria = "Essencial"
        elif "Estratégico" in nome_arq or "Estrategico" in nome_arq:
            categoria = "Estratégico"

        df_temp = pd.read_excel(caminho, skiprows=1, engine='calamine', dtype=str)
        df_temp.columns = [str(col).strip().replace('\n', ' ') for col in df_temp.columns]
        df_temp["Categoria_Consumo"] = categoria

        # Chaves padronizadas
        if "CPTM" in df_temp.columns:
            df_temp["ID_Produto_Reduzido"] = df_temp["CPTM"].apply(formatar_codigo_reduzido)
        if "Cód.Estr." in df_temp.columns:
            df_temp["ID_Produto_Estruturado"] = df_temp["Cód.Estr."].apply(formatar_texto_limpo)
        if "Centro de Controle" in df_temp.columns:
            df_temp["ID_Centro_Custo"] = df_temp["Centro de Controle"].apply(formatar_texto_limpo)

        data_ref = extrair_data_nome_arquivo(nome_arq)
        if data_ref:
            df_temp["ID_Data"] = data_ref

        dfs.append(df_temp)

    df_consolidado = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    print(f"  -> fPlanejamento_RES43 concluído: {len(df_consolidado)} linhas consolidadas de {len(arquivos)} arquivo(s).", flush=True)
    return df_consolidado


def processar_fato_estoque_res34() -> pd.DataFrame:
    """
    Consolida fEstoque_Almoxarifado_RES34 adicionando as chaves:
      - 'ID_Produto_Reduzido'
      - 'ID_Produto_Estruturado'
      - 'ID_Data'
    """
    print("\n[ETL] Processando Fato: fEstoque_Almoxarifado_RES34...", flush=True)
    pasta_origem = os.path.join(PASTA_FATOS, "RES34_Estoque_Almoxarifado")
    arquivos = obter_todos_arquivos_excel(pasta_origem)

    dfs = []
    for caminho in arquivos:
        nome_arq = os.path.basename(caminho)
        print(f"  -> Lendo: {nome_arq}", flush=True)
        df_temp = pd.read_excel(caminho, engine='calamine', dtype=str)
        df_temp.columns = [str(col).strip() for col in df_temp.columns]

        if "Cód. Red." in df_temp.columns:
            df_temp["ID_Produto_Reduzido"] = df_temp["Cód. Red."].apply(formatar_codigo_reduzido)
        if "Cód. Estr." in df_temp.columns:
            df_temp["ID_Produto_Estruturado"] = df_temp["Cód. Estr."].apply(formatar_texto_limpo)

        data_ref = extrair_data_nome_arquivo(nome_arq)
        if data_ref:
            df_temp["ID_Data"] = data_ref

        dfs.append(df_temp)

    df_consolidado = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    print(f"  -> fEstoque_Almoxarifado_RES34 concluído: {len(df_consolidado)} linhas consolidadas de {len(arquivos)} arquivo(s).", flush=True)
    return df_consolidado


def processar_fato_consumo_res75() -> pd.DataFrame:
    """
    Consolida TODOS os arquivos Excel da pasta fConsumoHistorico_RES75, aplica Unpivot e adiciona as chaves:
      - 'ID_Produto_Reduzido'
      - 'ID_Produto_Estruturado'
      - 'ID_Centro_Custo'
    Otimizado para manter baixa pegada de memória e filtrar apenas consumos reais (> 0).
    """
    print("\n[ETL] Processando Fato: fConsumoHistorico_RES75...", flush=True)
    pasta_origem = os.path.join(PASTA_FATOS, "RES75_Consumo_PCA_Historico")
    arquivos = obter_todos_arquivos_excel(pasta_origem)

    dfs_unpivoted = []
    for caminho in arquivos:
        print(f"  -> Lendo arquivo: {os.path.basename(caminho)}", flush=True)
        df = pd.read_excel(caminho, engine='calamine')
        df.columns = [str(col).strip() for col in df.columns]

        # Criação das chaves ANTES do unpivot
        if "Código CPTM" in df.columns:
            df["ID_Produto_Reduzido"] = df["Código CPTM"].apply(formatar_codigo_reduzido)
        if "Produto Estruturado" in df.columns:
            df["ID_Produto_Estruturado"] = df["Produto Estruturado"].apply(formatar_texto_limpo)
        if "Centro de Controle" in df.columns:
            df["ID_Centro_Custo"] = df["Centro de Controle"].apply(formatar_texto_limpo)

        colunas_anos = [c for c in df.columns if re.search(r'\d{4}\s+(MOV|PCA)', c)]
        
        # Seleção de colunas essenciais para evitar duplicação massiva de textos longos no unpivot
        colunas_id_desejadas = [
            "ID_Produto_Reduzido", "ID_Produto_Estruturado", "ID_Centro_Custo",
            "Código CPTM", "Produto Estruturado", "Centro de Controle",
            "Classe", "Grupo", "Subgrupo", "Unidade de Medida"
        ]
        colunas_id = [c for c in colunas_id_desejadas if c in df.columns]
        
        # Se restarem colunas importantes não mapeadas, mantém apenas para ID
        if not colunas_id:
            colunas_id = [c for c in df.columns if c not in colunas_anos]

        df_reduzido = df[colunas_id + colunas_anos].copy()

        df_unpivoted = pd.melt(
            df_reduzido,
            id_vars=colunas_id,
            value_vars=colunas_anos,
            var_name="Ano_Tipo",
            value_name="Quantidade"
        )

        df_unpivoted['Ano'] = df_unpivoted['Ano_Tipo'].apply(lambda x: x.split()[0])
        df_unpivoted['Tipo_Indicador'] = df_unpivoted['Ano_Tipo'].apply(lambda x: x.split()[1])
        df_unpivoted.drop(columns=['Ano_Tipo'], inplace=True)
        df_unpivoted['Quantidade'] = pd.to_numeric(df_unpivoted['Quantidade'], errors='coerce').fillna(0)

        # Remove registros sem produto reduzido e registros com quantidade 0 (sem movimento/PCA)
        df_unpivoted = df_unpivoted[
            (df_unpivoted["ID_Produto_Reduzido"] != "") & (df_unpivoted["Quantidade"] > 0)
        ]
        dfs_unpivoted.append(df_unpivoted)

    df_consolidado = pd.concat(dfs_unpivoted, ignore_index=True) if dfs_unpivoted else pd.DataFrame()
    print(f"  -> fConsumoHistorico_RES75 concluído com {len(df_consolidado)} linhas de consumo real consolidadas de {len(arquivos)} arquivo(s).", flush=True)
    return df_consolidado


def processar_fato_movimentacoes_res82() -> pd.DataFrame:
    """
    Consolida fMovimentacoes_RES82 adicionando as chaves:
      - 'ID_Produto_Estruturado'
      - 'ID_Data' (Formato YYYY-MM-DD extraído da data de Emissão)
    """
    print("\n[ETL] Processando Fato: fMovimentacoes_RES82...", flush=True)
    pasta_origem = os.path.join(PASTA_FATOS, "RES82_Movimentacoes_Estoque")
    arquivos = obter_todos_arquivos_excel(pasta_origem)

    dfs = []
    for caminho in arquivos:
        nome_arq = os.path.basename(caminho)
        print(f"  -> Lendo: {nome_arq}", flush=True)
        df_temp = pd.read_excel(caminho, engine='calamine', dtype=str)
        df_temp.columns = [str(col).strip() for col in df_temp.columns]

        if "Produto" in df_temp.columns:
            df_temp["ID_Produto_Estruturado"] = df_temp["Produto"].str.split(" - ").str[0].str.strip()
        
        if "Emissão" in df_temp.columns:
            dt_series = pd.to_datetime(df_temp["Emissão"], errors="coerce", dayfirst=True)
            df_temp["ID_Data"] = dt_series.dt.strftime("%Y-%m-%d")

        dfs.append(df_temp)

    df_consolidado = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    if "Chave" in df_consolidado.columns:
        df_consolidado = df_consolidado.drop_duplicates(subset=["Chave"], keep="last")

    print(f"  -> fMovimentacoes_RES82 concluído: {len(df_consolidado)} linhas consolidadas de {len(arquivos)} arquivo(s).", flush=True)
    return df_consolidado


def processar_fato_requisicoes_workflow() -> pd.DataFrame:
    """
    Consolida fRequisicoes_Workflow adicionando as chaves:
      - 'ID_Centro_Custo' (sem quebras de linha \n)
      - 'ID_Data' (Data de Aprovação ISO YYYY-MM-DD)
    """
    print("\n[ETL] Processando Fato: fRequisicoes_Workflow...", flush=True)
    pasta_origem = os.path.join(PASTA_FATOS, "Requisicoes_Workflow")
    arquivos = obter_todos_arquivos_excel(pasta_origem)

    dfs = []
    for caminho in arquivos:
        nome_arq = os.path.basename(caminho)
        print(f"  -> Lendo: {nome_arq}", flush=True)
        df_temp = pd.read_excel(caminho, engine='calamine', dtype=str)
        df_temp.columns = [str(col).strip() for col in df_temp.columns]

        if "Centro de Controle" in df_temp.columns:
            df_temp["ID_Centro_Custo"] = df_temp["Centro de Controle"].apply(
                lambda x: str(x).split("-")[0].strip() if pd.notna(x) else ""
            )

        if "Data Aprovação" in df_temp.columns:
            dt_series = pd.to_datetime(df_temp["Data Aprovação"], errors="coerce", dayfirst=True)
            df_temp["ID_Data"] = dt_series.dt.strftime("%Y-%m-%d")

        dfs.append(df_temp)

    df_consolidado = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    if "Número" in df_consolidado.columns:
        df_consolidado = df_consolidado.drop_duplicates(subset=["Número"], keep="last")

    print(f"  -> fRequisicoes_Workflow concluído: {len(df_consolidado)} linhas consolidadas de {len(arquivos)} arquivo(s).", flush=True)
    return df_consolidado


def enriquecer_dprodutos_curva_abc(df_produtos: pd.DataFrame, df_consumo: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula a Curva ABC (Classificação de Pareto: Classe A, B, C ou Sem Consumo)
    e enriquece a dimensão dProdutos com as colunas:
      - 'Classe_ABC': Classe A (80%), Classe B (15%), Classe C (5%) ou Sem Consumo.
      - 'Rank_Consumo': Posição do produto no ranking de consumo.
      - 'Quantidade_Consumida_Total': Volume total consumido historicamente.
      - 'Pct_Consumo_Acumulado': Percentual acumulado do consumo (Pareto).
    """
    print("\n[ETL] Calculando Curva ABC dos produtos a partir de fConsumoHistorico_RES75...", flush=True)
    if df_produtos is None or df_produtos.empty or df_consumo is None or df_consumo.empty:
        return df_produtos

    df_c = df_consumo.copy()
    df_c["Quantidade"] = pd.to_numeric(df_c["Quantidade"], errors="coerce").fillna(0)

    # Agrupa consumo por código reduzido do produto
    abc = df_c.groupby("ID_Produto_Reduzido")["Quantidade"].sum().reset_index()
    abc = abc[abc["Quantidade"] > 0].sort_values(by="Quantidade", ascending=False)

    total_consumo = abc["Quantidade"].sum()
    if total_consumo > 0:
        abc["Pct_Consumo"] = abc["Quantidade"] / total_consumo
        abc["Pct_Consumo_Acumulado"] = abc["Pct_Consumo"].cumsum()
        abc["Rank_Consumo"] = range(1, len(abc) + 1)

        def classificar_abc(pct):
            if pct <= 0.80:
                return "Classe A"
            elif pct <= 0.95:
                return "Classe B"
            else:
                return "Classe C"

        abc["Classe_ABC"] = abc["Pct_Consumo_Acumulado"].apply(classificar_abc)
    else:
        abc["Pct_Consumo_Acumulado"] = 0.0
        abc["Rank_Consumo"] = np.nan
        abc["Classe_ABC"] = "Sem Consumo"

    df_p = df_produtos.merge(
        abc[["ID_Produto_Reduzido", "Quantidade", "Rank_Consumo", "Pct_Consumo_Acumulado", "Classe_ABC"]],
        on="ID_Produto_Reduzido",
        how="left"
    )

    df_p["Quantidade_Consumida_Total"] = df_p["Quantidade"].fillna(0.0)
    if "Quantidade" in df_p.columns:
        df_p.drop(columns=["Quantidade"], inplace=True)

    df_p["Classe_ABC"] = df_p["Classe_ABC"].fillna("Sem Consumo")
    df_p["Pct_Consumo_Acumulado"] = df_p["Pct_Consumo_Acumulado"].fillna(0.0)

    print(f"  -> Curva ABC concluída! Resumo: {df_p['Classe_ABC'].value_counts().to_dict()}", flush=True)
    return df_p


# =============================================================================
# ORQUESTRADOR PRINCIPAL DO ETL
# =============================================================================

def executar_pipeline_etl():
    """
    Função orquestradora principal que executa todas as etapas de limpeza e exporta
    os resultados limpos e formatados com chaves padronizadas para consumo direto no Power BI.
    """
    print("=================================================================", flush=True)
    print("INICIANDO PIPELINE DE ETL EM PYTHON — PROJETO POWER BI CPTM", flush=True)
    print("=================================================================", flush=True)

    tabelas_funcoes = {
        "dCalendario": processar_dimensao_calendario,
        "dProdutos": processar_dimensao_produtos,
        "dEstruturaOrganizacional": processar_dimensao_estrutura,
        "dCentroCusto": processar_dimensao_centros_custo,
        "fPlanejamento_RES43": processar_fato_planejamento_res43,
        "fEstoque_Almoxarifado_RES34": processar_fato_estoque_res34,
        "fConsumoHistorico_RES75": processar_fato_consumo_res75,
        "fMovimentacoes_RES82": processar_fato_movimentacoes_res82,
        "fRequisicoes_Workflow": processar_fato_requisicoes_workflow
    }

    dfs_processados = {}

    for nome_tabela, funcao_etl in tabelas_funcoes.items():
        try:
            dfs_processados[nome_tabela] = funcao_etl()
        except Exception as e:
            print(f"  [ERRO CRÍTICO] Falha ao processar tabela '{nome_tabela}': {e}", flush=True)

    # Enriquece a dimensão dProdutos com a Curva ABC calculada a partir de fConsumoHistorico_RES75
    if "dProdutos" in dfs_processados and "fConsumoHistorico_RES75" in dfs_processados:
        dfs_processados["dProdutos"] = enriquecer_dprodutos_curva_abc(
            dfs_processados["dProdutos"],
            dfs_processados["fConsumoHistorico_RES75"]
        )

    # Salvamento de todas as tabelas em CSV e Parquet
    for nome_tabela, df_resultado in dfs_processados.items():
        if df_resultado is None or df_resultado.empty:
            continue

        df_resultado = reordenar_colunas_id(df_resultado)

        caminho_csv = os.path.join(PASTA_SAIDA, f"{nome_tabela}.csv")
        caminho_parquet = os.path.join(PASTA_SAIDA, f"{nome_tabela}.parquet")

        df_resultado.to_csv(caminho_csv, index=False, sep=";", encoding="utf-8-sig")
        print(f"  [SUCESSO] Tabela '{nome_tabela}' salva em CSV: {caminho_csv}", flush=True)

        try:
            df_resultado.to_parquet(caminho_parquet, index=False)
            print(f"  [SUCESSO] Tabela '{nome_tabela}' salva em Parquet: {caminho_parquet}", flush=True)
        except Exception as e_parquet:
            print(f"  [AVISO] Parquet não gerado para '{nome_tabela}': {e_parquet}", flush=True)

    print("\n=================================================================", flush=True)
    print("PIPELINE DE ETL CONCLUÍDO COM SUCESSO!", flush=True)
    print(f"Tabelas prontas para importação no Power BI salvas em:\n  {PASTA_SAIDA}", flush=True)
    print("=================================================================", flush=True)


if __name__ == "__main__":
    executar_pipeline_etl()
