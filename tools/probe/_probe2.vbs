' SW-2022 API probe: FeatureExtrusion2 / FeatureCircularPattern / InsertProtrusionBlend
' arg-count acceptance test (no valid selections -> calls return Nothing but wrong
' arg counts raise COM error 450/449 'parameter not optional')
Option Explicit
Dim sw, Part, fm, r
Set sw = GetObject(, "SldWorks.Application")
Set Part = sw.NewPart()
Set fm = Part.FeatureManager

Sub Probe(name, code)
    On Error Resume Next
    Err.Clear
    ExecuteGlobal code
    If Err.Number <> 0 Then
        WScript.Echo name & ": ERR " & Err.Number & " " & Err.Description
        Err.Clear
    Else
        WScript.Echo name & ": OK (" & TypeName(r) & ")"
    End If
    On Error Goto 0
End Sub

Probe "Extrusion2(20)", "r = fm.FeatureExtrusion2(True, False, False, 0, 0, 0.01, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)"
Probe "Extrusion2(23)", "r = fm.FeatureExtrusion2(True, False, False, 0, 0, 0.01, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)"
Probe "Extrusion3(23)", "r = fm.FeatureExtrusion3(True, False, False, 0, 0, 0.01, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)"
Probe "CircPattern(4)", "r = fm.FeatureCircularPattern(6, 6.283, False, """")"
Probe "CircPattern(6)", "r = fm.FeatureCircularPattern(6, 6.283, False, False, False, ""Axis1"")"
Probe "CircPattern2(6)", "r = fm.FeatureCircularPattern2(6, 6.283, False, False, False, ""Axis1"")"
Probe "CircPattern3(6)", "r = fm.FeatureCircularPattern3(6, 6.283, False, False, False, Nothing)"
Probe "CircPattern4(6)", "r = fm.FeatureCircularPattern4(6, 6.283, False, False, False, Nothing, False, False, 0, 0)"
Probe "ProtrusionBlend(16)", "r = fm.InsertProtrusionBlend(False, 0, False, True, 0, 0, 0, 0, 0, 0, 0, 0, False, False, False, 0)"
Probe "ProtrusionBlend(17)", "r = fm.InsertProtrusionBlend(False, 0, False, True, 0, 0, 0, 0, 0, 0, 0, 0, False, False, False, 0, False)"
Probe "InsertSurfaceBlend", "r = fm.InsertSurfaceBlend(0, 0, 0.1, 0.1, False, False, True, False, 0, 0, False, 0, 0, False, False, False, False)"
Probe "FeatureThicken", "r = fm.FeatureThicken(0.003, False, 6, True, True, True, False)"
Probe "Thicken2", "r = fm.FeatureThicken2(0.003, False, 6, True, True, True, False, True)"

On Error Resume Next
sw.CloseDoc Part.GetTitle
On Error Goto 0
WScript.Echo "PROBE2_DONE"
