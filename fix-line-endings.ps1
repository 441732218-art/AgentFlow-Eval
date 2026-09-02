$files = git diff --cached --name-only

foreach ($file in $files) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw

        # Remove UTF-8 BOM
        $content = $content -replace "^\uFEFF", ""

        # Convert CRLF -> LF
        $content = $content -replace "`r`n", "`n"

        # Remove trailing whitespace
        $lines = $content -split "`n" | ForEach-Object {
            $_.TrimEnd()
        }

        $content = ($lines -join "`n")

        [System.IO.File]::WriteAllText(
            $file,
            $content,
            New-Object System.Text.UTF8Encoding($false)
        )
    }
}