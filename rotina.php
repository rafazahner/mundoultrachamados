<?php
date_default_timezone_set('America/Sao_Paulo');

$CONFIG = [
    "MOVIDESK_TOKEN" => "fb6ad8cd-1026-40b2-8224-f2a8dad2c97d",
    "GOOGLE_SHEET_API" => "https://script.google.com/macros/s/AKfycbwow33xEPcD-y-1bkmgrLjAs7e65S9isuFw7Dw3AyQM1yG6dYC7SiPUNMpi9nRL62IU/exec",
    "AGENTES" => ["Rafael", "Carnaval", "Carol", "Rubens", "Enzo"]
];

function fetch_all_paginated($base_url, $max_pages = 20) {
    $all_records = [];
    $top = 1000;
    $skip = 0;

    for ($i = 0; $i < $max_pages; $i++) {
        $url = $base_url . '&$top=' . $top . '&$skip=' . $skip;
        
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, str_replace(' ', '%20', $url));
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        $response = curl_exec($ch);
        $httpcode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpcode != 200 || !$response) {
            break;
        }

        $batch = json_decode($response, true);
        if (!is_array($batch) || count($batch) == 0) {
            break;
        }

        $all_records = array_merge($all_records, $batch);

        if (count($batch) < $top) {
            break;
        }
        $skip += $top;
    }
    return $all_records;
}

function parse_iso_date($date_str) {
    if (!$date_str) return null;
    try {
        if (str_ends_with($date_str, 'Z')) {
            $date_str = str_replace('Z', '+00:00', $date_str);
        }
        return new DateTime($date_str);
    } catch (Exception $e) {
        return null;
    }
}

function calcular_minutos_uteis($inicio, $fim) {
    if ($inicio >= $fim) return 0;

    $inicio_ajustado = clone $inicio;
    $fim_ajustado = clone $fim;

    if ((int)$inicio_ajustado->format('H') < 9) {
        $inicio_ajustado->setTime(9, 0, 0);
    } elseif ((int)$inicio_ajustado->format('H') >= 18) {
        $inicio_ajustado->modify('+1 day');
        $inicio_ajustado->setTime(9, 0, 0);
    }

    if ((int)$fim_ajustado->format('H') > 18 || ((int)$fim_ajustado->format('H') == 18 && (int)$fim_ajustado->format('i') > 0)) {
        $fim_ajustado->setTime(18, 0, 0);
    } elseif ((int)$fim_ajustado->format('H') < 9) {
        $fim_ajustado->modify('-1 day');
        $fim_ajustado->setTime(18, 0, 0);
    }

    $minutos_uteis = 0;
    $cursor = clone $inicio_ajustado;

    while ($cursor < $fim_ajustado) {
        $dia_semana = (int)$cursor->format('N'); // 1=seg, 7=dom

        if ($dia_semana >= 6) { // Sabado ou Domingo
            $cursor->modify('+1 day');
            $cursor->setTime(9, 0, 0);
            continue;
        }

        $fim_expediente = clone $cursor;
        $fim_expediente->setTime(18, 0, 0);
        $limite_atual = min($fim_ajustado, $fim_expediente);

        if ($cursor > $limite_atual) {
            $cursor->modify('+1 day');
            $cursor->setTime(9, 0, 0);
            continue;
        }

        $minutos_uteis += ($limite_atual->getTimestamp() - $cursor->getTimestamp()) / 60;
        $cursor->modify('+1 day');
        $cursor->setTime(9, 0, 0);
    }

    return $minutos_uteis;
}

function formatar_sla($minutos) {
    $total = round($minutos);
    if ($total < 60) return $total . "m";
    return floor($total / 60) . "h " . str_pad($total % 60, 2, "0", STR_PAD_LEFT) . "m";
}

function media($lista) {
    if (count($lista) == 0) return 0;
    return array_sum($lista) / count($lista);
}

function extrair_relatorio() {
    global $CONFIG;
    $now = new DateTime();
    $year = $now->format('Y');
    $month = $now->format('m');
    $day = $now->format('d');

    $today_start_str = "{$year}-{$month}-{$day}T03:00:00.000Z";
    $month_start_str = "{$year}-{$month}-01T03:00:00.000Z";
    
    $now_utc = clone $now;
    $now_utc->setTimezone(new DateTimeZone('UTC'));
    $iso_now = $now_utc->format('Y-m-d\TH:i:s.000\Z');

    $relatorio = [
        "resumo" => [],
        "tempos" => [],
        "status" => [],
        "agentes" => [],
        "nps" => [
            "pessimo" => 0,
            "ruim" => 0,
            "regular" => 0,
            "bom" => 0,
            "otimo" => 0
        ]
    ];

    $token = $CONFIG["MOVIDESK_TOKEN"];
    $base = "https://api.movidesk.com/public/v1/tickets?token={$token}";

    $chamados_hoje_url = "{$base}&\$select=id&\$filter=createdDate ge {$today_start_str}";
    $chamados_resolvidos_hoje_url = "{$base}&\$select=id&\$filter=(baseStatus eq 'Resolved' or baseStatus eq 'Closed') and resolvedIn ge {$today_start_str}";
    $chamados_mes_url = "{$base}&\$select=id&\$filter=createdDate ge {$month_start_str}";
    
    $novos_url = "{$base}&\$select=id,baseStatus&\$filter=baseStatus eq 'New'";
    $andamento_url = "{$base}&\$select=id,baseStatus&\$filter=baseStatus eq 'InAttendance'";
    $parados_url = "{$base}&\$select=id,baseStatus&\$filter=baseStatus eq 'Stopped'";
    $vencidos_url = "{$base}&\$select=id&\$filter=slaSolutionDate ne null and slaSolutionDate lt {$iso_now} and (baseStatus eq 'New' or baseStatus eq 'InAttendance' or baseStatus eq 'Stopped')";

    $res_hoje = fetch_all_paginated($chamados_hoje_url);
    $res_resolvidos_hoje = fetch_all_paginated($chamados_resolvidos_hoje_url);
    $res_mes = fetch_all_paginated($chamados_mes_url);
    $res_novos = fetch_all_paginated($novos_url);
    $res_andamento = fetch_all_paginated($andamento_url);
    $res_parados = fetch_all_paginated($parados_url);
    $res_vencidos = fetch_all_paginated($vencidos_url);

    $relatorio["resumo"] = [
        "totalHoje" => count($res_hoje),
        "resolvidosHoje" => count($res_resolvidos_hoje),
        "chamadosNoMes" => count($res_mes)
    ];

    $relatorio["status"] = [
        "novos" => count($res_novos),
        "andamento" => count($res_andamento),
        "parados" => count($res_parados),
        "vencidos" => count($res_vencidos)
    ];

    $url_solucao = "{$base}&\$select=id,createdDate,resolvedIn,stoppedTimeWorkingTime,slaRealResponseDate&\$filter=createdDate ge 2026-01-01T00:00:00.000Z and resolvedIn ge {$month_start_str}";
    $data_solucao = fetch_all_paginated($url_solucao);

    $url_respostas = "{$base}&\$select=id,createdDate,slaRealResponseDate&\$filter=createdDate ge {$month_start_str}";
    $data_respostas = fetch_all_paginated($url_respostas);

    $tempos_resp_hoje = [];
    $tempos_resp_mes = [];
    $tempos_sol_hoje = [];
    $tempos_sol_mes = [];

    foreach ($data_respostas as $t) {
        if (empty($t["slaRealResponseDate"])) continue;
        $criacao = parse_iso_date($t["createdDate"]);
        $resposta = parse_iso_date($t["slaRealResponseDate"]);
        if (!$criacao || !$resposta) continue;

        $criacao->modify('-3 hours');
        $resposta->modify('-3 hours');

        $minutos = calcular_minutos_uteis($criacao, $resposta);
        $tempos_resp_mes[] = $minutos;
        if ($t["createdDate"] >= $today_start_str) {
            $tempos_resp_hoje[] = $minutos;
        }
    }

    $hoje_dt = new DateTime("{$year}-{$month}-{$day} 00:00:00");
    foreach ($data_solucao as $t) {
        $criacao = parse_iso_date($t["createdDate"] ?? null);
        $resolucao = parse_iso_date($t["resolvedIn"] ?? null);
        if (!$criacao || !$resolucao) continue;

        $criacao->modify('-3 hours');
        $resolucao->modify('-3 hours');

        $bruto = calcular_minutos_uteis($criacao, $resolucao);
        $parado = isset($t["stoppedTimeWorkingTime"]) ? $t["stoppedTimeWorkingTime"] : 0;
        $liquido = max(0, $bruto - $parado);

        $tempos_sol_mes[] = $liquido;
        if ($resolucao >= $hoje_dt) {
            $tempos_sol_hoje[] = $liquido;
        }
    }

    $relatorio["tempos"] = [
        "tmaRespostaHoje" => formatar_sla(media($tempos_resp_hoje)),
        "tmaRespostaMes" => formatar_sla(media($tempos_resp_mes)),
        "tmaSolucaoHoje" => formatar_sla(media($tempos_sol_hoje)),
        "tmaSolucaoMes" => formatar_sla(media($tempos_sol_mes))
    ];

    $url_pendentes_agente = "{$base}&\$select=id,baseStatus,slaSolutionDate&\$expand=owner(\$select=id,businessName)&\$filter=(baseStatus eq 'New' or baseStatus eq 'InAttendance' or baseStatus eq 'Stopped')";
    $pendentes_com_agente = fetch_all_paginated($url_pendentes_agente);

    foreach ($CONFIG["AGENTES"] as $agente) {
        $tks_agente = array_filter($pendentes_com_agente, function($t) use ($agente) {
            return !empty($t["owner"]) && !empty($t["owner"]["businessName"]) && strpos($t["owner"]["businessName"], $agente) !== false;
        });

        $url_resolv_agente = "{$base}&\$select=id&\$filter=(baseStatus eq 'Resolved' or baseStatus eq 'Closed') and resolvedIn ge {$today_start_str} and contains(owner/businessName, '{$agente}')";
        $resol_agente = fetch_all_paginated($url_resolv_agente);

        $relatorio["agentes"][] = [
            "nome" => $agente,
            "resolvidosHoje" => count($resol_agente),
            "novos" => count(array_filter($tks_agente, fn($t) => $t["baseStatus"] == "New")),
            "andamento" => count(array_filter($tks_agente, fn($t) => $t["baseStatus"] == "InAttendance")),
            "parados" => count(array_filter($tks_agente, fn($t) => $t["baseStatus"] == "Stopped")),
            "vencidos" => count(array_filter($tks_agente, fn($t) => !empty($t["slaSolutionDate"]) && $t["slaSolutionDate"] < $iso_now))
        ];
    }

    try {
        $nps_json = file_get_contents($CONFIG["GOOGLE_SHEET_API"]);
        if ($nps_json) {
            $data = json_decode($nps_json, true);
            if (!empty($data["data"])) {
                foreach ($data["data"] as $item) {
                    if (empty($item["Data"])) continue;
                    $d = parse_iso_date($item["Data"]);
                    if ($d && $d->format('Y-m') == $now->format('Y-m')) {
                        $nota = (int)($item["Nota"] ?? $item["nota"] ?? 0);
                        if ($nota == 1) $relatorio["nps"]["pessimo"]++;
                        if ($nota == 2) $relatorio["nps"]["ruim"]++;
                        if ($nota == 3) $relatorio["nps"]["regular"]++;
                        if ($nota == 4) $relatorio["nps"]["bom"]++;
                        if ($nota == 5) $relatorio["nps"]["otimo"]++;
                    }
                }
            }
        }
    } catch (Exception $e) {}

    return $relatorio;
}

function buscar_chamados_pendentes_por_agente() {
    global $CONFIG;
    $agentes = [
        ["nome" => "Rafael Zahner", "filtro" => "contains(owner/businessName,'Rafael Zahner')"],
        ["nome" => "Enzo Edner", "filtro" => "contains(owner/businessName,'Enzo Edner')"],
        ["nome" => "CAROLINE ARAUJO DA COSTA", "filtro" => "contains(owner/businessName,'CAROLINE ARAUJO DA COSTA')"],
        ["nome" => "Gabriel de Oliveira Carnaval", "filtro" => "contains(owner/businessName,'Gabriel de Oliveira Carnaval')"]
    ];

    $resultados = [];
    $base = "https://api.movidesk.com/public/v1/tickets?token=" . $CONFIG['MOVIDESK_TOKEN'];

    foreach ($agentes as $agente) {
        $url = "{$base}&\$select=id,subject,status,baseStatus,owner&\$filter={$agente['filtro']} " .
               "and baseStatus ne 'Closed' and baseStatus ne 'Resolved' and baseStatus ne 'Canceled' " .
               "and status ne 'Aguardando - retorno do cliente'";
        
        $chamados = fetch_all_paginated($url);
        $resultados[] = [
            "agente" => $agente["nome"],
            "totalPendentes" => count($chamados),
            "chamados" => $chamados
        ];
    }
    return $resultados;
}
?>
