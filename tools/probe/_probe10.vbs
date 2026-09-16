' Probe 10: isolate volute multi-loop extrude failure + fixed disk revolve
Option Explicit
Dim sw, Part, sk, fm, ext, rev, seg, axisSeg, i, pi
pi = 4 * Atn(1)
Set sw = GetObject(, "SldWorks.Application")

' ============ W1: volute sketch (circle + closed spiral), BLIND extrude ============
Set Part = sw.NewPart()
Set sk = Part.SketchManager
Set fm = Part.FeatureManager
Dim vsp(15), th, R, sx, sy, ex, ey
sk.InsertSketch True
Part.CreateCircle2 0, 0, 0, 0.1, 0, 0
For i = 0 To 7
  th = (25 + i * (360 / 7)) * pi / 180
  R = 0.105 + i * (0.095 / 7)
  vsp(i * 2) = R * Cos(th)
  vsp(i * 2 + 1) = R * Sin(th)
  If i = 0 Then
    sx = vsp(0)
    sy = vsp(1)
  End If
  If i = 7 Then
    ex = vsp(14)
    ey = vsp(15)
  End If
Next
For i = 0 To 6
  Part.CreateLine2 vsp(i * 2), vsp(i * 2 + 1), 0, vsp(i * 2 + 2), vsp(i * 2 + 3), 0
Next
Part.CreateLine2 ex, ey, 0, sx, sy, 0
sk.InsertSketch True
On Error Resume Next
Err.Clear
Set ext = fm.FeatureExtrusion3(True, False, False, 0, 0, 0.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
If Err.Number <> 0 Then
  WScript.Echo "W1 BLIND: ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "W1 BLIND: " & TypeName(ext)
End If
On Error Goto 0
On Error Resume Next
sw.CloseDoc Part.GetTitle
On Error Goto 0

' ============ W3: circle + separate triangle (multi-loop baseline) ============
Set Part = sw.NewPart()
Set sk = Part.SketchManager
Set fm = Part.FeatureManager
sk.InsertSketch True
Part.CreateCircle2 0, 0, 0, 0.1, 0, 0
Part.CreateLine2 0.3, 0, 0, 0.4, 0.1, 0
Part.CreateLine2 0.4, 0.1, 0, 0.4, -0.1, 0
Part.CreateLine2 0.4, -0.1, 0, 0.3, 0, 0
sk.InsertSketch True
On Error Resume Next
Err.Clear
Set ext = fm.FeatureExtrusion3(True, False, False, 0, 0, 0.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
If Err.Number <> 0 Then
  WScript.Echo "W3 multi-loop: ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "W3 multi-loop: " & TypeName(ext)
End If
On Error Goto 0
On Error Resume Next
sw.CloseDoc Part.GetTitle
On Error Goto 0

' ============ W4: washer (circle + concentric circle) ============
Set Part = sw.NewPart()
Set sk = Part.SketchManager
Set fm = Part.FeatureManager
sk.InsertSketch True
Part.CreateCircle2 0, 0, 0, 0.1, 0, 0
Part.CreateCircle2 0, 0, 0, 0.2, 0, 0
sk.InsertSketch True
On Error Resume Next
Err.Clear
Set ext = fm.FeatureExtrusion3(True, False, False, 0, 0, 0.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
If Err.Number <> 0 Then
  WScript.Echo "W4 washer: ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "W4 washer: " & TypeName(ext)
End If
On Error Goto 0
On Error Resume Next
sw.CloseDoc Part.GetTitle
On Error Goto 0

' ============ D1: FIXED disk profile + axis revolve ============
Set Part = sw.NewPart()
Set sk = Part.SketchManager
Set fm = Part.FeatureManager
sk.InsertSketch True
' rectangle: (0,-0.02)->(0.15,-0.02)->(0.15,0.0)->(0,0.0)->close along X=0
Part.CreateLine2 0, -0.02, 0, 0.15, -0.02, 0
Part.CreateLine2 0.15, -0.02, 0, 0.15, 0, 0
Part.CreateLine2 0.15, 0, 0, 0, 0, 0
Part.CreateLine2 0, 0, 0, 0, -0.02, 0
Set axisSeg = Part.CreateLine2(0, 0.01, 0, 0, -0.03, 0)
axisSeg.ConstructionGeometry = True
sk.InsertSketch True
Part.ClearSelection2 True
Dim selR
selR = axisSeg.Select2(True, 1)
WScript.Echo "axis Select2 returned: " & TypeName(selR) & " = " & selR
On Error Resume Next
Err.Clear
Set rev = fm.FeatureRevolve(6.2831853071796, False, 0, 0, 0, True, True, True)
If Err.Number <> 0 Then
  WScript.Echo "D1 REVOLVE: ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "D1 REVOLVE: " & TypeName(rev)
End If
On Error Goto 0
On Error Resume Next
sw.CloseDoc Part.GetTitle
On Error Goto 0
WScript.Echo "PROBE10_DONE"
