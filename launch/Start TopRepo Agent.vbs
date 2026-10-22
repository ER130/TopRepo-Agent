Dim shell, fso, dir, exitCode
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)

' Wait for the result (True) instead of firing-and-forgetting, so a
' failure can be reported -- without this, an error hit while running
' hidden had no way to reach the user at all.
exitCode = shell.Run("cmd /c """ & dir & "\start_webui.bat""", 0, True)
If exitCode <> 0 Then
    MsgBox "TopRepo Agent didn't start (exit code " & exitCode & ")." & vbCrLf & vbCrLf & _
        "Open Command Prompt, cd into this launch folder, and run start_webui.bat " & _
        "directly to see the actual error.", vbExclamation, "TopRepo Agent"
End If
