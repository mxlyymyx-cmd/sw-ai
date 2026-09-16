' Probe V1: volute single-loop spiral extrude (BLIND + MidPlane) + cavity cut
' Self-launching: attaches to running SW or creates a new instance
Option Explicit
Dim sw, Part, sk, fm, ext, cut, f, i, pi, created
pi = 4 * Atn(1)
created = False

On Error Resume Next
Set sw = GetObject(, "SldWorks.Application")
If Err.Number <> 0 Then
  Err.Clear
  Set sw = CreateObject("SldWorks.Application")
  If Err.Number <> 0 Then
    WScript.Echo "FATAL: " & Err.Description
    WScript.Quit 1
  End If
  created = True
  WScript.Echo "SW CREATED"
Else
  WScript.Echo "SW ATTACHED"
End If
On Error Goto 0
If created Then sw.Visible = False

Sub TryVolute(tag, midplane)
  Dim P2, s, k, th, R, px, py, prevx, prevy, sx, sy, exx, eyy, idx
  Set P2 = sw.NewPart()
  Set s = P2.SketchManager
  Dim fm2
  Set fm2 = P2.FeatureManager

  ' 72-point spiral: R2=0.2, A=0.1, theta_start=25deg
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

  Dim extF
  On Error Resume Next
  Err.Clear
  If midplane Then
    Set extF = fm2.FeatureExtrusion3(True, False, False, 6, 0, 0.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
  Else
    Set extF = fm2.FeatureExtrusion3(True, False, False, 0, 0, 0.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
  End If
  If Err.Number <> 0 Then
    WScript.Echo tag & " EXTRUDE: ERR " & Err.Number & " " & Err.Description
    Err.Clear
  Else
    WScript.Echo tag & " EXTRUDE: " & TypeName(extF)
  End If
  On Error Goto 0

  If TypeName(extF) = "Object" Then
    ' cavity cut: first RefPlane, circle R2=0.2, through-all
    Dim f0
    Set f0 = P2.FirstFeature
    idx = 0
    Do While Not f0 Is Nothing
      If f0.GetTypeName2 = "RefPlane" Then
        idx = idx + 1
        If idx = 1 Then Exit Do
      End If
      Set f0 = f0.GetNextFeature
    Loop
    If f0 Is Nothing Then
      WScript.Echo tag & " CUT: no plane"
    Else
      f0.Select2 False, 0
      s.InsertSketch True
      P2.CreateCircle2 0, 0, 0, 0.2, 0, 0
      s.InsertSketch True
      Dim cutF
      On Error Resume Next
      Err.Clear
      Set cutF = fm2.FeatureCut3(True, False, False, 1, 1, 0, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False)
      If Err.Number <> 0 Then
        WScript.Echo tag & " CUT: ERR " & Err.Number & " " & Err.Description
        Err.Clear
      Else
        WScript.Echo tag & " CUT: " & TypeName(cutF)
      End If
      On Error Goto 0
    End If
  End If

  On Error Resume Next
  sw.CloseDoc P2.GetTitle
  On Error Goto 0
End Sub

TryVolute "V1a(BLIND)", False
TryVolute "V1b(MIDPLANE)", True

If created Then
  On Error Resume Next
  sw.ExitApp
  On Error Goto 0
End If
WScript.Echo "PROBEV1_DONE"
