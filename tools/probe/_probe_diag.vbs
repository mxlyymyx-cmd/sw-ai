' Probe5: diagnose GetBodies2 / GetBodyBox call forms
Option Explicit

Dim swApp, Part, skMgr, featMgr, feat0, topPlane, extFeat
Dim bodies, b, box, idx, msg

On Error Resume Next

Set swApp = GetObject(, "SldWorks.Application")
Set Part = swApp.NewPart()
Set skMgr = Part.SketchManager
Set featMgr = Part.FeatureManager

Set feat0 = Part.FirstFeature
Set topPlane = Nothing
idx = 0
Do While Not feat0 Is Nothing
    If feat0.GetTypeName2 = "RefPlane" Then
        idx = idx + 1
        If idx = 2 Then
            Set topPlane = feat0
            Exit Do
        End If
    End If
    Set feat0 = feat0.GetNextFeature
Loop

topPlane.Select2 False, 0
skMgr.InsertSketch True
Part.CreateLine2 0.03, 0.005, 0, 0.05, 0.005, 0
Part.CreateLine2 0.05, 0.005, 0, 0.05, 0.02, 0
Part.CreateLine2 0.05, 0.02, 0, 0.03, 0.02, 0
Part.CreateLine2 0.03, 0.02, 0, 0.03, 0.005, 0
skMgr.InsertSketch True

Set extFeat = featMgr.FeatureExtrusion3(True, False, False, 0, 0, 0.03, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
If extFeat Is Nothing Then
    WScript.Echo "EXTRUDE_FAIL"
    WScript.Quit 1
End If

Err.Clear
bodies = Part.GetBodies2(0, False)
msg = "GetBodies2: IsArray=" & IsArray(bodies)
If Err.Number <> 0 Then
    msg = msg & " ERR=" & Err.Number
    Err.Clear
End If
WScript.Echo msg

If IsArray(bodies) Then
    WScript.Echo "UBound=" & UBound(bodies)
    WScript.Echo "TypeName(bodies(0))=" & TypeName(bodies(0))
    Set b = bodies(0)
    WScript.Echo "TypeName(b)=" & TypeName(b)

    Err.Clear
    box = b.GetBodyBox
    If Err.Number <> 0 Then
        WScript.Echo "noparen-call ERR=" & Err.Number & " " & Err.Description
        Err.Clear
    Else
        WScript.Echo "noparen OK: X[" & box(0) & "," & box(3) & "] Y[" & box(1) & "," & box(4) & "] Z[" & box(2) & "," & box(5) & "]"
    End If

    Err.Clear
    Dim fc
    fc = b.GetFaceCount
    If Err.Number <> 0 Then
        WScript.Echo "facecount ERR=" & Err.Number & " " & Err.Description
    Else
        WScript.Echo "facecount=" & fc
    End If
End If

WScript.Echo "PROBE5_DONE"
