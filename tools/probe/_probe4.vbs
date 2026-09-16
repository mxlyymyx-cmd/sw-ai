' Probe 4: polyline-based blade loft + volute dual-loop extrude (CreateSpline fails from VBS)
Option Explicit
Dim sw, Part, sk, fm, f, i, nfeat, loft, ext, circ, ln, pi, s
pi = 4 * Atn(1)
Set sw = GetObject(, "SldWorks.Application")
Set Part = sw.NewPart()
Set sk = Part.SketchManager
Set fm = Part.FeatureManager

Dim px(3), pz(3)
px(0)=0.05 : pz(0)=0
px(1)=0.08 : pz(1)=0.02
px(2)=0.12 : pz(2)=0.04
px(3)=0.15 : pz(3)=0.06

' ============ Section A: blade thin-loft via polylines ============
Dim h, seg
For h = 0 To 1
  sk.Insert3DSketch True
  For i = 0 To 2
    Part.CreateLine2 px(i), h * 0.05, pz(i), px(i + 1), h * 0.05, pz(i + 1)
  Next
  sk.Insert3DSketch True
Next

nfeat = 0
Part.ClearSelection2 True
Set f = Part.FirstFeature
Do While Not f Is Nothing
  If f.GetTypeName2 = "3DProfileFeature" Then
    f.Select2 True, 1
    nfeat = nfeat + 1
  End If
  Set f = f.GetNextFeature
Loop
WScript.Echo "selected " & nfeat & " 3D sketch features (mark 1)"

On Error Resume Next
Err.Clear
Set loft = fm.InsertProtrusionBlend(False, False, False, 1.0, 0, 0, 0, 0, False, False, True, 0.003, 0, 0, True, True, True)
If Err.Number <> 0 Then
  WScript.Echo "LOFT: ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "LOFT: " & TypeName(loft)
End If
On Error Goto 0

' ============ Section B: volute dual-loop extrude via polyline spiral ============
Dim vsp(15), th, R, sx, sy, ex, ey, nseg
sk.InsertSketch True
Set circ = Part.CreateCircle2(0, 0, 0, 0.1, 0, 0)
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
nseg = 0
For i = 0 To 6
  Part.CreateLine2 vsp(i * 2), vsp(i * 2 + 1), 0, vsp(i * 2 + 2), vsp(i * 2 + 3), 0
  nseg = nseg + 1
Next
Set ln = Part.CreateLine2(ex, ey, 0, sx, sy, 0)
sk.InsertSketch True
WScript.Echo "volute polyline: " & nseg & " segments, closing line = " & TypeName(ln)

On Error Resume Next
Err.Clear
Set ext = fm.FeatureExtrusion3(True, False, False, 0, 0, 0.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
If Err.Number <> 0 Then
  WScript.Echo "EXTRUDE: ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "EXTRUDE: " & TypeName(ext)
End If
On Error Goto 0

Dim n3
n3 = 0
Set f = Part.FirstFeature
Do While Not f Is Nothing
  n3 = n3 + 1
  Set f = f.GetNextFeature
Loop
WScript.Echo "total features now: " & n3

On Error Resume Next
sw.CloseDoc Part.GetTitle
On Error Goto 0
WScript.Echo "PROBE4_DONE"
