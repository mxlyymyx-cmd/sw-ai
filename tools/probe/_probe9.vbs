' Probe 9: FINAL recipes — volute multi-loop first-sketch extrude + impeller revolve+blade extrude
Option Explicit
Dim sw, Part, sk, fm, f, ext, rev, seg, axisSeg, i, pi
pi = 4 * Atn(1)
Set sw = GetObject(, "SldWorks.Application")

' ============ Doc 1: volute mini ============
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
Set ext = fm.FeatureExtrusion3(True, False, False, 6, 0, 0.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
If Err.Number <> 0 Then
  WScript.Echo "VOLUTE EXTRUDE: ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "VOLUTE EXTRUDE: " & TypeName(ext)
End If
On Error Goto 0
On Error Resume Next
sw.CloseDoc Part.GetTitle
On Error Goto 0

' ============ Doc 2: impeller mini (disk revolve + blade extrude) ============
Set Part = sw.NewPart()
Set sk = Part.SketchManager
Set fm = Part.FeatureManager

' --- rear disk: first sketch on default Front plane ---
sk.InsertSketch True
Part.CreateLine2 0.0, -0.02, 0, 0.05, -0.02, 0
Part.CreateLine2 0.05, -0.02, 0, 0.05, 0.0, 0
Part.CreateLine2 0.05, 0.0, 0, 0.15, 0.005, 0
Part.CreateLine2 0.15, 0.005, 0, 0.15, -0.02, 0
Part.CreateLine2 0.15, -0.02, 0, 0.0, -0.02, 0
Set axisSeg = Part.CreateLine2(0, 0.01, 0, 0, -0.03, 0)
axisSeg.ConstructionGeometry = True
sk.InsertSketch True
Part.ClearSelection2 True
axisSeg.Select2 True, 1

On Error Resume Next
Err.Clear
Set rev = fm.FeatureRevolve(6.2831853071796, False, 0, 0, 0, True, True, True)
If Err.Number <> 0 Then
  WScript.Echo "DISK REVOLVE: ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "DISK REVOLVE: " & TypeName(rev)
End If
On Error Goto 0

' --- blade: Top plane (tree idx 2) closed contour, midplane extrude ---
Dim feat0, idx
Set feat0 = Part.FirstFeature
idx = 0
Do While Not feat0 Is Nothing
  If feat0.GetTypeName2 = "RefPlane" Then
    idx = idx + 1
    If idx = 2 Then Exit Do
  End If
  Set feat0 = feat0.GetNextFeature
Loop
If feat0 Is Nothing Then
  WScript.Echo "no plane found"
Else
  feat0.Select2 False, 0
  sk.InsertSketch True
  ' thin curved blade contour (open polyline + offset return path)
  Part.CreateLine2 0.06, 0.00, 0, 0.09, 0.01, 0
  Part.CreateLine2 0.09, 0.01, 0, 0.12, 0.02, 0
  Part.CreateLine2 0.12, 0.02, 0, 0.14, 0.03, 0
  Part.CreateLine2 0.14, 0.03, 0, 0.14, 0.04, 0
  Part.CreateLine2 0.14, 0.04, 0, 0.12, 0.03, 0
  Part.CreateLine2 0.12, 0.03, 0, 0.09, 0.02, 0
  Part.CreateLine2 0.09, 0.02, 0, 0.06, 0.01, 0
  Part.CreateLine2 0.06, 0.01, 0, 0.06, 0.00, 0
  sk.InsertSketch True
  On Error Resume Next
  Err.Clear
  Set ext = fm.FeatureExtrusion3(True, False, False, 6, 0, 0.04, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
  If Err.Number <> 0 Then
    WScript.Echo "BLADE EXTRUDE: ERR " & Err.Number & " " & Err.Description
    Err.Clear
  Else
    WScript.Echo "BLADE EXTRUDE: " & TypeName(ext)
  End If
  On Error Goto 0
End If

On Error Resume Next
sw.CloseDoc Part.GetTitle
On Error Goto 0
WScript.Echo "PROBE9_DONE"
