' Probe 6: extrude prerequisites + 3D sketch sequencing
Option Explicit
Dim sw, Part, sk, fm, f, i, n, seg, ext

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

Sub ListFeatTypes()
  Dim ff
  Set ff = Part.FirstFeature
  Do While Not ff Is Nothing
    If ff.GetTypeName2 <> "FavoriteFolder" And ff.GetTypeName2 <> "HistoryFolder" _
      And ff.GetTypeName2 <> "SelectionSetFolder" And ff.GetTypeName2 <> "SensorFolder" _
      And ff.GetTypeName2 <> "DocsFolder" And ff.GetTypeName2 <> "DetailCabinet" _
      And ff.GetTypeName2 <> "InkMarkupFolder" And ff.GetTypeName2 <> "EnvFolder" _
      And ff.GetTypeName2 <> "SolidBodyFolder" And ff.GetTypeName2 <> "SurfaceBodyFolder" _
      And ff.GetTypeName2 <> "CommentsFolder" And ff.GetTypeName2 <> "EqnFolder" _
      And ff.GetTypeName2 <> "MaterialFolder" And ff.GetTypeName2 <> "ConfigTableFolder" Then
      WScript.Echo "  [feat] " & ff.Name & " (" & ff.GetTypeName2 & ")"
    End If
    Set ff = ff.GetNextFeature
  Loop
End Sub

Set sw = GetObject(, "SldWorks.Application")
Set Part = sw.NewPart()
Set sk = Part.SketchManager
Set fm = Part.FeatureManager

' ---- A: FIRST sketch = 2D circle on default plane, no selection, extrude ----
sk.InsertSketch True
Part.CreateCircle2 0, 0, 0, 0.1, 0, 0
sk.InsertSketch True
On Error Resume Next
Err.Clear
Set ext = fm.FeatureExtrusion3(True, False, False, 0, 0, 0.05, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
If Err.Number <> 0 Then
  WScript.Echo "A EXTRUDE(first sketch, circle): ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "A EXTRUDE(first sketch, circle): " & TypeName(ext)
End If
On Error Goto 0

' ---- B: sequential 3D sketch pairs, echo each line's TypeName ----
WScript.Echo "--- B: 3D pairs ---"
sk.Insert3DSketch True
Set seg = Part.CreateLine2(0.05, 0, 0, 0.08, 0.01, 0.02)
WScript.Echo "  B1 line: " & TypeName(seg)
sk.Insert3DSketch True
WScript.Echo "  after B1: 3D count = " & Count3D()

sk.Insert3DSketch True
Set seg = Part.CreateLine2(0.05, 0.05, 0, 0.08, 0.06, 0.02)
WScript.Echo "  B2 line: " & TypeName(seg)
sk.Insert3DSketch True
WScript.Echo "  after B2: 3D count = " & Count3D()

sk.Insert3DSketch True
Set seg = Part.CreateLine2(0.05, 0.10, 0, 0.08, 0.11, 0.02)
WScript.Echo "  B3 line: " & TypeName(seg)
sk.Insert3DSketch True
WScript.Echo "  after B3: 3D count = " & Count3D()
ListFeatTypes

' ---- C: 2D circle AFTER 3D work, no plane selection, extrude ----
sk.InsertSketch True
Part.CreateCircle2 0.3, 0, 0, 0.4, 0, 0
sk.InsertSketch True
On Error Resume Next
Err.Clear
Set ext = fm.FeatureExtrusion3(True, False, False, 0, 0, 0.05, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
If Err.Number <> 0 Then
  WScript.Echo "C EXTRUDE(after 3D, circle): ERR " & Err.Number & " " & Err.Description
  Err.Clear
Else
  WScript.Echo "C EXTRUDE(after 3D, circle): " & TypeName(ext)
End If
On Error Goto 0

' ---- D: 2D circle with EXPLICIT plane selection (tree idx 2), extrude ----
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
  WScript.Echo "D: no plane found"
Else
  feat0.Select2 False, 0
  sk.InsertSketch True
  Part.CreateCircle2 0.5, 0, 0, 0.6, 0, 0
  sk.InsertSketch True
  On Error Resume Next
  Err.Clear
  Set ext = fm.FeatureExtrusion3(True, False, False, 0, 0, 0.05, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
  If Err.Number <> 0 Then
    WScript.Echo "D EXTRUDE(plane-selected, circle): ERR " & Err.Number & " " & Err.Description
    Err.Clear
  Else
    WScript.Echo "D EXTRUDE(plane-selected, circle): " & TypeName(ext)
  End If
  On Error Goto 0
End If

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
WScript.Echo "PROBE6_DONE"
