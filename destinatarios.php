<?php
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') exit;

$path = __DIR__ . '/destinatarios.json';
$lista = file_exists($path) ? json_decode(file_get_contents($path), true) : ["rafael.zahner@ultraacademia.com.br"];
if (!is_array($lista)) $lista = [];

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    echo json_encode($lista);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
$email = isset($input['email']) ? strtolower(trim($input['email'])) : '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!$email || !strpos($email, '@')) {
        http_response_code(400); echo "E-mail invalido"; exit;
    }
    if (!in_array($email, $lista)) {
        $lista[] = $email;
        file_put_contents($path, json_encode(array_values($lista), JSON_PRETTY_PRINT));
    }
    echo json_encode($lista);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'DELETE') {
    $lista = array_filter($lista, function($e) use ($email) { return $e !== $email; });
    file_put_contents($path, json_encode(array_values($lista), JSON_PRETTY_PRINT));
    echo json_encode(array_values($lista));
    exit;
}

http_response_code(404);
?>
