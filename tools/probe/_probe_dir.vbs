' Probe2: extrude direction isolation test (SW2022 via cscript)
' Thin disk y=[0,0.005]; blade extruded from TOP plane depth 0.03.
' Candidate top faces at y=+0.03 (Dir=False forward) or y=-0.03 (reverse).
' Pick points far (>0.025) from any disk face. Control point must be False.
Option Explicit

Dim swApp, Part, skMgr, featMgr, segAxis, revFeat, extFeat
Dim feat0, topPlane, i, r(1)

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

    ' thin annular disk: y=[0,0.005], r=[0.02,0.06]
    skMgr.InsertSketch True
    Part.CreateLine2 0.02, 0, 0, 0.06, 0, 0
    Part.CreateLine2 0.06, 0, 0, 0.06, 0.005, 0
    Part.CreateLine2 0.06, 0.005, 0, 0.02, 0.005, 0
    Part.CreateLine2 0.02, 0.005, 0, 0.02, 0, 0
    Set segAxis = Part.CreateLine2(0, -0.01, 0, 0, 0.015, 0)
    segAxis.ConstructionGeometry = True
    skMgr.InsertSketch True
    Part.ClearSelection2 True
    segAxis.Select2 True, 1
    Set revFeat = featMgr.FeatureRevolve(6.2831853071796, False, 0, 0, 0, True, True, True)
    If revFeat Is Nothing Then
        WScript.Echo "REVOLVE_FAIL"
        WScript.Quit 1
    End If

    ' TOP plane = 2nd RefPlane
    Set feat0 = Part.FirstFeature
    Set topPlane = Nothing
    Dim idx
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

    If i = 0 Then
        Set extFeat = featMgr.FeatureExtrusion3(True, False, False, 0, 0, 0.03, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
        WScript.Echo "--- Dir=False ---"
    Else
        Set extFeat = featMgr.FeatureExtrusion3(True, False, True, 0, 0, 0.03, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
        WScript.Echo "--- Dir=True ---"
    End If
    If extFeat Is Nothing Then
        WScript.Echo "EXTRUDE_FAIL(i=" & i & ") err=" & Err.Number
    Else
        WScript.Echo "EXTRUDE_OK(i=" & i & ")"
    End If

    Dim b(4)
    Part.ClearSelection2 True
    b(0) = Part.Extension.SelectByID2("", "FACE", 0.04, 0.03, 0.0125, False, 0, Nothing, 0)
    Part.ClearSelection2 True
    b(1) = Part.Extension.SelectByID2("", "FACE", 0.04, 0.03, -0.0125, False, 0, Nothing, 0)
    Part.ClearSelection2 True
    b(2) = Part.Extension.SelectByID2("", "FACE", 0.04, -0.03, 0.0125, False, 0, Nothing, 0)
    Part.ClearSelection2 True
    b(3) = Part.Extension.SelectByID2("", "FACE", 0.04, -0.03, -0.0125, False, 0, Nothing, 0)
    Part.ClearSelection2 True
    b(4) = Part.Extension.SelectByID2("", "FACE", 0.04, 0.09, 0.0125, False, 0, Nothing, 0)
    Part.ClearSelection2 True
    WScript.Echo "pick +Y+Z=" & b(0) & " +Y-Z=" & b(1) & " -Y+Z=" & b(2) & " -Y-Z=" & b(3) & " CONTROL(y=0.09)=" & b(4)
Next

WScript.Echo "PROBE2_DONE"
