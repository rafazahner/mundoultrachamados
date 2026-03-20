import smtplib
import sys
import os
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ─────────────────────────────────────────
# CONFIGURAÇÕES DO E-MAIL
# ─────────────────────────────────────────

def _carregar_destinatarios():
    """Lê a lista de destinatários do arquivo destinatarios.json."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "destinatarios.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return ["rafael.zahner@ultraacademia.com.br"]

EMAIL_CONFIG = {
    "remetente": "alfred.ultraacademia@gmail.com",
    "senha_app": "binwgydtuswokcdh",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
}

# Adiciona o Desktop ao path para importar rotina.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rotina import extrair_relatorio, buscar_chamados_abertos_por_agente, buscar_chamados_pendentes_por_agente


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def badge(valor, cor):
    """Cria um badge colorido para usar no HTML."""
    return f'<span style="background:{cor};color:#fff;padding:2px 10px;border-radius:20px;font-weight:700;font-size:13px;">{valor}</span>'

def cor_status(valor, inverso=False):
    """Verde se bom, vermelho se ruim."""
    if inverso:
        return "#e74c3c" if valor > 0 else "#27ae60"
    return "#27ae60" if valor > 0 else "#95a5a6"

def calcular_nps(nps):
    """Calcula o NPS score (-100 a 100)."""
    total = sum(nps.values())
    if total == 0:
        return 0, 0, 0, 0
    promotores = nps.get("otimo", 0)
    detratores = nps.get("pessimo", 0) + nps.get("ruim", 0)
    score = round(((promotores - detratores) / total) * 100)
    return score, total, promotores, detratores


# ─────────────────────────────────────────
# MONTAGEM DO HTML DO E-MAIL
# ─────────────────────────────────────────

def montar_html(relatorio, pendentes):
    now = datetime.now()
    data_formatada = now.strftime("%d/%m/%Y")

    resumo = relatorio.get("resumo", {})
    tempos = relatorio.get("tempos", {})
    status = relatorio.get("status", {})
    agentes_data = relatorio.get("agentes", [])
    nps = relatorio.get("nps", {})

    # ── Linhas de agentes (tabela de performance) ──
    linhas_agentes = ""
    for a in agentes_data:
        resolvidos = a.get("resolvidosHoje", 0)
        vencidos = a.get("vencidos", 0)
        linhas_agentes += f"""
        <tr>
            <td style="padding:14px;border-bottom:1px solid #eee;font-weight:600;color:#333;">{a['nome']}</td>
            <td style="padding:14px;border-bottom:1px solid #eee;color:#00b8a9;font-weight:700;text-align:center;">{resolvidos}</td>
            <td style="padding:14px;border-bottom:1px solid #eee;color:#666;text-align:center;">{a.get('novos',0)}</td>
            <td style="padding:14px;border-bottom:1px solid #eee;color:#666;text-align:center;">{a.get('andamento',0)}</td>
            <td style="padding:14px;border-bottom:1px solid #eee;color:#e67e22;font-weight:700;text-align:center;">{a.get('parados',0)}</td>
            <td style="padding:14px;border-bottom:1px solid #eee;color:#e74c3c;font-weight:700;text-align:center;">{vencidos}</td>
        </tr>"""

    # HTML completo
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Relatório Diário de Chamados</title>
</head>
<body style="margin:0;padding:30px 0;background:#f2f4f6;font-family:'Segoe UI',Arial,sans-serif;">

  <center>
    <table width="680" cellpadding="0" cellspacing="0" style="max-width:680px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 15px rgba(0,0,0,0.05);">
        
      <!-- CABEÇALHO -->
      <tr>
        <td style="background:#ba3b89;padding:35px 20px;text-align:center;">
          <h1 style="margin:0;color:#ffffff;font-size:32px;font-weight:900;letter-spacing:1px;text-transform:uppercase;">
            MUNDO ULTRA - CHAMADOS
          </h1>
        </td>
      </tr>

      <!-- CONTEÚDO -->
      <tr>
        <td style="padding:35px;">
          <p style="margin:0 0 25px;color:#555;font-size:14px;">
            Resumo consolidado da operação em <strong>{data_formatada}</strong>:
          </p>

          <!-- 3 CARDS TOPO -->
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="31%" style="border:1px solid #eaeaea;border-radius:12px;padding:25px 10px;text-align:center;">
                <p style="margin:0;font-size:10px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:1px;">Total Hoje</p>
                <p style="margin:10px 0 0;font-size:34px;font-weight:800;color:#222;">{resumo.get('totalHoje', 0)}</p>
              </td>
              <td width="3.5%"></td>
              <td width="31%" style="border:1px solid #eaeaea;border-radius:12px;padding:25px 10px;text-align:center;">
                <p style="margin:0;font-size:10px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:1px;">Resolvidos Hoje</p>
                <p style="margin:10px 0 0;font-size:34px;font-weight:800;color:#00b8a9;">{resumo.get('resolvidosHoje', 0)}</p>
              </td>
              <td width="3.5%"></td>
              <td width="31%" style="border:1px solid #eaeaea;border-radius:12px;padding:25px 10px;text-align:center;">
                <p style="margin:0;font-size:10px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:1px;">Chamados no Mês</p>
                <p style="margin:10px 0 0;font-size:34px;font-weight:800;color:#ba3b89;">{resumo.get('chamadosNoMes', 0)}</p>
              </td>
            </tr>
          </table>

          <!-- 2 CARDS TEMPOS -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;">
            <tr>
              <td width="48%" style="border:1px solid #eaeaea;border-radius:12px;padding:20px;">
                <p style="margin:0 0 15px;font-size:11px;font-weight:700;color:#333;text-transform:uppercase;letter-spacing:1px;">Tempo de 1ª Resposta</p>
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="color:#666;font-size:13px;padding-bottom:10px;">Hoje:</td>
                    <td style="color:#222;font-size:14px;font-weight:700;text-align:right;padding-bottom:10px;">{tempos.get('tmaRespostaHoje','--')}</td>
                  </tr>
                  <tr>
                    <td style="color:#666;font-size:13px;">No Mês:</td>
                    <td style="color:#222;font-size:14px;font-weight:700;text-align:right;">{tempos.get('tmaRespostaMes','--')}</td>
                  </tr>
                </table>
              </td>
              <td width="4%"></td>
              <td width="48%" style="border:1px solid #eaeaea;border-radius:12px;padding:20px;">
                <p style="margin:0 0 15px;font-size:11px;font-weight:700;color:#333;text-transform:uppercase;letter-spacing:1px;">TMA Solução</p>
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="color:#666;font-size:13px;padding-bottom:10px;">Hoje:</td>
                    <td style="color:#222;font-size:14px;font-weight:700;text-align:right;padding-bottom:10px;">{tempos.get('tmaSolucaoHoje','--')}</td>
                  </tr>
                  <tr>
                    <td style="color:#666;font-size:13px;">No Mês:</td>
                    <td style="color:#222;font-size:14px;font-weight:700;text-align:right;">{tempos.get('tmaSolucaoMes','--')}</td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>

          <!-- 4 CARDS STATUS -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;">
            <tr>
              <td width="23%" style="background:#f9f9fa;border-radius:10px;padding:15px;text-align:center;">
                <p style="margin:0;font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1px;">Novos</p>
                <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:#222;">{status.get('novos', 0)}</p>
              </td>
              <td width="2.6%"></td>
              <td width="23%" style="background:#f9f9fa;border-radius:10px;padding:15px;text-align:center;">
                <p style="margin:0;font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1px;">Andamento</p>
                <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:#222;">{status.get('andamento', 0)}</p>
              </td>
              <td width="2.6%"></td>
              <td width="23%" style="background:#f9f9fa;border-radius:10px;padding:15px;text-align:center;">
                <p style="margin:0;font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1px;">Parados</p>
                <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:#e67e22;">{status.get('parados', 0)}</p>
              </td>
              <td width="2.6%"></td>
              <td width="23%" style="background:#f9f9fa;border-radius:10px;padding:15px;text-align:center;">
                <p style="margin:0;font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1px;">Vencidos</p>
                <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:#e74c3c;">{status.get('vencidos', 0)}</p>
              </td>
            </tr>
          </table>

          <!-- SEÇÃO PERFORMANCE POR AGENTE -->
          <div style="margin-top:40px;margin-bottom:15px;border-left:4px solid #ba3b89;padding-left:10px;">
            <h2 style="margin:0;font-size:14px;font-weight:800;color:#222;text-transform:uppercase;letter-spacing:1px;">Performance por Agente</h2>
          </div>
          
          <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #eaeaea;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="padding:0;">
                <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
                  <tr style="background:#fff;">
                    <th style="padding:16px 14px;text-align:left;color:#888;font-weight:600;border-bottom:1px solid #eee;">Agente</th>
                    <th style="padding:16px 14px;text-align:center;color:#00b8a9;font-weight:600;border-bottom:1px solid #eee;">Resolv.</th>
                    <th style="padding:16px 14px;text-align:center;color:#888;font-weight:600;border-bottom:1px solid #eee;">Novos</th>
                    <th style="padding:16px 14px;text-align:center;color:#888;font-weight:600;border-bottom:1px solid #eee;">Andam.</th>
                    <th style="padding:16px 14px;text-align:center;color:#e67e22;font-weight:600;border-bottom:1px solid #eee;">Parados</th>
                    <th style="padding:16px 14px;text-align:center;color:#e74c3c;font-weight:600;border-bottom:1px solid #eee;">Vencid.</th>
                  </tr>
                  {linhas_agentes}
                </table>
              </td>
            </tr>
          </table>

          <!-- SEÇÃO NPS -->
          <div style="margin-top:40px;margin-bottom:15px;border-left:4px solid #ba3b89;padding-left:10px;">
            <h2 style="margin:0;font-size:14px;font-weight:800;color:#222;text-transform:uppercase;letter-spacing:1px;">Satisfação (NPS)</h2>
          </div>

          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="18%" style="border:1px solid #fadbd8;border-radius:8px;padding:20px 5px;text-align:center;background:#fffcfc;">
                <p style="margin:0;font-size:9px;font-weight:700;color:#e74c3c;text-transform:uppercase;letter-spacing:1px;">Péssimo</p>
                <p style="margin:8px 0;font-size:28px;">😡</p>
                <p style="margin:0;font-size:18px;font-weight:800;color:#222;">{nps.get('pessimo',0)}</p>
              </td>
              <td width="2.5%"></td>
              <td width="18%" style="border:1px solid #fdebd0;border-radius:8px;padding:20px 5px;text-align:center;background:#fffdfa;">
                <p style="margin:0;font-size:9px;font-weight:700;color:#e67e22;text-transform:uppercase;letter-spacing:1px;">Ruim</p>
                <p style="margin:8px 0;font-size:28px;">😕</p>
                <p style="margin:0;font-size:18px;font-weight:800;color:#222;">{nps.get('ruim',0)}</p>
              </td>
              <td width="2.5%"></td>
              <td width="18%" style="border:1px solid #fcf3cf;border-radius:8px;padding:20px 5px;text-align:center;background:#fffefa;">
                <p style="margin:0;font-size:9px;font-weight:700;color:#f1c40f;text-transform:uppercase;letter-spacing:1px;">Regular</p>
                <p style="margin:8px 0;font-size:28px;">😐</p>
                <p style="margin:0;font-size:18px;font-weight:800;color:#222;">{nps.get('regular',0)}</p>
              </td>
              <td width="2.5%"></td>
              <td width="18%" style="border:1px solid #d1f2eb;border-radius:8px;padding:20px 5px;text-align:center;background:#fafdfc;">
                <p style="margin:0;font-size:9px;font-weight:700;color:#00b8a9;text-transform:uppercase;letter-spacing:1px;">Bom</p>
                <p style="margin:8px 0;font-size:28px;">😊</p>
                <p style="margin:0;font-size:18px;font-weight:800;color:#222;">{nps.get('bom',0)}</p>
              </td>
              <td width="2.5%"></td>
              <td width="18%" style="border:1px solid #d5f5e3;border-radius:8px;padding:20px 5px;text-align:center;background:#fbfffc;">
                <p style="margin:0;font-size:9px;font-weight:700;color:#27ae60;text-transform:uppercase;letter-spacing:1px;">Ótimo</p>
                <p style="margin:8px 0;font-size:28px;">🤩</p>
                <p style="margin:0;font-size:18px;font-weight:800;color:#222;">{nps.get('otimo',0)}</p>
              </td>
            </tr>
          </table>

        </td>
      </tr>

      <!-- RODAPÉ -->
      <tr>
        <td style="background:#f2f4f6;padding:25px;text-align:center;">
          <p style="margin:0;color:#bbb;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;">
            MUNDO ULTRA &copy; 2026 &bull; INTELIGÊNCIA DE DADOS
          </p>
        </td>
      </tr>
    </table>
  </center>
</body>
</html>"""
    return html


# ─────────────────────────────────────────
# ENVIO DO E-MAIL
# ─────────────────────────────────────────

def enviar_email(html):
    now = datetime.now()
    assunto = f"📊 Relatório de Chamados — {now.strftime('%d/%m/%Y')}"

    destinatarios = _carregar_destinatarios()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_CONFIG["remetente"]
    msg["To"] = ", ".join(destinatarios)

    # Configurando o HTML com codificação UTF-8 explícita
    html_part = MIMEText(html, "html", "utf-8")
    msg.attach(html_part)

    try:
        server = smtplib.SMTP(EMAIL_CONFIG["smtp_host"], EMAIL_CONFIG["smtp_port"])
        server.ehlo()
        server.starttls()
        server.login(EMAIL_CONFIG["remetente"], EMAIL_CONFIG["senha_app"])
        server.sendmail(
            EMAIL_CONFIG["remetente"],
            destinatarios,
            msg.as_string()
        )
        server.quit()
        print(f"✅ E-mail enviado com sucesso para: {', '.join(destinatarios)}")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
        raise


# ─────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🔄 Coletando dados do Movidesk...")

    relatorio = extrair_relatorio()
    if not relatorio:
        print("❌ Falha ao coletar relatório. Abortando.")
        sys.exit(1)

    pendentes_raw = buscar_chamados_pendentes_por_agente()
    pendentes = [{"Agente": p["agente"], "TotalPendentes": p["totalPendentes"]} for p in pendentes_raw]

    print("📧 Montando e-mail...")
    html = montar_html(relatorio, pendentes)

    print("📤 Enviando e-mail...")
    enviar_email(html)
