' Probe3: extrude direction via body bounding box (no disk, isolated blade box)
Option Explicit

Dim swApp, Part, skMgr, featMgr, feat0, topPlane, extFeat
Dim bodies, box, i, idx, s

On Error Resume Next

Set swApp = GetObject(, "SldWorks.Application")
If swApp Is Nothing Then
    WScript.Echo "PROBE_FAIL no swApp"
    WScript.Quit 1
End If

For i = 0 To 1
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
    ' sketch rect: u=[0.03,0.05] v=[0.005,0.02]
    Part.CreateLine2 0.03, 0.005, 0, 0.05, 0.005, 0
    Part.CreateLine2 0.05, 0.005, 0, 0.05, 0.02, 0
    Part.CreateLine2 0.05, 0.02, 0, 0.03, 0.02, 0
    Part.CreateLine2 0.03, 0.02, 0, 0.03, 0.005, 0
    skMgr.InsertSketch True

    If i = 0 Then
        Set extFeat = featMgr.FeatureExtrusion3(True, False, False, 0, 0, 0.03, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
        s = "Dir=False"
    Else
        Set extFeat = featMgr.FeatureExtrusion3(True, False, True, 0, 0, 0.03, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
        s = "Dir=True"
    End If
    If extFeat Is Nothing Then
        WScript.Echo s & " EXTRUDE_FAIL err=" & Err.Number
    Else
        Err.Clear
        bodies = Part.GetBodies2(0, False)
        If Err.Number <> 0 Or Not IsArray(bodies) Then
            WScript.Echo s & " GETBODIES_FAIL err=" & Err.Number & " " & Err.Description
        Else
            Err.Clear
            box = bodies(0).GetBodyBox()
            If Err.Number <> 0 Then
                WScript.Echo s & " GETBOX_FAIL err=" & Err.Number & " " & Err.Description
            Else
                WScript.Echo s & " X[" & box(0) & "," & box(3) & "] Y[" & box(1) & "," & box(4) & "] Z[" & box(2) & "," & box(5) & "]"
            End If
        End If
    End If
Next

WScript.Echo "PROBE3_DONE"
