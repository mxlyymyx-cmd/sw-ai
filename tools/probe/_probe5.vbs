' Probe 5: sequential 3D sketch semantics + extrude debug
Option Explicit
Dim sw, Part, sk, fm, f, i, n, seg1, seg2

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

WScript.Echo "start: 3D sketches = " & Count3D()

' --- sketch 1 ---
sk.Insert3DSketch True
Part.CreateLine2 0.05, 0, 0, 0.08, 0.01, 0.02
Part.CreateLine2 0.08, 0.01, 0.02, 0.12, 0.02, 0.04
sk.Insert3DSketch True
WScript.Echo "after pair 1: 3D sketches = " & Count3D()

' --- sketch 2 ---
sk.Insert3DSketch True
Part.CreateLine2 0.05, 0.05, 0, 0.08, 0.06, 0.02
Part.CreateLine2 0.08, 0.06, 0.02, 0.12, 0.07, 0.04
sk.Insert3DSketch True
WScript.Echo "after pair 2: 3D sketches = " & Count3D()

' --- sketch 3 (control: third sequential) ---
sk.Insert3DSketch True
Part.CreateLine2 0.05, 0.10, 0, 0.08, 0.11, 0.02
sk.Insert3DSketch True
WScript.Echo "after pair 3: 3D sketches = " & Count3D()

' --- now try loft between sketches 1 and 2 ---
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
WScript.Echo "selected: " & n

Dim loft
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

' --- volute-style 2D extrude on default plane ---
Dim circ, ln1, ln2
sk.InsertSketch True
Set circ = Part.CreateCircle2(0, 0, 0, 0.1, 0, 0)
Set ln1 = Part.CreateLine2(0.105, 0.05, 0, 0.15, 0.1, 0)
Set ln2 = Part.CreateLine2(0.15, 0.1, 0, 0.105, 0.05, 0)
sk.InsertSketch True
WScript.Echo "2D sketch segs: " & TypeName(circ) & "/" & TypeName(ln1) & "/" & TypeName(ln2)

Dim ext
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

Dim tot
tot = 0
Set f = Part.FirstFeature
Do While Not f Is Nothing
  tot = tot + 1
  Set f = f.GetNextFeature
Loop
WScript.Echo "total features: " & tot

On Error Resume Next
sw.CloseDoc Part.GetTitle
On Error Goto 0
WScript.Echo "PROBE5_DONE"
