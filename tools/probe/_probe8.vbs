' Probe 8: solid loft between closed 3D polyline loops
Option Explicit
Dim sw, Part, sk, fm, seg, loft, f, n, y

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

Sub ClosedLoop(y0)
  ' closed square loop in XZ plane at height y0, side 0.03, center x=0.06
  Part.CreateLine2 0.045, y0, 0, 0.075, y0, 0
  Part.CreateLine2 0.075, y0, 0, 0.075, y0, 0.03
  Part.CreateLine2 0.075, y0, 0.03, 0.045, y0, 0.03
  Part.CreateLine2 0.045, y0, 0.03, 0.045, y0, 0
End Sub

Set sw = GetObject(, "SldWorks.Application")
Set Part = sw.NewPart()
Set sk = Part.SketchManager
Set fm = Part.FeatureManager

For y = 0 To 1
  Part.ClearSelection2 True
  sk.Insert3DSketch True
  ClosedLoop(y * 0.06)
  sk.Insert3DSketch True
Next
WScript.Echo "3D sketches: " & Count3D()

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
WScript.Echo "selected " & n & " closed loops"

On Error Resume Next
Err.Clear
Set loft = fm.InsertProtrusionBlend(False, False, False, 1.0, 0, 0, 0, 0, False, False, False, 0, 0, 0, True, True, True)
If Err.Number <> 0 Then
  WScript.Echo "SOLID LOFT: ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "SOLID LOFT: " & TypeName(loft)
End If
On Error Goto 0

' thin variant on second doc
Dim Part2
Set Part2 = sw.NewPart()
Dim sk2, fm2, f2, n2, loft2
Set sk2 = Part2.SketchManager
Set fm2 = Part2.FeatureManager
For y = 0 To 1
  Part2.ClearSelection2 True
  sk2.Insert3DSketch True
  Part2.CreateLine2 0.045, y * 0.06, 0, 0.075, y * 0.06, 0
  Part2.CreateLine2 0.075, y * 0.06, 0, 0.045, y * 0.06, 0.03
  sk2.Insert3DSketch True
Next
Part2.ClearSelection2 True
n2 = 0
Set f2 = Part2.FirstFeature
Do While Not f2 Is Nothing
  If f2.GetTypeName2 = "3DProfileFeature" Then
    f2.Select2 True, 1
    n2 = n2 + 1
  End If
  Set f2 = f2.GetNextFeature
Loop
WScript.Echo "doc2 selected " & n2 & " open V-loops"

On Error Resume Next
Err.Clear
Set loft2 = fm2.InsertProtrusionBlend(False, False, False, 1.0, 0, 0, 0, 0, False, False, True, 0.003, 0, 0, True, True, True)
If Err.Number <> 0 Then
  WScript.Echo "THIN LOFT(open profiles): ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "THIN LOFT(open profiles): " & TypeName(loft2)
End If
On Error Goto 0

On Error Resume Next
sw.CloseDoc Part.GetTitle
sw.CloseDoc Part2.GetTitle
On Error Goto 0
WScript.Echo "PROBE8_DONE"
