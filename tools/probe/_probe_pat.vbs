' Probe: circular pattern recipe + extrude direction + face pick (SW2022 via cscript)
' 1. annular disk revolve (8-param, construction axis, mark=1)  [flange recipe]
' 2. square blade on TOP plane (2nd RefPlane) extruded blind, detect +Y vs -Y
' 3. select blade feature mark=1 + cylindrical face mark=4
' 4. FeatureCircularPattern3(6, 2pi, False, "NULL", False, True) -> fallbacks
Option Explicit

Dim swApp, Part, skMgr, featMgr, segAxis, revFeat, extFeat
Dim feat0, topPlane, lastFeat, f, idx
Dim bUp1, bUp2, bDn1, bDn2, bf, pat3, pat4, pat5

On Error Resume Next

Set swApp = GetObject(, "SldWorks.Application")
If swApp Is Nothing Then
    WScript.Echo "PROBE_FAIL no swApp"
    WScript.Quit 1
End If

Set Part = swApp.NewPart()
If Part Is Nothing Then
    WScript.Echo "PROBE_FAIL NewPart"
    WScript.Quit 1
End If
Set skMgr = Part.SketchManager
Set featMgr = Part.FeatureManager

' === 1. annular disk revolve ===
skMgr.InsertSketch True
Part.CreateLine2 0.02, 0, 0, 0.06, 0, 0
Part.CreateLine2 0.06, 0, 0, 0.06, 0.03, 0
Part.CreateLine2 0.06, 0.03, 0, 0.02, 0.03, 0
Part.CreateLine2 0.02, 0.03, 0, 0.02, 0, 0
Set segAxis = Part.CreateLine2(0, -0.01, 0, 0, 0.04, 0)
segAxis.ConstructionGeometry = True
skMgr.InsertSketch True
Part.ClearSelection2 True
segAxis.Select2 True, 1
Set revFeat = featMgr.FeatureRevolve(6.2831853071796, False, 0, 0, 0, True, True, True)
If revFeat Is Nothing Then
    WScript.Echo "REVOLVE_FAIL"
    WScript.Quit 1
Else
    WScript.Echo "REVOLVE_OK"
End If

' === 2. blade square on TOP plane (2nd RefPlane) ===
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
If topPlane Is Nothing Then
    WScript.Echo "NO_TOP_PLANE"
    WScript.Quit 1
End If
WScript.Echo "TOP_PLANE_OK"

topPlane.Select2 False, 0
skMgr.InsertSketch True
Part.CreateLine2 0.025, 0.005, 0, 0.045, 0.005, 0
Part.CreateLine2 0.045, 0.005, 0, 0.045, 0.025, 0
Part.CreateLine2 0.045, 0.025, 0, 0.025, 0.025, 0
Part.CreateLine2 0.025, 0.025, 0, 0.025, 0.005, 0
skMgr.InsertSketch True

Err.Clear
Set extFeat = featMgr.FeatureExtrusion3(True, False, False, 0, 0, 0.04, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
If extFeat Is Nothing Then
    WScript.Echo "EXTRUDE_FAIL err=" & Err.Number & " " & Err.Description
    WScript.Quit 1
Else
    WScript.Echo "EXTRUDE_OK"
End If

' === 3. direction check: top face at +Y or -Y? ===
Part.ClearSelection2 True
bUp1 = Part.Extension.SelectByID2("", "FACE", 0.035, 0.04, 0.015, False, 0, Nothing, 0)
Part.ClearSelection2 True
bUp2 = Part.Extension.SelectByID2("", "FACE", 0.035, 0.04, -0.015, False, 0, Nothing, 0)
Part.ClearSelection2 True
bDn1 = Part.Extension.SelectByID2("", "FACE", 0.035, -0.04, 0.015, False, 0, Nothing, 0)
Part.ClearSelection2 True
bDn2 = Part.Extension.SelectByID2("", "FACE", 0.035, -0.04, -0.015, False, 0, Nothing, 0)
Part.ClearSelection2 True
WScript.Echo "DIR face@Y+04,Z+15=" & bUp1 & " face@Y+04,Z-15=" & bUp2 & " face@Y-04,Z+15=" & bDn1 & " face@Y-04,Z-15=" & bDn2

' === 4. circular pattern ===
Set f = Part.FirstFeature
Set lastFeat = Nothing
Do While Not f Is Nothing
    Set lastFeat = f
    Set f = f.GetNextFeature
Loop
If lastFeat Is Nothing Then
    WScript.Echo "NO_LAST_FEATURE"
    WScript.Quit 1
End If
WScript.Echo "LAST_FEAT=" & lastFeat.Name

lastFeat.Select2 False, 1
bf = Part.Extension.SelectByID2("", "FACE", 0.06, 0.015, 0, True, 4, Nothing, 0)
WScript.Echo "FACE_MARK4=" & bf

Err.Clear
Set pat3 = featMgr.FeatureCircularPattern3(6, 6.2831853071796, False, "NULL", False, True)
If pat3 Is Nothing Then
    WScript.Echo "PATTERN3_FAIL err=" & Err.Number & " " & Err.Description
    Err.Clear
    Set pat4 = featMgr.FeatureCircularPattern4(6, 6.2831853071796, False, "NULL", False, True)
    If pat4 Is Nothing Then
        WScript.Echo "PATTERN4_FAIL err=" & Err.Number & " " & Err.Description
        Err.Clear
        Set pat5 = featMgr.FeatureCircularPattern5(6, 6.2831853071796, False, "NULL", False, True, False, False, False, False, 0, 0, "NULL", False)
        If pat5 Is Nothing Then
            WScript.Echo "PATTERN5_FAIL err=" & Err.Number & " " & Err.Description
        Else
            WScript.Echo "PATTERN5_OK"
        End If
    Else
        WScript.Echo "PATTERN4_OK"
    End If
Else
    WScript.Echo "PATTERN3_OK"
End If

WScript.Echo "PROBE_DONE"
