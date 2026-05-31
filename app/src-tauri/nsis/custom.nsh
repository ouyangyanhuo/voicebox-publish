!macro NSIS_HOOK_PREUNINSTALL
  ; ── Remove all runtime data directories ──
  RMDir /r "$INSTDIR\data"
  RMDir /r "$INSTDIR\cache"
  RMDir /r "$INSTDIR\model"
  RMDir /r "$INSTDIR\logs"
  RMDir /r "$INSTDIR\preset-voices"

  ; ── Clean up registry entries ──
  ; Install location
  DeleteRegKey SHCTX "${MANUPRODUCTKEY}"
  DeleteRegKey /ifempty SHCTX "${MANUKEY}"

  ; Autostart entry
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${PRODUCTNAME}"

  ; Installer language
  DeleteRegValue HKCU "${MANUPRODUCTKEY}" "Installer Language"
  DeleteRegKey /ifempty HKCU "${MANUPRODUCTKEY}"
  DeleteRegKey /ifempty HKCU "${MANUKEY}"

  ; Windows Start Menu / Taskbar backup entries
  ; Enumerate values under StartPage, remove any whose name starts with
  ; "ListOfEventDrivenBackedUpApps" AND whose data contains our product name.
  StrCpy $0 0
  backup_loop:
    EnumRegValue $1 HKCU "Software\Microsoft\Windows\CurrentVersion\StartPage" $0
    StrCmp $1 "" backup_done
    ; Only process values whose name starts with "ListOfEventDrivenBackedUpApps"
    StrCpy $2 $1 28
    StrCmp $2 "ListOfEventDrivenBackedUpApps" 0 backup_next
    ; Read the value data and check if it mentions our app
    ReadRegStr $3 HKCU "Software\Microsoft\Windows\CurrentVersion\StartPage" $1
    ; Simple substring search: use System::Call to strstr()
    System::Call 'msvcrt::strstr(t r3, t "${PRODUCTNAME}") t .r4'
    StrCmp $4 "" backup_next
    ; Found — delete the value; do NOT increment index (next value shifts down)
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\StartPage" $1
    Goto backup_loop
  backup_next:
    IntOp $0 $0 + 1
    Goto backup_loop
  backup_done:
!macroend
