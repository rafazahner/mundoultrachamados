<?php
require_once 'rotina.php';

$EMAIL_CONFIG = [
    "remetente" => "alfred.ultraacademia@gmail.com",
    "senha_app" => "binwgydtuswokcdh",
    "smtp_host" => "ssl://smtp.gmail.com",
    "smtp_port" => 465
];

function _carregar_destinatarios() {
    $path = __DIR__ . '/destinatarios.json';
    try {
        if (file_exists($path)) {
            $data = json_decode(file_get_contents($path), true);
            if (is_array($data)) return $data;
        }
    } catch (Exception $e) {}
    return ["rafael.zahner@ultraacademia.com.br"];
}

function badge($valor, $cor) {
    return "<span style=\"background:{$cor};color:#fff;padding:2px 10px;border-radius:20px;font-weight:700;font-size:13px;\">{$valor}</span>";
}

function cor_status($valor, $inverso = false) {
    if ($inverso) return $valor > 0 ? "#e74c3c" : "#27ae60";
    return $valor > 0 ? "#27ae60" : "#95a5a6";
}

function calcular_nps($nps) {
    $total = array_sum($nps);
    if ($total == 0) return [0, 0, 0, 0];
    $promotores = $nps['otimo'];
    $detratores = $nps['pessimo'] + $nps['ruim'];
    $score = round((($promotores - $detratores) / $total) * 100);
    return [$score, $total, $promotores, $detratores];
}

function montar_html($relatorio, $pendentes) {
    $resumo = $relatorio['resumo'];
    $tempos = $relatorio['tempos'];
    $status = $relatorio['status'];
    $nps = $relatorio['nps'];

    list($nps_score, $nps_total) = calcular_nps($nps);
    $nps_cor = $nps_score >= 75 ? "#27ae60" : ($nps_score >= 50 ? "#f1c40f" : "#e74c3c");

    $linhas_agentes = "";
    foreach ($relatorio['agentes'] as $a) {
        $linhas_agentes .= "
        <tr>
            <td style=\"padding:16px 14px;border-bottom:1px solid #f5f5f5;\">
                <span style=\"font-weight:700;color:#333;\">{$a['nome']}</span>
            </td>
            <td style=\"padding:16px 14px;text-align:center;border-bottom:1px solid #f5f5f5;\">" . badge($a['resolvidosHoje'], '#00b8a9') . "</td>
            <td style=\"padding:16px 14px;text-align:center;border-bottom:1px solid #f5f5f5;\">" . badge($a['novos'], cor_status($a['novos'], true)) . "</td>
            <td style=\"padding:16px 14px;text-align:center;border-bottom:1px solid #f5f5f5;\">" . badge($a['andamento'], '#3498db') . "</td>
            <td style=\"padding:16px 14px;text-align:center;border-bottom:1px solid #f5f5f5;\">" . badge($a['parados'], '#e67e22') . "</td>
            <td style=\"padding:16px 14px;text-align:center;border-bottom:1px solid #f5f5f5;\">" . badge($a['vencidos'], cor_status($a['vencidos'], true)) . "</td>
        </tr>";
    }

    $now = date('d/m/Y');
    
    $html = <<<HTML
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:25px 0;background:#f4f7f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <div style="max-width:700px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.05);">
    
    <!-- HEADER -->
    <div style="background:linear-gradient(135deg, #102a43 0%, #1a3a5a 100%);padding:40px 30px;text-align:center;">
      <h1 style="margin:0;color:#fff;font-size:26px;font-weight:800;letter-spacing:1px;">Resumo Diário Ultra</h1>
      <p style="margin:10px 0 0;color:#8fabbc;font-size:14px;font-weight:600;text-transform:uppercase;letter-spacing:2px;">{$now}</p>
    </div>

    <!-- BODY -->
    <div style="padding:35px 30px;">
      
      <!-- DESEMPENHO SQUAD -->
      <div style="margin-bottom:15px;border-left:4px solid #ba3b89;padding-left:10px;">
        <h2 style="margin:0;font-size:14px;font-weight:800;color:#222;text-transform:uppercase;letter-spacing:1px;">Desempenho da Squad</h2>
      </div>

      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <!-- RESUMO GERAL -->
          <td width="48%" style="border:1px solid #eaeaea;border-radius:12px;padding:20px;">
            <p style="margin:0 0 15px;font-size:11px;font-weight:700;color:#333;text-transform:uppercase;letter-spacing:1px;">Geral</p>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="color:#666;font-size:13px;padding-bottom:10px;">Abertos Hoje:</td>
                <td style="color:#222;font-size:14px;font-weight:700;text-align:right;padding-bottom:10px;">{$resumo['totalHoje']}</td>
              </tr>
              <tr>
                <td style="color:#666;font-size:13px;padding-bottom:10px;">Resolvidos Hoje:</td>
                <td style="color:#00b8a9;font-size:14px;font-weight:700;text-align:right;padding-bottom:10px;">{$resumo['resolvidosHoje']}</td>
              </tr>
            </table>
          </td>
          <td width="4%"></td>
          <!-- TMA SOLUÇÃO -->
          <td width="48%" style="border:1px solid #eaeaea;border-radius:12px;padding:20px;">
            <p style="margin:0 0 15px;font-size:11px;font-weight:700;color:#333;text-transform:uppercase;letter-spacing:1px;">TMA Solução</p>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="color:#666;font-size:13px;padding-bottom:10px;">Hoje:</td>
                <td style="color:#222;font-size:14px;font-weight:700;text-align:right;padding-bottom:10px;">{$tempos['tmaSolucaoHoje']}</td>
              </tr>
              <tr>
                <td style="color:#666;font-size:13px;">No Mês:</td>
                <td style="color:#222;font-size:14px;font-weight:700;text-align:right;">{$tempos['tmaSolucaoMes']}</td>
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
            <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:#222;">{$status['novos']}</p>
          </td>
          <td width="2.6%"></td>
          <td width="23%" style="background:#f9f9fa;border-radius:10px;padding:15px;text-align:center;">
            <p style="margin:0;font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1px;">Andamento</p>
            <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:#222;">{$status['andamento']}</p>
          </td>
          <td width="2.6%"></td>
          <td width="23%" style="background:#f9f9fa;border-radius:10px;padding:15px;text-align:center;">
            <p style="margin:0;font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1px;">Parados</p>
            <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:#e67e22;">{$status['parados']}</p>
          </td>
          <td width="2.6%"></td>
          <td width="23%" style="background:#f9f9fa;border-radius:10px;padding:15px;text-align:center;">
            <p style="margin:0;font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1px;">Vencidos</p>
            <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:#e74c3c;">{$status['vencidos']}</p>
          </td>
        </tr>
      </table>

      <!-- PERFORMANCE -->
      <div style="margin-top:40px;margin-bottom:15px;border-left:4px solid #ba3b89;padding-left:10px;">
        <h2 style="margin:0;font-size:14px;font-weight:800;color:#222;text-transform:uppercase;letter-spacing:1px;">Performance por Agente</h2>
      </div>
      <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #eaeaea;border-radius:12px;overflow:hidden;">
        <tr><td style="padding:0;">
          <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
            <tr style="background:#fff;">
              <th style="padding:16px 14px;text-align:left;color:#888;font-weight:600;border-bottom:1px solid #eee;">Agente</th>
              <th style="padding:16px 14px;text-align:center;color:#00b8a9;font-weight:600;border-bottom:1px solid #eee;">Resolv.</th>
              <th style="padding:16px 14px;text-align:center;color:#888;font-weight:600;border-bottom:1px solid #eee;">Novos</th>
              <th style="padding:16px 14px;text-align:center;color:#888;font-weight:600;border-bottom:1px solid #eee;">Andam.</th>
              <th style="padding:16px 14px;text-align:center;color:#e67e22;font-weight:600;border-bottom:1px solid #eee;">Parados</th>
              <th style="padding:16px 14px;text-align:center;color:#e74c3c;font-weight:600;border-bottom:1px solid #eee;">Vencid.</th>
            </tr>
            {$linhas_agentes}
          </table>
        </td></tr>
      </table>

      <!-- NPS -->
      <div style="margin-top:40px;margin-bottom:15px;border-left:4px solid #ba3b89;padding-left:10px;">
        <h2 style="margin:0;font-size:14px;font-weight:800;color:#222;text-transform:uppercase;letter-spacing:1px;">Satisfação (NPS) - {$nps_total} Avals</h2>
      </div>
      <div style="text-align:center;background:#f9f9fa;padding:15px;border-radius:10px;">
        <span style="font-size:16px;font-weight:800;color:{$nps_cor};">✓ Score: {$nps_score}</span>
      </div>

    </div>
  </div>
</body>
</html>
HTML;
    return $html;
}

function send_smtp_email($to_list, $subject, $body) {
    global $EMAIL_CONFIG;
    
    $sock = fsockopen($EMAIL_CONFIG['smtp_host'], $EMAIL_CONFIG['smtp_port'], $errno, $errstr, 30);
    if (!$sock) throw new Exception("Falha ao conectar via SMTP: $errstr");
    
    stream_set_timeout($sock, 10);
    $res = fgets($sock, 515);
    
    function send_cmd($sock, $cmd, $expect) {
        fputs($sock, $cmd . "\r\n");
        $res = fgets($sock, 515);
        if (substr($res, 0, 3) != $expect) {
            throw new Exception("Erro SMTP: " . $res);
        }
        return $res;
    }
    
    send_cmd($sock, "EHLO localhost", "250");
    send_cmd($sock, "AUTH LOGIN", "334");
    send_cmd($sock, base64_encode($EMAIL_CONFIG['remetente']), "334");
    send_cmd($sock, base64_encode($EMAIL_CONFIG['senha_app']), "235");
    send_cmd($sock, "MAIL FROM: <" . $EMAIL_CONFIG['remetente'] . ">", "250");
    
    foreach ($to_list as $to) {
        send_cmd($sock, "RCPT TO: <$to>", "250");
    }
    
    send_cmd($sock, "DATA", "354");
    
    $headers = [
        "MIME-Version: 1.0",
        "Content-type: text/html; charset=UTF-8",
        "From: " . $EMAIL_CONFIG['remetente'],
        "To: " . implode(", ", $to_list),
        "Subject: =?UTF-8?B?" . base64_encode($subject) . "?="
    ];
    
    $data = implode("\r\n", $headers) . "\r\n\r\n" . $body . "\r\n.";
    send_cmd($sock, $data, "250");
    fputs($sock, "QUIT\r\n");
    fclose($sock);
}

if (php_sapi_name() == "cli" || isset($_GET['run'])) {
    echo "🔄 Coletando dados do Movidesk...\n";
    $relatorio = extrair_relatorio();
    if (!$relatorio) die("❌ Falha ao coletar relatório.");

    $pendentes_raw = buscar_chamados_pendentes_por_agente();
    $pendentes = [];
    foreach ($pendentes_raw as $p) {
        $pendentes[] = ["Agente" => $p["agente"], "TotalPendentes" => $p["totalPendentes"]];
    }

    echo "📧 Montando e-mail...\n";
    $html = montar_html($relatorio, $pendentes);

    $destinatarios = _carregar_destinatarios();
    $assunto = "📊 Relatório de Chamados — " . date('d/m/Y');
    
    echo "📤 Enviando e-mail...\n";
    try {
        send_smtp_email($destinatarios, $assunto, $html);
        echo "✅ E-mail enviado com sucesso!\n";
    } catch (Exception $e) {
        die("❌ Erro ao enviar SMTP: " . $e->getMessage());
    }
}
?>
