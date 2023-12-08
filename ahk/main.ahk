
getInput(prompt, validation, &value) {
    
    if (A_Clipboard != "") {
        found := RegExMatch(A_Clipboard, validation, &Result)
        if found {
            value := Result[1]
            return 1
        }
    } 
    
    res := InputBox("Value", prompt)
    if res.Result == "Cancel" {
        return 0
    }

    found := RegExMatch(res.Value, validation, &Result)
    if found {
        value := Result[1]
        return 1
    } else {
        MsgBox "entered value fails validation", "Error", "iconx"
    }

    return 0
}

;
; Opens a changeset (identified by its id) in osmcha, either from
; the clipboard or by entering it manually
;
OpenChangeset() {

    if !getInput("Enter Changeset Id", "(\d+)", &changesetId) {
        return
    }

    Run "http://osmcha.org/changesets/" changesetId
}

;
; Make an active JOSM session jump to specified coords, getting
; them either from the clipboard or by entering them manually
; Format of the coords needs to be one of:  
; lat, lon
; lat lon 
; lat/lon
;
JumpToCoordsInJosm() {

    if !getInput("Enter Coordinates", "([+-]?\d+(?:\.\d+)?)[\/\s,]+([+-]?\d+(?:\.\d+)?)", &out) {
        return
    }

    if WinExist("Java OpenStreetMap Editor") {
        SetWinDelay 500
        SetKeyDelay 50

        WinActivate

        SendEvent "^j"

        SendEvent "{Tab}" out[1] "{Tab}" out[2] "{Tab}10{Enter}"
    }
        
}

^+#s::JumpToCoordsInJosm() ; This script will be triggered by Ctrl+Shift+Win+S

^+#c::OpenChangeset() ; This script will be triggered by Ctrl+Shift+Win+C
