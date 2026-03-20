<?php
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

if (php_sapi_name() !== "cli" && $_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(404);
    exit;
}

$status_file = __DIR__ . '/status.json';

function add_log($tipo, $msg) {
    global $status_file;
    $data = file_exists($status_file) ? json_decode(file_get_contents($status_file), true) : ["logs" => []];
    $data["logs"][] = ["tipo" => $tipo, "timestamp" => date("Y-m-d H:i:s"), "mensagem" => $msg];
    if (count($data["logs"]) > 100) $data["logs"] = array_slice($data["logs"], -100);
    file_put_contents($status_file, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
}

add_log("inicio", "Iniciando processo de envio de e-mail");

ob_start();
try {
    $_GET['run'] = 1;
    require_once 'email_report.php';
    $output = ob_get_clean();
    $sucesso = strpos($output, 'sucesso') !== false;
    
    add_log("sucesso", "E-mail enviado com sucesso!");
    add_log("fim", "Processo encerrado em " . date("Y-m-d H:i:s"));
    
    $data = json_decode(file_get_contents($status_file), true);
    $data['ultimo_envio'] = [
        "sucesso" => $sucesso,
        "timestamp" => date("Y-m-d H:i:s"),
        "erro" => null
    ];
    file_put_contents($status_file, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    
    echo "OK";
} catch (Exception $e) {
    ob_end_clean();
    add_log("erro", "Erro: " . $e->getMessage());
    $data = json_decode(file_get_contents($status_file), true);
    $data['ultimo_envio'] = ["sucesso" => false, "timestamp" => date("Y-m-d H:i:s"), "erro" => $e->getMessage()];
    file_put_contents($status_file, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    
    http_response_code(500);
    echo "Error";
}
?>
