$ErrorActionPreference = 'Continue'
Write-Output '=== Security registry values ==='
$sec = Get-ItemProperty 'HKCU:\Software\SolidWorks\SOLIDWORKS 2022\Security' -ErrorAction SilentlyContinue
if ($sec) { $sec | Format-List * } else { Write-Output 'no Security key values' }

# minimal test macro
$testBas = "$env:TEMP\SWAI_probe_min.bas"
@'
Attribute VB_Name = "Module1"
Sub main()
    ' minimal probe - do nothing
End Sub
'@ | Set-Content -Path $testBas -Encoding Default
Write-Output ("test bas written: " + $testBas + " (" + (Get-Item $testBas).Length + " bytes)")

Write-Output '=== attach to running SW ==='
$sw = [Runtime.InteropServices.Marshal]::GetActiveObject('SldWorks.Application')
Write-Output ("attached: " + $sw.RevisionNumber())

Write-Output '=== RunMacro2 minimal test ==='
$err = 0
try {
    $r = $sw.RunMacro2($testBas, "Module1", "main", 1, [ref]$err)
    Write-Output ("RunMacro2 returned: " + $r + "  error code: " + $err)
} catch {
    Write-Output ("RunMacro2 THREW: " + $_.Exception.Message)
}
