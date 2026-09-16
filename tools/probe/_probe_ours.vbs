Option Explicit
On Error Resume Next
Dim sw, obj
Set sw = GetObject(, "SldWorks.Application")
If Err.Number <> 0 Then
  WScript.Echo "SW_ATTACH_FAILED: " & Err.Description
  WScript.Quit 1
End If
Err.Clear
WScript.Echo "SW revision: " & sw.RevisionNumber()

Set obj = sw.GetAddInObject("SWAI.Addin")
If obj Is Nothing Then
  WScript.Echo "GetAddInObject(SWAI.Addin) = NULL"
Else
  WScript.Echo "GetAddInObject(SWAI.Addin) = OK !!!"
End If
Err.Clear
Set obj = Nothing

Set obj = sw.GetAddInObject("SWAI.SWAIAddin")
If obj Is Nothing Then
  WScript.Echo "GetAddInObject(SWAI.SWAIAddin) = NULL"
Else
  WScript.Echo "GetAddInObject(SWAI.SWAIAddin) = OK !!!"
End If
Err.Clear
Set obj = Nothing
