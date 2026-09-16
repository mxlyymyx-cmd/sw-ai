' Probe 3: blade thin-loft + volute dual-loop extrude — real geometry test on live SW
Option Explicit
Dim sw, Part, sk, fm, f, sp(11), vsp(15), spl1, spl2, i, nfeat, loft, ext, circ, ln, pi
pi = 4 * Atn(1)
Set sw = GetObject(, "SldWorks.Application")
Set Part = sw.NewPart()
Set sk = Part.SketchManager
Set fm = Part.FeatureManager

' ================= Section A: blade thin-loft =================
sk.Insert3DSketch True
sp(0)=0.05 : sp(1)=0    : sp(2)=0
sp(3)=0.08 : sp(4)=0.01 : sp(5)=0.02
sp(6)=0.12 : sp(7)=0.02 : sp(8)=0.04
sp(9)=0.15 : sp(10)=0.03 : sp(11)=0.06
Set spl1 = sk.CreateSpline(sp)
sk.Insert3DSketch True

sk.Insert3DSketch True
sp(1)=0.05
sp(4)=0.05
sp(7)=0.05
sp(10)=0.05
Set spl2 = sk.CreateSpline(sp)
sk.Insert3DSketch True

WScript.Echo "splines: " & TypeName(spl1) & " / " & TypeName(spl2)

Set f = Part.FirstFeature
Do While Not f Is Nothing
  WScript.Echo "FEAT: " & f.Name & " | " & f.GetTypeName2
  Set f = f.GetNextFeature
Loop

Part.ClearSelection2 True
nfeat = 0
Set f = Part.FirstFeature
Do While Not f Is Nothing
  If f.GetTypeName2 = "3DProfileFeature" Then
    f.Select2 True, 1
    nfeat = nfeat + 1
  End If
  Set f = f.GetNextFeature
Loop
WScript.Echo "selected " & nfeat & " 3D sketches (mark 1)"

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

' ================= Section B: volute dual-loop extrude =================
Dim th, R, sx, sy, ex, ey
sk.InsertSketch True
' inner circle r=0.1
Set circ = Part.CreateCircle2(0, 0, 0, 0.1, 0, 0)
' spiral: theta 25deg..385deg, R 0.105..0.2 (8 pts)
For i = 0 To 7
  th = (25 + i * (360 / 7)) * pi / 180
  R = 0.105 + i * (0.095 / 7)
  vsp(i * 2) = R * Cos(th)
  vsp(i * 2 + 1) = R * Sin(th)
  If i = 0 Then
    sx = vsp(0) : sy = vsp(1)
  End If
  If i = 7 Then
    ex = vsp(14) : ey = vsp(15)
  End If
Next
Dim vspl
Set vspl = sk.CreateSpline(vsp)
Set ln = Part.CreateLine2(ex, ey, 0, sx, sy, 0)
sk.InsertSketch True
WScript.Echo "volute sketch: " & TypeName(vspl) & " / " & TypeName(ln) & " / " & TypeName(circ)

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
WScript.Echo "PROBE3_DONE"
