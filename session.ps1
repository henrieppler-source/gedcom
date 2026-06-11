param(
    [Parameter(Mandatory=$true)]
    [string]$Phrase
)

if (-not $Phrase -and $args.Count -gt 0) {
    $Phrase = $args -join ' '
}

# Arbeiten aus dem Repository-Stamm aus
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Host "Phrase raw: [$Phrase]"
Write-Host "Phrase length: $($Phrase.Length)"
Write-Host "Phrase chars: $([string]::Join(', ', ($Phrase.ToCharArray() | ForEach-Object { [int]$_ })))"

$docPath = Join-Path $repoRoot 'ARBEITSDOKUMENTATION.md'

function Append-Entry {
    param(
        [string]$Status,
        [string]$Text
    )

    $date = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $entry = @(
        "- Datum: $date"
        "- Status: $Status"
        "- Was gemacht wurde:"
        "  - $Text"
        "- Nächste Schritte:"
        "  - ..."
        "- Bemerkung:"
        "  - Automatisch protokolliert durch session.ps1"
        ""
    )
    Add-Content -Path $docPath -Value $entry
}

function Git-CommitPush {
    param(
        [string]$Message
    )

    git add -A
    $commitOutput = git commit -m $Message 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git commit failed: $commitOutput"
    }

    $pushOutput = git push 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git push failed: $pushOutput"
    }
}

function Git-Pull {
    $pullOutput = git pull 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git pull failed: $pullOutput"
    }
    return $pullOutput
}

function Check-GitConfig {
    $name = git config user.name
    $email = git config user.email
    if (-not $name -or -not $email) {
        throw 'Git identity ist nicht konfiguriert. Setze sie mit `git config --global user.name "Name"` und `git config --global user.email "email@example.com"`.'
    }
}

$normalized = $Phrase.ToLower().Trim()
$normalizedKey = $normalized.Replace([string][char]0x00FC, 'ue')
$normalizedKey = $normalizedKey.Replace(([string][char]0x00C3 + [string][char]0x00BC), 'ue')

switch ($normalizedKey) {
    'fertig fuer heute' {
        Append-Entry -Status 'Fertig fuer heute' -Text 'Arbeitsende dokumentiert. Aenderungen werden gepusht.'
        try {
            Check-GitConfig
            Git-CommitPush -Message 'Arbeitsdokumentation: fertig fuer heute'
            Write-Host 'Dokumentation aktualisiert und gepusht.' -ForegroundColor Green
        } catch {
            Write-Error "$($_.Exception.Message)"
        }
        break
    }
    'fertig für heute' {
        Append-Entry -Status 'Fertig für heute' -Text 'Arbeitsende dokumentiert. Änderungen werden gepusht.'
        try {
            Check-GitConfig
            Git-CommitPush -Message 'Arbeitsdokumentation: fertig für heute'
            Write-Host 'Dokumentation aktualisiert und gepusht.' -ForegroundColor Green
        } catch {
            Write-Error "$($_.Exception.Message)"
        }
        break
    }
    'weiter gehts heute' {
        try {
            $pullResult = Git-Pull
            Write-Host $pullResult
            Append-Entry -Status 'Weiter gehts heute' -Text 'Repository aktualisiert und letzter Stand eingelesen.'
            git add ARBEITSDOKUMENTATION.md
            $commitOutput = git commit -m 'Arbeitsdokumentation: weiter gehts heute' 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host $commitOutput
            }
            Write-Host 'Pull ausgeführt und Dokumentation aktualisiert.' -ForegroundColor Green
        } catch {
            Write-Error "$($_.Exception.Message)"
        }
        break
    }
    default {
        Write-Host 'Ungültige Phrase. Verwende:' -ForegroundColor Yellow
        Write-Host '  .\session.ps1 -Phrase "fertig für heute"' -ForegroundColor Cyan
        Write-Host '  .\session.ps1 -Phrase "weiter gehts heute"' -ForegroundColor Cyan
        break
    }
}
