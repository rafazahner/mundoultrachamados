"""
Monitor + Agendador — processo único, roda 24h.

Inicia o servidor web na porta 8080 E o agendador de e-mails na mesma execução.
Disparo automático todo dia às 23:50 (horário local).

Para iniciar:
    py servidor_monitor.py

Acesse o monitor em: http://localhost:8080
"""

import http.server
import socketserver
import os
import sys
import json
import threading
import time
import subprocess
from datetime import datetime

# ── Configurações ─────────────────────────────────────────────────────────────

PORT         = 8085
HORARIO      = "23:50"          # << Horário do disparo diário
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
EMAIL_SCRIPT = os.path.join(SCRIPT_DIR, "email_report.py")
STATUS_FILE  = os.path.join(SCRIPT_DIR, "status.json")
TRIGGER_FILE = os.path.join(SCRIPT_DIR, "trigger_envio.flag")


# ── Helpers de status ─────────────────────────────────────────────────────────

_status_lock = threading.Lock()

def ler_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"logs": [], "ultimo_envio": None, "proximo_envio": HORARIO, "agendador_ativo": False}


def salvar_status(data):
    with _status_lock:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def adicionar_log(data, tipo, mensagem):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["logs"].append({"tipo": tipo, "timestamp": ts, "mensagem": mensagem})
    if len(data["logs"]) > 100:
        data["logs"] = data["logs"][-100:]


# ── Envio do relatório ────────────────────────────────────────────────────────

def rodar_relatorio():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{ts}] 🚀 Iniciando coleta e envio do relatório...")

    data = ler_status()
    data["agendador_ativo"] = True
    adicionar_log(data, "inicio", "Iniciando processo de envio de e-mail")
    salvar_status(data)

    sucesso   = False
    erro_msg  = ""

    try:
        resultado = subprocess.run(
            [sys.executable, EMAIL_SCRIPT],
            capture_output=True,
            text=True,
            timeout=300
        )
        if resultado.returncode == 0:
            sucesso = True
            print(resultado.stdout)
            adicionar_log(data, "sucesso", "E-mail enviado com sucesso!")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ E-mail enviado!")
        else:
            erro_msg = resultado.stderr or "Erro desconhecido"
            adicionar_log(data, "erro", f"Falha no envio: {erro_msg[:200]}")
            print(f"❌ Erro:\n{erro_msg}")

    except subprocess.TimeoutExpired:
        erro_msg = "Timeout: o script demorou mais de 5 minutos."
        adicionar_log(data, "erro", erro_msg)
        print(f"❌ {erro_msg}")
    except Exception as e:
        erro_msg = str(e)
        adicionar_log(data, "erro", f"Erro inesperado: {erro_msg}")
        print(f"❌ Erro inesperado: {e}")

    fim_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    adicionar_log(data, "fim", f"Processo encerrado em {fim_ts}")
    data["ultimo_envio"] = {
        "sucesso": sucesso,
        "timestamp": fim_ts,
        "erro": erro_msg if not sucesso else None,
    }
    data["agendador_ativo"] = True
    salvar_status(data)


# ── Loop do agendador (roda em thread separada) ───────────────────────────────

def loop_agendador():
    """
    Verifica a hora atual a cada 30 segundos.
    Dispara o e-mail quando o horário bate com HORARIO (HH:MM).
    Também verifica o arquivo de trigger manual a cada 10 s.
    """
    hora_alvo, minuto_alvo = map(int, HORARIO.split(":"))
    ultimo_disparo_dia = -1   # evita disparar mais de uma vez por dia

    print(f"⏰ Agendador interno iniciado — disparo todo dia às {HORARIO}h")

    tick = 0
    while True:
        agora = datetime.now()

        # ── Verifica trigger manual (botão "Forçar Envio") ──
        if tick % 10 == 0:
            if os.path.exists(TRIGGER_FILE):
                try:
                    os.remove(TRIGGER_FILE)
                except Exception:
                    pass
                print(f"\n[{agora.strftime('%H:%M:%S')}] 🔁 Envio forçado via monitor web!")
                threading.Thread(target=rodar_relatorio, daemon=True).start()

        # ── Verifica horário agendado ──
        if (agora.hour == hora_alvo and
                agora.minute == minuto_alvo and
                agora.day != ultimo_disparo_dia):
            ultimo_disparo_dia = agora.day
            print(f"\n[{agora.strftime('%H:%M:%S')}] ⏰ Horário de disparo atingido!")
            threading.Thread(target=rodar_relatorio, daemon=True).start()

        tick += 1
        time.sleep(1)


# ── Servidor HTTP ─────────────────────────────────────────────────────────────

class MonitorHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SCRIPT_DIR, **kwargs)

    # ── helpers ──

    def _dest_path(self):
        return os.path.join(SCRIPT_DIR, "destinatarios.json")

    def _ler_destinatarios(self):
        try:
            with open(self._dest_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _salvar_destinatarios(self, lista):
        with open(self._dest_path(), "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=2)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json_ok(self, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _text_ok(self, msg=b"OK"):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self._cors()
        self.end_headers()
        self.wfile.write(msg if isinstance(msg, bytes) else msg.encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)

    # ── métodos HTTP ──

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", ""):
            self.path = "/monitor.html"
            return super().do_GET()

        if self.path.startswith("/destinatarios"):
            return self._json_ok(self._ler_destinatarios())

        super().do_GET()

    def do_POST(self):
        # Limpar histórico
        if self.path.startswith("/limpar_logs"):
            try:
                data = ler_status()
                data["logs"] = []
                data["ultimo_envio"] = None
                salvar_status(data)
                self._text_ok()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
            return

        # Forçar envio agora
        if self.path.startswith("/trigger_envio"):
            try:
                with open(TRIGGER_FILE, "w") as f:
                    f.write("trigger")
                self._text_ok()
            except Exception as e:
                self.send_response(500)
                self._cors()
                self.end_headers()
                self.wfile.write(str(e).encode())
            return

        # Adicionar destinatário
        if self.path.startswith("/destinatarios"):
            try:
                payload = json.loads(self._read_body())
                email = payload.get("email", "").strip().lower()
                if not email or "@" not in email:
                    raise ValueError("e-mail inválido")
                lista = self._ler_destinatarios()
                if email not in lista:
                    lista.append(email)
                    self._salvar_destinatarios(lista)
                self._json_ok(lista)
            except Exception as e:
                self.send_response(400)
                self._cors()
                self.end_headers()
                self.wfile.write(str(e).encode())
            return

        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        if self.path.startswith("/destinatarios"):
            try:
                payload = json.loads(self._read_body())
                email = payload.get("email", "").strip().lower()
                lista = [e for e in self._ler_destinatarios() if e != email]
                self._salvar_destinatarios(lista)
                self._json_ok(lista)
            except Exception as e:
                self.send_response(400)
                self._cors()
                self.end_headers()
                self.wfile.write(str(e).encode())
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # silencia logs de acesso


# ── Inicialização ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Marca agendador como ativo no status.json
    data = ler_status()
    data["agendador_ativo"] = True
    data["proximo_envio"] = HORARIO
    adicionar_log(data, "info", f"Sistema iniciado — disparo agendado para {HORARIO}h")
    salvar_status(data)

    # Inicia o agendador em thread daemon (encerra junto com o processo principal)
    t = threading.Thread(target=loop_agendador, daemon=True)
    t.start()

    # Inicia o servidor HTTP
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MonitorHandler) as httpd:
        print(f"\n✅ Monitor + Agendador rodando em: http://localhost:{PORT}")
        print(f"   Disparo automático todo dia às {HORARIO}h")
        print(f"   Pressione Ctrl+C para encerrar.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

    # Ao encerrar, marca como inativo
    data = ler_status()
    data["agendador_ativo"] = False
    adicionar_log(data, "info", "Sistema encerrado pelo usuário.")
    salvar_status(data)
    print("\n👋 Sistema encerrado.")
