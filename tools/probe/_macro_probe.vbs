Option Explicit
Dim sw, r, err
Set sw = GetObject(, "SldWorks.Application")
If sw Is Nothing Then
    WScript.Echo "ATTACH FAILED"
    WScript.Quit 1
End If
WScript.Echo "attached, rev=" & sw.RevisionNumber()

err = 0
On Error Resume Next
r = sw.RunMacro2( CreateObject("WScript.Shell").ExpandEnvironmentStrings("%TEMP%") & "\SWAI_probe_min.bas", "Module1", "main", 1, err )
If Err.Number <> 0 Then
    WScript.Echo "RunMacro2 THREW: 0x" & Hex(Err.Number) & " " & Err.Description
Else
    WScript.Echo "RunMacro2 returned=" & r & " err=" & err
End If
On Error Goto 0
