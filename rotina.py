import requests
import json
import os
from datetime import datetime, timedelta, time

# Carrega variáveis do .env se existir
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

CONFIG = {
    "MOVIDESK_TOKEN": os.environ["MOVIDESK_TOKEN"],
    "GOOGLE_SHEET_API": os.environ["GOOGLE_SHEET_API"],
    "AGENTES": ["Rafael", "Carnaval", "Carol", "Rubens", "Enzo"]
}


# -------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------

def fetch_all_paginated(base_url, max_pages=20):
    all_records = []
    top = 1000
    skip = 0

    for _ in range(max_pages):
        url = f"{base_url}&$top={top}&$skip={skip}"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Erro na requisição: {response.status_code} - {response.text}")
            break

        try:
            batch = response.json()
        except Exception as e:
            print(f"Erro ao converter JSON: {e}")
            break

        if not isinstance(batch, list) or len(batch) == 0:
            break

        all_records.extend(batch)

        if len(batch) < top:
            break

        skip += top

    return all_records


def parse_iso_date(date_str):
    if not date_str:
        return None

    try:
        # Corrige Z para UTC
        if date_str.endswith("Z"):
            date_str = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(date_str)
    except Exception:
        return None


def calcular_minutos_uteis(inicio, fim):
    if inicio >= fim:
        return 0

    inicio_ajustado = inicio
    fim_ajustado = fim

    # Ajusta horário inicial
    if inicio_ajustado.hour < 9:
        inicio_ajustado = inicio_ajustado.replace(hour=9, minute=0, second=0, microsecond=0)
    elif inicio_ajustado.hour >= 18:
        inicio_ajustado = (inicio_ajustado + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    # Ajusta horário final
    if fim_ajustado.hour > 18 or (fim_ajustado.hour == 18 and fim_ajustado.minute > 0):
        fim_ajustado = fim_ajustado.replace(hour=18, minute=0, second=0, microsecond=0)
    elif fim_ajustado.hour < 9:
        fim_ajustado = (fim_ajustado - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)

    minutos_uteis = 0
    cursor = inicio_ajustado

    while cursor < fim_ajustado:
        dia_semana = cursor.weekday()  # segunda=0, domingo=6

        # Pula sábado e domingo
        if dia_semana >= 5:
            cursor = (cursor + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            continue

        fim_expediente = cursor.replace(hour=18, minute=0, second=0, microsecond=0)
        limite_atual = min(fim_ajustado, fim_expediente)

        if cursor > limite_atual:
            cursor = (cursor + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            continue

        minutos_uteis += (limite_atual - cursor).total_seconds() / 60
        cursor = (cursor + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    return minutos_uteis


def formatar_sla(minutos):
    total = round(minutos)
    if total < 60:
        return f"{total}m"
    return f"{total // 60}h {total % 60:02d}m"


def media(lista):
    return sum(lista) / len(lista) if lista else 0


# -------------------------------
# FUNÇÃO PRINCIPAL
# -------------------------------

def extrair_relatorio():
    now = datetime.now()
    year = now.year
    month = str(now.month).zfill(2)
    day = str(now.day).zfill(2)

    today_start_str = f"{year}-{month}-{day}T03:00:00.000Z"
    month_start_str = f"{year}-{month}-01T03:00:00.000Z"
    from datetime import timezone
    iso_now = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    relatorio = {
        "resumo": {},
        "tempos": {},
        "status": {},
        "agentes": [],
        "nps": {
            "pessimo": 0,
            "ruim": 0,
            "regular": 0,
            "bom": 0,
            "otimo": 0
        }
    }

    try:
        # 1. RESUMO
        chamados_hoje_url = (
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id"
            f"&$filter=createdDate ge {today_start_str}"
        )

        chamados_resolvidos_hoje_url = (
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id"
            f"&$filter=(baseStatus eq 'Resolved' or baseStatus eq 'Closed') and resolvedIn ge {today_start_str}"
        )

        chamados_mes_url = (
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id"
            f"&$filter=createdDate ge {month_start_str}"
        )

        # 2. STATUS GLOBAIS
        novos_url = (
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id,baseStatus"
            f"&$filter=baseStatus eq 'New'"
        )

        andamento_url = (
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id,baseStatus"
            f"&$filter=baseStatus eq 'InAttendance'"
        )

        parados_url = (
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id,baseStatus"
            f"&$filter=baseStatus eq 'Stopped'"
        )

        vencidos_url = (
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id"
            f"&$filter=slaSolutionDate ne null and slaSolutionDate lt {iso_now} "
            f"and (baseStatus eq 'New' or baseStatus eq 'InAttendance' or baseStatus eq 'Stopped')"
        )

        res_hoje = fetch_all_paginated(chamados_hoje_url)
        res_resolvidos_hoje = fetch_all_paginated(chamados_resolvidos_hoje_url)
        res_mes = fetch_all_paginated(chamados_mes_url)
        res_novos = fetch_all_paginated(novos_url)
        res_andamento = fetch_all_paginated(andamento_url)
        res_parados = fetch_all_paginated(parados_url)
        res_vencidos = fetch_all_paginated(vencidos_url)

        relatorio["resumo"] = {
            "totalHoje": len(res_hoje),
            "resolvidosHoje": len(res_resolvidos_hoje),
            "chamadosNoMes": len(res_mes)
        }

        relatorio["status"] = {
            "novos": len(res_novos),
            "andamento": len(res_andamento),
            "parados": len(res_parados),
            "vencidos": len(res_vencidos)
        }

        # 3. TEMPOS
        url_solucao = (
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id,createdDate,resolvedIn,stoppedTimeWorkingTime,slaRealResponseDate"
            f"&$filter=createdDate ge 2026-01-01T00:00:00.000Z and resolvedIn ge {month_start_str}"
        )
        data_solucao = fetch_all_paginated(url_solucao)

        url_respostas = (
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id,createdDate,slaRealResponseDate"
            f"&$filter=createdDate ge {month_start_str}"
        )
        data_respostas = fetch_all_paginated(url_respostas)

        tempos_resp_hoje = []
        tempos_resp_mes = []
        tempos_sol_hoje = []
        tempos_sol_mes = []

        # TMA 1ª resposta
        for t in data_respostas:
            if not t.get("slaRealResponseDate"):
                continue

            criacao = parse_iso_date(t.get("createdDate"))
            resposta = parse_iso_date(t.get("slaRealResponseDate"))

            if not criacao or not resposta:
                continue

            criacao -= timedelta(hours=3)
            resposta -= timedelta(hours=3)

            minutos = calcular_minutos_uteis(criacao, resposta)

            tempos_resp_mes.append(minutos)
            if t.get("createdDate", "") >= today_start_str:
                tempos_resp_hoje.append(minutos)

        # TMA solução
        hoje_dt = datetime(now.year, now.month, now.day, 0, 0, 0)
        for t in data_solucao:
            criacao = parse_iso_date(t.get("createdDate"))
            resolucao = parse_iso_date(t.get("resolvedIn"))

            if not criacao or not resolucao:
                continue

            criacao -= timedelta(hours=3)
            resolucao -= timedelta(hours=3)

            bruto = calcular_minutos_uteis(criacao, resolucao)
            parado = t.get("stoppedTimeWorkingTime") or 0
            liquido = bruto - parado

            if liquido < 0:
                liquido = 0

            tempos_sol_mes.append(liquido)
            resolucao_local = resolucao.replace(tzinfo=None) if resolucao.tzinfo else resolucao
            if resolucao_local >= hoje_dt:
                tempos_sol_hoje.append(liquido)

        relatorio["tempos"] = {
            "tmaRespostaHoje": formatar_sla(media(tempos_resp_hoje)),
            "tmaRespostaMes": formatar_sla(media(tempos_resp_mes)),
            "tmaSolucaoHoje": formatar_sla(media(tempos_sol_hoje)),
            "tmaSolucaoMes": formatar_sla(media(tempos_sol_mes))
        }

        # 4. PERFORMANCE POR AGENTE
        pendentes_com_agente = fetch_all_paginated(
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id,baseStatus,slaSolutionDate"
            f"&$expand=owner($select=id,businessName)"
            f"&$filter=(baseStatus eq 'New' or baseStatus eq 'InAttendance' or baseStatus eq 'Stopped')"
        )

        for agente in CONFIG["AGENTES"]:
            tks_agente = [
                t for t in pendentes_com_agente
                if t.get("owner")
                and t["owner"].get("businessName")
                and agente in t["owner"]["businessName"]
            ]

            url_resolv_agente = (
                f"https://api.movidesk.com/public/v1/tickets"
                f"?token={CONFIG['MOVIDESK_TOKEN']}"
                f"&$select=id"
                f"&$filter=(baseStatus eq 'Resolved' or baseStatus eq 'Closed') "
                f"and resolvedIn ge {today_start_str} "
                f"and contains(owner/businessName, '{agente}')"
            )

            resol_agente = fetch_all_paginated(url_resolv_agente)

            relatorio["agentes"].append({
                "nome": agente,
                "resolvidosHoje": len(resol_agente),
                "novos": len([t for t in tks_agente if t.get("baseStatus") == "New"]),
                "andamento": len([t for t in tks_agente if t.get("baseStatus") == "InAttendance"]),
                "parados": len([t for t in tks_agente if t.get("baseStatus") == "Stopped"]),
                "vencidos": len([
                    t for t in tks_agente
                    if t.get("slaSolutionDate") and t["slaSolutionDate"] < iso_now
                ])
            })

        # 5. NPS (Google Sheets)
        try:
            nps_res = requests.get(CONFIG["GOOGLE_SHEET_API"])
            if nps_res.status_code == 200:
                nps_json = nps_res.json()

                if nps_json and nps_json.get("data"):
                    current_month = now.month
                    current_year = now.year

                    for item in nps_json["data"]:
                        data_item = item.get("Data")
                        if not data_item:
                            continue

                        try:
                            d = parse_iso_date(data_item)
                            if not d:
                                continue

                            if d.month == current_month and d.year == current_year:
                                nota = int(item.get("Nota") or item.get("nota") or 0)

                                if nota == 1:
                                    relatorio["nps"]["pessimo"] += 1
                                elif nota == 2:
                                    relatorio["nps"]["ruim"] += 1
                                elif nota == 3:
                                    relatorio["nps"]["regular"] += 1
                                elif nota == 4:
                                    relatorio["nps"]["bom"] += 1
                                elif nota == 5:
                                    relatorio["nps"]["otimo"] += 1

                        except Exception:
                            continue
        except Exception as e:
            print(f"Erro na API de NPS Google: {e}")

        print(json.dumps(relatorio, indent=2, ensure_ascii=False))
        return relatorio

    except Exception as err:
        print(f"Erro ao gerar relatório: {err}")
        return None


# -------------------------------
# CHAMADOS EM ABERTO POR AGENTE
# -------------------------------

def buscar_chamados_abertos_por_agente():
    print("Consultando o Movidesk...")

    filtro = "(baseStatus eq 'New' or baseStatus eq 'InAttendance' or baseStatus eq 'Stopped')"

    url = (
        f"https://api.movidesk.com/public/v1/tickets"
        f"?token={CONFIG['MOVIDESK_TOKEN']}"
        f"&$select=id,baseStatus"
        f"&$expand=owner($select=id,businessName)"
        f"&$filter={filtro}"
        f"&$top=1000"
    )

    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Erro na API do Movidesk: Status {response.status_code}")

        chamados_em_aberto = response.json()
        print(f"Sucesso! Foram encontrados {len(chamados_em_aberto)} chamados em aberto no total.\n")

        resultado_por_agente = []

        for agente_nome in CONFIG["AGENTES"]:
            chamados_do_agente = [
                chamado for chamado in chamados_em_aberto
                if chamado.get("owner")
                and chamado["owner"].get("businessName")
                and agente_nome in chamado["owner"]["businessName"]
            ]

            resultado_por_agente.append({
                "agente": agente_nome,
                "totalAbertos": len(chamados_do_agente)
            })

        print(json.dumps(resultado_por_agente, indent=2, ensure_ascii=False))
        return resultado_por_agente

    except Exception as error:
        print(f"Erro ao processar os chamados: {error}")
        return None


# -------------------------------
# CHAMADOS PENDENTES POR AGENTE
# -------------------------------

def buscar_chamados_pendentes_por_agente():
    print("Consultando chamados pendentes no Movidesk...")

    agentes = [
        {"nome": "Rafael Zahner", "filtro": "contains(owner/businessName,'Rafael Zahner')"},
        {"nome": "Enzo Edner", "filtro": "contains(owner/businessName,'Enzo Edner')"},
        {"nome": "CAROLINE ARAUJO DA COSTA", "filtro": "contains(owner/businessName,'CAROLINE ARAUJO DA COSTA')"},
        {"nome": "Gabriel de Oliveira Carnaval", "filtro": "contains(owner/businessName,'Gabriel de Oliveira Carnaval')"}
    ]

    resultados = []

    for agente in agentes:
        url = (
            f"https://api.movidesk.com/public/v1/tickets"
            f"?token={CONFIG['MOVIDESK_TOKEN']}"
            f"&$select=id,subject,status,baseStatus,owner"
            f"&$filter={agente['filtro']} "
            f"and baseStatus ne 'Closed' "
            f"and baseStatus ne 'Resolved' "
            f"and baseStatus ne 'Canceled' "
            f"and status ne 'Aguardando - retorno do cliente'"
        )

        try:
            response = requests.get(url)
            if response.status_code != 200:
                raise Exception(f"Erro na API do Movidesk para o agente {agente['nome']}: Status {response.status_code}")

            chamados_pendentes = response.json()

            resultados.append({
                "agente": agente["nome"],
                "totalPendentes": len(chamados_pendentes),
                "chamados": chamados_pendentes
            })

        except Exception as error:
            print(f"Erro ao buscar chamados pendentes para o agente {agente['nome']}: {error}")

    resumo = [{"Agente": r["agente"], "TotalPendentes": r["totalPendentes"]} for r in resultados]
    print(json.dumps(resumo, indent=2, ensure_ascii=False))
    return resultados


# -------------------------------
# EXECUÇÃO
# -------------------------------

if __name__ == "__main__":
    extrair_relatorio()
    buscar_chamados_abertos_por_agente()
    buscar_chamados_pendentes_por_agente()