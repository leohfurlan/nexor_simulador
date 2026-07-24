"""Serviço de LancamentoMensal — upsert por competência, cálculo por linha e CSV.

O cálculo por linha integra o motor puro (Fase 1) com os parâmetros do tenant,
produzindo uma "view" pronta para o template (inputs + impostos dos 4 regimes +
regime recomendado).
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
import unicodedata
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calc.engine import (
    LP_CREDITO,
    LP_PURO,
    LP_REAL,
    SN_HIBRIDO,
    SN_PADRAO,
    calcular_lancamento,
)
from app.calc.recommend import recomendar
from app.models import Empresa, LancamentoMensal
from app.services.parametros_service import get_or_create_parametros
from app.utils.numbers import parse_money_default_zero, parse_optional_decimal_br

# Ordem das colunas de regime na tabela.
_COLS = (SN_PADRAO, SN_HIBRIDO, LP_PURO, LP_CREDITO, LP_REAL)

# Sentinela: distingue "não passar rbt12" (edição manual) de "definir rbt12" (import).
_UNSET = object()

_COMPETENCIA_ISO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_COMPETENCIA_BR = re.compile(r"^(0[1-9]|1[0-2])/\d{4}$")
_COMPETENCIA_MES_TEXTO = re.compile(r"^([a-z]{3,})\.?[\s/_-]*(\d{2}|\d{4})$")
_MESES_PT = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def _strip_accents(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def normalize_competencia(value: object) -> str:
    """Normaliza a competência para 'YYYY-MM'.

    Aceita date/datetime (Excel), 'YYYY-MM', 'MM/YYYY' e nome de mês pt-BR
    ('jan/26', 'jan./26', 'janeiro/2026'). Inválido → ValueError.
    """
    if isinstance(value, (dt.datetime, dt.date)):
        return f"{value.year:04d}-{value.month:02d}"
    s = str(value if value is not None else "").strip()
    if s == "":
        raise ValueError("competência vazia")
    if _COMPETENCIA_ISO.match(s):
        return s
    if _COMPETENCIA_BR.match(s):
        mes, ano = s.split("/")
        return f"{ano}-{mes}"
    m = _COMPETENCIA_MES_TEXTO.match(_strip_accents(s.lower()))
    if m:
        mon = _MESES_PT.get(m.group(1)[:3])
        if mon:
            ano = m.group(2)
            ano = f"20{ano}" if len(ano) == 2 else ano
            return f"{int(ano):04d}-{mon:02d}"
    raise ValueError(f"competência inválida: {value!r} (use AAAA-MM)")


async def list_lancamentos(
    session: AsyncSession, tenant_id: uuid.UUID, empresa_id: uuid.UUID
):
    stmt = (
        select(LancamentoMensal)
        .where(
            LancamentoMensal.tenant_id == tenant_id,
            LancamentoMensal.empresa_id == empresa_id,
        )
        .order_by(LancamentoMensal.competencia)
    )
    return (await session.execute(stmt)).scalars().all()


async def upsert_lancamento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    empresa_id: uuid.UUID,
    *,
    competencia: str,
    faturamento: str,
    despesas_com_credito: str,
    das_padrao_apurado: str,
    rbt12: object = _UNSET,
) -> LancamentoMensal:
    comp = normalize_competencia(competencia)
    fat = parse_money_default_zero(faturamento)
    desp = parse_money_default_zero(despesas_com_credito)
    das = parse_optional_decimal_br(das_padrao_apurado)
    definir_rbt = rbt12 is not _UNSET
    rbt = parse_optional_decimal_br(rbt12) if definir_rbt else None

    lanc = await session.scalar(
        select(LancamentoMensal).where(
            LancamentoMensal.tenant_id == tenant_id,
            LancamentoMensal.empresa_id == empresa_id,
            LancamentoMensal.competencia == comp,
        )
    )
    if lanc is None:
        lanc = LancamentoMensal(
            tenant_id=tenant_id,
            empresa_id=empresa_id,
            competencia=comp,
            faturamento=fat,
            despesas_com_credito=desp,
            das_padrao_apurado=das,
        )
        if definir_rbt:
            lanc.rbt12 = rbt
        session.add(lanc)
    else:
        lanc.faturamento = fat
        lanc.despesas_com_credito = desp
        lanc.das_padrao_apurado = das
        if definir_rbt:
            lanc.rbt12 = rbt
    await session.commit()
    await session.refresh(lanc)
    return lanc


async def delete_lancamento(
    session: AsyncSession, tenant_id: uuid.UUID, empresa_id: uuid.UUID, competencia: str
) -> bool:
    result = await session.execute(
        delete(LancamentoMensal).where(
            LancamentoMensal.tenant_id == tenant_id,
            LancamentoMensal.empresa_id == empresa_id,
            LancamentoMensal.competencia == competencia,
        )
    )
    await session.commit()
    return result.rowcount > 0


def _row_view(
    lanc: LancamentoMensal, calc_params, exige_credito_cliente: bool, margem=None
) -> dict:
    """Calcula uma linha e monta a estrutura consumida pelo template."""
    das_informado = lanc.das_padrao_apurado is not None
    margem_informada = margem is not None
    calc = calcular_lancamento(
        lanc.faturamento, lanc.despesas_com_credito, lanc.das_padrao_apurado,
        calc_params, margem=margem,
    )
    # Regimes indisponíveis por falta de dado: SN Padrão sem DAS, Lucro Real sem
    # margem de lucro informada.
    excluir = set()
    if not das_informado:
        excluir.add(SN_PADRAO)
    if not margem_informada:
        excluir.add(LP_REAL)
    rec = recomendar(calc, exige_credito_cliente, excluir=excluir or None)

    def _disponivel(chave: str) -> bool:
        if chave == SN_PADRAO:
            return das_informado
        if chave == LP_REAL:
            return margem_informada
        return True

    regimes = []
    for chave in _COLS:
        r = calc.regimes[chave]
        regimes.append(
            {
                "chave": chave,
                "imposto": r.imposto,
                "pct": r.pct_efetivo,
                "disponivel": _disponivel(chave),
            }
        )
    return {
        "id": str(lanc.id),
        "competencia": lanc.competencia,
        "faturamento": lanc.faturamento,
        "despesas": lanc.despesas_com_credito,
        "das": lanc.das_padrao_apurado,
        "recomendado": rec.regime.chave,
        "regimes": regimes,
        # Informativos (modo avançado do dashboard).
        "credito_despesa": calc.credito_despesa,
        "cbs": calc.cbs,
        "ibs": calc.ibs,
        "hibrido_bruto": calc.hibrido_bruto,
    }


async def compute_rows(
    session: AsyncSession, tenant_id: uuid.UUID, empresa: Empresa
) -> list[dict]:
    params = await get_or_create_parametros(session, tenant_id)
    calc_params = params.to_calc()
    lancs = await list_lancamentos(session, tenant_id, empresa.id)
    return [
        _row_view(lanc, calc_params, empresa.exige_credito_cliente,
                  margem=empresa.margem_lucro_estimada)
        for lanc in lancs
    ]


# --- Import CSV / XLSX ------------------------------------------------------
# A estrutura de coleta espelha a planilha do escritório (aba "SN HIBRIDO X
# PADRÃO"): colunas Mês, Faturamento Mensal, Despesas com Crédito, DAS Padrão e
# Fat. Acumulado 12 meses. As demais colunas (CBS, IBS, LP…) são calculadas.

def _norm_header(name: object) -> str:
    s = _strip_accents(str(name) if name is not None else "")
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")


_HEADER_ALIASES = {
    "competencia": "competencia",
    "mes": "competencia",
    "mes_ano": "competencia",
    "referencia": "competencia",
    "faturamento": "faturamento",
    "faturamento_mensal": "faturamento",
    "receita": "faturamento",
    "despesas_com_credito": "despesas_com_credito",
    "despesas": "despesas_com_credito",
    "despesa": "despesas_com_credito",
    "das_padrao_apurado": "das_padrao_apurado",
    "das": "das_padrao_apurado",
    "das_padrao": "das_padrao_apurado",
    "fat_acumulado_12_meses": "rbt12",
    "faturamento_acumulado_12_meses": "rbt12",
    "rbt12": "rbt12",
}

# Abas mais prováveis de conter os lançamentos, por prioridade de nome.
_SHEET_PREF = ("hibrido", "padrao", "calculo rt", "simples", "lancament", "lucro")


def _build_colmap(header) -> dict[str, int]:
    """Mapeia campo canônico → índice da coluna, a partir da linha de cabeçalho."""
    colmap: dict[str, int] = {}
    for i, h in enumerate(header or []):
        if h is None:
            continue
        alias = _HEADER_ALIASES.get(_norm_header(h))
        if alias and alias not in colmap:
            colmap[alias] = i
    return colmap


async def _import_one(session, tenant_id, empresa_id, comp, fat, desp, das, rbt) -> bool:
    """Faz upsert de uma linha. Retorna False se a linha for vazia/sem movimento."""
    if all(v is None or str(v).strip() == "" for v in (comp, fat, desp, das)):
        return False
    fat_dec = parse_money_default_zero(fat)
    desp_dec = parse_money_default_zero(desp)
    das_dec = parse_optional_decimal_br(das)
    # Mês sem movimento (linhas em branco do modelo) → ignora silenciosamente.
    if fat_dec == 0 and desp_dec == 0 and (das_dec is None or das_dec == 0):
        return False

    kwargs = dict(
        competencia=comp,
        faturamento="" if fat is None else fat,
        despesas_com_credito="" if desp is None else desp,
        das_padrao_apurado="" if das is None else das,
    )
    if rbt is not None and str(rbt).strip() != "":
        kwargs["rbt12"] = rbt
    await upsert_lancamento(session, tenant_id, empresa_id, **kwargs)
    return True


async def _import_rows(session, tenant_id, empresa_id, header, data_rows):
    colmap = _build_colmap(header)
    if "competencia" not in colmap:
        return 0, ['Não encontrei a coluna de competência (ex.: "Mês").']

    def cell(row, field):
        idx = colmap.get(field)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    importadas = 0
    erros: list[str] = []
    for n, row in enumerate(data_rows, start=1):
        try:
            if await _import_one(
                session, tenant_id, empresa_id,
                cell(row, "competencia"), cell(row, "faturamento"),
                cell(row, "despesas_com_credito"), cell(row, "das_padrao_apurado"),
                cell(row, "rbt12"),
            ):
                importadas += 1
        except ValueError as exc:
            erros.append(f"Linha {n}: {exc}")
    return importadas, erros


async def import_csv(session, tenant_id, empresa_id, content: bytes):
    """Importa de CSV (delimitador , ou ;). Retorna (importadas, erros)."""
    text = content.decode("utf-8-sig", errors="replace")
    sample = text[:2048]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    if not rows:
        return 0, ["CSV vazio ou sem cabeçalho."]
    return await _import_rows(session, tenant_id, empresa_id, rows[0], rows[1:])


async def import_xlsx(session, tenant_id, empresa_id, content: bytes):
    """Importa da 1ª aba com colunas de competência+faturamento.

    Retorna (importadas, erros, nome_da_aba). Prioriza abas por nome provável.
    """
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    try:
        def rank(title: str) -> int:
            low = _strip_accents(title.lower())
            for i, key in enumerate(_SHEET_PREF):
                if key in low:
                    return i
            return len(_SHEET_PREF)

        for ws in sorted(wb.worksheets, key=lambda w: rank(w.title)):
            rows = []
            for r in ws.iter_rows(values_only=True):
                rows.append(r)
                if len(rows) > 400:  # limite defensivo (33 anos de competências)
                    break
            header_idx = next(
                (i for i, r in enumerate(rows[:15])
                 if {"competencia", "faturamento"} <= set(_build_colmap(r))),
                None,
            )
            if header_idx is None:
                continue
            importadas, erros = await _import_rows(
                session, tenant_id, empresa_id, rows[header_idx], rows[header_idx + 1:]
            )
            return importadas, erros, ws.title
        return 0, ["Nenhuma aba com colunas de competência e faturamento."], None
    finally:
        wb.close()


async def import_file(session, tenant_id, empresa_id, filename: str, content: bytes):
    """Dispatcher por extensão. Retorna (importadas, erros, nota)."""
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        importadas, erros, aba = await import_xlsx(session, tenant_id, empresa_id, content)
        return importadas, erros, (f"aba “{aba}”" if aba else "")
    importadas, erros = await import_csv(session, tenant_id, empresa_id, content)
    return importadas, erros, ""
