function remove_alias {
    get-command cd
    Remove-Item -Path Alias:cd
    get-command cd
}

. remove_alias