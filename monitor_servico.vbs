Set oShell = CreateObject("WScript.Shell")
Set oFSO   = CreateObject("Scripting.FileSystemObject")

Dim sProjeto
sProjeto = "c:\Users\RafaelZahner\Desktop\Projeto_Chamados_Email"

' Caminho dos logs de início
Dim sLog
sLog = sProjeto & "\servico_log.txt"

Do While True
    Dim oLog
    Set oLog = oFSO.OpenTextFile(sLog, 8, True)   ' 8 = append
    oLog.WriteLine Now() & " — Iniciando servidor_monitor.py..."
    oLog.Close

    ' Roda o servidor (fica bloqueado enquanto ele estiver de pé)
    Dim oExec
    Set oExec = oShell.Exec("py " & sProjeto & "\servidor_monitor.py")

    ' Aguarda o processo terminar
    Do While oExec.Status = 0
        WScript.Sleep 5000
    Loop

    Dim oLog2
    Set oLog2 = oFSO.OpenTextFile(sLog, 8, True)
    oLog2.WriteLine Now() & " — Processo encerrado (código " & oExec.ExitCode & "). Reiniciando em 5s..."
    oLog2.Close

    WScript.Sleep 5000
Loop
