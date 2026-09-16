Option Explicit
Dim sw, Part, fm, r
Set sw = GetObject(, "SldWorks.Application")
Set Part = sw.NewPart()
Set fm = Part.FeatureManager

WScript.Echo "--- 12-arg call ---"
On Error Resume Next
r = fm.FeatureRevolve(True, False, False, False, False, 0, 0, 6.283, 0, False, False, False)
If Err.Number <> 0 Then
    WScript.Echo "12-arg: ERROR " & Err.Number & " " & Err.Description
    Err.Clear
Else
    WScript.Echo "12-arg: accepted, result=" & TypeName(r)
End If
On Error Goto 0

WScript.Echo "--- 8-arg call ---"
On Error Resume Next
r = fm.FeatureRevolve(6.283, False, 0, 1, 0, False, True, True)
If Err.Number <> 0 Then
    WScript.Echo "8-arg: ERROR " & Err.Number & " " & Err.Description
    Err.Clear
Else
    WScript.Echo "8-arg: accepted, result=" & TypeName(r)
End If
On Error Goto 0

Part.Visible = False
WScript.Echo "PROBE_DONE"
