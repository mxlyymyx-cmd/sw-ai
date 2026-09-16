' Probe 7: reliable sequential 3D sketches (ClearSelection2-before-open hypothesis)
Option Explicit
Dim sw, Part, sk, fm, seg, loft, f, n

Function Count3D()
  Dim c, ff
  c = 0
  Set ff = Part.FirstFeature
  Do While Not ff Is Nothing
    If ff.GetTypeName2 = "3DProfileFeature" Then c = c + 1
    Set ff = ff.GetNextFeature
  Loop
  Count3D = c
End Function

Set sw = GetObject(, "SldWorks.Application")
Set Part = sw.NewPart()
Set sk = Part.SketchManager
Set fm = Part.FeatureManager

' ---- pair 1 (baseline, no clear) ----
sk.Insert3DSketch True
Set seg = Part.CreateLine2(0.05, 0, 0, 0.08, 0.01, 0.02)
sk.Insert3DSketch True
WScript.Echo "pair1 (no clear): count = " & Count3D()

' ---- pair 2 (WITH ClearSelection2 before open) ----
Part.ClearSelection2 True
sk.Insert3DSketch True
Set seg = Part.CreateLine2(0.05, 0.05, 0, 0.08, 0.06, 0.02)
sk.Insert3DSketch True
WScript.Echo "pair2 (clear): count = " & Count3D()

' ---- pair 3 (WITH ClearSelection2 before open) ----
Part.ClearSelection2 True
sk.Insert3DSketch True
Set seg = Part.CreateLine2(0.05, 0.10, 0, 0.08, 0.11, 0.02)
sk.Insert3DSketch True
WScript.Echo "pair3 (clear): count = " & Count3D()

' ---- pair 4 (WITH ClearSelection2 before open) ----
Part.ClearSelection2 True
sk.Insert3DSketch True
Set seg = Part.CreateLine2(0.05, 0.15, 0, 0.08, 0.16, 0.02)
sk.Insert3DSketch True
WScript.Echo "pair4 (clear): count = " & Count3D()

' ---- loft between all 4 (thin body) ----
Part.ClearSelection2 True
n = 0
Set f = Part.FirstFeature
Do While Not f Is Nothing
  If f.GetTypeName2 = "3DProfileFeature" Then
    f.Select2 True, 1
    n = n + 1
  End If
  Set f = f.GetNextFeature
Loop
WScript.Echo "selected " & n & " sketches"

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

On Error Resume Next
sw.CloseDoc Part.GetTitle
On Error Goto 0
WScript.Echo "PROBE7_DONE"
