' Probe V2: cavity cut variations (no-tangency, Dir flip, both-end)
Option Explicit
Dim sw, i, pi
pi = 4 * Atn(1)

On Error Resume Next
Set sw = GetObject(, "SldWorks.Application")
If Err.Number <> 0 Then
  Err.Clear
  WScript.Echo "FATAL: no SW"
  WScript.Quit 1
End If
On Error Goto 0

Sub TryVolute(tag, cavityR, dirFlip)
  Dim P2, s, fm2, extF, cutF, f0, idx, th, R, px, py, prevx, prevy, sx, sy, exx, eyy
  Set P2 = sw.NewPart()
  Set s = P2.SketchManager
  Set fm2 = P2.FeatureManager

  s.InsertSketch True
  prevx = 0 : prevy = 0
  For i = 0 To 71
    th = (25 + i * (360 / 71)) * pi / 180
    R = 0.2 + 0.1 * (i / 71)
    px = R * Cos(th)
    py = R * Sin(th)
    If i = 0 Then
      sx = px
      sy = py
    End If
    If i = 71 Then
      exx = px
      eyy = py
    End If
    If i > 0 Then
      P2.CreateLine2 prevx, prevy, 0, px, py, 0
    End If
    prevx = px
    prevy = py
  Next
  P2.CreateLine2 exx, eyy, 0, sx, sy, 0
  s.InsertSketch True

  On Error Resume Next
  Err.Clear
  Set extF = fm2.FeatureExtrusion3(True, False, False, 6, 0, 0.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
  If Err.Number <> 0 Then
    WScript.Echo tag & " EXTRUDE: ERR " & Err.Number
    Err.Clear
    extF = Empty
  End If
  On Error Goto 0
  WScript.Echo tag & " EXTRUDE: " & TypeName(extF)

  ' cavity cut on first plane
  Set f0 = P2.FirstFeature
  idx = 0
  Do While Not f0 Is Nothing
    If f0.GetTypeName2 = "RefPlane" Then
      idx = idx + 1
      If idx = 1 Then Exit Do
    End If
    Set f0 = f0.GetNextFeature
  Loop
  f0.Select2 False, 0
  s.InsertSketch True
  P2.CreateCircle2 0, 0, 0, cavityR, 0, 0
  s.InsertSketch True
  On Error Resume Next
  Err.Clear
  Set cutF = fm2.FeatureCut3(True, False, dirFlip, 1, 1, 0, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False)
  If Err.Number <> 0 Then
    WScript.Echo tag & " CUT(r=" & cavityR & ", dir=" & dirFlip & "): ERR " & Err.Number & " " & Err.Description
    Err.Clear
  Else
    WScript.Echo tag & " CUT(r=" & cavityR & ", dir=" & dirFlip & "): " & TypeName(cutF)
  End If
  On Error Goto 0

  On Error Resume Next
  sw.CloseDoc P2.GetTitle
  On Error Goto 0
End Sub

TryVolute "V2a", 0.19, False
TryVolute "V2b", 0.2, True
TryVolute "V2c", 0.19, True
WScript.Echo "PROBEV2_DONE"
